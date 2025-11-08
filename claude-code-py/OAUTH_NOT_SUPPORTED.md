# OAuth Tokens - Why They Don't Work ❌

## TL;DR

**OAuth tokens from `claude setup-token` DO NOT WORK with this app.**

Use API key instead - it's simple, free ($5 credit), and gives you full features!

## What Happened

We tried implementing OAuth support, but it's not possible because:

### 1. Public API Doesn't Accept OAuth Tokens

```
Error: 401 - invalid x-api-key
```

The public Anthropic API (`api.anthropic.com`) only accepts API keys (sk-ant-api03-*), not OAuth tokens (sk-ant-oat01-*).

### 2. Private API is Inaccessible

OAuth tokens work with a **private claude.ai API** that:
- Is not publicly documented
- Requires reverse engineering the official CLI
- Can change without notice
- May violate Terms of Service
- Requires complex session management

We tried endpoints like:
- `https://claude.ai/api/organizations` → 403 Forbidden
- `https://api.claude.ai/api/organizations` → DNS error

Both failed, confirming OAuth tokens need a different backend.

### 3. Not Worth the Effort

Even if we reverse-engineered it:
- ❌ Unstable (changes without warning)
- ❌ Unofficial (may violate ToS)
- ❌ Complex (cookies, sessions, CSRF tokens)
- ❌ Limited features (no tools/agents)
- ❌ Maintenance nightmare

## What We Built (Then Removed)

We created:
1. `claude_ai_client.py` - Custom HTTP client for claude.ai
2. `unified_client.py` - Token type detection wrapper
3. Auto-detection in `api_client.py`

**Result:** Code compiles but gets 401/403 errors. OAuth tokens simply don't work with public API.

## The Solution: Use API Key ✅

**Why API key is better:**

| Feature | OAuth Token | API Key |
|---------|------------|---------|
| Works | ❌ No | ✅ Yes |
| Stable | ❌ No | ✅ Yes |
| Official | ❌ No | ✅ Yes |
| Tools/Agents | ❌ No | ✅ Yes |
| Setup time | N/A | 2 minutes |
| Free credit | N/A | $5 |

**How to get API key:**

```bash
# 1. Clear OAuth token from .env
# Set: CLAUDE_CODE_OAUTH_TOKEN=

# 2. Run app
python claude.py

# 3. Press Enter at setup prompt
# 4. Browser opens → console.anthropic.com
# 5. Sign up (can use Google)
# 6. Copy API key → paste
# 7. Done! ✅
```

## For Claude Max/Pro Users

If you have Claude Max/Pro and want to use your subscription:

**Use official Claude Code CLI instead:**

```bash
# Install official CLI (Node.js)
npm install -g @anthropic-ai/claude-code

# Run it
claude
```

The official CLI:
- ✅ Supports OAuth tokens natively
- ✅ Maintained by Anthropic
- ✅ Works with your subscription
- ✅ Official support

This Python port is best for users who:
- Want to use API keys
- Need Python-specific features
- Don't have Node.js

## Technical Details

### Why OAuth Tokens Fail

The official Claude Code CLI uses a proprietary protocol:

1. **Authentication Flow:**
   ```
   OAuth Token → claude.ai → Session Cookie → API Requests
   ```

2. **Our App (Simplified):**
   ```
   OAuth Token → api.anthropic.com → ❌ 401 Error
   ```

The public API expects `x-api-key` header with API keys, not OAuth Bearer tokens.

### What Would Be Required

To make OAuth work, we'd need to:

1. **Reverse engineer** official CLI:
   - Install and run with network sniffer
   - Capture exact HTTP requests
   - Extract endpoint URLs, headers, payload format
   - Understand session management

2. **Implement** complex auth flow:
   - Exchange OAuth token for session
   - Manage cookies/CSRF tokens
   - Handle refreshes/expiry
   - Cloudflare bypass

3. **Maintain** as private API changes:
   - Monitor for breaking changes
   - Update code constantly
   - Risk of sudden failures

**Estimated effort:** 8-16 hours initial + ongoing maintenance

**Benefit:** Questionable (API key is easier)

## Conclusion

OAuth tokens are **not supported** and won't be implemented because:
1. They don't work with public API
2. Private API requires reverse engineering
3. Solution would be unstable and unofficial
4. API keys are simpler and better

**Recommendation:** Use API key - it just works! ✅

---

**Questions?** See README for API key setup guide.

**Want OAuth?** Use official Claude Code CLI instead.
