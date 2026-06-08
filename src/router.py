import os
import google.generativeai as genai

INTENT_LABELS = ["knowledge_query", "new_research", "out_of_scope"]

_ROUTER_SYSTEM = """You are an intent classifier for an academic research assistant.

Given a user message, return EXACTLY one of these labels (nothing else):
- knowledge_query  : user is asking about a research topic that may already be in the knowledge base
- new_research     : user explicitly wants to search for new papers or explore a brand-new topic
- out_of_scope     : the message has nothing to do with academic research (e.g., movies, cooking, games)

Reply with the label only. No punctuation, no explanation."""

_model = None


def _get_model():
    global _model
    if _model is None:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        _model = genai.GenerativeModel(
            model_name="gemini-3.1-flash-lite",
            system_instruction=_ROUTER_SYSTEM,
        )
    return _model


def route(query: str) -> str:
    """Classify user query into one of: knowledge_query, new_research, out_of_scope."""
    try:
        response = _get_model().generate_content(query)
        label = response.text.strip().lower()
        for valid in INTENT_LABELS:
            if valid in label:
                return valid
    except Exception:
        pass
    return "new_research"
