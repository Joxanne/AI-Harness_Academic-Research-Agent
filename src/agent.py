import asyncio
import json
import os
from typing import Awaitable, Callable, Any

import google.generativeai as genai
from google.generativeai import protos
from dotenv import load_dotenv

from src.governance import TurnBudget, check_input, groundedness_check
from src.router import route
from src.rewriter import rewrite
from src.tools.declarations import TOOL_DECLARATIONS, TOOL_REGISTRY

load_dotenv()

SYSTEM_PROMPT = """你是一位智慧學術研究助理，專門幫助研究者搜尋、整理和深入理解學術論文。

## 工作流程（必須遵守）
1. 收到問題後，**先呼叫 query_knowledge_base** 查詢本地知識庫
2. 若回傳的 kb_sufficient=true（表示資料已足夠），直接根據知識庫結果回答
3. 若 kb_sufficient=false 或知識庫為空，則：
   a. 呼叫 search_papers 搜尋 arXiv（查詢關鍵字請用英文）
   b. 對每篇相關論文呼叫 summarize_paper 產生中文摘要
   c. 呼叫 save_to_knowledge_base 將論文存入知識庫
   d. 根據搜尋結果回答問題
4. 若需要更詳細的段落內容，呼叫 expand_context 擴展上下文

## 回答規則
- 語言：**繁體中文**
- 每次回答必須標注資料來源（論文標題 + arXiv URL）
- 保持學術但易懂的風格
- 若引用多篇論文，請條列說明各篇的貢獻"""

StepCallback = Callable[[str, dict, Any], Awaitable[None]]


class ResearchAgent:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(
            model_name="gemini-3.1-flash-lite",
            tools=[TOOL_DECLARATIONS],
            system_instruction=SYSTEM_PROMPT,
        )
        self.reset()

    def reset(self):
        self.chat = self.model.start_chat(history=[])

    async def run(self, user_message: str, on_step: StepCallback | None = None) -> str:
        # ── Stage 1: Governance ──────────────────────────────────────────
        gov_result = check_input(user_message)
        if on_step:
            await on_step("_governance", {"input": user_message[:200]}, gov_result)
        if gov_result["blocked"]:
            return f"⚠️ 此請求已被安全機制攔截：{gov_result['reason']}"

        # ── Stage 2: Intent routing ──────────────────────────────────────
        intent = await asyncio.to_thread(route, user_message)
        if on_step:
            await on_step("_router", {"query": user_message[:200]}, {"intent": intent})
        if intent == "out_of_scope":
            return "抱歉，此問題超出學術研究助理的服務範圍。請提問與論文研究相關的問題。"

        # ── Stage 3: Query rewriting ─────────────────────────────────────
        rewritten = await asyncio.to_thread(rewrite, user_message)
        if on_step:
            await on_step(
                "_rewriter",
                {"original": user_message[:200]},
                {"rewritten": rewritten},
            )

        # ── Stage 4: LLM + tool loop ─────────────────────────────────────
        budget = TurnBudget(max_turns=12)
        tool_results: list[Any] = []

        response = await asyncio.to_thread(self.chat.send_message, rewritten)

        while budget.allow():
            fn_calls = [
                p.function_call
                for p in response.parts
                if hasattr(p, "function_call") and p.function_call.name
            ]
            if not fn_calls:
                break

            fn_response_parts = []
            for fc in fn_calls:
                # Normalize protobuf types: RepeatedComposite → list, MapComposite → dict
                args = {
                    k: list(v) if "Repeated" in type(v).__name__ else v
                    for k, v in fc.args.items()
                }
                tool_fn = TOOL_REGISTRY.get(fc.name)
                if tool_fn:
                    result = await asyncio.to_thread(tool_fn, **args)
                else:
                    result = {"error": f"Unknown tool: {fc.name}"}

                tool_results.append(result)

                if on_step:
                    await on_step(fc.name, args, result)

                fn_response_parts.append(
                    protos.Part(
                        function_response=protos.FunctionResponse(
                            name=fc.name,
                            response={"result": json.dumps(result, ensure_ascii=False, default=str)},
                        )
                    )
                )

            response = await asyncio.to_thread(self.chat.send_message, fn_response_parts)

        # ── Stage 5: Groundedness check ───────────────────────────────────
        try:
            answer = response.text
        except Exception:
            return "無法生成回應，請稍後再試。"

        violations = groundedness_check(answer, tool_results)
        if violations and on_step:
            await on_step(
                "_groundedness",
                {"turns_used": budget.used},
                {"violations": violations, "count": len(violations)},
            )

        return answer
