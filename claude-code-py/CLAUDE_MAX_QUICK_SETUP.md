# Claude Max Quick Setup 🚀

## ✨ Super Quick - 3 Commands!

Masz Claude Max/Pro? Użyj swojej subskrypcji w 3 krokach:

### 1. Zainstaluj official Claude Code (tylko do tokena)

```bash
npm install -g @anthropic-ai/claude-code
```

### 2. Wygeneruj token

```bash
claude setup-token
```

To otworzy browser, zalogujesz się Claude Max, token zapisze się automatycznie!

### 3. Skopiuj token do naszego Python clone

```bash
# Linux/Mac
echo "CLAUDE_CODE_OAUTH_TOKEN=$(jq -r '.accessToken' ~/.claude/oauth_token.json)" >> .env

# Windows PowerShell
$token = (Get-Content ~\.claude\oauth_token.json | ConvertFrom-Json).accessToken
Add-Content .env "CLAUDE_CODE_OAUTH_TOKEN=$token"
```

### 4. Uruchom!

```bash
python claude.py
```

**GOTOWE!** Używasz Claude Max subscription! 🎉

---

## 🎯 Alternatywnie - Manual Copy

Jeśli automatyczne kopiowanie nie działa:

1. Otwórz token file:
   ```bash
   # Linux/Mac
   cat ~/.claude/oauth_token.json

   # Windows
   type %USERPROFILE%\.claude\oauth_token.json
   ```

2. Skopiuj wartość `accessToken`

3. Dodaj do `.env`:
   ```env
   CLAUDE_CODE_OAUTH_TOKEN=paste-token-here
   ```

4. Run:
   ```bash
   python claude.py
   ```

---

## ✅ Co zobaczysz:

```
╔═══════════════════════════════════════════════╗
║     Claude Code Python - Sonnet 4.5 MVP      ║
║          Extended Thinking Enabled            ║
╚═══════════════════════════════════════════════╝

✅ Using CLAUDE_CODE_OAUTH_TOKEN from environment
   (Claude Max/Pro subscription token)

ℹ Tools enabled (6 tools)
ℹ Agents enabled (4 specialized agents)

You> █
```

**Używasz swojej Claude Max subskrypcji zamiast płacić za API!** 💰

---

## 🔄 Token Refresh

Token z `claude setup-token` jest **long-lived** (~6 hours).

Gdy wygaśnie, po prostu uruchom ponownie:
```bash
claude setup-token
```

I skopiuj nowy token do `.env`!

---

## 💡 Dlaczego to działa?

- Official Claude Code generuje token linked do Twojej Claude Max subscription
- Ten token działa jak API key, ale używa Twojej subskrypcji zamiast API credits!
- Nasz Python clone używa tego samego tokena
- **Zero dodatkowych kosztów!** Wszystko w ramach Twojej Max subscription!

---

## 🎉 TL;DR

```bash
# Raz (setup):
npm install -g @anthropic-ai/claude-code
claude setup-token
# Skopiuj token z ~/.claude/oauth_token.json do .env jako CLAUDE_CODE_OAUTH_TOKEN

# Potem zawsze:
python claude.py  # UŻYWA CLAUDE MAX! 🚀
```

**Super lekkie, używa Twojej subskrypcji, zero extra kosztów!** ✨
