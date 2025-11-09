#!/usr/bin/env python3
"""Get sessionKey from claude.ai for OAuth authentication."""

import webbrowser
import time
from pathlib import Path
from typing import Optional

# Import automatic extractor
try:
    from utils.auto_session_extractor import extract_session_key_auto
    AUTO_EXTRACTOR_AVAILABLE = True
except ImportError:
    AUTO_EXTRACTOR_AVAILABLE = False


def get_session_key_interactive() -> Optional[str]:
    """Get sessionKey from claude.ai interactively.

    This will:
    1. Open claude.ai in browser
    2. Show instructions for getting sessionKey
    3. Wait for user to paste the sessionKey

    Returns:
        sessionKey or None if cancelled
    """
    print()
    print("="*70)
    print("  🔐 Getting sessionKey from claude.ai")
    print("="*70)
    print()
    print("  This will open claude.ai in your browser.")
    print("  You need to copy the sessionKey cookie from your browser.")
    print()

    # Ask if user wants to continue
    try:
        response = input("  Press Enter to continue (or Ctrl+C to cancel): ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        print("  ❌ Cancelled")
        return None

    # Open claude.ai
    print()
    print("  🌐 Opening claude.ai...")
    print()

    try:
        webbrowser.open("https://claude.ai/new")
        time.sleep(2)  # Give browser time to open
    except Exception as e:
        print(f"  ⚠️  Could not open browser: {e}")
        print("     Please open https://claude.ai/new manually")

    # Show instructions
    print("="*70)
    print("  📋 How to get your sessionKey:")
    print("="*70)
    print()
    print("  1. Make sure you're logged in to claude.ai")
    print("  2. Open Developer Tools (F12 or Ctrl+Shift+I)")
    print("  3. Go to 'Application' tab (Chrome) or 'Storage' tab (Firefox)")
    print("  4. Click 'Cookies' → 'https://claude.ai'")
    print("  5. Find the cookie named 'sessionKey'")
    print("  6. Copy its VALUE (should start with 'sk-ant-sid01-')")
    print("  7. Paste it below")
    print()
    print("="*70)
    print()

    # Get sessionKey from user
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            session_key = input("  Paste sessionKey here: ").strip()

            if not session_key:
                print("  ⚠️  Empty input, try again")
                continue

            # Validate format
            if not session_key.startswith("sk-ant-sid01-"):
                print()
                print("  ⚠️  Warning: sessionKey should start with 'sk-ant-sid01-'")
                print(f"     You entered: {session_key[:20]}...")
                print()

                # Ask if they want to continue anyway
                try:
                    confirm = input("  Use this token anyway? [y/N]: ").strip().lower()
                    if confirm != 'y':
                        if attempt < max_attempts - 1:
                            print("  Try again...")
                            continue
                        else:
                            print("  ❌ Max attempts reached")
                            return None
                except (KeyboardInterrupt, EOFError):
                    print()
                    print("  ❌ Cancelled")
                    return None

            # Looks good!
            print()
            print("  ✅ sessionKey received!")
            print(f"     {session_key[:20]}...{session_key[-10:]}")
            return session_key

        except (KeyboardInterrupt, EOFError):
            print()
            print("  ❌ Cancelled")
            return None

    print()
    print("  ❌ Failed to get sessionKey")
    return None


def save_session_key_to_env(session_key: str) -> bool:
    """Save sessionKey to .env file.

    Args:
        session_key: sessionKey to save

    Returns:
        True if successful
    """
    try:
        # Find .env file (in project root, relative to this script)
        # Script is in src/utils/, so go up 2 levels
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
        env_file = project_root / ".env"

        print()
        print(f"  💾 Saving sessionKey to .env...")
        print(f"     Location: {env_file}")

        # Read existing .env content
        if env_file.exists():
            with open(env_file, 'r') as f:
                lines = f.readlines()
        else:
            lines = []

        # Update or add CLAUDE_CODE_OAUTH_TOKEN line
        # (We'll reuse this variable name for backwards compatibility)
        found = False
        for i, line in enumerate(lines):
            if line.startswith('CLAUDE_CODE_OAUTH_TOKEN='):
                lines[i] = f'CLAUDE_CODE_OAUTH_TOKEN={session_key}\n'
                found = True
                break
            elif line.startswith('ANTHROPIC_API_KEY='):
                # Also update API key field
                lines[i] = f'ANTHROPIC_API_KEY={session_key}\n'

        if not found:
            # Add new line
            if lines and not lines[-1].endswith('\n'):
                lines.append('\n')
            lines.append(f'\nCLAUDE_CODE_OAUTH_TOKEN={session_key}\n')
            lines.append(f'ANTHROPIC_API_KEY={session_key}\n')

        # Write back to file
        with open(env_file, 'w') as f:
            f.writelines(lines)

        print("  ✅ sessionKey saved to .env!")
        return True

    except Exception as e:
        print(f"  ❌ Failed to save sessionKey: {e}")
        return False


def setup_claude_ai_session() -> Optional[str]:
    """Interactive setup for claude.ai session.

    Uses FULL AUTO extraction (Selenium) by default.
    Falls back to manual if auto fails.

    Returns:
        sessionKey or None if setup failed
    """
    session_key = None

    # Try FULL AUTO extraction first (recommended!)
    if AUTO_EXTRACTOR_AVAILABLE:
        print()
        print("  🤖 Using FULL AUTO sessionKey extraction!")
        print("     You just need to sign in - Python does the rest!")
        print()

        session_key = extract_session_key_auto()

    # Fallback to manual if auto failed
    if not session_key:
        print()
        print("  ⚠️  Auto extraction not available or failed")
        print("     Falling back to manual method...")
        print()

        session_key = get_session_key_interactive()

    if session_key:
        if save_session_key_to_env(session_key):
            print()
            print("="*70)
            print("  🎉 Setup Complete!")
            print("="*70)
            print()
            print("  ✅ sessionKey saved to .env")
            print("  ✅ Ready to use with claude.ai proxy!")
            print()
            print("  💡 This will use your Claude Max/Pro subscription")
            print()
            return session_key
        else:
            print()
            print("  ⚠️  Could not save to .env, but you have the token")
            return session_key

    return None


if __name__ == "__main__":
    # Test the setup
    session_key = setup_claude_ai_session()
    if session_key:
        print(f"✅ Got sessionKey: {session_key[:20]}...")
    else:
        print("❌ Setup failed")
