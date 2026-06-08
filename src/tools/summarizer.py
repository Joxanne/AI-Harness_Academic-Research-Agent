import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

_model = None


def _get_model():
    global _model
    if _model is None:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        _model = genai.GenerativeModel("gemini-3.1-flash-lite")
    return _model


def summarize_paper(title: str, abstract: str) -> str:
    """Tool 2: 將論文摘要整理為繁體中文結構化摘要。"""
    model = _get_model()
    prompt = f"""請用繁體中文對以下學術論文進行結構化摘要。

論文標題：{title}

論文摘要（英文原文）：
{abstract}

請嚴格按照以下格式輸出：
**研究問題：** （一句話說明本論文解決什麼問題）
**研究方法：** （使用了什麼關鍵方法或技術架構）
**主要貢獻：** （最重要的發現、創新或實驗結果）
**關鍵詞：** （3至5個英文技術關鍵詞，用逗號分隔）"""

    response = model.generate_content(prompt)
    return response.text
