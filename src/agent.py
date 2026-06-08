import asyncio
import json
import os
from typing import Awaitable, Callable, Any

import google.generativeai as genai
from google.generativeai import protos
from dotenv import load_dotenv

from src.tools.arxiv_search import search_papers
from src.tools.summarizer import summarize_paper
from src.tools.knowledge_base import save_to_knowledge_base, query_knowledge_base, list_knowledge_base
from src.tools.context_expander import expand_context

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

_TOOL_DECLARATIONS = protos.Tool(
    function_declarations=[
        protos.FunctionDeclaration(
            name="search_papers",
            description="在 arXiv 搜尋學術論文。當知識庫資料不足時使用。建議使用英文關鍵字。",
            parameters=protos.Schema(
                type=protos.Type.OBJECT,
                properties={
                    "query": protos.Schema(type=protos.Type.STRING, description="搜尋關鍵字（英文效果最佳）"),
                    "max_results": protos.Schema(type=protos.Type.INTEGER, description="最多回傳篇數，預設 5"),
                },
                required=["query"],
            ),
        ),
        protos.FunctionDeclaration(
            name="summarize_paper",
            description="將論文標題與英文摘要翻譯並整理為繁體中文結構化摘要。",
            parameters=protos.Schema(
                type=protos.Type.OBJECT,
                properties={
                    "title": protos.Schema(type=protos.Type.STRING, description="論文標題"),
                    "abstract": protos.Schema(type=protos.Type.STRING, description="論文英文摘要"),
                },
                required=["title", "abstract"],
            ),
        ),
        protos.FunctionDeclaration(
            name="save_to_knowledge_base",
            description="將論文資料儲存到本地 ChromaDB 知識庫，供未來查詢使用。",
            parameters=protos.Schema(
                type=protos.Type.OBJECT,
                properties={
                    "title": protos.Schema(type=protos.Type.STRING, description="論文標題"),
                    "abstract": protos.Schema(type=protos.Type.STRING, description="論文英文摘要"),
                    "arxiv_id": protos.Schema(type=protos.Type.STRING, description="arXiv ID"),
                    "url": protos.Schema(type=protos.Type.STRING, description="論文 URL"),
                    "tags": protos.Schema(
                        type=protos.Type.ARRAY,
                        items=protos.Schema(type=protos.Type.STRING),
                        description="分類標籤列表",
                    ),
                    "year": protos.Schema(type=protos.Type.INTEGER, description="發表年份"),
                },
                required=["title", "abstract", "arxiv_id", "url"],
            ),
        ),
        protos.FunctionDeclaration(
            name="query_knowledge_base",
            description="從本地知識庫以 RAG 方式查詢相關論文。優先使用此工具。回傳 kb_sufficient 表示是否有足夠資料。",
            parameters=protos.Schema(
                type=protos.Type.OBJECT,
                properties={
                    "question": protos.Schema(type=protos.Type.STRING, description="查詢問題或關鍵字"),
                    "use_chunks": protos.Schema(type=protos.Type.BOOLEAN, description="是否啟用細粒度區塊查詢，預設 true"),
                },
                required=["question"],
            ),
        ),
        protos.FunctionDeclaration(
            name="expand_context",
            description="取得特定論文段落的前後相鄰 chunk，擴展上下文以獲得更完整資訊。",
            parameters=protos.Schema(
                type=protos.Type.OBJECT,
                properties={
                    "arxiv_id": protos.Schema(type=protos.Type.STRING, description="arXiv ID"),
                    "chunk_index": protos.Schema(type=protos.Type.INTEGER, description="目標段落索引"),
                },
                required=["arxiv_id", "chunk_index"],
            ),
        ),
    ]
)

_TOOL_REGISTRY: dict[str, Any] = {
    "search_papers": search_papers,
    "summarize_paper": summarize_paper,
    "save_to_knowledge_base": save_to_knowledge_base,
    "query_knowledge_base": query_knowledge_base,
    "expand_context": expand_context,
}

StepCallback = Callable[[str, dict, Any], Awaitable[None]]


class ResearchAgent:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(
            model_name="gemini-3.1-flash-lite",
            tools=[_TOOL_DECLARATIONS],
            system_instruction=SYSTEM_PROMPT,
        )
        self.reset()

    def reset(self):
        self.chat = self.model.start_chat(history=[])

    async def run(self, user_message: str, on_step: StepCallback | None = None) -> str:
        response = await asyncio.to_thread(self.chat.send_message, user_message)

        for _ in range(12):
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
                tool_fn = _TOOL_REGISTRY.get(fc.name)
                if tool_fn:
                    result = await asyncio.to_thread(tool_fn, **args)
                else:
                    result = {"error": f"Unknown tool: {fc.name}"}

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

        try:
            return response.text
        except Exception:
            return "無法生成回應，請稍後再試。"
