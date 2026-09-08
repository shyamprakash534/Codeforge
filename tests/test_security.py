from codeforge.core.security.security_policy import SecurityPolicyEngine

def test_detects_hardcoded_secret():
    findings = SecurityPolicyEngine.scan_content("x.py", 'api_key = "1234567890abcdef"')
    assert any(f.risk_type == "secret_leak" for f in findings)

def test_detects_dangerous_call():
    findings = SecurityPolicyEngine.scan_content("x.py", "eval(user_input)")
    assert any(f.risk_type == "dangerous_call" for f in findings)

def test_clean_content():
    assert SecurityPolicyEngine.scan_content("x.py", "print('hello')") == []
