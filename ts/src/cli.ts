#!/usr/bin/env node
/**
 * Command-line interface for TikTok Uploader
 */

import * as fs from 'fs';
import * as path from 'path';

import { TikTokUploader } from './uploader';
import { getSession, interactiveLogin, printSessionInstructions } from './auth';
import { LoginRequiredError, SessionExpiredError, TikTokUploaderError } from './errors';
import { SUPPORTED_FORMATS } from './types';

const VERSION = '0.1.0';

function showHelp(): void {
  console.log(`
tiktok-upload - Upload videos to TikTok from the command line

Usage:
  tiktok-upload auth                    Login and get session token
  tiktok-upload upload <video> -c <caption>  Upload a video
  tiktok-upload check                   Verify session is valid
  tiktok-upload --help                  Show this help
  tiktok-upload --version               Show version

Commands:
  auth      Open browser for TikTok login and get session token
  upload    Upload a video to TikTok
  check     Check if the current session is valid

Upload Options:
  -c, --caption <text>     Video caption/description (required)
  --visibility <type>      Who can view: everyone, friends, private (default: everyone)
  --visible                Show browser window (not headless)
  --debug                  Enable debug mode (saves screenshots on error)
  -q, --quiet              Suppress progress output

Environment Variables:
  TIKTOK_SESSION    Session token from 'tiktok-upload auth'

Examples:
  tiktok-upload auth
  tiktok-upload upload video.mp4 -c "Hello TikTok! #fyp"
  tiktok-upload upload video.mp4 -c "My video" --visibility friends
  tiktok-upload check
`);
}

function showVersion(): void {
  console.log(`tiktok-upload ${VERSION}`);
}

async function cmdAuth(args: string[]): Promise<number> {
  let saveToFile: string | undefined;

  // Parse --save-to-file option
  const saveIndex = args.indexOf('--save-to-file');
  if (saveIndex !== -1 && args[saveIndex + 1]) {
    saveToFile = args[saveIndex + 1];
  }

  try {
    const sessionToken = await interactiveLogin(saveToFile);
    printSessionInstructions(sessionToken);
    return 0;
  } catch (error) {
    console.error(`Error: ${error}`);
    return 1;
  }
}

async function cmdUpload(args: string[]): Promise<number> {
  // Parse arguments
  let videoPath: string | undefined;
  let caption: string | undefined;
  let visibility: 'everyone' | 'friends' | 'private' = 'everyone';
  let visible = false;
  let debug = false;
  let quiet = false;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '-c' || arg === '--caption') {
      caption = args[++i];
    } else if (arg === '--visibility') {
      const v = args[++i];
      if (v === 'everyone' || v === 'friends' || v === 'private') {
        visibility = v;
      }
    } else if (arg === '--visible') {
      visible = true;
    } else if (arg === '--debug') {
      debug = true;
    } else if (arg === '-q' || arg === '--quiet') {
      quiet = true;
    } else if (!arg.startsWith('-') && !videoPath) {
      videoPath = arg;
    }
  }

  if (!videoPath) {
    console.error('Error: Video file path is required');
    return 1;
  }

  if (!caption) {
    console.error('Error: Caption is required (-c or --caption)');
    return 1;
  }

  try {
    // Get session
    let session: string;
    try {
      session = getSession();
    } catch {
      console.error('Error: No TikTok session found.');
      console.error("Run 'tiktok-upload auth' first to login.");
      return 1;
    }

    // Create uploader
    const uploader = new TikTokUploader({
      session,
      headless: !visible,
      debug,
    });

    // Progress callback
    const showProgress = (progress: number): void => {
      const barWidth = 30;
      const filled = Math.floor((barWidth * progress) / 100);
      const bar = '\u2588'.repeat(filled) + '\u2591'.repeat(barWidth - filled);
      process.stdout.write(`\r  [${bar}] ${progress}%`);
      if (progress === 100) {
        console.log();
      }
    };

    console.log(`Uploading: ${videoPath}`);
    console.log(`Caption: ${caption.length > 50 ? caption.substring(0, 50) + '...' : caption}`);
    console.log();

    const result = await uploader.upload(videoPath, caption, {
      visibility,
      onProgress: quiet ? undefined : showProgress,
    });

    if (result.success) {
      console.log('\n\u2705 Upload successful!');
      if (result.videoUrl) {
        console.log(`   URL: ${result.videoUrl}`);
      }
      return 0;
    } else {
      console.error(`\n\u274C Upload failed: ${result.error}`);
      return 1;
    }
  } catch (error) {
    if (error instanceof SessionExpiredError) {
      console.error(`\n\u274C ${error.message}`);
    } else if (error instanceof TikTokUploaderError) {
      console.error(`\n\u274C Error: ${error.message}`);
    } else {
      console.error(`\n\u274C Unexpected error: ${error}`);
      if (debug) {
        console.error(error);
      }
    }
    return 1;
  }
}

async function cmdCheck(): Promise<number> {
  try {
    const session = getSession();
    console.log('\u2705 Session found');
    console.log('   Validating session...');
    // Just verify session can be parsed
    new TikTokUploader({ session, headless: true });
    console.log('   Session appears valid');
    return 0;
  } catch (error) {
    if (error instanceof LoginRequiredError) {
      console.log('\u274C No session found');
      console.log("   Run 'tiktok-upload auth' to login");
    } else if (error instanceof SessionExpiredError) {
      console.log('\u274C Session expired');
      console.log("   Run 'tiktok-upload auth' to get a new session");
    } else {
      console.error(`Error: ${error}`);
    }
    return 1;
  }
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);

  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    showHelp();
    process.exit(0);
  }

  if (args.includes('--version') || args.includes('-v')) {
    showVersion();
    process.exit(0);
  }

  const command = args[0];
  const commandArgs = args.slice(1);

  let exitCode = 0;

  switch (command) {
    case 'auth':
      exitCode = await cmdAuth(commandArgs);
      break;
    case 'upload':
      exitCode = await cmdUpload(commandArgs);
      break;
    case 'check':
      exitCode = await cmdCheck();
      break;
    default:
      // Check if first arg looks like a video file (shorthand for upload)
      const ext = path.extname(command).toLowerCase();
      if (SUPPORTED_FORMATS.has(ext)) {
        exitCode = await cmdUpload(args);
      } else {
        console.error(`Unknown command: ${command}`);
        showHelp();
        exitCode = 1;
      }
  }

  process.exit(exitCode);
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
