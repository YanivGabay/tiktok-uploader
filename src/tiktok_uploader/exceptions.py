"""Custom exceptions for TikTok Uploader"""


class TikTokUploaderError(Exception):
    """Base exception for all TikTok Uploader errors"""
    pass


class SessionExpiredError(TikTokUploaderError):
    """Session has expired, need to re-authenticate"""

    def __init__(self, message: str = None):
        self.message = message or (
            "Your TikTok session has expired.\n"
            "Run 'tiktok-upload auth' to get a new session token."
        )
        super().__init__(self.message)


class LoginRequiredError(TikTokUploaderError):
    """No session found, need to authenticate"""

    def __init__(self, message: str = None):
        self.message = message or (
            "No TikTok session found.\n"
            "Either:\n"
            "  1. Run 'tiktok-upload auth' to login and get a session token\n"
            "  2. Set TIKTOK_SESSION environment variable\n"
            "  3. Pass session= parameter to TikTokUploader()"
        )
        super().__init__(self.message)


class UploadFailedError(TikTokUploaderError):
    """Upload failed for some reason"""

    def __init__(self, message: str, screenshot_path: str = None):
        self.message = message
        self.screenshot_path = screenshot_path
        super().__init__(self.message)


class VideoNotFoundError(TikTokUploaderError):
    """Video file not found"""

    def __init__(self, path: str):
        self.path = path
        self.message = f"Video file not found: {path}"
        super().__init__(self.message)


class VideoTooLargeError(TikTokUploaderError):
    """Video file exceeds TikTok's size limit"""

    def __init__(self, size_mb: float, max_size_mb: float = 287):
        self.size_mb = size_mb
        self.max_size_mb = max_size_mb
        self.message = f"Video too large: {size_mb:.1f}MB (max: {max_size_mb}MB)"
        super().__init__(self.message)


class UnsupportedFormatError(TikTokUploaderError):
    """Video format not supported"""

    SUPPORTED_FORMATS = [".mp4", ".mov", ".webm"]

    def __init__(self, extension: str):
        self.extension = extension
        self.message = (
            f"Unsupported video format: {extension}\n"
            f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
        )
        super().__init__(self.message)
