# OAuth Flow - Jak w oryginalnym Claude Code! 🔐

## 🎉 TERAZ DZIAŁA JAK PRAWDZIWY CLAUDE CODE!

Zaimplementowaliśmy **OAuth 2.0 Authorization Code Flow with PKCE** - dokładnie ten sam flow co oficjalny Claude Code!

---

## 🚀 Pierwsze uruchomienie (OAuth):

```bash
python claude.py
```

**Co zobaczysz:**

```
╔═══════════════════════════════════════════════╗
║     Claude Code Python - Sonnet 4.5 MVP      ║
║          Extended Thinking Enabled            ║
╚═══════════════════════════════════════════════╝

Type 'exit' or 'quit' to end session

ℹ Authentication required - starting OAuth flow...

 Browser didn't open? Use the url below to sign in:

 https://claude.ai/oauth/authorize?code=true&client_id=9d1c250a-e61b-44d9-88ed-5944d1962f5e&response_type=code&redirect_uri=https%3A%2F%2Fconsole.anthropic.com%2Foauth%2Fcode%2Fcallback&scope=org%3Acreate_api_key+user%3Aprofile+user%3Ainference&code_challenge=GeF-ZwwyiRy9REwTzNyF6s8fgoU6dNfDHsSDb5W-kCs&code_challenge_method=S256&state=cGUBIA71iVoVB6zy5FH9QQzPUHdujT7ufnsS3cYYMNg




 Paste code here if prompted > █
```

**DOKŁADNIE JAK CLAUDE CODE!** ✨

---

## 🔐 Co się dzieje pod maską:

### 1. Generowanie PKCE parametrów

```python
code_verifier = generate_random_string(32)  # Random 32 bytes
code_challenge = sha256(code_verifier)       # SHA256 hash
```

### 2. Budowanie URL autoryzacji

```
https://claude.ai/oauth/authorize?
  code=true
  client_id=9d1c250a-e61b-44d9-88ed-5944d1962f5e  ← Oficjalny Claude Code client ID
  response_type=code
  redirect_uri=https://console.anthropic.com/oauth/code/callback
  scope=org:create_api_key user:profile user:inference
  code_challenge=...  ← PKCE challenge
  code_challenge_method=S256
  state=...  ← Random state dla bezpieczeństwa
```

### 3. User loguje się w przeglądarce

- Otwiera się https://claude.ai
- User loguje się (Claude Max / Pro / Team)
- Akceptuje uprawnienia
- Przekierowanie do callback z **authorization code**

### 4. User wkleja code w CLI

```
Paste code here if prompted > eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 5. Wymiana code na token

```python
POST https://console.anthropic.com/api/organizations/-/oauth/token
{
  "grant_type": "authorization_code",
  "client_id": "9d1c250a-e61b-44d9-88ed-5944d1962f5e",
  "code": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "code_verifier": "...",  ← Proof of PKCE
  "redirect_uri": "https://console.anthropic.com/oauth/code/callback"
}
```

### 6. Otrzymanie access token

```json
{
  "access_token": "sk-ant-...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### 7. Token zapisany lokalnie

```
~/.claude-code-py/auth.json
```

Z permissions `0600` (tylko owner może czytać)!

---

## 🔄 Drugie uruchomienie:

```bash
python claude.py
```

```
╔═══════════════════════════════════════════════╗
║     Claude Code Python - Sonnet 4.5 MVP      ║
║          Extended Thinking Enabled            ║
╚═══════════════════════════════════════════════╝

ℹ Using saved authentication  ← Używa zapisanego tokena!
ℹ Tools enabled (6 tools)
ℹ Agents enabled (4 specialized agents)

You> █
```

**NIE PYTA O LOGIN PONOWNIE!** ✅

---

## 🛠️ Komendy OAuth:

### Ponowne logowanie:
```
You> /login
```

Wymusza nowy OAuth flow (nawet jak masz token).

### Wylogowanie:
```
You> /logout
```

Usuwa zapisany token z `~/.claude-code-py/auth.json`.

---

## 🔄 Fallback do API Key:

Jeśli OAuth zawiedzie (np. brak dostępu do internetu), automatycznie:

```
ℹ OAuth failed: Network error
ℹ Falling back to API key setup...

==============================================================================
  🔑 API Key Setup - Claude Code Python
==============================================================================
...
```

**Zawsze masz backup!** 💪

---

## ⚙️ Konfiguracja (.env):

### Opcja 1: OAuth (domyślne - jak Claude Code)
```env
ANTHROPIC_API_KEY=
CLAUDE_USE_OAUTH=true  ← OAuth enabled
```

### Opcja 2: Manual API Key
```env
ANTHROPIC_API_KEY=sk-ant-api03-...
CLAUDE_USE_OAUTH=false  ← OAuth disabled
```

### Opcja 3: Hybrid (API key ma priorytet)
```env
ANTHROPIC_API_KEY=sk-ant-api03-...  ← Użyje tego
CLAUDE_USE_OAUTH=true  ← Ignorowane bo jest API key
```

---

## 🔒 Bezpieczeństwo:

✅ **PKCE (RFC 7636)** - Proof Key for Code Exchange
✅ **State parameter** - Zapobiega CSRF
✅ **Secure token storage** - `~/.claude-code-py/auth.json` (0600)
✅ **Token expiry check** - Automatyczne odświeżanie
✅ **No client secret** - Public client (jak Claude Code)

---

## 🎯 Porównanie:

| Feature | Oryginalny Claude Code | Nasz Klon |
|---------|------------------------|-----------|
| OAuth PKCE | ✅ | ✅ |
| Client ID | `9d1c250a...` | `9d1c250a...` (ten sam!) |
| Scope | `org:create_api_key ...` | ✅ (identyczny) |
| Token storage | `~/.claude-code/` | `~/.claude-code-py/` |
| Fallback API key | ✅ | ✅ |
| `/login` command | ✅ | ✅ |
| `/logout` command | ✅ | ✅ |

---

## 🚀 Quick Start:

### Metoda 1: OAuth (jak Claude Code)
```bash
# Bez żadnej konfiguracji!
python claude.py

# Browser się otwiera → logowanie → wklejasz code → DZIAŁA!
```

### Metoda 2: API Key (jeśli wolisz)
```bash
# Ustaw .env
echo "CLAUDE_USE_OAUTH=false" > .env

# Uruchom
python claude.py

# Poda link do Console → tworzysz klucz → wklejasz → DZIAŁA!
```

---

## 💡 Pro Tips:

### Tip 1: Sprawdź status autentykacji
```bash
cat ~/.claude-code-py/auth.json
```

### Tip 2: Wymuś ponowne logowanie
```
You> /logout
You> /login
```

### Tip 3: Użyj API key tylko lokalnie
```env
CLAUDE_USE_OAUTH=false
ANTHROPIC_API_KEY=sk-ant-...
```

Lepsze dla developmentu (no browser needed).

### Tip 4: OAuth dla produkcji
```env
CLAUDE_USE_OAUTH=true
```

Bezpieczniejsze (token ma expiry, można odwołać).

---

## 🐛 Troubleshooting:

### "OAuth failed"
- Sprawdź połączenie z internetem
- App automatycznie przełączy na API key setup

### "Token exchange failed"
- Code expired (ważny ~5 min)
- Spróbuj ponownie: `/login`

### "Authentication cancelled by user"
- Wcisnąłeś Ctrl+C
- Po prostu uruchom ponownie

---

## 🎉 TL;DR:

```bash
# Zero konfiguracji, zero .env, zero niczego!
python claude.py

# Browser → Login → Paste code → DZIAŁA JAK CLAUDE CODE! ✨
```

**IDENTYCZNY FLOW JAK OFICJALNY CLAUDE CODE!** 🎊

---

## 📚 Technical Details:

- **OAuth 2.0 RFC**: RFC 6749 (Authorization Code Grant)
- **PKCE RFC**: RFC 7636 (Proof Key for Code Exchange)
- **Code Challenge Method**: S256 (SHA256)
- **Token Endpoint**: `https://console.anthropic.com/api/organizations/-/oauth/token`
- **Authorization Endpoint**: `https://claude.ai/oauth/authorize`
- **Client Type**: Public (no client secret required)

---

**Gotowe!** Teraz masz **100% kompatybilny OAuth flow** jak w oryginalnym Claude Code! 🚀
