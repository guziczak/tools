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

### First Run Setup:

❌ **OAuth tokens DO NOT WORK** - use API key instead!

**Why OAuth doesn't work:**
- Tokens from `claude setup-token` only work with official Node.js CLI
- Public Anthropic API doesn't accept OAuth tokens
- This is a limitation of Anthropic's API

**✅ Use API Key (Simple & Works!):**
1. Run: `python claude.py`
2. Press Enter
3. Browser opens → https://console.anthropic.com
4. Sign up/login (can use Google)
5. Create API key → Paste
6. Done! ✅

**Free account includes $5 credit!** All features work (tools, agents, thinking)!

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
