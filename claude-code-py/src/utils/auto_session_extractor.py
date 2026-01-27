#!/usr/bin/env python3
"""FULLY AUTOMATIC sessionKey extraction using Selenium.

This opens a browser, lets you log in, then AUTOMATICALLY extracts sessionKey.
TRUE "FULL AUTO" - you just sign in, Python does the rest!
"""

import sys
import time
import subprocess
from typing import Optional


def ensure_selenium_installed() -> bool:
    """Ensure Selenium and webdriver-manager are installed.

    Returns:
        True if successful
    """
    missing = []

    # Check Selenium
    try:
        import selenium
    except ImportError:
        missing.append("selenium")

    # Check webdriver-manager (auto-downloads drivers)
    try:
        import webdriver_manager
    except ImportError:
        missing.append("webdriver-manager")

    # Install missing packages
    if missing:
        print(f"  [*] Installing automation tools: {', '.join(missing)}...")
        print("     (This may take a moment...)")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--user", *missing],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"  [OK] Installed: {', '.join(missing)}")
            return True
        except subprocess.CalledProcessError:
            # Try without --user
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", *missing],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print(f"  [OK] Installed: {', '.join(missing)}")
                return True
            except subprocess.CalledProcessError:
                print(f"  [ERR] Failed to install: {', '.join(missing)}")
                print(f"     Please run: pip install {' '.join(missing)}")
                return False

    return True


def extract_session_key_auto() -> Optional[str]:
    """Automatically extract sessionKey from claude.ai.

    This will:
    1. Open claude.ai in automated browser
    2. Wait for you to sign in
    3. AUTOMATICALLY extract sessionKey cookie
    4. Close browser and return sessionKey

    Returns:
        sessionKey or None if failed
    """
    # Ensure Selenium is installed
    if not ensure_selenium_installed():
        return None

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError as e:
        print(f"  [ERR] Import error: {e}")
        print("     Please restart the script to reload packages")
        return None

    print()
    print("=" * 70)
    print("  FULL AUTO sessionKey Extraction")
    print("=" * 70)
    print()
    print("  Opening automated browser...")
    print("     Please sign in when the browser opens")
    print("     Python will AUTOMATICALLY extract sessionKey when done!")
    print()

    driver = None
    try:
        # Setup Chrome options
        chrome_options = Options()
        # Don't use headless - user needs to see to log in
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Create driver with auto-downloaded ChromeDriver
        print("  [*] Setting up Chrome driver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Navigate to claude.ai
        print("  [*] Opening claude.ai...")
        driver.get("https://claude.ai/new")

        print()
        print("=" * 70)
        print("  [*] Please sign in to claude.ai in the opened browser")
        print("=" * 70)
        print()
        print("  [...] Waiting for you to sign in...")
        print("     (Python will auto-detect when you're logged in)")
        print()

        # Wait for user to log in (check for sessionKey cookie)
        max_wait = 300  # 5 minutes max
        check_interval = 2  # Check every 2 seconds
        elapsed = 0

        session_key = None

        while elapsed < max_wait:
            time.sleep(check_interval)
            elapsed += check_interval

            # Try to get sessionKey cookie
            cookies = driver.get_cookies()
            for cookie in cookies:
                if cookie["name"] == "sessionKey":
                    session_key = cookie["value"]
                    break

            if session_key:
                print()
                print("  [OK] Login detected!")
                print("  [KEY] sessionKey extracted automatically!")
                print(f"     {session_key[:20]}...{session_key[-10:]}")
                break

            # Show progress
            if elapsed % 10 == 0:
                print(f"  [...] Still waiting... ({elapsed}s elapsed)")

        if not session_key:
            print()
            print("  [TIME]  Timeout waiting for login")
            print("     Please make sure you're fully logged in to claude.ai")
            return None

        return session_key

    except Exception as e:
        print()
        print(f"  [ERR] Error during automation: {e}")
        print()
        print("  [TIP] If Chrome didn't open, you might need to:")
        print("     1. Install Google Chrome")
        print("     2. Try restarting the script")
        return None

    finally:
        # Always close browser
        if driver:
            print()
            print("  [*] Closing browser...")
            try:
                driver.quit()
            except:
                pass


if __name__ == "__main__":
    # Test the auto extraction
    session_key = extract_session_key_auto()
    if session_key:
        print()
        print(f"[OK] Success! Got sessionKey: {session_key[:20]}...")
    else:
        print()
        print("[ERR] Failed to extract sessionKey")
