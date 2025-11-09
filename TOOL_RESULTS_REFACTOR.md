# Tool Results Refactor - Zero Redundancy

## Problem: Enriched Message Approach (BEFORE)

**Old approach** concatenated tool output into user message:

```python
# GitLogHandler (OLD)
enriched = f"""The user asked: "{user_message}"  ← REDUNDANT!

Here are the last 5 commits from git log:
{git_log}

Based on this commit history, please answer the user's question."""  ← META-COMMENTARY!

# To API:
messages = [{
    "role": "user",
    "content": "The user asked: 'widzisz ostatniego commita?'\n\nHere are commits..."
}]
```

**Problems:**
- ❌ Duplicates user question ("The user asked...")
- ❌ Meta-commentary ("Based on this...")
- ❌ Claude already knows the question (it's in history!)
- ❌ Wastes tokens
- ❌ Not following Anthropic API best practices

---

## Solution: Tool Results Format (AFTER - Opcja 1)

**New approach** injects tool results as proper `tool_use` + `tool_result` messages:

```python
# GitLogHandler (NEW)
return IntentResult(
    tool_results=[
        {
            "tool_name": "bash",
            "tool_input": {"command": "git log --oneline -5"},
            "tool_output": git_log  # ← Just data, no commentary!
        }
    ],
    metadata={"tool_executed": "bash"}
)

# chat_with_tools() injects as fake tool execution:
self.messages.append({
    "role": "assistant",
    "content": [{
        "type": "tool_use",
        "id": "pre-exec-0",
        "name": "bash",
        "input": {"command": "git log --oneline -5"}
    }]
})

self.messages.append({
    "role": "user",
    "content": [{
        "type": "tool_result",
        "tool_use_id": "pre-exec-0",
        "content": "e35c4f4 update\nfc96672 update\n..."  # ← CLEAN DATA!
    }]
})

# Then add ORIGINAL user message:
self.add_message("user", "widzisz ostatniego commita?")  # ← CLEAN! No enrichment!
```

**To API:**
```json
{
  "messages": [
    {
      "role": "assistant",
      "content": [
        {"type": "tool_use", "id": "pre-exec-0", "name": "bash",
         "input": {"command": "git log --oneline -5"}}
      ]
    },
    {
      "role": "user",
      "content": [
        {"type": "tool_result", "tool_use_id": "pre-exec-0",
         "content": "e35c4f4 update\nfc96672 update\n..."}
      ]
    },
    {
      "role": "user",
      "content": "widzisz ostatniego commita?"  // ← CLEAN! Original question!
    }
  ]
}
```

---

## Benefits

| Aspect | Before (enriched_message) | After (tool_results) |
|--------|---------------------------|----------------------|
| **User question duplication** | ❌ Yes ("The user asked...") | ✅ None |
| **Meta-commentary** | ❌ Yes ("Based on this...") | ✅ None |
| **Token efficiency** | ❌ Low (duplicates) | ✅ High (zero redundancy) |
| **Anthropic API compliance** | ⚠️ Works but not idiomatic | ✅ Perfect (tool_use/tool_result) |
| **Semantically correct** | ❌ Tool output in user message | ✅ Tool output in tool_result |
| **Claude perception** | ⚠️ "User pasted data" | ✅ "I executed this tool" |

---

## Implementation

### 1. IntentResult Dataclass

```python
@dataclass
class IntentResult:
    enriched_message: Optional[str] = None  # DEPRECATED
    metadata: Dict[str, Any] = field(default_factory=dict)
    skip_llm: bool = False
    tool_results: Optional[List[Dict[str, Any]]] = None  # NEW - preferred!
```

### 2. Handler Changes

**GitLogHandler:**
```python
# BEFORE:
enriched = f"""The user asked: "{user_message}"...{git_log}..."""
return IntentResult(enriched_message=enriched, ...)

# AFTER:
return IntentResult(
    tool_results=[{
        "tool_name": "bash",
        "tool_input": {"command": "git log --oneline -5"},
        "tool_output": git_log
    }],
    metadata={...}
)
```

**AnalyzeChangesHandler:**
```python
# BEFORE:
enriched = f"""User asked...{git_show_output}...INSTRUCTIONS: Analyze..."""
return IntentResult(enriched_message=enriched, ...)

# AFTER:
return IntentResult(
    tool_results=[{
        "tool_name": "bash",
        "tool_input": {"command": f"git show {hash}"},
        "tool_output": git_show_output
    }],
    metadata={
        "analysis_instructions": "Analyze WHAT CHANGED..."  # ← Injected to system!
    }
)
```

### 3. chat_with_tools() Changes

```python
if intent_result.tool_results:
    # Inject as fake tool_use + tool_result
    for i, tool_res in enumerate(intent_result.tool_results):
        self.messages.append({
            "role": "assistant",
            "content": [{"type": "tool_use", ...}]
        })
        self.messages.append({
            "role": "user",
            "content": [{"type": "tool_result", ...}]
        })

    # Use ORIGINAL user message (not enriched!)
    message_to_send = user_message  # ← CLEAN!

    # Analysis instructions → system prompt
    if intent_result.metadata.get("analysis_instructions"):
        system = f"{system}\n\n{instructions}"
```

---

## Example: "widzisz ostatniego commita?"

### BEFORE:
```
┌─────────────────────────────────────────────────────────────┐
│ TO API (enriched_message approach):                         │
├─────────────────────────────────────────────────────────────┤
│ messages: [                                                  │
│   {                                                          │
│     "role": "user",                                          │
│     "content": "The user asked: 'widzisz ostatniego comm... │  ← REDUNDANT!
│                                                              │
│                 Here are the last 5 commits from git log:   │  ← META!
│                 e35c4f4 update                               │
│                 fc96672 update                               │
│                 ...                                          │
│                 Based on this commit history, please answ..." │  ← MORE META!
│   }                                                          │
│ ]                                                            │
└─────────────────────────────────────────────────────────────┘

Tokens wasted: ~50 (redundancy + meta-commentary)
```

### AFTER:
```
┌─────────────────────────────────────────────────────────────┐
│ TO API (tool_results approach):                              │
├─────────────────────────────────────────────────────────────┤
│ messages: [                                                  │
│   {                                                          │
│     "role": "assistant",                                     │
│     "content": [                                             │
│       {"type": "tool_use", "id": "pre-exec-0",               │
│        "name": "bash",                                       │
│        "input": {"command": "git log --oneline -5"}}         │
│     ]                                                        │
│   },                                                         │
│   {                                                          │
│     "role": "user",                                          │
│     "content": [                                             │
│       {"type": "tool_result", "tool_use_id": "pre-exec-0",   │
│        "content": "e35c4f4 update\nfc96672 update\n..."}     │  ← CLEAN DATA!
│     ]                                                        │
│   },                                                         │
│   {                                                          │
│     "role": "user",                                          │
│     "content": "widzisz ostatniego commita?"                 │  ← ORIGINAL!
│   }                                                          │
│ ]                                                            │
└─────────────────────────────────────────────────────────────┘

Tokens saved: ~50 (zero redundancy!)
```

---

## Backwards Compatibility

✅ **Fully backwards compatible!**

Old handlers using `enriched_message` still work:

```python
# Old code still works (deprecated path):
if intent_result.enriched_message:
    message_to_send = intent_result.enriched_message
    print("📝 [API Client] Message enriched (deprecated approach)")
```

New handlers use `tool_results`:

```python
# New code (preferred path):
if intent_result.tool_results:
    # Inject as tool_use + tool_result
    ...
```

---

## Files Modified

1. **claude-code-py/src/core/intent_handlers.py**
   - IntentResult: Added `tool_results` field
   - GitLogHandler: Returns `tool_results` instead of `enriched_message`
   - AnalyzeChangesHandler: Returns `tool_results` with `analysis_instructions`
   - ExploreProjectHandler: Returns `tool_results`
   - ListFilesHandler: Returns `tool_results`

2. **claude-code-py/src/core/api_client.py**
   - chat_with_tools(): Injects `tool_results` as fake tool_use/tool_result
   - Handles `analysis_instructions` in metadata → system prompt
   - Backwards compatible with `enriched_message`

---

## Testing

Run:
```bash
python -m py_compile claude-code-py/src/core/api_client.py
python -m py_compile claude-code-py/src/core/intent_handlers.py
```

Expected: ✅ Both files compile successfully

---

## Impact

- **~50 tokens saved** per pre-executed tool
- **Zero redundancy** - user question appears once
- **Semantically correct** - tool results in proper API format
- **Better Claude perception** - sees tool execution, not paste
- **Follows Anthropic best practices** ✅

---

## Status

✅ **IMPLEMENTED**

Commit: [TBD]
