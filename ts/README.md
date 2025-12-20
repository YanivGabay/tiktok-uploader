# Simple TikTok Uploader (TypeScript/Node.js)

Upload videos to TikTok using Playwright - no API key required.

## Installation

```bash
npm install simple-tiktok-uploader
npx playwright install chromium
```

## Quick Start

```typescript
import { upload } from 'simple-tiktok-uploader';

// Set TIKTOK_SESSION environment variable first
await upload('video.mp4', 'My awesome video #fyp');
```

## CLI Usage

```bash
# Login and get session token
tiktok-upload auth

# Upload a video
tiktok-upload upload video.mp4 -c "My caption #fyp"

# Check if session is valid
tiktok-upload check
```

## API Usage

### Simple Upload

```typescript
import { upload } from 'simple-tiktok-uploader';

const result = await upload('video.mp4', 'My caption #fyp', {
  session: process.env.TIKTOK_SESSION,
  headless: true,
});

console.log(result.success); // true
```

### With Progress Callback

```typescript
import { TikTokUploader } from 'simple-tiktok-uploader';

const uploader = new TikTokUploader({
  session: process.env.TIKTOK_SESSION,
  headless: true,
  debug: true,
});

const result = await uploader.upload('video.mp4', 'My video #fyp', {
  onProgress: (progress) => console.log(`${progress}%`),
});
```

### Batch Upload

```typescript
import { TikTokUploader } from 'simple-tiktok-uploader';

const uploader = new TikTokUploader();

const results = await uploader.uploadMany([
  { video: 'video1.mp4', description: 'First video #fyp' },
  { video: 'video2.mp4', description: 'Second video #viral' },
]);
```

## Authentication

### Interactive Login

```typescript
import { interactiveLogin, printSessionInstructions } from 'simple-tiktok-uploader';

const sessionToken = await interactiveLogin();
printSessionInstructions(sessionToken);
```

### Using Session Token

Set the `TIKTOK_SESSION` environment variable:

```bash
export TIKTOK_SESSION="your_session_token_here"
```

Or pass it directly:

```typescript
const uploader = new TikTokUploader({
  session: 'your_session_token_here',
});
```

## Requirements

- Node.js 18+
- Playwright Chromium browser

## License

MIT
