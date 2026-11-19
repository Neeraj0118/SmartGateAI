"""
Storage service for securely persisting and deleting student enrollment photographs.
"""

import os
import uuid
from typing import Optional, Union
import cv2
import numpy as np


class PhotoStorageService:
    """Manages saving and deleting student enrollment photos on disk."""

    def __init__(self, base_storage_dir: Optional[str] = None) -> None:
        if base_storage_dir is None:
            # Default to backend/storage/student_photos
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            base_storage_dir = os.path.join(backend_dir, "storage", "student_photos")

        self.storage_dir = base_storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def save_photo(
        self,
        student_id: str,
        image: np.ndarray,
        extension: str = ".jpg"
    ) -> str:
        """
        Save an OpenCV image array to disk with a unique, sanitized filename.
        Returns the relative path from the storage directory.
        """
        clean_id = "".join(c for c in student_id if c.isalnum() or c in ("-", "_"))
        unique_token = uuid.uuid4().hex[:10]
        filename = f"{clean_id}_{unique_token}{extension}"
        absolute_path = os.path.join(self.storage_dir, filename)

        success = cv2.imwrite(absolute_path, image)
        if not success:
            raise IOError(f"Failed to write image to disk at: {absolute_path}")

        return filename

    def get_absolute_path(self, filename: str) -> str:
        """Return the absolute path for a saved photo filename."""
        return os.path.join(self.storage_dir, filename)

    def delete_photo(self, filename: Optional[str]) -> bool:
        """Delete a photo file from storage."""
        if not filename:
            return False
        abs_path = os.path.join(self.storage_dir, filename)
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
                return True
            except OSError:
                return False
        return False
