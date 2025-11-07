# Windows Setup Guide 🪟

## 🚀 Quick Start dla Windows

### **Krok 1: Przygotuj API Key**

1. Otwórz folder w Eksplorator Plików
2. Kliknij prawym na `.env.example` → **Copy**
3. **Paste** → Zmień nazwę na `.env` (usuń `.example`)
4. Otwórz w Notepadzie: `notepad .env`
5. Dodaj swój API key:

```env
ANTHROPIC_API_KEY=sk-ant-twoj-klucz-tutaj
CLAUDE_USE_OAUTH=false
```

**Gdzie wziąć API key?**
- Idź na: https://console.anthropic.com/
- Settings → API Keys → Create Key

---

### **Krok 2: Zainstaluj Dependencies**

Otwórz **Command Prompt** lub **PowerShell** w folderze projektu:

```cmd
pip install -r requirements.txt
```

Jeśli nie masz Python:
- Pobierz z: https://www.python.org/downloads/
- Zainstaluj z opcją "Add Python to PATH"

---

### **Krok 3: Uruchom!**

#### **Opcja A: Przez Windows Batch Script** (NAJŁATWIEJSZE)

```cmd
RUN_ME.bat
```

Lub kliknij dwukrotnie na `RUN_ME.bat` w Eksplorator Plików.

#### **Opcja B: Bezpośrednio Python** (NAJPROSTSZE!)

```cmd
python claude.py
```

#### **Opcja C: Przez PowerShell**

```powershell
python claude.py
```

---

## 🎯 Co Zobaczysz:

```
╔═══════════════════════════════════════════════╗
║     Claude Code Python - Sonnet 4.5 MVP      ║
║          Extended Thinking Enabled            ║
╚═══════════════════════════════════════════════╝

ℹ Using API key from environment
ℹ Tools enabled (6 tools)
ℹ Agents enabled (4 specialized agents)
ℹ Available agents: Test Writer, Code Reviewer, Bug Fixer, Refactorer

You> █
```

---

## 📝 Przykłady Użycia:

### 1. Zobacz agentów:
```
You> /agents
```

### 2. Użyj agenta:
```
You> Write tests for my bash tool

Claude: 🔧 delegate_to_test_writer
        [Agent pisze testy...]
```

### 3. Użyj thinking:
```
You> ultrathink about this problem

ℹ Thinking level: ULTRA (32,000 tokens)
🧠 Thinking...
```

### 4. Użyj tools:
```
You> Read the README.md file

Claude: 🔧 read_file
        ✓ Tool result (Success)
        [Zawartość...]
```

---

## 🐛 Problemy na Windowsie?

### "python is not recognized"
**Fix:** Python nie jest w PATH
1. Zainstaluj Python z python.org
2. Podczas instalacji zaznacz "Add Python to PATH"
3. Albo dodaj manualnie do PATH

### "No module named 'anthropic'"
**Fix:** Dependencies nie zainstalowane
```cmd
pip install -r requirements.txt
```

### "Cannot open .env"
**Fix:** Plik nie istnieje lub zła nazwa
```cmd
copy .env.example .env
notepad .env
```

### "API key not found"
**Fix:** Sprawdź .env
```cmd
type .env
```
Powinno być: `ANTHROPIC_API_KEY=sk-ant-...`

### "bash tool not working"
**OK!** Bash tool automatycznie użyje **PowerShell** na Windowsie!
Cross-platform support działa. ✅

---

## 💡 Windows-Specific Tips:

1. **Ścieżki:**
   - Windows: `src\main.py` (backslash)
   - Linux: `src/main.py` (forward slash)
   - Kod obsługuje oba! ✅

2. **Shell Commands:**
   - Bash tool automatycznie wykrywa Windows
   - Używa PowerShell/CMD zamiast bash
   - Komendy powinny działać normalnie

3. **Edytor:**
   - Notepad: `notepad .env`
   - Notepad++: `notepad++ .env`
   - VS Code: `code .env`

4. **Terminal:**
   - Command Prompt (cmd.exe) ✅
   - PowerShell ✅
   - Git Bash ✅
   - WSL ✅

---

## 🎯 Szybkie Komendy:

```cmd
REM Setup
copy .env.example .env
notepad .env

REM Install
pip install -r requirements.txt

REM Run
RUN_ME.bat
REM lub
python src\main.py

REM Test
python -m pytest tests\
```

---

## 📚 Więcej Info:

- [QUICKSTART.md](QUICKSTART.md) - General guide
- [README.md](README.md) - Full documentation
- [BEST_PRACTICES.md](BEST_PRACTICES.md) - Developer guide

---

## ✅ Checklist:

- [ ] Python zainstalowany (3.8+)
- [ ] pip działa
- [ ] Dependencies zainstalowane (`pip install -r requirements.txt`)
- [ ] Plik `.env` utworzony
- [ ] API key dodany do `.env`
- [ ] Uruchomione: `RUN_ME.bat` lub `python src\main.py`

---

**Gotowe!** Teraz możesz używać Claude Code Python na Windowsie! 🎉
