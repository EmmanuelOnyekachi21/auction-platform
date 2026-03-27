"""Tests for Cloudinary image upload service."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import UploadFile

from apps.auctions.cloudinary_service import MAX_FILE_SIZE, CloudinaryService
from common.exceptions import ValidationException


@pytest.fixture
def cloudinary_service():
    """Create CloudinaryService instance with mocked config."""
    # We patch settings because the __init__ calls cloudinary.config(settings.X)
    with patch("apps.auctions.cloudinary_service.settings") as mock_settings:
        mock_settings.cloudinary_cloud_name = "test_cloud"
        mock_settings.cloudinary_api_key = "test_key"
        mock_settings.cloudinary_api_secret = "test_secret"
        service = CloudinaryService()
    return service


@pytest.fixture
def mock_upload_file():
    """Create a mock UploadFile for testing."""

    def _create_file(
        filename: str = "test.jpg",
        content_type: str = "image/jpeg",
        content: bytes = b"fake image content",
    ):
        file = Mock(spec=UploadFile)
        file.filename = filename
        file.content_type = content_type
        # In your service, you use await file.read() and await file.seek(0)
        file.read = AsyncMock(return_value=content)
        file.seek = AsyncMock()
        return file

    return _create_file


class TestCloudinaryServiceUpload:
    """Test suite for CloudinaryService upload operations."""

    @pytest.mark.asyncio
    async def test_upload_jpeg_success(self, cloudinary_service, mock_upload_file):
        """Test successful JPEG image upload."""
        file = mock_upload_file()
        mock_result = {
            "secure_url": "https://res.cloudinary.com/test/image/upload/v1/test.jpg",
            "public_id": "auction_items/test123",
            "width": 800,
            "height": 600,
        }

        with patch("cloudinary.uploader.upload", return_value=mock_result):
            result = await cloudinary_service.upload_image(file)

        assert result["url"] == mock_result["secure_url"]
        assert result["public_id"] == mock_result["public_id"]
        file.read.assert_called_once()
        file.seek.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, cloudinary_service, mock_upload_file):
        """Test upload with invalid file type raises error."""
        file = mock_upload_file(content_type="application/pdf")
        with pytest.raises(ValidationException, match="Invalid file type"):
            await cloudinary_service.upload_image(file)

    @pytest.mark.asyncio
    async def test_upload_file_exceeds_size_limit(
        self, cloudinary_service, mock_upload_file
    ):
        """Test upload with file exceeding size limit raises error."""
        large_content = b"x" * (MAX_FILE_SIZE + 1)
        file = mock_upload_file(content=large_content)

        with pytest.raises(ValidationException, match="exceeds 5MB limit"):
            await cloudinary_service.upload_image(file)


class TestCloudinaryServiceDelete:
    """Test suite for CloudinaryService delete operations."""

    def test_delete_image_success(self, cloudinary_service):
        """Test successful image deletion."""
        public_id = "test_id"
        with patch("cloudinary.uploader.destroy", return_value={"result": "ok"}):
            assert cloudinary_service.delete_image(public_id) is True

    def test_delete_image_failure(self, cloudinary_service):
        """Test image deletion failure."""
        public_id = "test_id"
        with patch("cloudinary.uploader.destroy", return_value={"result": "not found"}):
            assert cloudinary_service.delete_image(public_id) is False


class TestCloudinaryServiceConfiguration:
    """Verifies that the service initializes with correct settings."""

    def test_init_configures_cloudinary(self):
        """Test that CloudinaryService initializes with correct settings."""
        with (
            patch("apps.auctions.cloudinary_service.settings") as mock_settings,
            patch("cloudinary.config") as mock_config,
        ):

            mock_settings.cloudinary_cloud_name = "cloud"
            mock_settings.cloudinary_api_key = "key"
            mock_settings.cloudinary_api_secret = "secret"

            CloudinaryService()

            mock_config.assert_called_once_with(
                cloud_name="cloud", api_key="key", api_secret="secret", secure=True
            )
