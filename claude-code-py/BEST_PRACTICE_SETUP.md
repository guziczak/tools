# Best Practice Setup Guide 🏆

## 🎯 Recommended Method: API Key Authentication

This is the **official, supported** authentication method from Anthropic.

---

## ✨ Super Simple Setup (2 commands!)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run
python claude.py
```

**That's it!** The app handles everything else! 🚀

---

## 📺 What You'll See:

### First Run:

```
╔═══════════════════════════════════════════════╗
║     Claude Code Python - Sonnet 4.5 MVP      ║
║          Extended Thinking Enabled            ║
╚═══════════════════════════════════════════════╝

Type 'exit' or 'quit' to end session

ℹ No API key found - starting setup...

==============================================================================
  🔑 API Key Setup - Claude Code Python
==============================================================================

  You need an Anthropic API key to use Claude Code Python.

  📌 Step 1: Create your API key

     Direct link: https://console.anthropic.com/settings/keys

  → Open this link in your browser now? [Y/n]: █
```

### Press Enter (or type `y`):

```
  → Open this link in your browser now? [Y/n]: y
     Opening browser...
     ✅ Browser opened!

  📝 In the Anthropic Console:
     1. Sign in (or create account if needed)
     2. You'll see 'API Keys' page
     3. Click '+ Create Key' button (top right)
     4. Enter a name for your key
        Suggested name: claude-code-python-20251107
     5. Click 'Create Key'
     6. COPY the key (it starts with 'sk-ant-...')
        ⚠️  You can only see it once!

  📌 Step 2: Paste your API key below
     → The key will be saved to .env automatically
     → You can cancel anytime with Ctrl+C

==============================================================================

  Paste your API key here: █
```

### Paste your key and press Enter:

```
  Paste your API key here: sk-ant-api03-abc123...

  💾 Saving to .env...
  ✅ API key saved successfully!

  🎉 Setup complete! Starting Claude Code Python...

==============================================================================

ℹ Using API key from environment
ℹ Tools enabled (6 tools)
ℹ Agents enabled (4 specialized agents)
ℹ Available agents: Test Writer, Code Reviewer, Bug Fixer, Refactorer
ℹ Model: claude-sonnet-4-20250514
ℹ Extended Thinking: Enabled (budget: 10000 tokens)

════════════════════════════════════════════════

You> █
```

**READY TO USE!** ✅

---

## 🔄 Second Run (Already Have API Key):

```bash
python claude.py
```

```
╔═══════════════════════════════════════════════╗
║     Claude Code Python - Sonnet 4.5 MVP      ║
║          Extended Thinking Enabled            ║
╚═══════════════════════════════════════════════╝

ℹ Using API key from environment  ← No setup needed!
ℹ Tools enabled (6 tools)
ℹ Agents enabled (4 specialized agents)

You> █
```

**Instant start!** No questions, no setup! 🚀

---

## 💡 Why This is Best Practice:

### ✅ Officially Supported
- Documented at https://docs.anthropic.com/
- Support team can help
- Guaranteed to work

### ✅ Simple & Reliable
- No Cloudflare issues
- No browser requirements for token exchange
- Works on all platforms

### ✅ Secure
- API key stored in `.env` (git-ignored)
- File permissions: 0600 (owner only)
- Easy to rotate keys

### ✅ Portable
- Works in CI/CD pipelines
- Works in Docker containers
- Works on servers without GUI

### ✅ Feature-Complete
- Full API access
- All models available
- Tools, agents, thinking - everything works!

---

## 🔐 Security Best Practices:

### 1. Never Commit `.env` to Git
Already configured in `.gitignore` ✅

### 2. Use Separate Keys for Different Environments
```bash
# Development
ANTHROPIC_API_KEY=sk-ant-dev-...

# Production (use env variables, not .env)
export ANTHROPIC_API_KEY=sk-ant-prod-...
```

### 3. Rotate Keys Periodically
Visit https://console.anthropic.com/settings/keys and create new keys every few months.

### 4. Use Environment Variables in Production
```bash
# Don't use .env in production
# Use system environment variables instead
export ANTHROPIC_API_KEY=sk-ant-...
python claude.py
```

### 5. Monitor Usage
Check usage at https://console.anthropic.com/settings/usage

---

## 🚀 Advanced Setup:

### Option 1: Pre-configure `.env` (Skip Interactive Setup)

```bash
# Copy example
cp .env.example .env

# Edit .env manually
nano .env
```

Set:
```env
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE
CLAUDE_USE_OAUTH=false
```

Then run:
```bash
python claude.py  # Starts immediately!
```

### Option 2: Use Environment Variables

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
export CLAUDE_USE_OAUTH=false
python claude.py
```

### Option 3: CI/CD Setup

```yaml
# GitHub Actions
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  CLAUDE_USE_OAUTH: false

steps:
  - run: python claude.py
```

---

## ❓ FAQ:

### Q: Why not OAuth like official Claude Code?
**A:** OAuth token endpoint is protected by Cloudflare and returns 403 for third-party clients. API key is the officially documented method for API access.

### Q: Can I still try OAuth?
**A:** Yes! Set `CLAUDE_USE_OAUTH=true` in `.env`. But it will likely fail with Cloudflare error, then fallback to API key setup automatically.

### Q: What's the difference between Claude subscription and API?
**A:**
- **Claude Max/Pro** = Subscription → Web interface, mobile app, official Claude Code
- **Anthropic API** = Pay-as-you-go → API access, your custom apps
- This project uses **API** → Needs API key

### Q: Do I need Claude Max for this?
**A:** No! You only need an Anthropic API account (free to create, pay for usage). Separate from Claude subscription.

### Q: How much does it cost?
**A:** See pricing at https://www.anthropic.com/pricing#anthropic-api
- Sonnet 4.5: $3 per million input tokens
- Free tier available for testing

### Q: Can I use my Claude Max subscription here?
**A:** Not directly. Claude Max uses OAuth (subscription billing). This project uses API (usage billing). They're separate systems.

---

## 🎯 Summary:

**Just run:**
```bash
python claude.py
```

**The app will:**
1. Detect no API key
2. Open browser to Console
3. Show step-by-step instructions
4. Validate your API key
5. Save to `.env` automatically
6. Start immediately

**Best practice = Easiest practice!** 🏆

---

## 📚 Additional Resources:

- **Full Documentation:** `README.md`
- **Authentication Deep Dive:** `AUTHENTICATION.md`
- **Quick Reference:** `README_SHORT.md`
- **Anthropic API Docs:** https://docs.anthropic.com/
- **API Console:** https://console.anthropic.com/

---

**Ready? Let's go!** 🚀

```bash
pip install -r requirements.txt
python claude.py
```

That's all you need! ✨
