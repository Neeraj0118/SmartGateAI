"""
Student Enrollment and Lifecycle Service for SmartGateAI.
Coordinates:
- Database transactions (SQLAlchemy)
- Face quality checks & embedding extraction (YuNet + SFace)
- Storage of original reference images
- Real-time in-memory vector cache synchronization (VectorMatcher)
"""

from typing import List, Optional, Union, Tuple
import os
import cv2
import numpy as np
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from ..models.student import Student, FaceEmbedding
from .ai.base import FaceEngine
from .ai.vector_matcher import VectorMatcher
from .ai.quality import validate_enrollment_image
from .storage_service import PhotoStorageService


class StudentService:
    """
    Manages student registration, photo additions, updates, and deletion
    with automated real-time in-memory recognition cache updates.
    """

    def __init__(
        self,
        db: Session,
        engine: FaceEngine,
        matcher: VectorMatcher,
        storage: Optional[PhotoStorageService] = None
    ) -> None:
        self.db = db
        self.engine = engine
        self.matcher = matcher
        self.storage = storage or PhotoStorageService()

    def sync_cache_from_db(self) -> int:
        """
        Load all active students and their embeddings from the database into the
        in-memory VectorMatcher cache on system startup.
        Returns the number of active students cached.
        """
        stmt = (
            select(Student)
            .where(Student.is_active == True)
        )
        students = self.db.scalars(stmt).all()
        cached_count = 0

        for student in students:
            if not student.embeddings:
                continue

            person = self.matcher.enroll_person(
                person_id=student.student_id,
                name=student.full_name,
                department=student.department
            )
            # Clear any stale embeddings for this identity in memory
            person.embeddings.clear()

            for emb_record in student.embeddings:
                emb_vec = emb_record.to_numpy()
                person.add_embedding(emb_vec)

            cached_count += 1

        return cached_count

    def _resolve_image(self, photo_input: Union[str, np.ndarray, bytes]) -> np.ndarray:
        """Helper to convert various photo input formats into a valid BGR numpy array."""
        if isinstance(photo_input, np.ndarray):
            if photo_input.size == 0:
                raise ValueError("Provided image array is empty.")
            return photo_input
        elif isinstance(photo_input, str):
            if not os.path.exists(photo_input):
                raise FileNotFoundError(f"Image file does not exist at: {photo_input}")
            img = cv2.imread(photo_input)
            if img is None:
                raise ValueError(f"Could not decode image file from: {photo_input}")
            return img
        elif isinstance(photo_input, bytes):
            nparr = np.frombuffer(photo_input, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image from provided byte stream.")
            return img
        else:
            raise TypeError(f"Unsupported image input type: {type(photo_input)}")

    def _process_single_face_photo(
        self,
        photo_input: Union[str, np.ndarray, bytes],
        min_blur_score: float = 50.0
    ) -> Tuple[np.ndarray, np.ndarray, float]:
        """
        Detect face, validate single clear face, and extract normalized 128-D embedding.
        Returns: (image_bgr, embedding_vector, quality_score)
        """
        img = self._resolve_image(photo_input)
        dets = self.engine.detect_faces(img)

        is_valid, err_msg, quality_score = validate_enrollment_image(
            image=img,
            detections=dets,
            min_face_size=60,
            min_blur_score=min_blur_score,
            min_confidence=0.65
        )

        if not is_valid:
            raise ValueError(f"Enrollment photo quality validation failed: {err_msg}")

        # Canonical alignment using 5 landmarks to 112x112
        crop = self.engine.align_crop(img, dets[0])
        # SFace produces normalized 128-D embedding
        emb = self.engine.extract_embedding(crop)

        return img, emb, quality_score

    def register_student(
        self,
        student_id: str,
        full_name: str,
        photos: List[Union[str, np.ndarray, bytes]],
        department: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        consent_given: bool = True,
        min_blur_score: float = 50.0
    ) -> Student:
        """
        Register a new student using 1–2 face photographs.
        Performs:
        1. Duplicate student ID check.
        2. Image quality and face count validation for each photo.
        3. Extraction of 128-D feature embeddings.
        4. Storage of reference photos on disk.
        5. SQLite persistence of Student and FaceEmbedding entities.
        6. Immediate real-time update of in-memory VectorMatcher recognition registry.
        """
        clean_id = student_id.strip()
        clean_name = full_name.strip()

        if not clean_id:
            raise ValueError("Student ID cannot be empty.")
        if not clean_name:
            raise ValueError("Student name cannot be empty.")
        if not photos or len(photos) == 0:
            raise ValueError("At least 1 face photograph is required for student registration.")

        # Check for existing student ID
        existing = self.db.scalar(select(Student).where(Student.student_id == clean_id))
        if existing:
            raise ValueError(f"Student ID '{clean_id}' is already registered in the system.")

        # Process each photo before touching database
        processed_data: List[Tuple[np.ndarray, np.ndarray, float]] = []
        for idx, photo_item in enumerate(photos):
            try:
                img_bgr, emb_vec, quality = self._process_single_face_photo(
                    photo_item, min_blur_score=min_blur_score
                )
                processed_data.append((img_bgr, emb_vec, quality))
            except Exception as e:
                raise ValueError(f"Photo #{idx + 1} validation failed: {str(e)}")

        # Create Student record
        student = Student(
            student_id=clean_id,
            full_name=clean_name,
            department=department.strip() if department else None,
            email=email.strip() if email else None,
            phone=phone.strip() if phone else None,
            consent_given=consent_given,
            is_active=True
        )
        self.db.add(student)
        self.db.flush()  # Assigns student.id

        saved_photo_filenames: List[str] = []
        extracted_vectors: List[np.ndarray] = []

        try:
            for idx, (img_bgr, emb_vec, quality) in enumerate(processed_data):
                # Save photo to secure storage
                filename = self.storage.save_photo(clean_id, img_bgr)
                saved_photo_filenames.append(filename)

                emb_record = FaceEmbedding.from_numpy(
                    embedding=emb_vec,
                    quality_score=quality,
                    photo_path=filename,
                    is_primary=(idx == 0)
                )
                emb_record.student_id = student.id
                self.db.add(emb_record)
                extracted_vectors.append(emb_vec)

            self.db.commit()
            self.db.refresh(student)

        except Exception as e:
            self.db.rollback()
            # Clean up any photos already written to disk
            for fn in saved_photo_filenames:
                self.storage.delete_photo(fn)
            raise IOError(f"Database error while enrolling student: {str(e)}")

        # CRITICAL: Immediately update the in-memory recognition cache
        # Allows instant recognition through camera stream with ZERO restart or retraining!
        person = self.matcher.enroll_person(
            person_id=student.student_id,
            name=student.full_name,
            department=student.department
        )
        for emb in extracted_vectors:
            person.add_embedding(emb)

        return student

    def add_photo_to_student(
        self,
        student_id: str,
        photo_input: Union[str, np.ndarray, bytes],
        is_primary: bool = False,
        min_blur_score: float = 50.0
    ) -> FaceEmbedding:
        """
        Add an additional face photograph to an existing enrolled student.
        Expands the student's multi-view exemplar set for enhanced recognition.
        """
        student = self.db.scalar(select(Student).where(Student.student_id == student_id))
        if not student:
            raise KeyError(f"Student with ID '{student_id}' does not exist.")

        img_bgr, emb_vec, quality = self._process_single_face_photo(
            photo_input, min_blur_score=min_blur_score
        )

        filename = self.storage.save_photo(student.student_id, img_bgr)

        try:
            emb_record = FaceEmbedding.from_numpy(
                embedding=emb_vec,
                quality_score=quality,
                photo_path=filename,
                is_primary=is_primary
            )
            emb_record.student_id = student.id
            self.db.add(emb_record)
            self.db.commit()
            self.db.refresh(emb_record)
        except Exception as e:
            self.db.rollback()
            self.storage.delete_photo(filename)
            raise IOError(f"Failed to record new photo embedding: {e}")

        # Update in-memory cache immediately
        self.matcher.add_photo_embedding(student.student_id, emb_vec)
        return emb_record

    def get_student_by_id(self, student_id: str) -> Optional[Student]:
        """Retrieve student by unique student ID string."""
        return self.db.scalar(select(Student).where(Student.student_id == student_id))

    def list_students(
        self,
        skip: int = 0,
        limit: int = 100,
        search_query: Optional[str] = None,
        active_only: bool = True
    ) -> List[Student]:
        """List students with pagination and optional search filter."""
        stmt = select(Student)
        if active_only:
            stmt = stmt.where(Student.is_active == True)

        if search_query:
            term = f"%{search_query.strip()}%"
            stmt = stmt.where(
                or_(
                    Student.student_id.ilike(term),
                    Student.full_name.ilike(term),
                    Student.department.ilike(term)
                )
            )

        stmt = stmt.order_by(Student.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def update_student(
        self,
        student_id: str,
        full_name: Optional[str] = None,
        department: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Student:
        """Update student details and synchronize in-memory registry."""
        student = self.get_student_by_id(student_id)
        if not student:
            raise KeyError(f"Student with ID '{student_id}' does not exist.")

        if full_name is not None and full_name.strip():
            student.full_name = full_name.strip()
        if department is not None:
            student.department = department.strip() if department else None
        if email is not None:
            student.email = email.strip() if email else None
        if phone is not None:
            student.phone = phone.strip() if phone else None
        if is_active is not None:
            student.is_active = is_active

        self.db.commit()
        self.db.refresh(student)

        # Update in-memory matcher state
        if not student.is_active:
            # If deactivated, remove from recognition search
            self.matcher.remove_person(student.student_id)
        else:
            # Re-sync identity in matcher
            person = self.matcher.enroll_person(
                student.student_id, student.full_name, student.department
            )
            person.name = student.full_name
            person.department = student.department

        return student

    def delete_student(self, student_id: str) -> bool:
        """
        Delete a student.
        Cascades to delete FaceEmbeddings in SQLite, deletes reference images from disk,
        and removes identity immediately from the in-memory recognition cache.
        """
        student = self.get_student_by_id(student_id)
        if not student:
            return False

        # Gather photo paths before deletion
        photo_paths = [emb.photo_path for emb in student.embeddings if emb.photo_path]

        # Delete database record (SQLite CASCADE deletes embeddings automatically)
        self.db.delete(student)
        self.db.commit()

        # Delete photos on disk
        for path in photo_paths:
            self.storage.delete_photo(path)

        # CRITICAL: Immediately remove from in-memory matcher
        self.matcher.remove_person(student_id)

        return True
