import os
import google.generativeai as genai

_REWRITER_SYSTEM = """You are an academic search query optimizer.

Rewrite the user's message into clear English academic search keywords suitable for arXiv.
Rules:
- Translate to English
- Remove conversational filler (e.g., "help me find", "I want to know")
- Keep the core research intent
- Output 1–2 lines of keywords only, no explanation

Example:
Input: 幫我找關於 transformer 在影像辨識的應用論文
Output: transformer image recognition computer vision deep learning"""

_model = None


def _get_model():
    global _model
    if _model is None:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        _model = genai.GenerativeModel(
            model_name="gemini-3.1-flash-lite",
            system_instruction=_REWRITER_SYSTEM,
        )
    return _model


def rewrite(query: str) -> str:
    """Rewrite a user query into English academic search keywords."""
    try:
        response = _get_model().generate_content(query)
        rewritten = response.text.strip()
        if rewritten:
            return rewritten
    except Exception:
        pass
    return query
