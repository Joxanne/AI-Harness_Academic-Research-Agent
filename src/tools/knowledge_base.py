from src.memory.chroma_store import ChromaStore

_store: ChromaStore | None = None
CONFIDENCE_THRESHOLD = 0.7


def _get_store() -> ChromaStore:
    global _store
    if _store is None:
        _store = ChromaStore()
    return _store


def save_to_knowledge_base(
    title: str,
    abstract: str,
    arxiv_id: str,
    url: str,
    tags: list[str] | None = None,
    year: int = 0,
) -> str:
    """Tool 3: 將論文資料儲存到本地 ChromaDB 知識庫。"""
    store = _get_store()
    count = store.add_paper(title, abstract, arxiv_id, url, tags or [], year)
    return f"已成功儲存論文《{title}》（{arxiv_id}）。知識庫目前共有 {count} 篇論文。"


def query_knowledge_base(question: str, use_chunks: bool = True) -> dict:
    """Tool 4: 從知識庫查詢相關論文（兩層 RAG）。回傳 papers、chunks 及 min_distance。"""
    store = _get_store()

    abstract_results = store.query_abstracts(question, n_results=3)

    output: dict = {
        "papers": [],
        "chunks": [],
        "min_distance": None,
        "kb_sufficient": False,
    }

    if abstract_results["ids"][0]:
        distances = abstract_results["distances"][0]
        min_dist = min(distances) if distances else None
        output["min_distance"] = min_dist
        output["kb_sufficient"] = (min_dist is not None and min_dist < CONFIDENCE_THRESHOLD)

        for i, paper_id in enumerate(abstract_results["ids"][0]):
            meta = abstract_results["metadatas"][0][i]
            output["papers"].append({
                "arxiv_id": paper_id,
                "title": meta.get("title", ""),
                "url": meta.get("url", ""),
                "distance": distances[i],
                "snippet": abstract_results["documents"][0][i][:400],
            })

    if use_chunks and output["papers"]:
        chunk_results = store.query_chunks(question, n_results=5)
        if chunk_results["ids"][0]:
            for i, chunk_id in enumerate(chunk_results["ids"][0]):
                meta = chunk_results["metadatas"][0][i]
                output["chunks"].append({
                    "chunk_id": chunk_id,
                    "arxiv_id": meta.get("arxiv_id", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "content": chunk_results["documents"][0][i],
                    "distance": chunk_results["distances"][0][i],
                })

    return output


def list_knowledge_base() -> list[dict]:
    """列出知識庫中所有論文（供 agent 了解已存內容）。"""
    return _get_store().list_all_papers()
