"""
Student management endpoints (Registration, Retrieval, Update, Deletion, Photo Addition).
All enrollment, update, and deletion operations require administrator authentication.
"""

from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    status
)
from sqlalchemy import select, func

from app.schemas.student import (
    StudentResponse,
    StudentListResponse,
    StudentUpdate,
    FaceEmbeddingResponse,
    MessageResponse
)
from app.models.student import Student
from app.services.student_service import StudentService
from app.api.deps import get_student_service, require_admin, get_db_session

router = APIRouter()

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit


def _validate_image_file(file: UploadFile) -> bytes:
    """Validate image MIME type and read raw bytes safely."""
    if file.content_type and file.content_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file.content_type}'. Allowed types: {list(ALLOWED_MIME_TYPES)}"
        )
    content = file.file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file '{file.filename}' is empty."
        )
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File '{file.filename}' exceeds maximum allowed size of 10 MB."
        )
    return content


@router.post(
    "",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a New Student",
    description="Enroll a student using 1–2 face photographs. Requires admin authentication and explicit biometric consent."
)
def register_student(
    student_id: str = Form(..., description="Unique alphanumeric student ID (e.g. STU-2026-001)"),
    full_name: str = Form(..., description="Full legal name of student"),
    department: Optional[str] = Form(None, description="Academic department or faculty"),
    email: Optional[str] = Form(None, description="Contact email address"),
    phone: Optional[str] = Form(None, description="Contact phone number"),
    consent_given: bool = Form(..., description="Explicit consent for biometric enrollment"),
    category: str = Form("Day Scholar", description="'Day Scholar' or 'Hosteller'"),
    hostel_name: Optional[str] = Form(None, description="Hostel Name if Hosteller"),
    hostel_block: Optional[str] = Form(None, description="Hostel Block if Hosteller"),
    room_number: Optional[str] = Form(None, description="Room Number if Hosteller"),
    photos: List[UploadFile] = File(..., description="1 to 2 face photographs for registration"),
    service: StudentService = Depends(get_student_service),
    _admin: str = Depends(require_admin)
) -> StudentResponse:
    if not consent_given:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Biometric enrollment requires explicit consent ('consent_given' must be true)."
        )

    if not photos or len(photos) < 1 or len(photos) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration requires between 1 and 2 photographs (maximum 5)."
        )

    # Read and validate image byte streams
    image_bytes_list: List[bytes] = []
    for f in photos:
        content = _validate_image_file(f)
        image_bytes_list.append(content)

    try:
        student = service.register_student(
            student_id=student_id,
            full_name=full_name,
            photos=image_bytes_list,
            department=department,
            email=email,
            phone=phone,
            consent_given=consent_given,
            category=category,
            hostel_name=hostel_name,
            hostel_block=hostel_block,
            room_number=room_number
        )
        return StudentResponse.model_validate(student)

    except ValueError as e:
        err_msg = str(e)
        if "already registered" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed due to an internal error: {str(e)}"
        )


@router.get(
    "",
    response_model=StudentListResponse,
    summary="List Registered Students",
    description="Retrieve paginated list of students with optional text search and active status filter. Requires admin authentication."
)
def list_students(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Page size limit"),
    search_query: Optional[str] = Query(None, description="Search by student ID, name, or department"),
    active_only: bool = Query(True, description="Filter for active students only"),
    service: StudentService = Depends(get_student_service),
    db = Depends(get_db_session),
    _admin: str = Depends(require_admin)
) -> StudentListResponse:
    items = service.list_students(
        skip=skip,
        limit=limit,
        search_query=search_query,
        active_only=active_only
    )

    # Count total matching
    count_stmt = select(func.count(Student.id))
    if active_only:
        count_stmt = count_stmt.where(Student.is_active == True)
    total_count = db.scalar(count_stmt) or 0

    return StudentListResponse(
        total=total_count,
        items=[StudentResponse.model_validate(s) for s in items],
        skip=skip,
        limit=limit
    )


@router.get(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Get Student Details",
    description="Retrieve a single student's profile and registered photo references by unique student ID. Requires admin authentication."
)
def get_student(
    student_id: str,
    service: StudentService = Depends(get_student_service),
    _admin: str = Depends(require_admin)
) -> StudentResponse:
    student = service.get_student_by_id(student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID '{student_id}' was not found."
        )
    return StudentResponse.model_validate(student)


@router.put(
    "/{student_id}",
    response_model=StudentResponse,
    summary="Update Student Profile",
    description="Update non-biometric student details. Automatically synchronizes in-memory recognition cache."
)
def update_student(
    student_id: str,
    payload: StudentUpdate,
    service: StudentService = Depends(get_student_service),
    _admin: str = Depends(require_admin)
) -> StudentResponse:
    try:
        updated = service.update_student(
            student_id=student_id,
            full_name=payload.full_name,
            department=payload.department,
            email=payload.email,
            phone=payload.phone,
            is_active=payload.is_active,
            category=payload.category,
            hostel_name=payload.hostel_name,
            hostel_block=payload.hostel_block,
            room_number=payload.room_number
        )
        return StudentResponse.model_validate(updated)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID '{student_id}' was not found."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update student: {str(e)}"
        )


@router.delete(
    "/{student_id}",
    response_model=MessageResponse,
    summary="Delete Student",
    description="Delete a student, cascade-delete all biometric embeddings, remove photos, and evict identity from memory."
)
def delete_student(
    student_id: str,
    service: StudentService = Depends(get_student_service),
    _admin: str = Depends(require_admin)
) -> MessageResponse:
    success = service.delete_student(student_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID '{student_id}' was not found."
        )
    return MessageResponse(
        message=f"Student '{student_id}' and all associated face embeddings were successfully deleted."
    )


@router.post(
    "/{student_id}/photos",
    response_model=FaceEmbeddingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Additional Face Photograph",
    description="Upload an additional photograph for an enrolled student to expand multi-view recognition accuracy."
)
def add_student_photo(
    student_id: str,
    photo: UploadFile = File(..., description="Additional face photograph"),
    is_primary: bool = Form(False, description="Set as primary reference photo"),
    service: StudentService = Depends(get_student_service),
    _admin: str = Depends(require_admin)
) -> FaceEmbeddingResponse:
    content = _validate_image_file(photo)
    try:
        emb_record = service.add_photo_to_student(
            student_id=student_id,
            photo_input=content,
            is_primary=is_primary
        )
        return FaceEmbeddingResponse.model_validate(emb_record)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID '{student_id}' was not found."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record photo embedding: {str(e)}"
        )
