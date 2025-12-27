"""Core TikTok upload functionality"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Optional, Union

from playwright.sync_api import BrowserContext, Page, sync_playwright

from .exceptions import (
    LoginRequiredError,
    SessionExpiredError,
    UnsupportedFormatError,
    UploadFailedError,
    VideoNotFoundError,
    VideoTooLargeError,
)

logger = logging.getLogger(__name__)

# Constants
TIKTOK_UPLOAD_URL = "https://www.tiktok.com/creator-center/upload?lang=en"
TIKTOK_BASE_URL = "https://www.tiktok.com/"
MAX_VIDEO_SIZE_MB = 287
SUPPORTED_FORMATS = {".mp4", ".mov", ".webm"}

# Stealth browser configuration
STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--disable-infobars",
    "--disable-background-timer-throttling",
    "--disable-popup-blocking",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--no-first-run",
    "--no-default-browser-check",
    "--no-sandbox",
]

# Realistic user agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# JavaScript to hide automation indicators
STEALTH_JS = """
() => {
    // Hide webdriver property
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });

    // Hide automation-related properties
    window.navigator.chrome = { runtime: {} };

    // Override permissions query
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );

    // Hide plugins length
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });

    // Hide languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
}
"""


@dataclass
class UploadResult:
    """Result of an upload operation"""
    success: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    status: str = ""
    error: Optional[str] = None
    screenshot_path: Optional[str] = None


class TikTokUploader:
    """
    TikTok video uploader using Playwright with stealth mode.

    Usage:
        uploader = TikTokUploader()
        result = uploader.upload("video.mp4", "My caption #fyp")
    """

    def __init__(
        self,
        session: Optional[str] = None,
        headless: bool = True,
        timeout: int = 60000,
        debug: bool = False,
        retries: int = 2,
    ):
        """
        Initialize the uploader.

        Args:
            session: Session token (base64 encoded cookies or raw sessionid).
                     If not provided, reads from TIKTOK_SESSION env var.
            headless: Run browser in headless mode (default: True)
            timeout: Default timeout in milliseconds (default: 60000)
            debug: Enable debug logging and save screenshots on error
            retries: Number of retry attempts on failure (default: 2)
        """
        self.session = session or os.getenv("TIKTOK_SESSION")
        self.headless = headless
        self.timeout = timeout
        self.debug = debug
        self.retries = retries

        if debug:
            logging.basicConfig(level=logging.DEBUG)

        self._cookies = None
        if self.session:
            self._cookies = self._parse_session(self.session)

    def _parse_session(self, session: str) -> list[dict]:
        """Parse session string into cookies list.

        Supports:
        - Base64 encoded JSON array of cookies
        - Raw sessionid string
        - Semicolon-separated key=value pairs (e.g., "sessionid=xxx;csrf_session_id=yyy")
        """
        # Try to decode as base64 JSON first
        try:
            decoded = base64.b64decode(session).decode("utf-8")
            cookies = json.loads(decoded)
            if isinstance(cookies, list):
                logger.debug(f"Parsed {len(cookies)} cookies from base64 JSON")
                return cookies
        except Exception:
            pass

        # Try semicolon-separated key=value pairs
        if "=" in session and ";" in session:
            cookies = []
            for pair in session.split(";"):
                pair = pair.strip()
                if "=" in pair:
                    name, value = pair.split("=", 1)
                    cookies.append({
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": ".tiktok.com",
                        "path": "/"
                    })
            if cookies:
                logger.debug(f"Parsed {len(cookies)} cookies from key=value pairs")
                return cookies

        # Assume it's a raw sessionid
        logger.debug("Using raw sessionid format")
        return [
            {"name": "sessionid", "value": session, "domain": ".tiktok.com", "path": "/"},
            {"name": "sessionid_ss", "value": session, "domain": ".tiktok.com", "path": "/"},
        ]

    def _validate_video(self, video_path: Union[str, Path]) -> Path:
        """Validate video file exists and meets requirements"""
        path = Path(video_path).resolve()

        if not path.exists():
            raise VideoNotFoundError(str(path))

        # Check format
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            raise UnsupportedFormatError(path.suffix)

        # Check size
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_VIDEO_SIZE_MB:
            raise VideoTooLargeError(size_mb, MAX_VIDEO_SIZE_MB)

        return path

    def _apply_stealth(self, page: Page) -> None:
        """Apply stealth scripts to hide automation indicators"""
        try:
            page.add_init_script(STEALTH_JS)
        except Exception as e:
            logger.warning(f"Failed to apply stealth script: {e}")

    def _setup_context(self, context: BrowserContext) -> None:
        """Setup browser context with cookies"""
        if not self._cookies:
            raise LoginRequiredError()

        # Go to TikTok first to set cookies
        page = context.new_page()
        self._apply_stealth(page)
        page.goto(TIKTOK_BASE_URL)
        page.wait_for_timeout(1000)

        # Add cookies
        context.add_cookies(self._cookies)
        logger.debug(f"Added {len(self._cookies)} cookies to context")
        page.close()

    def _take_screenshot(self, page: Page, name: str) -> Optional[str]:
        """Take a debug screenshot and return the path"""
        try:
            timestamp = int(time.time())
            path = f"debug_{name}_{timestamp}.png"
            page.screenshot(path=path)
            logger.info(f"Screenshot saved: {path}")
            return path
        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")
            return None

    def _dismiss_modals(self, page: Page) -> None:
        """Dismiss any modal popups"""
        modal_buttons = ["Cancel", "Not now", "Close", "Skip", "Got it", "Maybe later"]

        for button_text in modal_buttons:
            try:
                btn = page.locator(f"text={button_text}").first
                if btn.is_visible(timeout=1000):
                    btn.click()
                    page.wait_for_timeout(500)
                    logger.debug(f"Dismissed modal with '{button_text}'")
                    return
            except Exception:
                continue

    def _find_post_button(self, page: Page):
        """Find the actual Post submit button"""
        # Scroll to bottom to ensure button is in DOM
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)

        # Find all buttons with "Post" text
        buttons = page.locator("button").filter(has_text="Post").all()

        for btn in buttons:
            try:
                text = (btn.text_content() or "").strip()
                box = btn.bounding_box()
                # Real Post button is larger and has exact "Post" text
                if box and text == "Post" and box["width"] > 100:
                    return btn
            except Exception:
                continue

        return None

    def _wait_for_upload_complete(
        self,
        page: Page,
        timeout_seconds: int = 60,
        on_progress: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """Wait for upload to complete, return True if successful"""
        for i in range(timeout_seconds // 5):
            page.wait_for_timeout(5000)
            current_url = page.url

            if on_progress:
                # Estimate progress based on time (rough)
                progress = min(95, (i + 1) * 5 * 100 // timeout_seconds)
                on_progress(progress)

            # Success indicators
            if "/content" in current_url or "/posts" in current_url:
                if on_progress:
                    on_progress(100)
                return True

            # Check for exit modal (means upload failed)
            try:
                exit_modal = page.locator("text=Are you sure you want to exit?")
                if exit_modal.is_visible(timeout=500):
                    logger.error("Exit modal appeared - upload may have failed")
                    return False
            except Exception:
                pass

        return False

    def _upload_attempt(
        self,
        video_path: Path,
        description: str,
        visibility: str,
        on_progress: Optional[Callable[[int], None]],
    ) -> UploadResult:
        """Single upload attempt"""
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=STEALTH_ARGS,
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 1024},
                user_agent=USER_AGENT,
            )

            page = None
            try:
                # Setup session
                self._setup_context(context)

                page = context.new_page()
                self._apply_stealth(page)

                logger.info(f"Navigating to upload page...")
                page.goto(TIKTOK_UPLOAD_URL)
                page.wait_for_timeout(3000)

                if on_progress:
                    on_progress(10)

                # Check if we're logged in
                current_url = page.url
                logger.info(f"Current URL: {current_url}")

                if "login" in current_url.lower():
                    screenshot = self._take_screenshot(page, "login_redirect") if self.debug else None
                    logger.error(f"Redirected to login page: {current_url}")
                    raise SessionExpiredError(
                        f"Session invalid - redirected to: {current_url}"
                    )

                # Upload video file
                logger.info("Uploading video file...")
                file_input = page.locator("input[type='file']")
                file_input.set_input_files(str(video_path))
                page.wait_for_timeout(10000)  # Wait for processing

                if on_progress:
                    on_progress(40)

                # Dismiss any modals
                self._dismiss_modals(page)

                # Set description
                logger.info("Setting description...")
                desc_field = page.locator("div[contenteditable='true']").first
                desc_field.click()
                desc_field.fill(description)
                page.keyboard.press("Escape")  # Close any dropdown
                page.wait_for_timeout(1000)

                if on_progress:
                    on_progress(60)

                # Find and click Post button
                logger.info("Clicking Post...")
                post_btn = self._find_post_button(page)

                if not post_btn:
                    screenshot = self._take_screenshot(page, "no_post_button") if self.debug else None
                    raise UploadFailedError(
                        "Could not find Post button",
                        screenshot_path=screenshot,
                    )

                post_btn.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                post_btn.click()

                if on_progress:
                    on_progress(70)

                # Wait for completion
                logger.info("Waiting for upload to complete...")
                success = self._wait_for_upload_complete(
                    page,
                    timeout_seconds=self.timeout // 1000,
                    on_progress=on_progress,
                )

                if success:
                    logger.info("Upload successful!")
                    return UploadResult(
                        success=True,
                        status="uploaded",
                    )
                else:
                    screenshot = self._take_screenshot(page, "upload_failed") if self.debug else None
                    raise UploadFailedError(
                        "Upload did not complete successfully",
                        screenshot_path=screenshot,
                    )

            except (LoginRequiredError, SessionExpiredError):
                raise
            except UploadFailedError:
                raise
            except Exception as e:
                screenshot = None
                if self.debug and page:
                    screenshot = self._take_screenshot(page, "error")
                raise UploadFailedError(str(e), screenshot_path=screenshot) from e
            finally:
                browser.close()

    def upload(
        self,
        video: Union[str, Path],
        description: str,
        *,
        visibility: Literal["everyone", "friends", "private"] = "everyone",
        on_progress: Optional[Callable[[int], None]] = None,
    ) -> UploadResult:
        """
        Upload a video to TikTok with retry support.

        Args:
            video: Path to video file
            description: Video caption/description (can include hashtags)
            visibility: Who can view the video (default: "everyone")
            on_progress: Optional callback for progress updates (0-100)

        Returns:
            UploadResult with success status and details

        Raises:
            LoginRequiredError: No session token found
            SessionExpiredError: Session has expired
            VideoNotFoundError: Video file doesn't exist
            UploadFailedError: Upload failed for some reason
        """
        # Validate video
        video_path = self._validate_video(video)
        logger.info(f"Uploading: {video_path}")

        if on_progress:
            on_progress(0)

        last_error = None
        for attempt in range(self.retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt}/{self.retries}...")
                    time.sleep(2 ** attempt)  # Exponential backoff

                return self._upload_attempt(video_path, description, visibility, on_progress)

            except SessionExpiredError:
                # Don't retry on session errors - they won't fix themselves
                raise
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.retries:
                    raise

        # Should not reach here, but just in case
        raise UploadFailedError(f"All {self.retries + 1} attempts failed: {last_error}")

    def upload_many(
        self,
        videos: list[dict],
        *,
        on_video_complete: Optional[Callable[[int, UploadResult], None]] = None,
    ) -> list[UploadResult]:
        """
        Upload multiple videos.

        Args:
            videos: List of dicts with 'video' and 'description' keys
            on_video_complete: Callback after each video (index, result)

        Returns:
            List of UploadResult for each video
        """
        results = []

        for i, video_info in enumerate(videos):
            try:
                result = self.upload(
                    video=video_info["video"],
                    description=video_info["description"],
                    visibility=video_info.get("visibility", "everyone"),
                )
            except Exception as e:
                result = UploadResult(success=False, error=str(e))

            results.append(result)

            if on_video_complete:
                on_video_complete(i, result)

        return results


# Convenience functions

def upload(
    video: Union[str, Path],
    description: str,
    *,
    session: Optional[str] = None,
    visibility: Literal["everyone", "friends", "private"] = "everyone",
    headless: bool = True,
    retries: int = 2,
) -> UploadResult:
    """
    Upload a video to TikTok (convenience function).

    Args:
        video: Path to video file
        description: Video caption/description
        session: Session token (or reads from TIKTOK_SESSION env)
        visibility: Who can view the video
        headless: Run in headless mode
        retries: Number of retry attempts

    Returns:
        UploadResult with success status
    """
    uploader = TikTokUploader(session=session, headless=headless, retries=retries)
    return uploader.upload(video, description, visibility=visibility)


def upload_many(
    videos: list[dict],
    *,
    session: Optional[str] = None,
    headless: bool = True,
) -> list[UploadResult]:
    """Upload multiple videos (convenience function)"""
    uploader = TikTokUploader(session=session, headless=headless)
    return uploader.upload_many(videos)
