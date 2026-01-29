"""Tests for ConversationManager."""

from core.conversation import ConversationManager


def test_add_and_retrieve():
    cm = ConversationManager()
    cm.add("user", "hello")
    cm.add("assistant", "hi")
    assert len(cm) == 2
    assert cm.messages[0] == {"role": "user", "content": "hello"}
    assert cm.messages[1] == {"role": "assistant", "content": "hi"}


def test_sliding_window():
    cm = ConversationManager(max_history=3)
    for i in range(5):
        cm.add("user", f"msg-{i}")
    assert len(cm) == 3
    assert cm.messages[0]["content"] == "msg-2"
    assert cm.messages[2]["content"] == "msg-4"


def test_clear():
    cm = ConversationManager()
    cm.add("user", "hello")
    cm.clear()
    assert len(cm) == 0


def test_add_raw():
    cm = ConversationManager()
    cm.add_raw({"role": "user", "content": [{"type": "tool_result", "tool_use_id": "x", "content": "ok"}]})
    assert len(cm) == 1
    assert cm.messages[0]["role"] == "user"
