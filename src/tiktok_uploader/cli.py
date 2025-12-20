"""Command-line interface for TikTok Uploader"""

import argparse
import sys
from pathlib import Path

from . import __version__
from .auth import get_session, interactive_login, print_session_instructions
from .exceptions import (
    LoginRequiredError,
    SessionExpiredError,
    TikTokUploaderError,
)
from .uploader import TikTokUploader


def cmd_auth(args):
    """Handle auth command"""
    try:
        session_token = interactive_login(
            save_to_file=args.save_to_file if hasattr(args, 'save_to_file') else None
        )
        print_session_instructions(session_token)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_upload(args):
    """Handle upload command"""
    try:
        # Get session
        try:
            session = get_session()
        except LoginRequiredError:
            print("Error: No TikTok session found.", file=sys.stderr)
            print("Run 'tiktok-upload auth' first to login.", file=sys.stderr)
            return 1

        # Create uploader
        uploader = TikTokUploader(
            session=session,
            headless=not args.visible,
            debug=args.debug,
        )

        # Progress callback
        def show_progress(progress: int):
            bar_width = 30
            filled = int(bar_width * progress / 100)
            bar = "█" * filled + "░" * (bar_width - filled)
            print(f"\r  [{bar}] {progress}%", end="", flush=True)
            if progress == 100:
                print()

        print(f"Uploading: {args.video}")
        print(f"Caption: {args.caption[:50]}..." if len(args.caption) > 50 else f"Caption: {args.caption}")
        print()

        result = uploader.upload(
            video=args.video,
            description=args.caption,
            visibility=args.visibility,
            on_progress=show_progress if not args.quiet else None,
        )

        if result.success:
            print("\n✅ Upload successful!")
            if result.video_url:
                print(f"   URL: {result.video_url}")
            return 0
        else:
            print(f"\n❌ Upload failed: {result.error}", file=sys.stderr)
            return 1

    except SessionExpiredError as e:
        print(f"\n❌ {e}", file=sys.stderr)
        return 1
    except TikTokUploaderError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\nUpload cancelled.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def cmd_check(args):
    """Check if session is valid"""
    try:
        session = get_session()
        print("✅ Session found")

        # Try a quick validation
        print("   Validating session...")
        _ = TikTokUploader(session=session, headless=True)  # noqa: F841
        # Could add a validation method here
        print("   Session appears valid")
        return 0
    except LoginRequiredError:
        print("❌ No session found")
        print("   Run 'tiktok-upload auth' to login")
        return 1
    except SessionExpiredError:
        print("❌ Session expired")
        print("   Run 'tiktok-upload auth' to get a new session")
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog="tiktok-upload",
        description="Upload videos to TikTok from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tiktok-upload auth                    # Login and get session token
  tiktok-upload video.mp4 -c "Hello!"   # Upload a video
  tiktok-upload check                   # Verify session is valid

Environment Variables:
  TIKTOK_SESSION    Session token from 'tiktok-upload auth'
        """,
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Auth command
    auth_parser = subparsers.add_parser(
        "auth",
        help="Login to TikTok and get session token",
    )
    auth_parser.add_argument(
        "--save-to-file",
        type=str,
        help="Save session token to a file",
    )

    # Upload command (also default when video path is given)
    upload_parser = subparsers.add_parser(
        "upload",
        help="Upload a video",
    )
    upload_parser.add_argument(
        "video",
        type=str,
        help="Path to video file",
    )
    upload_parser.add_argument(
        "-c", "--caption",
        type=str,
        required=True,
        help="Video caption/description",
    )
    upload_parser.add_argument(
        "--visibility",
        choices=["everyone", "friends", "private"],
        default="everyone",
        help="Who can view the video (default: everyone)",
    )
    upload_parser.add_argument(
        "--visible",
        action="store_true",
        help="Show browser window (not headless)",
    )
    upload_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (saves screenshots on error)",
    )
    upload_parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output",
    )

    # Check command
    subparsers.add_parser(
        "check",
        help="Check if session is valid",
    )

    # Parse arguments
    args = parser.parse_args()

    # Handle direct video path (shorthand)
    if args.command is None:
        # Check if first arg looks like a video file
        if len(sys.argv) > 1 and Path(sys.argv[1]).suffix.lower() in {".mp4", ".mov", ".webm"}:
            # Reparse as upload command
            sys.argv.insert(1, "upload")
            args = parser.parse_args()
        else:
            parser.print_help()
            return 0

    # Route to command handler
    if args.command == "auth":
        return cmd_auth(args)
    elif args.command == "upload":
        return cmd_upload(args)
    elif args.command == "check":
        return cmd_check(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
