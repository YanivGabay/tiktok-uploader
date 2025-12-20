/**
 * Core TikTok upload functionality
 */

import { chromium, BrowserContext, Page } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';

import {
  UploadResult,
  UploaderOptions,
  UploadOptions,
  VideoInfo,
  Cookie,
  SUPPORTED_FORMATS,
  MAX_VIDEO_SIZE_MB,
  TIKTOK_UPLOAD_URL,
  TIKTOK_BASE_URL,
} from './types';

import {
  LoginRequiredError,
  SessionExpiredError,
  UploadFailedError,
  VideoNotFoundError,
  VideoTooLargeError,
  UnsupportedFormatError,
} from './errors';

/**
 * TikTok video uploader using Playwright.
 *
 * @example
 * ```typescript
 * const uploader = new TikTokUploader({ session: process.env.TIKTOK_SESSION });
 * const result = await uploader.upload('video.mp4', 'My caption #fyp');
 * ```
 */
export class TikTokUploader {
  private session?: string;
  private headless: boolean;
  private timeout: number;
  private debug: boolean;
  private cookies?: Cookie[];

  constructor(options: UploaderOptions = {}) {
    this.session = options.session || process.env.TIKTOK_SESSION;
    this.headless = options.headless ?? true;
    this.timeout = options.timeout ?? 60000;
    this.debug = options.debug ?? false;

    if (this.session) {
      this.cookies = this.parseSession(this.session);
    }
  }

  /**
   * Parse session string into cookies list
   */
  private parseSession(session: string): Cookie[] {
    // Try to decode as base64 JSON first
    try {
      const decoded = Buffer.from(session, 'base64').toString('utf-8');
      const cookies = JSON.parse(decoded);
      if (Array.isArray(cookies)) {
        return cookies;
      }
    } catch {
      // Not base64 JSON, treat as raw sessionid
    }

    // Assume it's a raw sessionid
    return [
      { name: 'sessionid', value: session, domain: '.tiktok.com', path: '/' },
      { name: 'sessionid_ss', value: session, domain: '.tiktok.com', path: '/' },
    ];
  }

  /**
   * Validate video file exists and meets requirements
   */
  private validateVideo(videoPath: string): string {
    const resolvedPath = path.resolve(videoPath);

    if (!fs.existsSync(resolvedPath)) {
      throw new VideoNotFoundError(resolvedPath);
    }

    // Check format
    const ext = path.extname(resolvedPath).toLowerCase();
    if (!SUPPORTED_FORMATS.has(ext)) {
      throw new UnsupportedFormatError(ext);
    }

    // Check size
    const stats = fs.statSync(resolvedPath);
    const sizeMb = stats.size / (1024 * 1024);
    if (sizeMb > MAX_VIDEO_SIZE_MB) {
      throw new VideoTooLargeError(sizeMb, MAX_VIDEO_SIZE_MB);
    }

    return resolvedPath;
  }

  /**
   * Setup browser context with cookies
   */
  private async setupContext(context: BrowserContext): Promise<void> {
    if (!this.cookies) {
      throw new LoginRequiredError();
    }

    // Go to TikTok first to set cookies
    const page = await context.newPage();
    await page.goto(TIKTOK_BASE_URL);
    await page.waitForTimeout(1000);

    // Add cookies
    await context.addCookies(this.cookies);
    await page.close();
  }

  /**
   * Dismiss any modal popups
   */
  private async dismissModals(page: Page): Promise<void> {
    const modalButtons = ['Cancel', 'Not now', 'Close', 'Skip', 'Got it'];

    for (const buttonText of modalButtons) {
      try {
        const btn = page.locator(`text=${buttonText}`).first();
        if (await btn.isVisible({ timeout: 1000 })) {
          await btn.click();
          await page.waitForTimeout(500);
          if (this.debug) {
            console.log(`Dismissed modal with '${buttonText}'`);
          }
          return;
        }
      } catch {
        continue;
      }
    }
  }

  /**
   * Find the actual Post submit button
   */
  private async findPostButton(page: Page): Promise<any> {
    // Scroll to bottom to ensure button is in DOM
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);

    // Find all buttons with "Post" text
    const buttons = await page.locator('button').filter({ hasText: 'Post' }).all();

    for (const btn of buttons) {
      try {
        const text = (await btn.textContent() || '').trim();
        const box = await btn.boundingBox();
        // Real Post button is larger and has exact "Post" text
        if (box && text === 'Post' && box.width > 100) {
          return btn;
        }
      } catch {
        continue;
      }
    }

    return null;
  }

  /**
   * Wait for upload to complete
   */
  private async waitForUploadComplete(
    page: Page,
    timeoutSeconds: number,
    onProgress?: (progress: number) => void
  ): Promise<boolean> {
    const iterations = Math.floor(timeoutSeconds / 5);

    for (let i = 0; i < iterations; i++) {
      await page.waitForTimeout(5000);
      const currentUrl = page.url();

      if (onProgress) {
        const progress = Math.min(95, ((i + 1) * 5 * 100) / timeoutSeconds);
        onProgress(Math.round(progress));
      }

      // Success indicators
      if (currentUrl.includes('/content') || currentUrl.includes('/posts')) {
        if (onProgress) {
          onProgress(100);
        }
        return true;
      }

      // Check for exit modal (means upload failed)
      try {
        const exitModal = page.locator('text=Are you sure you want to exit?');
        if (await exitModal.isVisible({ timeout: 500 })) {
          console.error('Exit modal appeared - upload may have failed');
          return false;
        }
      } catch {
        // Continue waiting
      }
    }

    return false;
  }

  /**
   * Upload a video to TikTok.
   *
   * @param video - Path to video file
   * @param description - Video caption/description (can include hashtags)
   * @param options - Upload options
   * @returns Upload result with success status and details
   */
  async upload(
    video: string,
    description: string,
    options: UploadOptions = {}
  ): Promise<UploadResult> {
    const { onProgress } = options;

    // Validate video
    const videoPath = this.validateVideo(video);
    if (this.debug) {
      console.log(`Uploading: ${videoPath}`);
    }

    if (onProgress) {
      onProgress(0);
    }

    const browser = await chromium.launch({ headless: this.headless });
    const context = await browser.newContext({ viewport: { width: 1280, height: 1024 } });

    try {
      // Setup session
      await this.setupContext(context);

      const page = await context.newPage();
      await page.goto(TIKTOK_UPLOAD_URL);
      await page.waitForTimeout(3000);

      if (onProgress) {
        onProgress(10);
      }

      // Check if we're logged in
      if (page.url().toLowerCase().includes('login')) {
        throw new SessionExpiredError();
      }

      // Upload video file
      if (this.debug) {
        console.log('Uploading video file...');
      }
      const fileInput = page.locator("input[type='file']");
      await fileInput.setInputFiles(videoPath);
      await page.waitForTimeout(10000); // Wait for processing

      if (onProgress) {
        onProgress(40);
      }

      // Dismiss any modals
      await this.dismissModals(page);

      // Set description
      if (this.debug) {
        console.log('Setting description...');
      }
      const descField = page.locator("div[contenteditable='true']").first();
      await descField.click();
      await descField.fill(description);
      await page.keyboard.press('Escape'); // Close any dropdown
      await page.waitForTimeout(1000);

      if (onProgress) {
        onProgress(60);
      }

      // Find and click Post button
      if (this.debug) {
        console.log('Clicking Post...');
      }
      const postBtn = await this.findPostButton(page);

      if (!postBtn) {
        if (this.debug) {
          await page.screenshot({ path: 'debug_no_post_button.png' });
        }
        throw new UploadFailedError('Could not find Post button');
      }

      await postBtn.scrollIntoViewIfNeeded();
      await page.waitForTimeout(500);
      await postBtn.click();

      if (onProgress) {
        onProgress(70);
      }

      // Wait for completion
      if (this.debug) {
        console.log('Waiting for upload to complete...');
      }
      const success = await this.waitForUploadComplete(
        page,
        Math.floor(this.timeout / 1000),
        onProgress
      );

      if (success) {
        if (this.debug) {
          console.log('Upload successful!');
        }
        return {
          success: true,
          status: 'uploaded',
        };
      } else {
        if (this.debug) {
          await page.screenshot({ path: 'debug_upload_failed.png' });
        }
        throw new UploadFailedError(
          'Upload did not complete successfully',
          this.debug ? 'debug_upload_failed.png' : undefined
        );
      }
    } catch (error) {
      if (
        error instanceof LoginRequiredError ||
        error instanceof SessionExpiredError ||
        error instanceof UploadFailedError
      ) {
        throw error;
      }
      throw new UploadFailedError(String(error));
    } finally {
      await browser.close();
    }
  }

  /**
   * Upload multiple videos.
   *
   * @param videos - List of video info objects
   * @param onVideoComplete - Callback after each video
   * @returns List of upload results
   */
  async uploadMany(
    videos: VideoInfo[],
    onVideoComplete?: (index: number, result: UploadResult) => void
  ): Promise<UploadResult[]> {
    const results: UploadResult[] = [];

    for (let i = 0; i < videos.length; i++) {
      const videoInfo = videos[i];
      let result: UploadResult;

      try {
        result = await this.upload(videoInfo.video, videoInfo.description, {
          visibility: videoInfo.visibility,
        });
      } catch (error) {
        result = {
          success: false,
          status: 'failed',
          error: String(error),
        };
      }

      results.push(result);

      if (onVideoComplete) {
        onVideoComplete(i, result);
      }
    }

    return results;
  }
}

/**
 * Upload a video to TikTok (convenience function).
 *
 * @example
 * ```typescript
 * await upload('video.mp4', 'My caption #fyp');
 * ```
 */
export async function upload(
  video: string,
  description: string,
  options: UploaderOptions & UploadOptions = {}
): Promise<UploadResult> {
  const uploader = new TikTokUploader(options);
  return uploader.upload(video, description, options);
}

/**
 * Upload multiple videos (convenience function).
 */
export async function uploadMany(
  videos: VideoInfo[],
  options: UploaderOptions = {}
): Promise<UploadResult[]> {
  const uploader = new TikTokUploader(options);
  return uploader.uploadMany(videos);
}
