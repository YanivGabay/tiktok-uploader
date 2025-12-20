"""Tests for the CLI module"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tiktok_uploader.cli import cmd_auth, cmd_check, main


class TestCLIMain:
    """Test main CLI entry point"""

    def test_main_no_args_shows_help(self, capsys):
        """Should show help when no arguments provided"""
        with patch.object(sys, "argv", ["tiktok-upload"]):
            result = main()

        captured = capsys.readouterr()
        assert result == 0
        assert "usage" in captured.out.lower() or "tiktok" in captured.out.lower()

    def test_main_version_flag(self, capsys):
        """Should show version with --version flag"""
        with patch.object(sys, "argv", ["tiktok-upload", "--version"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "0.1.0" in captured.out

    def test_main_routes_to_auth(self):
        """Should route 'auth' command to cmd_auth"""
        with patch.object(sys, "argv", ["tiktok-upload", "auth"]):
            with patch("tiktok_uploader.cli.cmd_auth") as mock_auth:
                mock_auth.return_value = 0
                main()
                mock_auth.assert_called_once()

    def test_main_routes_to_upload(self):
        """Should route 'upload' command to cmd_upload"""
        with patch.object(sys, "argv", ["tiktok-upload", "upload", "video.mp4", "-c", "caption"]):
            with patch("tiktok_uploader.cli.cmd_upload") as mock_upload:
                mock_upload.return_value = 0
                main()
                mock_upload.assert_called_once()

    def test_main_routes_to_check(self):
        """Should route 'check' command to cmd_check"""
        with patch.object(sys, "argv", ["tiktok-upload", "check"]):
            with patch("tiktok_uploader.cli.cmd_check") as mock_check:
                mock_check.return_value = 0
                main()
                mock_check.assert_called_once()


class TestCLIUploadCommand:
    """Test upload command"""

    def test_upload_requires_caption(self, capsys):
        """Should require --caption flag"""
        with patch.object(sys, "argv", ["tiktok-upload", "upload", "video.mp4"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 2  # argparse error code
        captured = capsys.readouterr()
        assert "caption" in captured.err.lower()

    def test_upload_accepts_visibility(self):
        """Should accept --visibility flag"""
        with patch.object(sys, "argv", [
            "tiktok-upload", "upload", "video.mp4",
            "-c", "test caption",
            "--visibility", "friends"
        ]):
            with patch("tiktok_uploader.cli.get_session") as mock_get_session:
                mock_get_session.return_value = "test_session"
                with patch("tiktok_uploader.cli.TikTokUploader") as mock_uploader:
                    mock_instance = MagicMock()
                    mock_instance.upload.return_value = MagicMock(success=True)
                    mock_uploader.return_value = mock_instance

                    main()

                    # Check that visibility was passed
                    mock_instance.upload.assert_called_once()
                    call_kwargs = mock_instance.upload.call_args[1]
                    assert call_kwargs["visibility"] == "friends"

    def test_upload_no_session_error(self, capsys):
        """Should show error when no session found"""
        with patch.object(sys, "argv", [
            "tiktok-upload", "upload", "video.mp4", "-c", "test"
        ]):
            with patch("tiktok_uploader.cli.get_session") as mock_get_session:
                from tiktok_uploader.exceptions import LoginRequiredError
                mock_get_session.side_effect = LoginRequiredError()

                result = main()

        assert result == 1
        captured = capsys.readouterr()
        assert "session" in captured.err.lower() or "auth" in captured.err.lower()


class TestCLIAuthCommand:
    """Test auth command"""

    def test_auth_calls_interactive_login(self):
        """Should call interactive_login"""
        with patch("tiktok_uploader.cli.interactive_login") as mock_login:
            mock_login.return_value = "mock_token"
            with patch("tiktok_uploader.cli.print_session_instructions"):
                args = MagicMock()
                args.save_to_file = None

                result = cmd_auth(args)

        mock_login.assert_called_once()
        assert result == 0

    def test_auth_returns_error_on_failure(self):
        """Should return 1 on login failure"""
        with patch("tiktok_uploader.cli.interactive_login") as mock_login:
            mock_login.side_effect = Exception("Login failed")

            args = MagicMock()
            result = cmd_auth(args)

        assert result == 1


class TestCLICheckCommand:
    """Test check command"""

    def test_check_success_with_session(self, capsys):
        """Should return 0 when session is found"""
        with patch("tiktok_uploader.cli.get_session") as mock_get_session:
            mock_get_session.return_value = "valid_session"
            with patch("tiktok_uploader.cli.TikTokUploader"):
                args = MagicMock()
                result = cmd_check(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "found" in captured.out.lower()

    def test_check_failure_no_session(self, capsys):
        """Should return 1 when no session found"""
        with patch("tiktok_uploader.cli.get_session") as mock_get_session:
            from tiktok_uploader.exceptions import LoginRequiredError
            mock_get_session.side_effect = LoginRequiredError()

            args = MagicMock()
            result = cmd_check(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "no session" in captured.out.lower()


class TestCLIArgParsing:
    """Test argument parsing"""

    def test_upload_visibility_choices(self, capsys):
        """Should only accept valid visibility values"""
        with patch.object(sys, "argv", [
            "tiktok-upload", "upload", "video.mp4",
            "-c", "test",
            "--visibility", "invalid_value"
        ]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "invalid choice" in captured.err.lower()

    def test_upload_debug_flag(self):
        """Should accept --debug flag"""
        with patch.object(sys, "argv", [
            "tiktok-upload", "upload", "video.mp4",
            "-c", "test",
            "--debug"
        ]):
            with patch("tiktok_uploader.cli.get_session", return_value="session"):
                with patch("tiktok_uploader.cli.TikTokUploader") as mock_uploader:
                    mock_instance = MagicMock()
                    mock_instance.upload.return_value = MagicMock(success=True)
                    mock_uploader.return_value = mock_instance

                    main()

                    # Check debug was passed to TikTokUploader
                    call_kwargs = mock_uploader.call_args[1]
                    assert call_kwargs["debug"] is True

    def test_upload_quiet_flag(self):
        """Should accept --quiet flag"""
        with patch.object(sys, "argv", [
            "tiktok-upload", "upload", "video.mp4",
            "-c", "test",
            "-q"
        ]):
            with patch("tiktok_uploader.cli.get_session", return_value="session"):
                with patch("tiktok_uploader.cli.TikTokUploader") as mock_uploader:
                    mock_instance = MagicMock()
                    mock_instance.upload.return_value = MagicMock(success=True)
                    mock_uploader.return_value = mock_instance

                    main()

                    # Check on_progress is None when quiet
                    call_kwargs = mock_instance.upload.call_args[1]
                    assert call_kwargs.get("on_progress") is None
