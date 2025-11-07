# Setup Demo - Co Zobaczysz

## 🎬 Pierwsze Uruchomienie (Krok po kroku)

### 1. Uruchamiasz:
```bash
python claude.py
```

### 2. Widzisz banner i setup prompt:

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

### 3. Naciskasz Enter (lub `y`):

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

### 4. W przeglądarce:

Browser automatycznie otwiera się na: `https://console.anthropic.com/settings/keys`

**Co widzisz w Console:**
```
┌─────────────────────────────────────────────┐
│  Anthropic Console                          │
│  ┌────────┐                                 │
│  │ API Keys                   [+ Create Key]│
│  └────────┘                                 │
│                                             │
│  No API keys yet                            │
│  Create your first API key to get started  │
└─────────────────────────────────────────────┘
```

Klikasz **[+ Create Key]**, widzisz popup:
```
┌──────────────────────────┐
│  Create API Key          │
│                          │
│  Name:                   │
│  [________________]      │
│                          │
│  [ Cancel ]  [ Create ]  │
└──────────────────────────┘
```

Wpisujesz: `claude-code-python-20251107` (lub własną nazwę)

Klikasz **Create**, widzisz:
```
┌────────────────────────────────────────┐
│  ✅ API Key Created                    │
│                                        │
│  sk-ant-api03-abc123xyz...             │
│                                        │
│  ⚠️ Copy this now!                     │
│  You won't be able to see it again    │
│                                        │
│  [ Copy to Clipboard ]       [ Done ]  │
└────────────────────────────────────────┘
```

Klikasz **Copy to Clipboard**

### 5. Wracasz do terminala:

```
  Paste your API key here: sk-ant-api03-abc123xyz...█
```

Wklejasz (Ctrl+V / Cmd+V) i Enter.

### 6. Setup kończy się sukcesem:

```
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

**GOTOWE!** 🎉

---

## ✨ Co się stało w tle:

1. ✅ Utworzony plik `.env` (jeśli nie istniał)
2. ✅ Dodany `ANTHROPIC_API_KEY=sk-ant-...`
3. ✅ Ustawiony `CLAUDE_USE_OAUTH=false`
4. ✅ Klucz załadowany do aplikacji
5. ✅ Wszystko działa!

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

Type 'exit' or 'quit' to end session

ℹ Using API key from environment
ℹ Tools enabled (6 tools)
ℹ Agents enabled (4 specialized agents)
ℹ Available agents: Test Writer, Code Reviewer, Bug Fixer, Refactorer
ℹ Model: claude-sonnet-4-20250514
ℹ Extended Thinking: Enabled (budget: 10000 tokens)

════════════════════════════════════════════════

You> █
```

**NIE PYTA O KLUCZ!** Bo już go masz w `.env`! ✅

---

## 💡 Tip: Jeśli nie chcesz auto-open browser:

```
  → Open this link in your browser now? [Y/n]: n
```

Wtedy po prostu ręcznie skopiujesz link i otworzysz.

---

## 🎯 To wszystko!

Super prosty setup, **zero ręcznej edycji plików**!

Tak powinno wyglądać CLI w 2025! 🚀
