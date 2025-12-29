/**
 * Custom error classes for TikTok Uploader
 */

/** Base error class for all TikTok uploader errors */
export class TikTokUploaderError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'TikTokUploaderError';
  }
}

/** Error when session has expired */
export class SessionExpiredError extends TikTokUploaderError {
  constructor(message = 'Session has expired. Please login again with tiktok-upload auth') {
    super(message);
    this.name = 'SessionExpiredError';
  }
}

/** Error when no session/login is found */
export class LoginRequiredError extends TikTokUploaderError {
  constructor(
    message = 'No TikTok session found. Run "tiktok-upload auth" or set TIKTOK_SESSION environment variable.'
  ) {
    super(message);
    this.name = 'LoginRequiredError';
  }
}

/** Error when upload fails */
export class UploadFailedError extends TikTokUploaderError {
  screenshotPath?: string;

  constructor(message: string, screenshotPath?: string) {
    super(message);
    this.name = 'UploadFailedError';
    this.screenshotPath = screenshotPath;
  }
}

/** Error when video file is not found */
export class VideoNotFoundError extends TikTokUploaderError {
  path: string;

  constructor(path: string) {
    super(`Video file not found: ${path}`);
    this.name = 'VideoNotFoundError';
    this.path = path;
  }
}

/** Error when video exceeds size limit */
export class VideoTooLargeError extends TikTokUploaderError {
  sizeMb: number;
  maxSizeMb: number;

  constructor(sizeMb: number, maxSizeMb: number) {
    super(`Video too large: ${sizeMb.toFixed(1)}MB exceeds limit of ${maxSizeMb}MB`);
    this.name = 'VideoTooLargeError';
    this.sizeMb = sizeMb;
    this.maxSizeMb = maxSizeMb;
  }
}

/** Error when video format is not supported */
export class UnsupportedFormatError extends TikTokUploaderError {
  extension: string;

  constructor(extension: string) {
    super(`Unsupported video format: ${extension}. Supported formats: .mp4, .mov, .webm`);
    this.name = 'UnsupportedFormatError';
    this.extension = extension;
  }
}
