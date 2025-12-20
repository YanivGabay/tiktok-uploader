"""
TikTok Uploader - Simple video uploads to TikTok using Playwright

Usage:
    from tiktok_uploader import upload, TikTokUploader

    # Simple one-liner (reads TIKTOK_SESSION from env)
    upload("video.mp4", "My awesome video #fyp")

    # Or with more control
    uploader = TikTokUploader(headless=True)
    result = uploader.upload("video.mp4", "My video #fyp")
    print(result.status)
"""

from .auth import get_session, interactive_login
from .exceptions import (
    LoginRequiredError,
    SessionExpiredError,
    TikTokUploaderError,
    UploadFailedError,
    VideoNotFoundError,
)
from .uploader import TikTokUploader, upload, upload_many

__version__ = "0.1.0"
__all__ = [
    "TikTokUploader",
    "upload",
    "upload_many",
    "get_session",
    "interactive_login",
    "TikTokUploaderError",
    "SessionExpiredError",
    "UploadFailedError",
    "LoginRequiredError",
    "VideoNotFoundError",
]
