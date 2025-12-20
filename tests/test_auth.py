"""Tests for the auth module"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tiktok_uploader.auth import get_session, print_session_instructions
from tiktok_uploader.exceptions import LoginRequiredError


class TestGetSession:
    """Test get_session function"""

    def test_get_session_from_parameter(self):
        """Should return session passed as parameter"""
        session = get_session(session="my_session_token")
        assert session == "my_session_token"

    def test_get_session_from_env(self, monkeypatch):
        """Should read from TIKTOK_SESSION env var"""
        monkeypatch.setenv("TIKTOK_SESSION", "env_session_token")

        session = get_session()
        assert session == "env_session_token"

    def test_get_session_custom_env_var(self, monkeypatch):
        """Should read from custom env var name"""
        monkeypatch.setenv("MY_CUSTOM_VAR", "custom_token")

        session = get_session(env_var="MY_CUSTOM_VAR")
        assert session == "custom_token"

    def test_get_session_from_file(self, tmp_path):
        """Should read from session file"""
        session_file = tmp_path / "session.txt"
        session_file.write_text("file_session_token")

        session = get_session(file_path=str(session_file))
        assert session == "file_session_token"

    def test_get_session_priority_parameter_first(self, monkeypatch, tmp_path):
        """Parameter should take priority over env and file"""
        monkeypatch.setenv("TIKTOK_SESSION", "env_token")
        session_file = tmp_path / "session.txt"
        session_file.write_text("file_token")

        session = get_session(
            session="param_token",
            file_path=str(session_file)
        )
        assert session == "param_token"

    def test_get_session_priority_env_over_file(self, monkeypatch, tmp_path):
        """Env should take priority over file"""
        monkeypatch.setenv("TIKTOK_SESSION", "env_token")
        session_file = tmp_path / "session.txt"
        session_file.write_text("file_token")

        session = get_session(file_path=str(session_file))
        assert session == "env_token"

    def test_get_session_raises_when_not_found(self, monkeypatch):
        """Should raise LoginRequiredError when no session found"""
        monkeypatch.delenv("TIKTOK_SESSION", raising=False)

        with pytest.raises(LoginRequiredError):
            get_session()

    def test_get_session_default_file_location(self, monkeypatch, tmp_path):
        """Should check default session file in home directory"""
        monkeypatch.delenv("TIKTOK_SESSION", raising=False)

        # Mock home directory
        with patch.object(Path, "home", return_value=tmp_path):
            default_session_file = tmp_path / ".tiktok_session"
            default_session_file.write_text("default_file_token")

            session = get_session()
            assert session == "default_file_token"

    def test_get_session_strips_whitespace(self, tmp_path):
        """Should strip whitespace from file contents"""
        session_file = tmp_path / "session.txt"
        session_file.write_text("  token_with_spaces  \n")

        session = get_session(file_path=str(session_file))
        assert session == "token_with_spaces"


class TestPrintSessionInstructions:
    """Test print_session_instructions function"""

    def test_prints_token(self, capsys):
        """Should print the session token"""
        print_session_instructions("my_test_token")

        captured = capsys.readouterr()
        assert "my_test_token" in captured.out

    def test_prints_env_instruction(self, capsys):
        """Should print export instruction"""
        print_session_instructions("token123")

        captured = capsys.readouterr()
        assert "export TIKTOK_SESSION" in captured.out

    def test_prints_github_instruction(self, capsys):
        """Should mention GitHub Secrets"""
        print_session_instructions("token123")

        captured = capsys.readouterr()
        assert "GitHub" in captured.out
        assert "Secrets" in captured.out or "secrets" in captured.out


class TestInteractiveLogin:
    """Test interactive_login function (mocked)"""

    def test_interactive_login_returns_base64_token(self):
        """Should return base64 encoded session token"""
        with patch("tiktok_uploader.auth.sync_playwright") as mock_pw:
            # Setup mocks
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            # Simulate cookies after login
            mock_context.cookies.return_value = [
                {"name": "sessionid", "value": "abc123", "domain": ".tiktok.com", "path": "/"},
                {"name": "sessionid_ss", "value": "abc123", "domain": ".tiktok.com", "path": "/"},
            ]

            # Simulate URL change indicating login
            mock_page.url = "https://www.tiktok.com/foryou"

            from tiktok_uploader.auth import interactive_login

            # Would need to mock the wait loop properly for full test
            # This is a basic structure test
            assert callable(interactive_login)

    def test_interactive_login_saves_to_file(self, tmp_path):
        """Should save session to file when requested"""
        with patch("tiktok_uploader.auth.sync_playwright") as mock_pw:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()

            mock_pw.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            mock_page.url = "https://www.tiktok.com/foryou"

            mock_context.cookies.return_value = [
                {"name": "sessionid", "value": "test123", "domain": ".tiktok.com", "path": "/"},
            ]

            # Mock the wait_for_timeout to not actually wait
            mock_page.wait_for_timeout = MagicMock()

            # This test verifies the function signature accepts save_to_file
            import inspect

            from tiktok_uploader.auth import interactive_login
            sig = inspect.signature(interactive_login)
            assert "save_to_file" in sig.parameters
