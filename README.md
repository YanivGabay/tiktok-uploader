# TikTok Uploader

Simple TikTok video uploader using Playwright. No API key required.

## Features

- **Simple API** - Upload videos with one line of code
- **CLI Tool** - Upload from command line
- **Session Management** - Easy login flow, reusable sessions
- **GitHub Actions Ready** - Works in CI/CD pipelines
- **Cross-Platform** - Windows, macOS, Linux

## Installation

```bash
pip install tiktok-uploader
playwright install chromium
```

## Quick Start

### 1. Get Session Token (one-time)

Run this on your local machine (needs a display):

```bash
tiktok-upload auth
```

This opens a browser → you log in → it gives you a session token.

### 2. Upload Videos

**CLI:**
```bash
export TIKTOK_SESSION="your_token_here"
tiktok-upload video.mp4 --caption "My awesome video #fyp #viral"
```

**Python:**
```python
from tiktok_uploader import upload

upload("video.mp4", "My awesome video #fyp #viral")
```

## Usage

### Command Line

```bash
# Login and get session token
tiktok-upload auth

# Upload a video
tiktok-upload upload video.mp4 --caption "Hello TikTok! #fyp"

# Upload with visibility setting
tiktok-upload upload video.mp4 --caption "Friends only" --visibility friends

# Check if session is valid
tiktok-upload check
```

### Python API

```python
from tiktok_uploader import TikTokUploader, upload

# Simple one-liner (reads TIKTOK_SESSION from env)
upload("video.mp4", "My caption #fyp")

# With more control
uploader = TikTokUploader(
    session="your_session_token",  # or reads from TIKTOK_SESSION env
    headless=True,
)

result = uploader.upload(
    video="video.mp4",
    description="My awesome video #fyp #viral",
    visibility="everyone",  # or "friends", "private"
)

if result.success:
    print("Upload successful!")
else:
    print(f"Upload failed: {result.error}")
```

### Upload Multiple Videos

```python
from tiktok_uploader import TikTokUploader

uploader = TikTokUploader()

videos = [
    {"video": "video1.mp4", "description": "First video #fyp"},
    {"video": "video2.mp4", "description": "Second video #viral"},
]

results = uploader.upload_many(videos)
```

## GitHub Actions

```yaml
name: Upload to TikTok

on:
  workflow_dispatch:

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install tiktok-uploader
          playwright install chromium --with-deps

      - name: Upload to TikTok
        run: tiktok-upload upload video.mp4 --caption "Automated upload! #fyp"
        env:
          TIKTOK_SESSION: ${{ secrets.TIKTOK_SESSION }}
```

## Session Management

### Getting a Session Token

```bash
tiktok-upload auth
```

This opens a browser for you to log in. After login, it outputs a session token.

### Using the Session Token

**Option 1: Environment Variable**
```bash
export TIKTOK_SESSION="your_token"
```

**Option 2: GitHub Secrets**
1. Go to your repo → Settings → Secrets → New secret
2. Name: `TIKTOK_SESSION`
3. Value: your token

**Option 3: Pass directly**
```python
uploader = TikTokUploader(session="your_token")
```

### Session Expiration

Sessions last approximately 30 days. When expired, run `tiktok-upload auth` again.

## Error Handling

```python
from tiktok_uploader import upload, SessionExpiredError, LoginRequiredError

try:
    upload("video.mp4", "My caption")
except LoginRequiredError:
    print("No session found. Run 'tiktok-upload auth' first.")
except SessionExpiredError:
    print("Session expired. Run 'tiktok-upload auth' to refresh.")
```

## Requirements

- Python 3.9+
- Playwright (with Chromium)

## Limitations

- TikTok may change their site, which could break uploads
- Sessions expire after ~30 days
- Interactive login requires a display (run locally, use token in CI)

## License

MIT
