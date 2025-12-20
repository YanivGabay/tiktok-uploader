"""Tests for custom exceptions"""


from tiktok_uploader.exceptions import (
    LoginRequiredError,
    SessionExpiredError,
    TikTokUploaderError,
    UnsupportedFormatError,
    UploadFailedError,
    VideoNotFoundError,
    VideoTooLargeError,
)


class TestExceptionHierarchy:
    """Test exception inheritance"""

    def test_all_exceptions_inherit_from_base(self):
        """All exceptions should inherit from TikTokUploaderError"""
        exceptions = [
            SessionExpiredError,
            LoginRequiredError,
            UploadFailedError,
            VideoNotFoundError,
            VideoTooLargeError,
            UnsupportedFormatError,
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, TikTokUploaderError)

    def test_base_inherits_from_exception(self):
        """Base exception should inherit from Exception"""
        assert issubclass(TikTokUploaderError, Exception)


class TestSessionExpiredError:
    """Test SessionExpiredError"""

    def test_default_message(self):
        """Should have helpful default message"""
        error = SessionExpiredError()
        assert "expired" in str(error).lower()
        assert "auth" in str(error).lower()

    def test_custom_message(self):
        """Should accept custom message"""
        error = SessionExpiredError("Custom message")
        assert error.message == "Custom message"


class TestLoginRequiredError:
    """Test LoginRequiredError"""

    def test_default_message(self):
        """Should have helpful default message"""
        error = LoginRequiredError()
        assert "session" in str(error).lower() or "login" in str(error).lower()

    def test_mentions_auth_command(self):
        """Should mention auth command"""
        error = LoginRequiredError()
        assert "auth" in str(error).lower()

    def test_mentions_env_var(self):
        """Should mention TIKTOK_SESSION env var"""
        error = LoginRequiredError()
        assert "TIKTOK_SESSION" in str(error)


class TestUploadFailedError:
    """Test UploadFailedError"""

    def test_with_message(self):
        """Should store message"""
        error = UploadFailedError("Upload timed out")
        assert error.message == "Upload timed out"
        assert str(error) == "Upload timed out"

    def test_with_screenshot_path(self):
        """Should store screenshot path"""
        error = UploadFailedError("Failed", screenshot_path="/tmp/debug.png")
        assert error.screenshot_path == "/tmp/debug.png"


class TestVideoNotFoundError:
    """Test VideoNotFoundError"""

    def test_stores_path(self):
        """Should store video path"""
        error = VideoNotFoundError("/path/to/video.mp4")
        assert error.path == "/path/to/video.mp4"
        assert "/path/to/video.mp4" in str(error)


class TestVideoTooLargeError:
    """Test VideoTooLargeError"""

    def test_stores_sizes(self):
        """Should store actual and max sizes"""
        error = VideoTooLargeError(300.5, 287)
        assert error.size_mb == 300.5
        assert error.max_size_mb == 287

    def test_message_includes_sizes(self):
        """Message should include both sizes"""
        error = VideoTooLargeError(300.5, 287)
        assert "300.5" in str(error)
        assert "287" in str(error)


class TestUnsupportedFormatError:
    """Test UnsupportedFormatError"""

    def test_stores_extension(self):
        """Should store the extension"""
        error = UnsupportedFormatError(".avi")
        assert error.extension == ".avi"

    def test_message_includes_extension(self):
        """Message should include the extension"""
        error = UnsupportedFormatError(".avi")
        assert ".avi" in str(error)

    def test_lists_supported_formats(self):
        """Message should list supported formats"""
        error = UnsupportedFormatError(".avi")
        assert ".mp4" in str(error)
        assert ".mov" in str(error)
        assert ".webm" in str(error)
