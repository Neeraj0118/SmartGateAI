"""
Pydantic Request & Response DTOs for Students and Embeddings.
Strictly excludes raw embedding vectors to preserve biometric privacy.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FaceEmbeddingResponse(BaseModel):
    """Public face photograph metadata. Excludes raw biometric embedding data."""
    id: int
    photo_path: Optional[str] = Field(None, description="Stored reference image filename or path")
    quality_score: float = Field(..., description="Sharpness / blur metric at enrollment")
    is_primary: bool = Field(False, description="Primary face portrait flag")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentResponse(BaseModel):
    """Complete student entity response excluding biometric vectors."""
    id: int
    student_id: str = Field(..., description="Unique alphanumeric student registration ID")
    full_name: str
    department: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    consent_given: bool = Field(..., description="Explicit biometric enrollment consent")
    is_active: bool
    created_at: datetime
    updated_at: datetime
    embeddings: List[FaceEmbeddingResponse] = Field(
        default_factory=list,
        description="Registered reference photo exemplars"
    )

    model_config = ConfigDict(from_attributes=True)


class StudentUpdate(BaseModel):
    """Payload for updating an existing student."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=120)
    department: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=120)
    phone: Optional[str] = Field(None, max_length=30)
    is_active: Optional[bool] = None


class StudentListResponse(BaseModel):
    """Paginated student listing response."""
    total: int
    items: List[StudentResponse]
    skip: int
    limit: int


class HealthResponse(BaseModel):
    """System health and diagnostic status."""
    status: str
    app_name: str
    version: str
    database_connected: bool
    cached_students_count: int
    models_ready: bool


class MessageResponse(BaseModel):
    """Standard generic operational confirmation response."""
    message: str
    detail: Optional[str] = None
