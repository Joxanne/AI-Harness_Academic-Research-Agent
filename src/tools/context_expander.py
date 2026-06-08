from src.memory.chroma_store import ChromaStore

_store: ChromaStore | None = None


def _get_store() -> ChromaStore:
    global _store
    if _store is None:
        _store = ChromaStore()
    return _store


def expand_context(arxiv_id: str, chunk_index: int) -> str:
    """Tool 5: 擴展指定論文段落的上下文，取前後相鄰 chunk 合併回傳。"""
    store = _get_store()
    chunks = store.get_chunks_by_arxiv_id(arxiv_id)

    if not chunks:
        return f"找不到 arxiv_id={arxiv_id} 的段落資料。"

    total = len(chunks)
    target_indices = set(range(max(0, chunk_index - 1), min(total, chunk_index + 2)))
    selected = [c for c in chunks if c["metadata"]["chunk_index"] in target_indices]
    selected.sort(key=lambda x: x["metadata"]["chunk_index"])

    combined = " ".join(c["document"] for c in selected)
    return combined if combined else "無法擴展上下文。"
