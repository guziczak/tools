"""OAuth PKCE flow authentication for Anthropic API (like Claude Code)."""

import time
import json
import webbrowser
import hashlib
import base64
import secrets
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode

# Try to import cloudscraper for Cloudflare bypass (optional)
try:
    import cloudscraper

    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    import requests

    CLOUDSCRAPER_AVAILABLE = False


class AuthenticationError(Exception):
    """Authentication error."""

    pass


class TokenStorage:
    """Secure token storage manager."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize token storage.

        Args:
            config_dir: Directory to store tokens (default: ~/.claude-code-py)
        """
        if config_dir is None:
            config_dir = Path.home() / ".claude-code-py"

        self.config_dir = config_dir
        self.token_file = config_dir / "auth.json"

        # Ensure directory exists with proper permissions
        self.config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    def save_token(self, token_data: Dict[str, Any]) -> None:
        """Save token data securely.

        Args:
            token_data: Token data from OAuth flow
        """
        # Add expiry timestamp
        if "expires_in" in token_data:
            expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
            token_data["expires_at"] = expires_at.isoformat()

        # Write with restricted permissions
        with open(self.token_file, "w") as f:
            json.dump(token_data, f, indent=2)

        # Ensure file is only readable by owner
        self.token_file.chmod(0o600)

    def load_token(self) -> Optional[Dict[str, Any]]:
        """Load token data.

        Returns:
            Token data or None if not found/expired
        """
        if not self.token_file.exists():
            return None

        try:
            with open(self.token_file, "r") as f:
                token_data = json.load(f)

            # Check if token is expired
            if "expires_at" in token_data:
                expires_at = datetime.fromisoformat(token_data["expires_at"])
                if datetime.now() >= expires_at:
                    # Token expired
                    self.clear_token()
                    return None

            return token_data
        except Exception:
            return None

    def clear_token(self) -> None:
        """Clear stored token."""
        if self.token_file.exists():
            self.token_file.unlink()

    def get_access_token(self) -> Optional[str]:
        """Get valid access token.

        Returns:
            Access token or None if not available
        """
        token_data = self.load_token()
        if token_data:
            return token_data.get("access_token")
        return None

    def load_official_claude_token(self) -> Optional[Dict[str, Any]]:
        """Load token from official Claude Code installation.

        Checks ~/.claude/oauth_token.json (official Claude Code location)

        Returns:
            Token data or None if not found
        """
        # Check official Claude Code token location
        official_token_path = Path.home() / ".claude" / "oauth_token.json"

        if not official_token_path.exists():
            return None

        try:
            with open(official_token_path, "r") as f:
                token_data = json.load(f)

            # Check if token is expired
            if "expires_at" in token_data:
                # Official Claude Code stores as milliseconds timestamp
                expires_at_ms = token_data["expires_at"]
                expires_at = datetime.fromtimestamp(expires_at_ms / 1000.0)
                if datetime.now() >= expires_at:
                    # Token expired
                    return None

            return token_data
        except Exception:
            return None


class PKCEAuth:
    """OAuth PKCE flow authentication (like official Claude Code)."""

    # Anthropic OAuth endpoints (EXACT same as official Claude Code - from reverse engineering!)
    AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
    TOKEN_URL = (
        "https://console.anthropic.com/oauth/token"  # Correct endpoint from claude_max research!
    )
    REDIRECT_URI = "https://console.anthropic.com/oauth/code/callback"

    # Official Claude Code client ID
    CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"

    # Scopes (same as Claude Code)
    SCOPES = "org:create_api_key user:profile user:inference"

    def __init__(self, token_storage: TokenStorage):
        """Initialize PKCE flow authenticator.

        Args:
            token_storage: Token storage manager
        """
        self.token_storage = token_storage
        self.code_verifier: Optional[str] = None

    @staticmethod
    def generate_code_verifier() -> str:
        """Generate PKCE code verifier.

        Returns:
            Random code verifier string (43-128 chars)
        """
        # Generate 32 random bytes, base64url encode
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8")
        # Remove padding
        return code_verifier.rstrip("=")

    @staticmethod
    def generate_code_challenge(verifier: str) -> str:
        """Generate PKCE code challenge from verifier.

        Args:
            verifier: Code verifier string

        Returns:
            SHA256 hash of verifier, base64url encoded
        """
        # SHA256 hash
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        # Base64url encode
        challenge = base64.urlsafe_b64encode(digest).decode("utf-8")
        # Remove padding
        return challenge.rstrip("=")

    @staticmethod
    def generate_state() -> str:
        """Generate random state parameter.

        Returns:
            Random state string
        """
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")

    def build_authorization_url(self) -> tuple[str, str]:
        """Build authorization URL with PKCE parameters.

        Returns:
            Tuple of (authorization_url, code_verifier)
        """
        # Generate PKCE parameters
        self.code_verifier = self.generate_code_verifier()
        code_challenge = self.generate_code_challenge(self.code_verifier)
        state = self.generate_state()

        # Build query parameters (exactly like Claude Code)
        params = {
            "code": "true",
            "client_id": self.CLIENT_ID,
            "response_type": "code",
            "redirect_uri": self.REDIRECT_URI,
            "scope": self.SCOPES,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
        }

        url = f"{self.AUTHORIZE_URL}?{urlencode(params)}"
        return url, self.code_verifier

    def exchange_code_for_token(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token.

        Args:
            authorization_code: Authorization code from OAuth redirect (may include #state)

        Returns:
            Token data with access_token

        Raises:
            AuthenticationError: If exchange fails
        """
        if not self.code_verifier:
            raise AuthenticationError("No code verifier found. Start authorization flow first.")

        try:
            # Clean authorization code - remove state parameter if present
            # Format: "code#state" -> we only need "code"
            if "#" in authorization_code:
                clean_code = authorization_code.split("#")[0]
                print(f"  Extracted code (removed state parameter)")
            else:
                clean_code = authorization_code

            # Prepare request data (OAuth typically uses form-data, not JSON!)
            payload = {
                "grant_type": "authorization_code",
                "client_id": self.CLIENT_ID,
                "code": clean_code,  # Use cleaned code without state
                "code_verifier": self.code_verifier,
                "redirect_uri": self.REDIRECT_URI,
            }

            # OAuth 2.0 standard: use application/x-www-form-urlencoded
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "claude-code-python/1.0.0 (Python; OAuth Client)",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Origin": "https://console.anthropic.com",
                "Referer": "https://console.anthropic.com/",
            }

            # Debug: Show what we're sending
            print(f"\n  DEBUG - Request details:")
            print(f"  URL: {self.TOKEN_URL}")
            print(f"  Payload: {payload}")
            print(f"  Headers: Content-Type = {headers['Content-Type']}\n")

            # Use cloudscraper if available (handles Cloudflare challenges)
            if CLOUDSCRAPER_AVAILABLE:
                print("  Using cloudscraper to bypass Cloudflare...")

                # Create session with more aggressive browser emulation
                scraper = cloudscraper.create_scraper(
                    browser={
                        "browser": "chrome",
                        "platform": "windows",
                        "desktop": True,
                        "mobile": False,
                    },
                    delay=10,  # Add delay to appear more human
                    interpreter="native",  # Use native JS interpreter
                )

                # Add more realistic headers
                headers["Sec-Fetch-Dest"] = "empty"
                headers["Sec-Fetch-Mode"] = "cors"
                headers["Sec-Fetch-Site"] = "same-origin"

                response = scraper.post(
                    self.TOKEN_URL,
                    data=payload,  # Use 'data' for form-encoded (not 'json')
                    headers=headers,
                    timeout=30,
                )
            else:
                # Fallback to regular requests (may fail with Cloudflare)
                print("  Using requests library (may fail with Cloudflare)...")
                print("  Install cloudscraper for better compatibility: pip install cloudscraper")
                import requests

                response = requests.post(
                    self.TOKEN_URL,
                    data=payload,  # Use 'data' for form-encoded (not 'json')
                    headers=headers,
                    timeout=30,
                )

            if response.status_code == 200:
                token_data = response.json()
                # Save token
                self.token_storage.save_token(token_data)
                print("  ✅ Token exchange successful!")
                return token_data
            else:
                error_msg = f"Token exchange failed: {response.status_code}"

                # Check if it's Cloudflare blocking
                if response.status_code == 403:
                    if not CLOUDSCRAPER_AVAILABLE:
                        error_msg += "\n\n💡 Tip: Install cloudscraper to bypass Cloudflare:"
                        error_msg += "\n   pip install cloudscraper"
                        error_msg += "\n   Then try again with OAuth enabled."
                    else:
                        error_msg += "\n   Cloudflare blocked the request even with cloudscraper."
                        error_msg += (
                            "\n   This endpoint may be restricted to official Claude Code only."
                        )

                try:
                    error_data = response.json()
                    error_msg += f"\n   Error: {error_data.get('error', error_data)}"
                except Exception:
                    # Don't show HTML response (Cloudflare challenge page)
                    if len(response.text) > 200:
                        error_msg += "\n   (Received Cloudflare challenge page)"
                    else:
                        error_msg += f"\n   {response.text}"

                raise AuthenticationError(error_msg)

        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(f"Network error during token exchange: {e}")

    def authenticate(self, open_browser: bool = True) -> str:
        """Complete PKCE OAuth flow authentication (like Claude Code).

        Args:
            open_browser: Whether to automatically open browser

        Returns:
            Access token

        Raises:
            AuthenticationError: If authentication fails
        """
        # Build authorization URL with PKCE
        auth_url, code_verifier = self.build_authorization_url()

        # Show user the URL (like Claude Code does)
        print()
        print(" Browser didn't open? Use the url below to sign in:")
        print()
        print(f" {auth_url}")
        print()
        print()
        print()

        # Try to open browser
        if open_browser:
            try:
                webbrowser.open(auth_url)
            except Exception:
                pass  # Silent fail, user has the URL

        # Wait for user to paste the code
        print(" Paste code here if prompted >", end=" ", flush=True)

        try:
            authorization_code = input().strip()
        except (KeyboardInterrupt, EOFError):
            print()
            raise AuthenticationError("Authentication cancelled by user")

        if not authorization_code:
            raise AuthenticationError("No authorization code provided")

        # Exchange code for token
        token_data = self.exchange_code_for_token(authorization_code)

        return token_data["access_token"]


class AuthManager:
    """High-level authentication manager."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize auth manager.

        Args:
            config_dir: Directory to store tokens
        """
        self.token_storage = TokenStorage(config_dir)
        self.pkce_auth = PKCEAuth(self.token_storage)

    def get_access_token(self, force_reauth: bool = False) -> str:
        """Get valid access token, authenticating if needed.

        Priority:
        1. Check our own token storage (~/.claude-code-py/)
        2. Check official Claude Code token (~/.claude/oauth_token.json)
        3. Try OAuth PKCE flow

        Args:
            force_reauth: Force re-authentication even if token exists

        Returns:
            Valid access token

        Raises:
            AuthenticationError: If authentication fails
        """
        # Check for existing token in our storage
        if not force_reauth:
            token = self.token_storage.get_access_token()
            if token:
                return token

        # Check for official Claude Code token (from claude setup-token)
        if not force_reauth:
            official_token_data = self.token_storage.load_official_claude_token()
            if official_token_data:
                access_token = official_token_data.get("accessToken") or official_token_data.get(
                    "access_token"
                )
                if access_token:
                    print("  ✅ Using token from official Claude Code (~/.claude/)")
                    return access_token

        # Need to authenticate using PKCE flow
        return self.pkce_auth.authenticate()

    def logout(self) -> None:
        """Clear stored credentials."""
        self.token_storage.clear_token()

    def is_authenticated(self) -> bool:
        """Check if user is authenticated.

        Returns:
            True if valid token exists
        """
        return self.token_storage.get_access_token() is not None
