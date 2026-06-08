import re

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "ignore prior instructions",
    "disregard previous",
    "disregard all previous",
    "forget previous instructions",
    "system prompt",
    "you are now",
    "developer mode",
    "jailbreak",
    "bypass your",
    "override your",
    "pretend you are",
    "act as if you have no",
    "ignore your guidelines",
    "ignore your rules",
    "reveal your instructions",
    "tell me your instructions",
    "what are your instructions",
    "忽略之前",
    "忽略前面",
    "忽略所有之前",
    "忘記之前的指示",
    "系統提示",
    "越獄",
    "繞過規則",
    "假裝你沒有限制",
    "告訴我你的指示",
]


class TurnBudget:
    """Tracks and enforces max LLM turns per request."""

    def __init__(self, max_turns: int = 12):
        self.max_turns = max_turns
        self._used = 0

    def allow(self) -> bool:
        if self._used >= self.max_turns:
            return False
        self._used += 1
        return True

    @property
    def used(self) -> int:
        return self._used

    @property
    def remaining(self) -> int:
        return self.max_turns - self._used


def check_input(text: str) -> dict:
    """Detect prompt injection attempts. Returns {"blocked": bool, "reason": str}."""
    lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lower:
            return {
                "blocked": True,
                "reason": f"Potential prompt injection detected: '{pattern}'",
            }
    return {"blocked": False, "reason": ""}


def groundedness_check(answer: str, tool_results: list) -> list[str]:
    """
    Check that large numbers cited in the answer appear in tool results.
    Returns a list of violation strings (empty = no violations).
    """
    answer_numbers = set(re.findall(r"\b\d{4,}\b", answer))
    if not answer_numbers:
        return []

    facts_text = " ".join(str(r) for r in tool_results)
    facts_numbers = set(re.findall(r"\b\d{4,}\b", facts_text))

    return [
        f"Ungrounded number: {num}"
        for num in answer_numbers
        if num not in facts_numbers
    ]
