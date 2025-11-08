# Authentication Best Practices 🔐

## 🎯 Recommended: API Key Authentication

**Status:** ✅ **Officially Supported** by Anthropic

### Why API Key?

1. **Official Method** - Documented in Anthropic API docs
2. **Reliable** - No Cloudflare issues, no browser requirements
3. **Simple** - One-time setup, works everywhere
4. **Portable** - Works in CI/CD, containers, servers
5. **Supported** - Anthropic support team can help

### Quick Setup:

```bash
python claude.py
# App automatically:
# 1. Opens browser to Console
# 2. Shows step-by-step instructions
# 3. Validates key format
# 4. Saves to .env
# 5. Starts immediately
```

---

## ⚠️ OAuth: Limited Third-Party Support

**Status:** ⚠️ **Restricted** - May not work for third-party clients

### Current Limitations:

#### 1. **Cloudflare Protection**
- Token endpoint (`console.anthropic.com/api/organizations/-/oauth/token`) is behind Cloudflare
- Returns 403 with JavaScript challenge
- Requires browser environment (not suitable for CLI)

#### 2. **Token Restrictions**
- OAuth tokens from Claude Code are **restricted**
- Error message: _"This credential is only authorized for use with Claude Code and cannot be used for other API requests"_
- Tokens may only work with official Claude Code client

#### 3. **Not Publicly Documented**
- OAuth flow exists but is not in official API documentation
- Endpoint URLs not officially published
- No official third-party client support

#### 4. **Intended for Claude Subscription Users**
- OAuth is for Claude Max/Pro/Team subscribers
- Uses Claude.ai subscription, not API credits
- Different billing model than API keys

### Technical Details:

We implemented OAuth 2.0 with PKCE (exactly like official Claude Code):
- ✅ Client ID: `9d1c250a-e61b-44d9-88ed-5944d1962f5e` (official)
- ✅ Authorization URL: `https://claude.ai/oauth/authorize`
- ✅ PKCE: SHA256 code challenge
- ✅ Scopes: `org:create_api_key user:profile user:inference`
- ❌ Token exchange: **Blocked by Cloudflare**

**Result:** OAuth flow works up to authorization, but token exchange fails due to Cloudflare protection on the endpoint.

---

## 🤔 Why Does Official Claude Code Work?

Official Claude Code likely has:
1. **Whitelisted IP addresses** or **special certificates**
2. **Special User-Agent** recognized by Cloudflare
3. **Pre-shared secrets** or **client certificates**
4. **Different endpoint** (internal/private API)
5. **Direct server-side token exchange** (no client-side request)

**We cannot replicate this** without official third-party client support from Anthropic.

---

## 📊 Comparison:

| Feature | API Key | OAuth (Current) |
|---------|---------|-----------------|
| **Official Support** | ✅ Yes | ⚠️ Limited |
| **Documentation** | ✅ Public | ❌ Internal only |
| **Setup Complexity** | ⭐ Easy | ⭐⭐⭐ Complex |
| **Cloudflare Issues** | ✅ None | ❌ Blocked |
| **Works in CLI** | ✅ Yes | ❌ No |
| **Works in CI/CD** | ✅ Yes | ❌ No |
| **Billing** | API credits | Subscription |
| **Third-party Clients** | ✅ Supported | ❌ Restricted |

---

## 🎯 Our Recommendation:

### For Individual Developers:
```env
# Use API Key
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_USE_OAUTH=false
```

**Benefits:**
- ✅ Works reliably
- ✅ No browser required
- ✅ Officially supported
- ✅ Great for development

### For Organizations:
```env
# Use API Key with Admin API
ANTHROPIC_API_KEY=sk-ant-...
```

**Benefits:**
- ✅ Admin API for key management
- ✅ Usage tracking and cost reports
- ✅ Workspace management
- ✅ Officially documented

---

## 🔄 Fallback Strategy (Current Implementation):

Our app tries in this order:

1. **Manual API Key** (if set in .env) → ✅ Works
2. **OAuth** (if enabled) → ⚠️ May fail (Cloudflare)
3. **Interactive API Key Setup** → ✅ Always works

**Smart Fallback:**
```python
# Priority 1: Manual API key (reliable)
if ANTHROPIC_API_KEY is set:
    use it ✅

# Priority 2: OAuth (experimental)
if CLAUDE_USE_OAUTH=true:
    try OAuth
    if fails → fallback to API key setup

# Priority 3: Interactive setup (failsafe)
run API key setup wizard ✅
```

---

## 💡 Best Practices:

### ✅ DO:
- Use API key authentication (official method)
- Store API key in `.env` file (git-ignored)
- Use environment variables in production
- Rotate API keys periodically
- Use Admin API for team management

### ❌ DON'T:
- Try to bypass Cloudflare (violates ToS)
- Use unofficial OAuth flows (unreliable)
- Hardcode API keys in code
- Share API keys publicly
- Use personal keys in CI/CD (create dedicated keys)

---

## 🚀 Quick Start (Best Practice):

```bash
# 1. Clone and install
git clone https://github.com/you/claude-code-py
cd claude-code-py
pip install -r requirements.txt

# 2. Run (auto-setup)
python claude.py
# → Opens browser
# → Get API key from Console
# → Paste in CLI
# → Saved automatically

# 3. Done! Start using
You> Write tests for my code
```

**That's it!** No OAuth complexity, just works! ✨

---

## 📚 Official Resources:

- **API Documentation:** https://docs.anthropic.com/
- **API Console:** https://console.anthropic.com/settings/keys
- **API Support:** https://support.anthropic.com/
- **Pricing:** https://www.anthropic.com/pricing#anthropic-api

---

## 🔮 Future:

If Anthropic officially supports third-party OAuth clients:
- We'll update implementation
- Remove Cloudflare workarounds
- Add to documentation
- Test thoroughly

**Until then:** API key is the **official, supported, reliable** method! ✅

---

## Summary:

**Use API Keys!** They work, they're official, they're simple.

OAuth is a nice feature but currently:
- ❌ Blocked by Cloudflare for third-party clients
- ❌ Not officially documented for third-party use
- ❌ Tokens are restricted to official Claude Code
- ⚠️ May never work without official Anthropic support

**API Key Setup** is:
- ✅ Interactive wizard
- ✅ Auto-opens browser
- ✅ Step-by-step instructions
- ✅ Auto-validates format
- ✅ Auto-saves to .env
- ✅ Works everywhere

**This is the best practice!** 🏆
