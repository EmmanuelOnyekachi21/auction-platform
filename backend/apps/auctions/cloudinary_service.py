"""Cloudinary image upload and management service."""

import logging

import cloudinary
import cloudinary.uploader
from fastapi import UploadFile

from common.exceptions import ValidationException
from config.settings import settings

logger = logging.getLogger(__name__)

# Allowed image MIME types
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes


class CloudinaryService:
    """Service for uploading and managing images on Cloudinary.

    Handles image validation, upload, and deletion operations.
    """

    def __init__(self):
        """Initialize Cloudinary configuration."""
        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True,
        )

    async def upload_image(
        self, file: UploadFile, folder: str = "auction_items"
    ) -> dict:
        """Upload image to Cloudinary.

        Args:
            file: Uploaded file from FastAPI
            folder: Cloudinary folder path (default: "auction_items")

        Returns:
            dict with:
                - url: str (secure HTTPS URL)
                - public_id: str (Cloudinary public ID)
                - width: int (image width in pixels)
                - height: int (image height in pixels)

        Raises:
            ValidationException: If file type is invalid, size exceeds limit,
                or upload fails

        """
        # Validate file type
        if file.content_type not in ALLOWED_TYPES:
            logger.error(
                f"Invalid file type: {file.content_type}. "
                f"Allowed: {', '.join(ALLOWED_TYPES)}"
            )
            raise ValidationException(
                "Invalid file type. Allowed types: JPEG, PNG, WebP"
            )

        # Read file content to check size
        content = await file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            logger.error(f"File size {file_size} exceeds limit {MAX_FILE_SIZE}")
            raise ValidationException(
                f"File size exceeds 5MB limit. Your file: "
                f"{file_size / (1024 * 1024):.2f}MB"
            )

        # Reset file pointer for upload
        await file.seek(0)

        try:
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                content, folder=folder, resource_type="image"
            )

            logger.info(f"Image uploaded successfully: {result['public_id']}")

            return {
                "url": result["secure_url"],
                "public_id": result["public_id"],
                "width": result["width"],
                "height": result["height"],
            }

        except Exception as e:
            logger.error(f"Cloudinary upload failed: {str(e)}")
            raise ValidationException(f"Image upload failed: {str(e)}")

    def delete_image(self, public_id: str) -> bool:
        """Delete image from Cloudinary.

        Args:
            public_id: Cloudinary public ID of the image to delete

        Returns:
            True if deleted successfully, False otherwise

        """
        try:
            result = cloudinary.uploader.destroy(public_id)
            success = result.get("result") == "ok"

            if success:
                logger.info(f"Image deleted successfully: {public_id}")
            else:
                logger.warning(f"Image deletion failed: {public_id}, result: {result}")

            return success
        except Exception as e:
            logger.error(f"Error deleting image {public_id}: {str(e)}")
            return False
