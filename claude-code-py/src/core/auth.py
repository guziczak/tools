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
import requests


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
        with open(self.token_file, 'w') as f:
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
            with open(self.token_file, 'r') as f:
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


class PKCEAuth:
    """OAuth PKCE flow authentication (like official Claude Code)."""

    # Anthropic OAuth endpoints (same as official Claude Code)
    AUTHORIZE_URL = "https://claude.ai/oauth/authorize"
    TOKEN_URL = "https://console.anthropic.com/api/organizations/-/oauth/token"
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
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
        # Remove padding
        return code_verifier.rstrip('=')

    @staticmethod
    def generate_code_challenge(verifier: str) -> str:
        """Generate PKCE code challenge from verifier.

        Args:
            verifier: Code verifier string

        Returns:
            SHA256 hash of verifier, base64url encoded
        """
        # SHA256 hash
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        # Base64url encode
        challenge = base64.urlsafe_b64encode(digest).decode('utf-8')
        # Remove padding
        return challenge.rstrip('=')

    @staticmethod
    def generate_state() -> str:
        """Generate random state parameter.

        Returns:
            Random state string
        """
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

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
            'code': 'true',
            'client_id': self.CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': self.REDIRECT_URI,
            'scope': self.SCOPES,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'state': state,
        }

        url = f"{self.AUTHORIZE_URL}?{urlencode(params)}"
        return url, self.code_verifier

    def exchange_code_for_token(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token.

        Args:
            authorization_code: Authorization code from OAuth redirect

        Returns:
            Token data with access_token

        Raises:
            AuthenticationError: If exchange fails
        """
        if not self.code_verifier:
            raise AuthenticationError("No code verifier found. Start authorization flow first.")

        try:
            # Exchange code for token (like Claude Code does)
            response = requests.post(
                self.TOKEN_URL,
                json={
                    "grant_type": "authorization_code",
                    "client_id": self.CLIENT_ID,
                    "code": authorization_code,
                    "code_verifier": self.code_verifier,
                    "redirect_uri": self.REDIRECT_URI,
                },
                headers={
                    "Content-Type": "application/json",
                },
                timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()
                # Save token
                self.token_storage.save_token(token_data)
                return token_data
            else:
                error_msg = f"Token exchange failed: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('error', error_data)}"
                except Exception:
                    error_msg += f" - {response.text}"
                raise AuthenticationError(error_msg)

        except requests.RequestException as e:
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

        Args:
            force_reauth: Force re-authentication even if token exists

        Returns:
            Valid access token

        Raises:
            AuthenticationError: If authentication fails
        """
        # Check for existing token
        if not force_reauth:
            token = self.token_storage.get_access_token()
            if token:
                return token

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
