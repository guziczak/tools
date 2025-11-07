# Claude Code Python - MVP

Natywny Python clone Claude Code z extended thinking i Rich terminal UI.

## Features

- 💬 **Chat z Claude Sonnet 4.5** - najnowszy model
- 🧠 **Extended thinking** - deep reasoning z widocznym procesem myślenia
- 🎨 **Rich terminal UI** - kolorowy interface z emoji i formatowaniem
- 📝 **Streaming responses** - real-time odpowiedzi
- 💾 **Historia konwersacji** - kontekst zachowywany przez całą sesję
- 🔐 **OAuth device flow** - autentykacja przez przeglądarkę (jak w Claude Code!)
- 🔧 **Tool calling** - Claude może używać narzędzi:
  - `read_file` - czytanie plików
  - `write_file` - pisanie plików
  - `edit_file` - edycja plików (find & replace)
  - `bash` - wykonywanie komend shell (**cross-platform**: Linux/Mac/Windows!)
  - `grep` - szukanie tekstu w plikach (regex support)
  - `glob` - znajdowanie plików po pattern (`*.py`, `**/*.txt`, etc)

## Instalacja

1. **Sklonuj/przejdź do katalogu:**
   ```bash
   cd claude-code-py
   ```

2. **Zainstaluj zależności:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Skonfiguruj API key:**
   ```bash
   cp .env.example .env
   # Edytuj .env i dodaj swój ANTHROPIC_API_KEY
   nano .env
   ```

   **⚠️ UWAGA:** OAuth device flow **może nie działać** - Anthropic API może nie mieć publicznych OAuth endpoints. **Zalecam użycie manual API key!**

   W `.env` ustaw:
   ```env
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   CLAUDE_USE_OAUTH=false
   ```

## Użycie

```bash
python src/main.py
# lub
./claude.sh
```

## Testowanie

Przed pełnym uruchomieniem, przetestuj czy wszystko działa:

```bash
# Test podstawowego chatu (bez tools)
python test_basic.py
```

Powinno wyświetlić:
```
✓ PASS - Basic Chat
✓ PASS - Extended Thinking
```

Jeśli testy przechodzą - wszystko działa! Możesz uruchomić pełną aplikację:

```bash
./claude.sh
```

## Komendy

- `/help` - Pomoc
- `/clear` - Wyczyść ekran
- `/reset` - Wyczyść historię konwersacji
- `/login` - Re-autentykacja (force OAuth flow)
- `/logout` - Wyloguj (usuń zapisany token)
- `exit` / `quit` - Wyjście

## Konfiguracja (.env)

```env
# OAuth (recommended) - zostaw puste żeby użyć browser auth
ANTHROPIC_API_KEY=
CLAUDE_USE_OAUTH=true

# Albo manual API key
# ANTHROPIC_API_KEY=sk-ant-...
# CLAUDE_USE_OAUTH=false

# Model configuration
CLAUDE_MODEL=claude-sonnet-4-20250514
CLAUDE_MAX_TOKENS=8000
CLAUDE_TEMPERATURE=1.0
CLAUDE_THINKING_ENABLED=true
CLAUDE_THINKING_BUDGET=10000
```

### Dwa sposoby autentykacji:

1. **Manual API Key (ZALECANE)** ✅
   - Wpisz swój API key w `ANTHROPIC_API_KEY`
   - Ustaw `CLAUDE_USE_OAUTH=false`
   - **To działa zawsze!**

2. **OAuth Device Flow (EKSPERYMENTALNE)** ⚠️
   - Zostaw `ANTHROPIC_API_KEY` pusty
   - Ustaw `CLAUDE_USE_OAUTH=true`
   - **UWAGA:** Może nie działać - Anthropic API może nie mieć publicznych OAuth endpoints
   - Jeśli OAuth nie działa, aplikacja automatycznie pokaże instrukcje jak użyć manual API key

## Wymagania

- Python 3.8+
- Anthropic API key
- Linux/macOS/Windows (WSL)

## Architecture

```
src/
├── core/
│   └── api_client.py       # Anthropic API wrapper
├── ui/
│   └── terminal.py         # Rich terminal interface
└── main.py                 # Main application
```

## Bezpieczeństwo

- Token OAuth zapisywany w `~/.claude-code-py/auth.json` z permissions `0600` (tylko owner może czytać)
- Katalog config z permissions `0700`
- Token automatycznie wygasa i wymaga re-autentykacji

## TODO

**✅ Zrobione:**
- [x] OAuth device flow authentication
- [x] Token storage (secure)
- [x] Extended thinking support
- [x] Tool system architecture (base + registry)
- [x] Tool calling (Read/Write/Edit/Bash/Grep/Glob)
- [x] Cross-platform Bash tool (PowerShell on Windows)
- [x] Rich UI z tool visualization

**🚧 W trakcie:**
- [ ] Full tool execution loop (Claude → Tool → Claude → Response)
- [ ] Multi-line input editor ([X more lines] feature)
- [ ] Output collapsing dla długich wyników

**📋 Planowane:**
- [ ] Session persistence (save/load conversations)
- [ ] Markdown rendering w Rich (prettier output)
- [ ] Syntax highlighting dla code blocks w tool output
- [ ] History navigation (arrow keys)
- [ ] More tools (Git, Docker, etc)
- [ ] MCP server support

## Przykłady użycia

```bash
# Uruchom aplikację
./claude.sh

# Przykładowe komendy do Claude:
You> Read the file README.md and summarize it
Claude: 🔧 Using tool: read_file
       ✓ Tool result (Success)
       [Claude podsumowuje zawartość]

You> Create a Python script that prints hello world
Claude: [pisze kod]
       🔧 Using tool: write_file
       ✓ Tool result (Success)
       Created file: hello.py

You> Search for "TODO" in all Python files
Claude: 🔧 Using tool: grep
       ✓ Tool result (Success)
       Found 5 matches in 3 files...
```

## Cross-platform Support

**Tools działają natywnie na wszystkich platformach:**

- **Linux/Mac**: używa `bash`, `grep`, standardowe narzędzia
- **Windows**: automatycznie wykrywa i używa PowerShell/CMD
- **File operations**: `pathlib` - uniwersalne ścieżki

## Różnice vs oryginał Claude Code

**Co już działa:**
- ✅ Extended thinking (Sonnet 4.5)
- ✅ OAuth device flow authentication
- ✅ Streaming responses
- ✅ Rich terminal UI
- ✅ Tool calling (Read/Write/Edit/Bash/Grep/Glob)
- ✅ Cross-platform shell execution

**Co jeszcze nie / Co może nie działać:**
- ⚠️ **OAuth device flow** - może nie działać (endpointy mogą nie istnieć), użyj manual API key
- ❌ **MCP servers** - nie zaimplementowane
- ❌ **Agentic mode** - nie zaimplementowane
- ❌ **Git integration** - nie zaimplementowane
- ❌ **Edit tool (diff-based)** - mamy tylko find/replace
- ❌ **Session persistence** - brak save/load
