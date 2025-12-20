"""Pytest configuration and fixtures"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_video_file():
    """Create a temporary video file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        # Write some dummy content (not a real video, but enough for path validation)
        f.write(b"fake video content")
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_large_video_file():
    """Create a temporary video file that exceeds size limit"""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        # Write content larger than MAX_VIDEO_SIZE_MB (287MB)
        # We'll just create a small file but mock the size check
        f.write(b"fake video content")
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_session():
    """Return a mock session token"""
    return "mock_session_id_12345"


@pytest.fixture
def mock_session_base64():
    """Return a base64 encoded mock session"""
    import base64
    import json

    cookies = [
        {"name": "sessionid", "value": "mock123", "domain": ".tiktok.com", "path": "/"},
        {"name": "sessionid_ss", "value": "mock123", "domain": ".tiktok.com", "path": "/"},
    ]
    return base64.b64encode(json.dumps(cookies).encode()).decode()


@pytest.fixture
def mock_playwright():
    """Mock Playwright for testing without actual browser"""
    with patch("tiktok_uploader.uploader.sync_playwright") as mock_pw:
        # Setup mock browser chain
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_context.cookies.return_value = []

        # Setup page mock
        mock_page.url = "https://www.tiktok.com/creator-center/upload"
        mock_page.goto.return_value = None
        mock_page.wait_for_timeout.return_value = None

        yield {
            "playwright": mock_pw,
            "browser": mock_browser,
            "context": mock_context,
            "page": mock_page,
        }


@pytest.fixture
def env_with_session(mock_session, monkeypatch):
    """Set TIKTOK_SESSION environment variable"""
    monkeypatch.setenv("TIKTOK_SESSION", mock_session)
    yield mock_session


@pytest.fixture
def env_without_session(monkeypatch):
    """Ensure TIKTOK_SESSION is not set"""
    monkeypatch.delenv("TIKTOK_SESSION", raising=False)
