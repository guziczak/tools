#!/usr/bin/env python3
"""Automatic Claude Max token setup."""

import os
import sys
import subprocess
import time
import re
from pathlib import Path
from typing import Optional

# Import OAuth to API key converter
try:
    from utils.oauth_to_apikey import generate_api_key_from_oauth

    OAUTH_TO_APIKEY_AVAILABLE = True
except ImportError:
    OAUTH_TO_APIKEY_AVAILABLE = False

# Import claude.ai session setup
try:
    from utils.claude_ai_session import setup_claude_ai_session

    CLAUDE_AI_SESSION_AVAILABLE = True
except ImportError:
    CLAUDE_AI_SESSION_AVAILABLE = False


def check_npm_installed() -> bool:
    """Check if npm is installed.

    Returns:
        True if npm is available
    """
    try:
        # On Windows, use shell=True to access npm from PATH
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=True,  # Important for Windows!
        )
        return result.returncode == 0
    except Exception:
        return False


def install_claude_code() -> bool:
    """Install official Claude Code via npm.

    Returns:
        True if successful
    """
    print("  📦 Installing @anthropic-ai/claude-code...")
    print("     (This may take a minute...)")
    print()

    try:
        result = subprocess.run(
            ["npm", "install", "-g", "@anthropic-ai/claude-code"],
            capture_output=True,
            text=True,
            timeout=120,
            shell=True,  # Important for Windows!
        )

        if result.returncode == 0:
            print("  ✅ Claude Code installed successfully!")
            return True
        else:
            print(f"  ❌ Installation failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("  ❌ Installation timed out")
        return False
    except Exception as e:
        print(f"  ❌ Installation error: {e}")
        return False


def run_claude_setup_token() -> Optional[str]:
    """Run claude setup-token command and extract token.

    This will open a browser for the user to authenticate.
    The token is parsed from the command output.

    Returns:
        Access token if successful, None otherwise
    """
    print()
    print("  🌐 Opening browser for authentication...")
    print("     Please sign in with your Claude Max/Pro account")
    print()

    try:
        # Run claude setup-token and capture output
        # This will open browser and wait for user to authenticate
        result = subprocess.run(
            ["claude", "setup-token"],
            capture_output=True,  # Capture stdout/stderr
            text=True,  # Decode as text
            timeout=300,  # 5 minutes for user to authenticate
            shell=True,  # Important for Windows!
        )

        # Combine stdout and stderr (token might be in either)
        output = result.stdout + result.stderr

        # Look for token in output (format: sk-ant-oat01-...)
        token_pattern = r"(sk-ant-oat01-[A-Za-z0-9_-]+)"
        match = re.search(token_pattern, output)

        if match:
            token = match.group(1)
            print()
            print("  ✅ Token captured successfully!")
            print(f"     Token: {token[:20]}...{token[-10:]}")
            return token
        elif result.returncode == 0:
            # Command succeeded but no token found in output
            print()
            print("  ⚠️  Command succeeded but token not found in output")
            print("     Token might be in file instead...")
            return None
        else:
            print()
            print("  ⚠️  Token generation may have failed")
            return None

    except subprocess.TimeoutExpired:
        print()
        print("  ⚠️  Timed out waiting for authentication")
        return None
    except Exception as e:
        print()
        print(f"  ❌ Error: {e}")
        return None


def save_api_key_to_env(api_key: str) -> bool:
    """Save API key to .env file.

    Args:
        api_key: API key to save

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
        print(f"  💾 Saving API key to .env...")
        print(f"     Location: {env_file}")

        # Read existing .env content
        if env_file.exists():
            with open(env_file, "r") as f:
                lines = f.readlines()
        else:
            lines = []

        # Update or add ANTHROPIC_API_KEY line
        found = False
        for i, line in enumerate(lines):
            if line.startswith("ANTHROPIC_API_KEY="):
                lines[i] = f"ANTHROPIC_API_KEY={api_key}\n"
                found = True
                break

        if not found:
            lines.append(f"\nANTHROPIC_API_KEY={api_key}\n")

        # Write back to file
        with open(env_file, "w") as f:
            f.writelines(lines)

        print(f"  ✅ API key saved to .env!")
        return True

    except Exception as e:
        print(f"  ❌ Error saving API key: {e}")
        return False


def save_token_to_env(token: str) -> bool:
    """Save token to .env file.

    Args:
        token: Access token to save

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
        print(f"  💾 Saving token to .env...")
        print(f"     Location: {env_file}")

        # Read existing .env content
        if env_file.exists():
            with open(env_file, "r") as f:
                lines = f.readlines()
        else:
            lines = []

        # Check if CLAUDE_CODE_OAUTH_TOKEN already exists
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("CLAUDE_CODE_OAUTH_TOKEN="):
                # Update existing line
                lines[i] = f"CLAUDE_CODE_OAUTH_TOKEN={token}\n"
                updated = True
                break

        # Add new line if not found
        if not updated:
            # Add blank line if file is not empty and doesn't end with newline
            if lines and not lines[-1].endswith("\n"):
                lines.append("\n")
            lines.append(f"CLAUDE_CODE_OAUTH_TOKEN={token}\n")

        # Write back to file
        with open(env_file, "w") as f:
            f.writelines(lines)

        print("  ✅ Token saved to .env!")
        return True

    except Exception as e:
        print(f"  ❌ Failed to save token: {e}")
        return False


def get_token_path() -> Path:
    """Get path to Claude token file.

    Returns:
        Path to oauth_token.json
    """
    return Path.home() / ".claude" / "oauth_token.json"


def wait_for_token(timeout: int = 10) -> bool:
    """Wait for token file to be created.

    Args:
        timeout: Maximum seconds to wait

    Returns:
        True if token file exists
    """
    token_path = get_token_path()
    start = time.time()

    while time.time() - start < timeout:
        if token_path.exists():
            return True
        time.sleep(0.5)

    return False


def read_token() -> Optional[str]:
    """Read access token from Claude Code token file.

    Returns:
        Access token or None
    """
    import json

    token_path = get_token_path()

    if not token_path.exists():
        return None

    try:
        with open(token_path, "r") as f:
            data = json.load(f)

        return data.get("accessToken") or data.get("access_token")
    except Exception as e:
        print(f"  ❌ Error reading token: {e}")
        return None


def automatic_claude_max_setup() -> Optional[str]:
    """Automatically set up Claude Max authentication.

    This will:
    1. Open claude.ai in browser
    2. Ask user to copy sessionKey cookie
    3. Save sessionKey to .env
    4. Return sessionKey for immediate use

    Returns:
        sessionKey or None if setup failed
    """
    print()
    print("=" * 70)
    print("  🚀 Automatic Claude Max Setup")
    print("=" * 70)
    print()

    # Use new claude.ai session setup (gets sessionKey from browser)
    if CLAUDE_AI_SESSION_AVAILABLE:
        return setup_claude_ai_session()

    # Fallback to old method (won't work but kept for compatibility)
    print("  ⚠️  New session setup not available")
    print("     Falling back to old method...")
    print()

    # Step 1: Check npm
    print("  🔍 Checking for npm...")
    if not check_npm_installed():
        print()
        print("  ❌ npm is not installed!")
        print()
        print("     Install Node.js from: https://nodejs.org/")
        print("     Then run this again!")
        print()
        return None
    print("  ✅ npm found!")
    print()

    # Step 2: Install Claude Code
    if not install_claude_code():
        print()
        print("  ❌ Failed to install Claude Code")
        print()
        print("     Try manually:")
        print("     npm install -g @anthropic-ai/claude-code")
        print()
        return None

    # Step 3: Run setup-token and capture token
    print()
    print("=" * 70)
    print("  🔐 Generating Claude Max Token")
    print("=" * 70)

    token = run_claude_setup_token()

    if token:
        # Token captured! Now try to generate API key from it
        print()
        print("=" * 70)
        print("  🔄 Converting OAuth token to API key...")
        print("=" * 70)

        # Try to generate API key from OAuth token
        api_key = None
        if OAUTH_TO_APIKEY_AVAILABLE:
            api_key = generate_api_key_from_oauth(token)

        if api_key:
            # Successfully generated API key! Use it instead of OAuth token
            if save_api_key_to_env(api_key):
                print()
                print("=" * 70)
                print("  🎉 Setup Complete!")
                print("=" * 70)
                print()
                print("  ✅ OAuth token → API key conversion successful!")
                print("  ✅ API key saved to .env!")
                print("  ✅ Ready to use with full functionality!")
                print()
                print("  💡 Benefits:")
                print("     • Uses your Claude Max/Pro subscription")
                print("     • Full access to tools, agents, extended thinking")
                print("     • No manual key copying needed!")
                print()
                return api_key

        # API key generation failed or not available - fall back to saving OAuth token
        print()
        print("  ℹ️  Could not auto-generate API key")
        print("     Saving OAuth token instead (limited functionality)")

        if save_token_to_env(token):
            print()
            print("=" * 70)
            print("  ⚠️  Setup Complete (OAuth token saved)")
            print("=" * 70)
            print()
            print("  ⚠️  OAuth tokens have limited functionality")
            print("  💡 For full features, use an API key instead")
            print()
            return token
        else:
            # Saving failed, but we still have the token
            print()
            print("  ⚠️  Could not save to .env, but token is available")
            print(f"     Token: {token}")
            print()
            return token

    # Fallback: Token not in output, try reading from file
    print()
    print("  📖 Token not in output, checking file...")

    if not wait_for_token(timeout=5):
        print("  ⚠️  Token file not found yet, checking anyway...")

    file_token = read_token()

    if file_token:
        # Found token in file! Try to generate API key from it
        print("  ✅ Token found in file!")
        print()
        print("  🔄 Converting OAuth token to API key...")

        # Try to generate API key from OAuth token
        api_key = None
        if OAUTH_TO_APIKEY_AVAILABLE:
            api_key = generate_api_key_from_oauth(file_token)

        if api_key:
            # Successfully generated API key!
            if save_api_key_to_env(api_key):
                print()
                print("=" * 70)
                print("  🎉 Setup Complete!")
                print("=" * 70)
                print()
                print("  ✅ OAuth token → API key conversion successful!")
                print("  ✅ API key saved to .env!")
                print("  ✅ Ready to use with full functionality!")
                print()
                return api_key

        # Fallback: save OAuth token
        print()
        print("  ℹ️  Could not auto-generate API key")
        print("     Saving OAuth token instead")

        if save_token_to_env(file_token):
            print()
            print("=" * 70)
            print("  ⚠️  Setup Complete (OAuth token saved)")
            print("=" * 70)
            print()
            print("  ⚠️  OAuth tokens have limited functionality")
            print()
            return file_token
        else:
            # Saving failed but we have the token
            print()
            print("  ⚠️  Could not save to .env, but token is available")
            return file_token
    else:
        # No token found anywhere
        print()
        print("  ❌ Could not find token")
        print()
        print("     Token should be at:")
        print(f"     {get_token_path()}")
        print()
        print("     You can try manually:")
        print("     1. Run: claude setup-token")
        print("     2. Copy token and add to .env:")
        print("        CLAUDE_CODE_OAUTH_TOKEN=your-token")
        print()
        return None


if __name__ == "__main__":
    # Test the setup
    token = automatic_claude_max_setup()
    if token:
        print(f"Got token: {token[:20]}...")
    else:
        print("Setup failed")
