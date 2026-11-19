"""
Multi-embedding vector matcher with unique identity assignment and unknown rejection.
Ensures:
1. Multi-photo representation per person.
2. Cosine similarity matching against all exemplar vectors.
3. No duplicate identity assignment in the same frame.
4. Strict rejection for matches below threshold.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import numpy as np
from .base import FaceEngine, FaceDetectionResult


@dataclass
class EnrolledPerson:
    """Represents a registered person with one or more facial embeddings."""
    person_id: str
    name: str
    department: Optional[str] = None
    embeddings: List[np.ndarray] = field(default_factory=list)

    def add_embedding(self, embedding: np.ndarray) -> None:
        emb = embedding.astype(np.float32).flatten()
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        self.embeddings.append(emb)


@dataclass
class RecognitionResult:
    """Recognition decision for a single face detected in a frame."""
    face_index: int
    bbox: Tuple[int, int, int, int]
    landmarks: np.ndarray
    confidence: float
    assigned_person_id: Optional[str] = None
    assigned_name: str = "Unknown Person"
    similarity_score: float = 0.0
    is_recognised: bool = False
    all_scores: Dict[str, float] = field(default_factory=dict)


class VectorMatcher:
    """
    Manages registered identities, multi-exemplar cosine matching, and
    conflict-free identity assignment.
    """

    def __init__(
        self,
        engine: FaceEngine,
        similarity_threshold: float = 0.637
    ) -> None:
        self.engine = engine
        self.similarity_threshold = similarity_threshold
        self.registry: Dict[str, EnrolledPerson] = {}

    def enroll_person(
        self,
        person_id: str,
        name: str,
        department: Optional[str] = None
    ) -> EnrolledPerson:
        if person_id not in self.registry:
            self.registry[person_id] = EnrolledPerson(
                person_id=person_id,
                name=name,
                department=department
            )
        return self.registry[person_id]

    def add_photo_embedding(self, person_id: str, embedding: np.ndarray) -> None:
        if person_id not in self.registry:
            raise KeyError(f"Person with ID '{person_id}' is not enrolled. Call enroll_person first.")
        self.registry[person_id].add_embedding(embedding)

    def remove_person(self, person_id: str) -> bool:
        if person_id in self.registry:
            del self.registry[person_id]
            return True
        return False

    def get_enrolled_count(self) -> int:
        return len(self.registry)

    def match_single_embedding(
        self,
        query_embedding: np.ndarray
    ) -> Tuple[Optional[str], str, float, Dict[str, float]]:
        """
        Match a single query embedding against all registered identities.
        Returns: (best_person_id, best_name, max_similarity, all_scores)
        """
        if not self.registry:
            return None, "Unknown Person", 0.0, {}

        scores: Dict[str, float] = {}
        best_id: Optional[str] = None
        best_name = "Unknown Person"
        max_sim = -1.0

        for pid, person in self.registry.items():
            if not person.embeddings:
                continue

            # Compare query with each stored exemplar for this person; take maximum similarity
            exemplar_sims = [
                self.engine.compute_similarity(query_embedding, emb)
                for emb in person.embeddings
            ]
            person_score = max(exemplar_sims) if exemplar_sims else -1.0
            scores[pid] = person_score

            if person_score > max_sim:
                max_sim = person_score
                best_id = pid
                best_name = person.name

        if max_sim >= self.similarity_threshold and best_id is not None:
            return best_id, best_name, max_sim, scores
        else:
            return None, "Unknown Person", max(0.0, max_sim), scores

    def recognise_frame_faces(
        self,
        image: np.ndarray,
        detections: List[FaceDetectionResult]
    ) -> List[RecognitionResult]:
        """
        Process multiple detected faces in a single frame simultaneously.
        Enforces unique assignment: an enrolled identity cannot be assigned
        to more than one face in the same frame.
        """
        if not detections:
            return []

        # Step 1: Extract embeddings for each face in the frame
        query_embeddings: List[np.ndarray] = []
        for det in detections:
            crop = self.engine.align_crop(image, det)
            emb = self.engine.extract_embedding(crop)
            query_embeddings.append(emb)

        # Step 2: Build candidate match matrix
        # candidate_matches: list of (similarity, face_idx, person_id, person_name)
        candidate_matches: List[Tuple[float, int, str, str]] = []
        face_all_scores: List[Dict[str, float]] = []

        for face_idx, q_emb in enumerate(query_embeddings):
            scores: Dict[str, float] = {}
            for pid, person in self.registry.items():
                if not person.embeddings:
                    continue
                sims = [
                    self.engine.compute_similarity(q_emb, emb)
                    for emb in person.embeddings
                ]
                p_score = max(sims) if sims else 0.0
                scores[pid] = p_score
                if p_score >= self.similarity_threshold:
                    candidate_matches.append((p_score, face_idx, pid, person.name))
            face_all_scores.append(scores)

        # Step 3: Greedy unique assignment sorted by highest confidence first
        # Ensures that if multiple faces match the same identity, the one with
        # the higher similarity wins, preventing identity cloning.
        candidate_matches.sort(key=lambda x: x[0], reverse=True)

        assigned_faces: Dict[int, Tuple[str, str, float]] = {}
        claimed_identities: set = set()

        for sim, face_idx, pid, name in candidate_matches:
            if face_idx in assigned_faces:
                continue
            if pid in claimed_identities:
                continue

            assigned_faces[face_idx] = (pid, name, sim)
            claimed_identities.add(pid)

        # Step 4: Construct final results for all faces in frame
        results: List[RecognitionResult] = []
        for face_idx, det in enumerate(detections):
            if face_idx in assigned_faces:
                pid, name, sim = assigned_faces[face_idx]
                results.append(
                    RecognitionResult(
                        face_index=face_idx,
                        bbox=det.bbox,
                        landmarks=det.landmarks,
                        confidence=det.confidence,
                        assigned_person_id=pid,
                        assigned_name=name,
                        similarity_score=sim,
                        is_recognised=True,
                        all_scores=face_all_scores[face_idx]
                    )
                )
            else:
                # Find maximum score among candidates (even if rejected)
                best_sub_score = max(face_all_scores[face_idx].values()) if face_all_scores[face_idx] else 0.0
                results.append(
                    RecognitionResult(
                        face_index=face_idx,
                        bbox=det.bbox,
                        landmarks=det.landmarks,
                        confidence=det.confidence,
                        assigned_person_id=None,
                        assigned_name="Unknown Person",
                        similarity_score=max(0.0, best_sub_score),
                        is_recognised=False,
                        all_scores=face_all_scores[face_idx]
                    )
                )

        return results
