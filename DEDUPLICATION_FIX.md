# Deduplication Fix - Intent Classification

## Problem

W commit **1c852e6** system klasyfikował intencję użytkownika **DWUKROTNIE** dla każdego zapytania:

```
User: "widzisz ostatniego commita?"

🎯 [Intent] Tier 1 match: git_log (keyword: ostatni+commit)  ← PIERWSZA klasyfikacja
🎯 [IntentRouter] Routing 'git_log' to GitLogHandler
🎯 [GitLogHandler] Pre-executing git log...
   ✅ Got 74 chars of git log
📝 [API Client] Message enriched with pre-executed tool results
🌐 [API Client] Entering OAuth tool execution loop
🎯 [Intent] Tier 1 match: git_log (keyword: ostatni+commit)  ← DRUGA klasyfikacja! ❌
```

### Root Cause

```python
# api_client.py

def chat_with_tools(self, user_message: str, ...):
    # PIERWSZA klasyfikacja
    intent, tool_choice = self._classify_query_intent(user_message)  # ← 1️⃣

    # Pre-execution
    if self.intent_router:
        intent_result = self.intent_router.route(intent, user_message)
        message_to_send = intent_result.enriched_message

    # Wywołanie chat()
    events = self.chat(message_to_send, system)  # ← Wywołuje chat()


def chat(self, user_message: str, ...):
    # DRUGA klasyfikacja! ❌
    intent, tool_choice = self._classify_query_intent(user_message)  # ← 2️⃣

    self.add_message("user", user_message)

    for event in self.client.chat_streaming(
        messages=self.messages,
        tool_choice=tool_choice,  # ← Używa wyniku z DRUGIEJ klasyfikacji!
        ...
    ):
        yield event
```

### Konsekwencje

❌ **Marnowanie CPU** - Każda klasyfikacja wykonuje:
- Levenshtein distance (O(n²)) dla fuzzy matching
- Jaccard similarity dla semantic matching
- Multiple regex operations

❌ **Confusing logs** - Wydaje się że system działa 2x

❌ **Inconsistency** - Druga klasyfikacja dostaje enriched message, nie original:
```python
# PIERWSZA klasyfikacja:
"widzisz ostatniego commita?"

# DRUGA klasyfikacja (enriched!):
"""User asked: 'widzisz ostatniego commita?'

Here are the last 5 commits:
e35c4f4 update
fc96672 update
..."""
```

⚠️ **Potencjalny bug** - Jeśli enriched message zmieni classification result!

---

## Solution

### Zmiany w kodzie

**1. Dodanie parametru `tool_choice` do `chat()`:**

```diff
- def chat(self, user_message: str, system: Optional[str] = None):
+ def chat(self, user_message: str, system: Optional[str] = None,
+          tool_choice: Optional[Dict[str, Any]] = None):
     """Send a message and stream the response.

     Args:
         user_message: User's message
         system: Optional system prompt
+        tool_choice: Optional pre-classified tool choice (to avoid re-classification)

     Yields:
         Events containing response chunks with type and data
     """
-    # STATE OF THE ART: 3-tier intent classification
-    # Tier 1: Exact triggers | Tier 2: Semantic matching | Tier 3: Claude decides
-    intent, tool_choice = self._classify_query_intent(user_message)
+    # If tool_choice not provided, classify intent
+    # (This happens when chat() is called directly, not via chat_with_tools())
+    if tool_choice is None:
+        print("🎯 [Intent] Classifying in chat() (direct call, not from chat_with_tools)")
+        intent, tool_choice = self._classify_query_intent(user_message)
+    else:
+        print("🎯 [Intent] Using pre-classified tool_choice from chat_with_tools() (no re-classification)")
```

**2. Przekazywanie `tool_choice` z `chat_with_tools()` do `chat()`:**

```diff
 if tool_round == 0:
     # Add user message via chat() (use enriched message if available)
-    events = self.chat(message_to_send, system)
+    # PASS tool_choice to avoid re-classification! ✅
+    events = self.chat(message_to_send, system, tool_choice=tool_choice)
```

---

## Po fixie

```
User: "widzisz ostatniego commita?"

🎯 [Intent] Tier 1 match: git_log (keyword: ostatni+commit)  ← Jedyna klasyfikacja
🎯 [IntentRouter] Routing 'git_log' to GitLogHandler
🎯 [GitLogHandler] Pre-executing git log...
   ✅ Got 74 chars of git log
📝 [API Client] Message enriched with pre-executed tool results
🌐 [API Client] Entering OAuth tool execution loop
🎯 [Intent] Using pre-classified tool_choice from chat_with_tools() (no re-classification)  ✅
```

---

## Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Intent classifications | 2x | 1x | **50% reduction** ✅ |
| Levenshtein distance calcs | 2x | 1x | **50% reduction** ✅ |
| Semantic similarity calcs | 2x | 1x | **50% reduction** ✅ |
| Log clarity | Confusing | Clear | **Better UX** ✅ |
| Bug risk | Medium | Low | **Safer** ✅ |

---

## Backwards Compatibility

✅ **Fully backwards compatible**
- `tool_choice` parameter defaults to `None`
- Direct `chat()` calls still work (classification happens if `tool_choice is None`)
- No breaking changes to public API

---

## Files Modified

- `claude-code-py/src/core/api_client.py`
  - Line 461: Added `tool_choice` parameter to `chat()`
  - Line 473-479: Conditional classification
  - Line 672: Pass `tool_choice` from `chat_with_tools()` to `chat()`

---

## Testing

Run:
```bash
python test_deduplication_simple.py
```

Expected output: Clear before/after demonstration of the fix.

---

## Conclusion

This fix eliminates unnecessary duplicate intent classification, improving:
- **Performance** (50% fewer classification operations)
- **Code clarity** (cleaner logs)
- **Correctness** (avoids potential classification inconsistencies)
- **Maintainability** (clearer separation of concerns)

**Status: ✅ FIXED**
