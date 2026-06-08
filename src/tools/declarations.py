from typing import Any
from google.generativeai import protos

from src.tools.arxiv_search import search_papers
from src.tools.summarizer import summarize_paper
from src.tools.knowledge_base import save_to_knowledge_base, query_knowledge_base, list_knowledge_base
from src.tools.context_expander import expand_context

TOOL_DECLARATIONS = protos.Tool(
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

TOOL_REGISTRY: dict[str, Any] = {
    "search_papers": search_papers,
    "summarize_paper": summarize_paper,
    "save_to_knowledge_base": save_to_knowledge_base,
    "query_knowledge_base": query_knowledge_base,
    "list_knowledge_base": list_knowledge_base,
    "expand_context": expand_context,
}
