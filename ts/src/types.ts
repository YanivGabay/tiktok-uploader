/**
 * Type definitions for simple-tiktok-uploader
 */

/** Visibility options for uploaded videos */
export type Visibility = 'everyone' | 'friends' | 'private';

/** Result of an upload operation */
export interface UploadResult {
  success: boolean;
  videoId?: string;
  videoUrl?: string;
  status: string;
  error?: string;
}

/** Options for TikTokUploader constructor */
export interface UploaderOptions {
  /** Session token (base64 encoded cookies or raw sessionid) */
  session?: string;
  /** Run browser in headless mode (default: true) */
  headless?: boolean;
  /** Default timeout in milliseconds (default: 60000) */
  timeout?: number;
  /** Enable debug logging and save screenshots on error */
  debug?: boolean;
}

/** Options for upload method */
export interface UploadOptions {
  /** Who can view the video (default: 'everyone') */
  visibility?: Visibility;
  /** Optional callback for progress updates (0-100) */
  onProgress?: (progress: number) => void;
}

/** Video info for batch uploads */
export interface VideoInfo {
  /** Path to video file */
  video: string;
  /** Video caption/description */
  description: string;
  /** Visibility setting */
  visibility?: Visibility;
}

/** Cookie structure for session */
export interface Cookie {
  name: string;
  value: string;
  domain: string;
  path: string;
}

/** Auth cookies we capture from TikTok */
export const AUTH_COOKIES = new Set([
  'sessionid',
  'sessionid_ss',
  'sid_tt',
  'uid_tt',
  'sid_guard',
]);

/** Supported video formats */
export const SUPPORTED_FORMATS = new Set(['.mp4', '.mov', '.webm']);

/** Maximum video size in MB */
export const MAX_VIDEO_SIZE_MB = 287;

/** TikTok URLs */
export const TIKTOK_UPLOAD_URL = 'https://www.tiktok.com/creator-center/upload?lang=en';
export const TIKTOK_BASE_URL = 'https://www.tiktok.com/';
