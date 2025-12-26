"""Authentication and session management for TikTok Uploader"""

import base64
import json
import os
from pathlib import Path
from typing import Optional, Union

from playwright.sync_api import sync_playwright

from .exceptions import LoginRequiredError

# TikTok auth-related cookies we want to capture
AUTH_COOKIES = {
    "sessionid",
    "sessionid_ss",
    "sid_tt",
    "uid_tt",
    "sid_guard",
}


def interactive_login(
    save_to_file: Optional[Union[str, Path]] = None,
    timeout: int = 300000,  # 5 minutes to complete login
) -> str:
    """
    Open a browser for user to login interactively.

    Args:
        save_to_file: Optional path to save session token
        timeout: Max time to wait for login (milliseconds)

    Returns:
        Session token (base64 encoded cookies)
    """
    print("Opening browser for TikTok login...")
    print("Please log in to your TikTok account.")
    print("The browser will close automatically after login is detected.\n")

    with sync_playwright() as p:
        # Launch visible browser
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Go to TikTok login
        page.goto("https://www.tiktok.com/login")

        print("Waiting for login...")
        print("(You have 5 minutes to complete the login)\n")

        # Wait for successful login by checking for session cookie
        session_found = False
        check_interval = 2000  # Check every 2 seconds
        elapsed = 0

        while elapsed < timeout:
            page.wait_for_timeout(check_interval)
            elapsed += check_interval

            # Check cookies
            cookies = context.cookies()
            session_cookies = [c for c in cookies if c["name"] in AUTH_COOKIES]

            if any(c["name"] == "sessionid" for c in session_cookies):
                session_found = True
                print("Login detected!")
                break

            # Also check if we've navigated away from login page
            if "login" not in page.url.lower() and "/foryou" in page.url.lower():
                # Give it a moment to set cookies
                page.wait_for_timeout(2000)
                cookies = context.cookies()
                session_cookies = [c for c in cookies if c["name"] in AUTH_COOKIES]
                if any(c["name"] == "sessionid" for c in session_cookies):
                    session_found = True
                    print("Login detected!")
                    break

        if not session_found:
            browser.close()
            raise LoginRequiredError("Login timed out. Please try again.")

        # Extract auth cookies
        cookies = context.cookies()
        auth_cookies = [
            {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c["path"]}
            for c in cookies
            if c["name"] in AUTH_COOKIES
        ]

        browser.close()

        # Encode as base64 JSON
        session_token = base64.b64encode(
            json.dumps(auth_cookies).encode("utf-8")
        ).decode("utf-8")

        # Save to file if requested
        if save_to_file:
            save_path = Path(save_to_file)
            save_path.write_text(session_token)
            print(f"\nSession saved to: {save_path}")

        return session_token


def get_session(
    session: Optional[str] = None,
    env_var: str = "TIKTOK_SESSION",
    file_path: Optional[Union[str, Path]] = None,
) -> str:
    """
    Get session from various sources.

    Priority:
    1. Passed session parameter
    2. Environment variable
    3. Session file

    Args:
        session: Direct session string
        env_var: Environment variable name to check
        file_path: Path to session file

    Returns:
        Session token string

    Raises:
        LoginRequiredError: No session found
    """
    # Check direct parameter
    if session:
        return session

    # Check environment variable
    env_session = os.getenv(env_var)
    if env_session:
        return env_session

    # Check file
    if file_path:
        path = Path(file_path)
        if path.exists():
            return path.read_text().strip()

    # Check default session file location
    default_session_file = Path.home() / ".tiktok_session"
    if default_session_file.exists():
        return default_session_file.read_text().strip()

    raise LoginRequiredError()


def print_session_instructions(session_token: str) -> None:
    """Print instructions for using the session token"""
    print("\n" + "=" * 60)
    print("LOGIN SUCCESSFUL!")
    print("=" * 60)
    print("\nYour TikTok session token:\n")
    print(f"TIKTOK_SESSION={session_token}")
    print("\n" + "-" * 60)
    print("\nTo use this token:\n")
    print("Option 1: Set environment variable")
    print(f'  export TIKTOK_SESSION="{session_token}"')
    print("\nOption 2: Add to .env file")
    print(f'  TIKTOK_SESSION={session_token}')
    print("\nOption 3: Add to GitHub Secrets")
    print("  Go to your repo → Settings → Secrets → New secret")
    print("  Name: TIKTOK_SESSION")
    print(f"  Value: {session_token}")
    print("\n" + "-" * 60)
    print("\nThis token expires in approximately 30 days.")
    print("Run 'tiktok-upload auth' again when it expires.")
    print("=" * 60 + "\n")
