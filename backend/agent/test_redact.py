from backend.agent.redact import redact

def test_redact_phone():
    text = "Call me at 123-456-7890 or (987) 654-3210."
    redacted = redact(text)
    assert "[REDACTED_PHONE]" in redacted
    assert "123-456-7890" not in redacted
    assert "(987) 654-3210" not in redacted

def test_redact_ssn():
    text = "My SSN is 123-45-6789."
    redacted = redact(text)
    assert "[REDACTED_SSN]" in redacted
    assert "123-45-6789" not in redacted

def test_redact_long_id():
    text = "Your tracking ID is 987654321012."
    redacted = redact(text)
    assert "[REDACTED_ID]" in redacted
    assert "987654321012" not in redacted

def test_preserves_company_and_links():
    text = "Your interview at Google is confirmed. Link: https://meet.google.com/abc"
    redacted = redact(text)
    assert "Google" in redacted
    assert "https://meet.google.com/abc" in redacted
