# Quick Start Guide - Claude Code Python

## 🚀 Jak uruchomić w 3 krokach:

### Krok 1: Przygotuj API Key

```bash
# Skopiuj przykładową konfigurację
cp .env.example .env

# Edytuj .env i dodaj swój klucz API
nano .env
```

W pliku `.env` ustaw:
```env
ANTHROPIC_API_KEY=sk-ant-twoj-klucz-tutaj
CLAUDE_USE_OAUTH=false
CLAUDE_AGENTS_ENABLED=true
CLAUDE_TOOLS_ENABLED=true
```

**Gdzie wziąć API key?**
1. Idź na: https://console.anthropic.com/
2. Zaloguj się
3. Settings → API Keys
4. Create Key
5. Skopiuj i wklej do .env

---

### Krok 2: Uruchom!

```bash
# SUPER PROSTY sposób
python claude.py

# Albo przez skrypt
./claude.sh

# Albo launcher
./RUN_ME.sh
```

---

### Krok 3: Testuj agentów!

Gdy aplikacja wystartuje, zobaczysz:

```
╔═══════════════════════════════════════════════╗
║     Claude Code Python - Sonnet 4.5 MVP      ║
║          Extended Thinking Enabled            ║
╚═══════════════════════════════════════════════╝

ℹ Using API key from environment
ℹ Tools enabled (6 tools)
ℹ Agents enabled (4 specialized agents)
ℹ Available agents: Test Writer, Code Reviewer, Bug Fixer, Refactorer
ℹ Model: claude-sonnet-4-20250514

════════════════════════════════════════════════

You>
```

---

## 🎯 Przykłady użycia:

### 1. Zobacz dostępnych agentów:
```
You> /agents
```

### 2. Użyj Test Writer Agent:
```
You> Write comprehensive unit tests for the read_file function

Claude: 🔧 Claude wants to use: delegate_to_test_writer
        ⚙️ Executing tool: delegate_to_test_writer

        [Agent pisze testy...]
```

### 3. Użyj Bug Fixer Agent:
```
You> There's a bug in bash.py - fix the initialization order issue

Claude: [deleguje do Bug Fixer Agent]
        [Analizuje problem i proponuje fix]
```

### 4. Użyj Code Reviewer Agent:
```
You> Review the agent system code for potential issues

Claude: [deleguje do Code Reviewer]
        [Szczegółowa analiza kodu]
```

### 5. Użyj Thinking Levels:
```
You> ultrathink about refactoring the tool executor

ℹ Thinking level: ULTRA (32,000 tokens)
Claude: 🧠 Thinking...
        [Głęboka analiza przed odpowiedzią]
```

### 6. Użyj Tools bezpośrednio:
```
You> Read the README.md file

Claude: 🔧 Claude wants to use: read_file
        ✓ Tool result (Success)
        [Zawartość pliku]
```

---

## 📋 Dostępne Komendy:

```
/help     - Pomoc
/agents   - Pokaż agentów
/clear    - Wyczyść ekran
/reset    - Reset historii
/login    - Re-autentykacja
/logout   - Wyloguj
exit/quit - Wyjście
```

---

## 💡 Thinking Levels:

| Keyword | Tokens | Opis |
|---------|--------|------|
| `think` | 4,000 | Szybka analiza |
| `think hard` | 10,000 | Dokładna analiza |
| `think harder` | 20,000 | Głęboka analiza |
| `ultrathink` | 32,000 | Maksymalne reasoning |

**Przykład:**
```
You> think hard about the security implications of this code
ℹ Thinking level: STANDARD (10,000 tokens)
```

---

## 🔧 Dostępne Tools:

1. **read_file** - Czytaj pliki
2. **write_file** - Pisz pliki
3. **edit_file** - Edytuj pliki (find & replace)
4. **bash** - Wykonuj komendy shell (Linux/Mac/Windows!)
5. **grep** - Szukaj tekstu w plikach
6. **glob** - Znajdź pliki po pattern

---

## 🤖 Dostępni Agenci:

1. **Test Writer** - Pisze testy (unit, integration)
2. **Code Reviewer** - Reviewuje kod (bugs, security, quality)
3. **Bug Fixer** - Naprawia bugi (debugging, root cause analysis)
4. **Refactorer** - Poprawia strukturę kodu (design patterns, SOLID)

**Claude automatycznie wybiera odpowiedniego agenta!**

---

## ⚡ Pro Tips:

1. **Agents vs Tools:**
   - Tools → Proste operacje (read file, run command)
   - Agents → Złożone zadania (write tests, review code)

2. **Thinking Levels:**
   - Użyj dla złożonych problemów
   - "ultrathink" dla architektury/design

3. **Context:**
   - Cała historia jest zachowana
   - Możesz odnosić się do poprzednich wiadomości

4. **Multi-step:**
   - Claude może użyć wielu tools/agents w jednej odpowiedzi
   - Może delegować do agenta, który użyje tools

---

## 🐛 Troubleshooting:

### Problem: "ANTHROPIC_API_KEY not found"
**Fix:** Sprawdź czy masz `.env` z kluczem API

### Problem: "OAuth failed"
**Fix:** Ustaw `CLAUDE_USE_OAUTH=false` w .env i użyj manual API key

### Problem: "No module named 'anthropic'"
**Fix:** Zainstaluj dependencies:
```bash
pip install -r requirements.txt
```

### Problem: "Permission denied: ./claude.sh"
**Fix:** Zrób skrypt executable:
```bash
chmod +x claude.sh
```

---

## 📚 Więcej info:

- [README.md](README.md) - Pełna dokumentacja
- [CONTRIBUTING.md](CONTRIBUTING.md) - Developer guide
- [BEST_PRACTICES.md](BEST_PRACTICES.md) - Best practices

---

## 🎉 Gotowe!

Teraz możesz używać Claude Code Python z:
- ✅ Extended thinking
- ✅ Tool calling
- ✅ Automatic agent routing
- ✅ 4 specialized agents
- ✅ Cross-platform support

**Miłego kodowania!** 🚀
