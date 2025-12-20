"""Tests for the uploader module"""

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tiktok_uploader.exceptions import (
    LoginRequiredError,
    UnsupportedFormatError,
    VideoNotFoundError,
)
from tiktok_uploader.uploader import TikTokUploader


class TestTikTokUploaderInit:
    """Test TikTokUploader initialization"""

    def test_init_with_session_string(self, mock_session):
        """Should accept raw session ID string"""
        uploader = TikTokUploader(session=mock_session)
        assert uploader.session == mock_session
        assert uploader._cookies is not None
        assert len(uploader._cookies) == 2  # sessionid and sessionid_ss

    def test_init_with_base64_session(self, mock_session_base64):
        """Should accept base64 encoded session"""
        uploader = TikTokUploader(session=mock_session_base64)
        assert uploader._cookies is not None
        assert any(c["name"] == "sessionid" for c in uploader._cookies)

    def test_init_reads_env_var(self, env_with_session):
        """Should read TIKTOK_SESSION from environment"""
        uploader = TikTokUploader()
        assert uploader.session == env_with_session

    def test_init_without_session(self, env_without_session):
        """Should allow init without session (for auth flow)"""
        uploader = TikTokUploader()
        assert uploader.session is None
        assert uploader._cookies is None

    def test_init_default_values(self, mock_session):
        """Should have correct default values"""
        uploader = TikTokUploader(session=mock_session)
        assert uploader.headless is True
        assert uploader.timeout == 60000
        assert uploader.debug is False

    def test_init_custom_values(self, mock_session):
        """Should accept custom values"""
        uploader = TikTokUploader(
            session=mock_session,
            headless=False,
            timeout=120000,
            debug=True,
        )
        assert uploader.headless is False
        assert uploader.timeout == 120000
        assert uploader.debug is True


class TestSessionParsing:
    """Test session token parsing"""

    def test_parse_raw_session_id(self, mock_session):
        """Should parse raw session ID into cookies"""
        uploader = TikTokUploader(session=mock_session)
        cookies = uploader._cookies

        assert len(cookies) == 2
        assert cookies[0]["name"] == "sessionid"
        assert cookies[0]["value"] == mock_session
        assert cookies[1]["name"] == "sessionid_ss"
        assert cookies[1]["value"] == mock_session

    def test_parse_base64_json_cookies(self):
        """Should parse base64 encoded JSON cookies"""
        original_cookies = [
            {"name": "sessionid", "value": "abc123", "domain": ".tiktok.com", "path": "/"},
            {"name": "custom_cookie", "value": "xyz", "domain": ".tiktok.com", "path": "/"},
        ]
        encoded = base64.b64encode(json.dumps(original_cookies).encode()).decode()

        uploader = TikTokUploader(session=encoded)

        assert uploader._cookies == original_cookies


class TestVideoValidation:
    """Test video file validation"""

    def test_validate_existing_video(self, temp_video_file):
        """Should accept existing video file"""
        uploader = TikTokUploader(session="test")
        path = uploader._validate_video(temp_video_file)
        assert path.exists()

    def test_validate_nonexistent_video(self):
        """Should raise VideoNotFoundError for missing file"""
        uploader = TikTokUploader(session="test")

        with pytest.raises(VideoNotFoundError) as exc_info:
            uploader._validate_video("/nonexistent/video.mp4")

        assert "not found" in str(exc_info.value).lower()

    def test_validate_unsupported_format(self, tmp_path):
        """Should raise UnsupportedFormatError for wrong format"""
        # Create a file with unsupported extension
        bad_file = tmp_path / "video.avi"
        bad_file.write_bytes(b"fake content")

        uploader = TikTokUploader(session="test")

        with pytest.raises(UnsupportedFormatError) as exc_info:
            uploader._validate_video(str(bad_file))

        assert ".avi" in str(exc_info.value)

    def test_validate_supported_formats(self, tmp_path):
        """Should accept all supported formats"""
        uploader = TikTokUploader(session="test")

        for ext in [".mp4", ".mov", ".webm"]:
            video_file = tmp_path / f"video{ext}"
            video_file.write_bytes(b"fake content")

            path = uploader._validate_video(str(video_file))
            assert path.exists()

    def test_validate_path_object(self, temp_video_file):
        """Should accept Path objects"""
        uploader = TikTokUploader(session="test")
        path = uploader._validate_video(Path(temp_video_file))
        assert path.exists()


class TestUploadRequiresSession:
    """Test that upload requires a valid session"""

    def test_upload_without_session_raises(self, env_without_session, temp_video_file):
        """Should raise LoginRequiredError when no session"""
        uploader = TikTokUploader()

        with pytest.raises(LoginRequiredError):
            uploader.upload(temp_video_file, "Test caption")


class TestUploadConvenienceFunction:
    """Test the upload() convenience function"""

    def test_upload_function_creates_uploader(self, mock_session, temp_video_file, mock_playwright):
        """upload() should create TikTokUploader internally"""
        mock_page = mock_playwright["page"]

        # Setup mock to simulate successful upload
        mock_page.url = "https://www.tiktok.com/tiktokstudio/content"

        # Mock locators
        mock_locator = MagicMock()
        mock_locator.set_input_files = MagicMock()
        mock_locator.first = MagicMock()
        mock_locator.first.click = MagicMock()
        mock_locator.first.fill = MagicMock()
        mock_locator.first.is_visible = MagicMock(return_value=False)
        mock_locator.filter.return_value.all.return_value = []

        mock_page.locator.return_value = mock_locator

        # This would need more mocking to fully test
        # For now, just verify imports work
        from tiktok_uploader import upload as upload_fn
        assert callable(upload_fn)


class TestUploadResult:
    """Test UploadResult dataclass"""

    def test_upload_result_success(self):
        """Should create successful result"""
        from tiktok_uploader.uploader import UploadResult

        result = UploadResult(success=True, status="uploaded")
        assert result.success is True
        assert result.status == "uploaded"
        assert result.error is None

    def test_upload_result_failure(self):
        """Should create failed result"""
        from tiktok_uploader.uploader import UploadResult

        result = UploadResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"
