# Claude Code Python - Quick Reference

## 🚀 Super Quick Start

### 1. Install dependencies (one time):
```bash
pip install -r requirements.txt
```

### 2. Run:
```bash
python claude.py
```

### First Run - Choose Your Method:

**Option A: Claude Max/Pro Subscription** (use your existing plan!)
1. Install official Claude Code: `npm install -g @anthropic-ai/claude-code`
2. Generate token: `claude setup-token`
3. Copy token to `.env`: `CLAUDE_CODE_OAUTH_TOKEN=your-token`
4. Run: `python claude.py` ✅

See `CLAUDE_MAX_QUICK_SETUP.md` for details!

**Option B: API Key** (pay-as-you-go, auto-setup)
1. Just run: `python claude.py`
2. Browser opens → Console
3. Create API key → Paste
4. Done! ✅

**Simple, automatic, works!** 🎉

**OAuth Option:** Install `cloudscraper` to enable OAuth flow (bypasses Cloudflare):
```bash
pip install cloudscraper
echo "CLAUDE_USE_OAUTH=true" > .env
python claude.py
```
See `OAUTH_WITH_CLOUDSCRAPER.md` for details. API key is simpler and recommended for most users.

That's it! 🎉

---

## Windows (Same!):
```cmd
pip install -r requirements.txt
python claude.py
```

**Interactive setup works on all platforms!** 🪟🐧🍎

---

## Features:
- ✅ Extended thinking (Sonnet 4.5)
- ✅ Tool calling (6 tools)
- ✅ Agent routing (4 specialized agents)
- ✅ Thinking levels (4 levels)
- ✅ Cross-platform (Linux/Mac/Windows)

---

## Commands:
```
/help     - Help
/agents   - Show agents
/clear    - Clear screen
/reset    - Reset history
exit/quit - Exit
```

---

## Examples:
```
You> Write tests for my code
You> Review this file for bugs
You> ultrathink about the architecture
You> Read the README.md
```

---

## Agents:
1. **Test Writer** - Writes comprehensive tests
2. **Code Reviewer** - Reviews code quality
3. **Bug Fixer** - Debugs and fixes issues
4. **Refactorer** - Improves code structure

**Claude automatically chooses the right agent!**

---

## More info:
- [QUICKSTART.md](QUICKSTART.md) - Detailed guide
- [WINDOWS_SETUP.md](WINDOWS_SETUP.md) - Windows guide
- [README.md](README.md) - Full documentation
