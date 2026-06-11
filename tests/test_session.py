from hermes.session import Session


def test_session_roundtrip_and_resume():
    s = Session.new("anthropic/claude-haiku-4-5-20251001", "anthropic")
    s.add("user", "hello")
    s.add("assistant", "hi there")
    s.save()

    loaded = Session.load(s.id)
    assert loaded.id == s.id
    assert [m.role for m in loaded.messages] == ["user", "assistant"]
    assert loaded.messages[0].content == "hello"

    recent = Session.most_recent()
    assert recent is not None and recent.id == s.id


def test_session_structured_content_roundtrip():
    s = Session.new("anthropic/x", "anthropic")
    blocks = [{"type": "tool_use", "id": "t1", "name": "stub__echo", "input": {"text": "hi"}}]
    s.add("assistant", blocks)
    s.save()
    loaded = Session.load(s.id)
    assert loaded.messages[0].content == blocks
