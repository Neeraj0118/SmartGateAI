"""
SQLAlchemy ORM models for Students and Face Embeddings.
Supports:
- Unique student IDs with database-enforced integrity.
- Multiple face embeddings per student (one-to-many relationship).
- Binary BLOB storage of 128-D float32 normalized vectors.
- Automated cascade deletion of embeddings when a student is deleted.
"""

from datetime import datetime
from typing import List, Optional
import numpy as np
from sqlalchemy import (
    Integer,
    String,
    Boolean,
    Float,
    DateTime,
    LargeBinary,
    ForeignKey,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base


class Student(Base):
    """Registered Student / Person entity."""
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 1-to-many relationship with cascade delete
    embeddings: Mapped[List["FaceEmbedding"]] = relationship(
        "FaceEmbedding",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="FaceEmbedding.created_at"
    )

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, student_id='{self.student_id}', name='{self.full_name}', active={self.is_active})>"


class FaceEmbedding(Base):
    """
    Individual face embedding exemplar linked to a student.
    Stores the 128-dimensional normalized float32 vector in raw binary format (512 bytes).
    """
    __tablename__ = "face_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    embedding_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, default=128, nullable=False)
    photo_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationship back to student
    student: Mapped["Student"] = relationship("Student", back_populates="embeddings")

    def to_numpy(self) -> np.ndarray:
        """Deserialize binary BLOB back into float32 1D numpy array."""
        arr = np.frombuffer(self.embedding_data, dtype=np.float32)
        if arr.shape[0] != self.embedding_dim:
            raise ValueError(
                f"Corrupt embedding data: expected {self.embedding_dim} floats, got {arr.shape[0]}"
            )
        return arr

    def set_numpy(self, embedding: np.ndarray) -> None:
        """Serialize float32 1D numpy array into binary BLOB."""
        flat = embedding.astype(np.float32).flatten()
        self.embedding_dim = int(flat.shape[0])
        self.embedding_data = flat.tobytes()

    @classmethod
    def from_numpy(
        cls,
        embedding: np.ndarray,
        quality_score: float,
        photo_path: Optional[str] = None,
        is_primary: bool = False
    ) -> "FaceEmbedding":
        """Factory constructor from numpy embedding array."""
        flat = embedding.astype(np.float32).flatten()
        return cls(
            embedding_data=flat.tobytes(),
            embedding_dim=int(flat.shape[0]),
            quality_score=float(quality_score),
            photo_path=photo_path,
            is_primary=is_primary
        )

    def __repr__(self) -> str:
        return f"<FaceEmbedding(id={self.id}, student_id={self.student_id}, dim={self.embedding_dim}, quality={self.quality_score:.1f})>"
