import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix: uvicorn creates tasks with context=contextvars.Context() (isolated context),
# which clears sniffio's context variable. Fall back to get_running_loop() instead.
import asyncio
import sniffio as _sniffio
_orig_detect = _sniffio._impl.current_async_library

def _patched_detect():
    try:
        return _orig_detect()
    except _sniffio.AsyncLibraryNotFoundError:
        try:
            asyncio.get_running_loop()
            return "asyncio"
        except RuntimeError:
            pass
        raise

_sniffio._impl.current_async_library = _patched_detect
_sniffio.current_async_library = _patched_detect

# Fix 2: nest_asyncio (used by Chainlit CLI) replaces _CTask with _PyTask,
# but leaves asyncio.current_task as the C builtin. The C builtin doesn't
# see tasks registered by _PyTask in an empty contextvars.Context()
# (which uvicorn uses for each ASGI request), so it returns None.
# anyio's CancelScope then does WeakKeyDictionary[None] → TypeError.
# Solution: swap in the Python implementation which reads _current_tasks dict.
import asyncio.tasks as _tasks
if hasattr(_tasks, '_py_current_task') and asyncio.current_task is not _tasks._py_current_task:
    asyncio.current_task = _tasks.current_task = _tasks._py_current_task
    # anyio imports current_task at module load time; patch its binding too.
    try:
        import anyio._backends._asyncio as _anyio_be
        _anyio_be.current_task = _tasks._py_current_task
    except ImportError:
        pass

import json
import chainlit as cl
from src.agent import ResearchAgent

TOOL_LABELS = {
    # internal pipeline steps
    "_governance":    "🛡 安全檢查",
    "_router":        "🔀 意圖分類",
    "_rewriter":      "✏️ 查詢改寫",
    "_groundedness":  "✅ 事實驗證",
    # research tools
    "search_papers":           "搜尋 arXiv 論文",
    "summarize_paper":         "產生中文摘要",
    "save_to_knowledge_base":  "存入知識庫",
    "query_knowledge_base":    "查詢知識庫（RAG）",
    "expand_context":          "擴展段落上下文",
}

WELCOME_MESSAGE = """## 智慧學術研究助理

你好！我是你的學術研究助理，可以幫你：

- **搜尋論文** — 從 arXiv 找到最新相關研究
- **摘要整理** — 將英文論文整理為繁體中文結構化摘要
- **知識庫管理** — 自動將論文存入本地知識庫，下次直接查詢
- **深度解析** — 針對具體問題從已存論文中精準回答

請輸入你的研究問題或關鍵字，例如：
- `幫我搜尋 transformer 在自然語言處理的應用`
- `deep reinforcement learning 有哪些主要演算法？`
- `知識庫裡有哪些論文？`"""


@cl.on_chat_start
async def on_chat_start():
    agent = ResearchAgent()
    cl.user_session.set("agent", agent)
    cl.user_session.set("slots", {
        "topics_queried": [],
        "papers_saved": 0,
        "last_intent": None,
    })
    await cl.Message(content=WELCOME_MESSAGE).send()


@cl.on_message
async def on_message(message: cl.Message):
    agent: ResearchAgent = cl.user_session.get("agent")
    if agent is None:
        agent = ResearchAgent()
        cl.user_session.set("agent", agent)

    thinking_msg = cl.Message(content="")
    await thinking_msg.send()

    tool_steps: list[cl.Step] = []
    slots = cl.user_session.get("slots") or {
        "topics_queried": [], "papers_saved": 0, "last_intent": None
    }

    async def on_step(tool_name: str, args: dict, result):
        nonlocal slots
        label = TOOL_LABELS.get(tool_name, tool_name)
        step = cl.Step(name=tool_name, type="tool")
        await step.__aenter__()

        args_str = json.dumps(args, ensure_ascii=False, indent=2, default=str)
        step.input = f"**{label}**\n```json\n{args_str}\n```"

        if isinstance(result, str):
            preview = result[:500] + ("..." if len(result) > 500 else "")
        else:
            preview = json.dumps(result, ensure_ascii=False, default=str)
            if len(preview) > 500:
                preview = preview[:500] + "..."
        step.output = preview

        await step.__aexit__(None, None, None)
        tool_steps.append(step)

        # Update session slots
        if tool_name == "_router" and isinstance(result, dict):
            slots["last_intent"] = result.get("intent")
        elif tool_name == "save_to_knowledge_base":
            slots["papers_saved"] = slots.get("papers_saved", 0) + 1
        elif tool_name == "search_papers" and isinstance(args, dict) and args.get("query"):
            topics = slots.setdefault("topics_queried", [])
            if args["query"] not in topics:
                topics.append(args["query"])
        cl.user_session.set("slots", slots)

    try:
        response_text = await agent.run(message.content, on_step=on_step)
    except Exception as e:
        response_text = f"發生錯誤：{e}\n請確認 GEMINI_API_KEY 是否正確設定。"

    thinking_msg.content = response_text
    await thinking_msg.update()


@cl.on_chat_end
async def on_chat_end():
    cl.user_session.set("agent", None)
