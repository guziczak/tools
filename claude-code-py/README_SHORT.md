# Claude Code Python - Quick Reference

## 🚀 Super Quick Start

### 1. Setup (one time):
```bash
# Copy config
cp .env.example .env

# Edit and add your API key
nano .env  # or: notepad .env (Windows)

# Install dependencies
pip install -r requirements.txt
```

### 2. Run:
```bash
python claude.py
```

That's it! 🎉

---

## Windows:
```cmd
copy .env.example .env
notepad .env
pip install -r requirements.txt
python claude.py
```

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
