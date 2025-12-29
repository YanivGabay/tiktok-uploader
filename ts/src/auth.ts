/**
 * Authentication and session management for TikTok Uploader
 */

import { chromium } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

import { Cookie, AUTH_COOKIES } from './types';
import { LoginRequiredError } from './errors';

/**
 * Open a browser for user to login interactively.
 *
 * @param saveToFile - Optional path to save session token
 * @param timeout - Max time to wait for login (milliseconds)
 * @returns Session token (base64 encoded cookies)
 */
export async function interactiveLogin(
  saveToFile?: string,
  timeout = 300000 // 5 minutes
): Promise<string> {
  console.log('Opening browser for TikTok login...');
  console.log('Please log in to your TikTok account.');
  console.log('The browser will close automatically after login is detected.\n');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();

  // Go to TikTok login
  await page.goto('https://www.tiktok.com/login');

  console.log('Waiting for login...');
  console.log('(You have 5 minutes to complete the login)\n');

  // Wait for successful login by checking for session cookie
  let sessionFound = false;
  const checkInterval = 2000; // Check every 2 seconds
  let elapsed = 0;

  while (elapsed < timeout) {
    await page.waitForTimeout(checkInterval);
    elapsed += checkInterval;

    // Check cookies
    const cookies = await context.cookies();
    const sessionCookies = cookies.filter((c) => AUTH_COOKIES.has(c.name));

    if (sessionCookies.some((c) => c.name === 'sessionid')) {
      sessionFound = true;
      console.log('Login detected!');
      break;
    }

    // Also check if we've navigated away from login page
    const url = page.url().toLowerCase();
    if (!url.includes('login') && url.includes('/foryou')) {
      // Give it a moment to set cookies
      await page.waitForTimeout(2000);
      const newCookies = await context.cookies();
      const newSessionCookies = newCookies.filter((c) => AUTH_COOKIES.has(c.name));
      if (newSessionCookies.some((c) => c.name === 'sessionid')) {
        sessionFound = true;
        console.log('Login detected!');
        break;
      }
    }
  }

  if (!sessionFound) {
    await browser.close();
    throw new LoginRequiredError('Login timed out. Please try again.');
  }

  // Extract auth cookies
  const cookies = await context.cookies();
  const authCookies: Cookie[] = cookies
    .filter((c) => AUTH_COOKIES.has(c.name))
    .map((c) => ({
      name: c.name,
      value: c.value,
      domain: c.domain,
      path: c.path,
    }));

  await browser.close();

  // Encode as base64 JSON
  const sessionToken = Buffer.from(JSON.stringify(authCookies)).toString('base64');

  // Save to file if requested
  if (saveToFile) {
    const savePath = path.resolve(saveToFile);
    fs.writeFileSync(savePath, sessionToken);
    console.log(`\nSession saved to: ${savePath}`);
  }

  return sessionToken;
}

/**
 * Get session from various sources.
 *
 * Priority:
 * 1. Passed session parameter
 * 2. Environment variable
 * 3. Session file
 *
 * @param session - Direct session string
 * @param envVar - Environment variable name to check
 * @param filePath - Path to session file
 * @returns Session token string
 */
export function getSession(
  session?: string,
  envVar = 'TIKTOK_SESSION',
  filePath?: string
): string {
  // Check direct parameter
  if (session) {
    return session;
  }

  // Check environment variable
  const envSession = process.env[envVar];
  if (envSession) {
    return envSession;
  }

  // Check file
  if (filePath) {
    const resolvedPath = path.resolve(filePath);
    if (fs.existsSync(resolvedPath)) {
      return fs.readFileSync(resolvedPath, 'utf-8').trim();
    }
  }

  // Check default session file location
  const defaultSessionFile = path.join(os.homedir(), '.tiktok_session');
  if (fs.existsSync(defaultSessionFile)) {
    return fs.readFileSync(defaultSessionFile, 'utf-8').trim();
  }

  throw new LoginRequiredError();
}

/**
 * Print instructions for using the session token
 */
export function printSessionInstructions(sessionToken: string): void {
  console.log('\n' + '='.repeat(60));
  console.log('LOGIN SUCCESSFUL!');
  console.log('='.repeat(60));
  console.log('\nYour TikTok session token:\n');
  console.log(`TIKTOK_SESSION=${sessionToken}`);
  console.log('\n' + '-'.repeat(60));
  console.log('\nTo use this token:\n');
  console.log('Option 1: Set environment variable');
  console.log(`  export TIKTOK_SESSION="${sessionToken}"`);
  console.log('\nOption 2: Add to .env file');
  console.log(`  TIKTOK_SESSION=${sessionToken}`);
  console.log('\nOption 3: Add to GitHub Secrets');
  console.log('  Go to your repo -> Settings -> Secrets -> New secret');
  console.log('  Name: TIKTOK_SESSION');
  console.log(`  Value: ${sessionToken}`);
  console.log('\n' + '-'.repeat(60));
  console.log('\nThis token expires in approximately 30 days.');
  console.log('Run "tiktok-upload auth" again when it expires.');
  console.log('='.repeat(60) + '\n');
}
