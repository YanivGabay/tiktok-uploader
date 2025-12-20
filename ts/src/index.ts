/**
 * Simple TikTok Uploader - TypeScript/Node.js version
 *
 * Upload videos to TikTok using Playwright - no API key required.
 *
 * @example
 * ```typescript
 * import { upload, TikTokUploader } from 'simple-tiktok-uploader';
 *
 * // Simple one-liner (reads TIKTOK_SESSION from env)
 * await upload('video.mp4', 'My awesome video #fyp');
 *
 * // Or with more control
 * const uploader = new TikTokUploader({ headless: true });
 * const result = await uploader.upload('video.mp4', 'My video #fyp');
 * console.log(result.status);
 * ```
 */

// Main uploader
export { TikTokUploader, upload, uploadMany } from './uploader';

// Authentication
export { getSession, interactiveLogin, printSessionInstructions } from './auth';

// Types
export {
  UploadResult,
  UploaderOptions,
  UploadOptions,
  VideoInfo,
  Visibility,
  Cookie,
  SUPPORTED_FORMATS,
  MAX_VIDEO_SIZE_MB,
} from './types';

// Errors
export {
  TikTokUploaderError,
  SessionExpiredError,
  LoginRequiredError,
  UploadFailedError,
  VideoNotFoundError,
  VideoTooLargeError,
  UnsupportedFormatError,
} from './errors';
