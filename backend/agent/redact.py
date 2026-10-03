import re

def redact(text: str) -> str:
    """
    Removes highly sensitive PII before sending text to the LLM.
    - Phone numbers
    - SSNs
    - Long numeric IDs
    Note: Real-world street address redaction usually requires an NER model (like spaCy), 
    so we do a simple regex best-effort for common patterns here.
    """
    # 1. Phone numbers
    # Matches formats like: 123-456-7890, (123) 456-7890, 1234567890, +1 123 456 7890
    phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    text = re.sub(phone_pattern, '[REDACTED_PHONE]', text)
    
    # 2. SSN-like patterns
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    text = re.sub(ssn_pattern, '[REDACTED_SSN]', text)
    
    # 3. Long numeric IDs (e.g., tracking numbers or candidate IDs > 10 digits)
    long_id_pattern = r'\b\d{10,}\b'
    text = re.sub(long_id_pattern, '[REDACTED_ID]', text)
    
    return text
