import re
class PromptSecurity:
    INJECTION = re.compile(r"ignore\s+(all|previous)|system\s+prompt|developer\s+message|reveal\s+(the\s+)?prompt", re.I)
    SENSITIVE = re.compile(r"(?i)(password|secret|api[_ -]?key|token)\s*[:=]\s*[^\s,;]+")
    def validate(self, prompt):
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 12000: raise ValueError("invalid_prompt")
        if self.INJECTION.search(prompt): raise ValueError("prompt_injection_detected")
        return True
    def filter_sensitive(self, text): return self.SENSITIVE.sub(lambda m: m.group(1) + "=[REDACTED]", str(text))
    def isolate(self, organization_id, records): return [r for r in records if r.get("organization_id") in {None, organization_id}]
