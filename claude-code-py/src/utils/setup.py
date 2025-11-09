#!/usr/bin/env python3
"""Interactive setup utility for Claude Code Python."""

import os
import re
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional


def validate_api_key(key: str) -> bool:
    """Validate API key format.

    Args:
        key: API key to validate

    Returns:
        True if valid format
    """
    # Anthropic API keys start with sk-ant-
    return bool(re.match(r'^sk-ant-[a-zA-Z0-9\-_]+$', key.strip()))


def get_env_file_path() -> Path:
    """Get path to .env file.

    Returns:
        Path to .env file (may not exist yet)
    """
    # Get project root (claude-code-py/)
    src_dir = Path(__file__).parent.parent
    project_root = src_dir.parent
    return project_root / ".env"


def save_api_key_to_env(api_key: str) -> bool:
    """Save API key to .env file.

    Args:
        api_key: API key to save

    Returns:
        True if successful
    """
    try:
        env_path = get_env_file_path()
        env_example = env_path.parent / ".env.example"

        # If .env doesn't exist but .env.example does, copy it
        if not env_path.exists() and env_example.exists():
            with open(env_example, 'r') as f:
                content = f.read()
        elif env_path.exists():
            # Read existing .env
            with open(env_path, 'r') as f:
                content = f.read()
        else:
            # Create minimal .env
            content = "# Anthropic API Configuration\nANTHROPIC_API_KEY=\n"

        # Update or add API key
        if 'ANTHROPIC_API_KEY=' in content:
            # Replace existing line
            content = re.sub(
                r'ANTHROPIC_API_KEY=.*',
                f'ANTHROPIC_API_KEY={api_key}',
                content
            )
        else:
            # Add new line
            content += f'\nANTHROPIC_API_KEY={api_key}\n'

        # Ensure OAuth is disabled
        if 'CLAUDE_USE_OAUTH=' in content:
            content = re.sub(
                r'CLAUDE_USE_OAUTH=.*',
                'CLAUDE_USE_OAUTH=false',
                content
            )
        else:
            content += 'CLAUDE_USE_OAUTH=false\n'

        # Write back
        with open(env_path, 'w') as f:
            f.write(content)

        # Reload environment
        from dotenv import load_dotenv
        load_dotenv(override=True)

        return True
    except Exception as e:
        print(f"Error saving to .env: {e}")
        return False


def interactive_setup() -> Optional[str]:
    """Run interactive setup to get API key.

    Returns:
        API key if successful, None otherwise
    """
    # Generate suggested key name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    suggested_name = f"claude-code-python-{timestamp}"

    # Console URL
    console_url = "https://console.anthropic.com/settings/keys"

    print()
    print("  🌐 Opening browser...")
    print()

    # Open browser automatically (no asking!)
    try:
        webbrowser.open(console_url)
        print("  ✅ Browser opened → console.anthropic.com")
    except Exception as e:
        print(f"  ⚠️  Could not auto-open browser")
        print(f"     Please open: {console_url}")

    print()
    print("  📝 In the browser:")
    print("     1. Sign in (can use Google)")
    print("     2. Click '+ Create Key'")
    print("     3. Copy the key")
    print()
    print("=" * 78)
    print()

    # Get API key from user
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            api_key = input("  Paste your API key here: ").strip()

            # Allow user to cancel
            if api_key.lower() in ['exit', 'quit', 'cancel', '']:
                print()
                print("  ❌ Setup cancelled.")
                print()
                return None

            # Validate format
            if not validate_api_key(api_key):
                print()
                print("  ⚠️  Invalid API key format!")
                print("     API keys should start with 'sk-ant-' followed by alphanumeric characters")
                print()
                if attempt < max_attempts - 1:
                    print(f"  💡 Try again ({max_attempts - attempt - 1} attempts left)...")
                    print()
                continue

            # Save to .env
            print()
            print("  💾 Saving to .env...")
            if save_api_key_to_env(api_key):
                print("  ✅ API key saved successfully!")
                print()
                print("  🎉 Setup complete! Starting Claude Code Python...")
                print()
                print("=" * 78)
                print()
                return api_key
            else:
                print("  ❌ Failed to save API key to .env")
                print()
                return None

        except KeyboardInterrupt:
            print()
            print()
            print("  ❌ Setup cancelled.")
            print()
            return None
        except EOFError:
            print()
            print()
            print("  ❌ Setup cancelled.")
            print()
            return None

    # Max attempts reached
    print()
    print("  ❌ Too many invalid attempts. Please try again later.")
    print()
    return None


def check_and_setup() -> Optional[str]:
    """Check if API key exists, if not run interactive setup.

    Returns:
        API key if available, None otherwise
    """
    # Check environment first
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key and validate_api_key(api_key):
        return api_key

    # Run interactive setup
    return interactive_setup()


if __name__ == "__main__":
    # Test the interactive setup
    result = interactive_setup()
    if result:
        print(f"Success! Got key: {result[:15]}...")
    else:
        print("Setup failed or cancelled")
