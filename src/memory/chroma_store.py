import os
from typing import Optional
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VECTORSTORE_PATH = os.path.join(BASE_DIR, "vectorstore")
CHUNK_SIZE = 300
CHUNK_OVERLAP = 50


def _chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks if chunks else [text]


class ChromaStore:
    def __init__(self):
        embedding_fn = SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.client = chromadb.PersistentClient(path=VECTORSTORE_PATH)
        self.layer1 = self.client.get_or_create_collection(
            name="paper_abstracts",
            embedding_function=embedding_fn,
            metadata={"description": "Layer1: paper-level abstract index"},
        )
        self.layer2 = self.client.get_or_create_collection(
            name="paper_chunks",
            embedding_function=embedding_fn,
            metadata={"description": "Layer2: chunk-level index"},
        )

    def add_paper(
        self,
        title: str,
        abstract: str,
        arxiv_id: str,
        url: str,
        tags: list[str],
        year: int,
    ) -> int:
        existing = self.layer1.get(ids=[arxiv_id])
        if existing["ids"]:
            return self.layer1.count()

        self.layer1.add(
            ids=[arxiv_id],
            documents=[f"{title}\n{abstract}"],
            metadatas=[{
                "title": title,
                "arxiv_id": arxiv_id,
                "url": url,
                "tags": ",".join(tags) if tags else "",
                "year": year,
            }],
        )

        chunks = _chunk_text(abstract)
        self.layer2.add(
            ids=[f"{arxiv_id}_chunk_{i}" for i in range(len(chunks))],
            documents=chunks,
            metadatas=[{
                "arxiv_id": arxiv_id,
                "title": title,
                "chunk_index": i,
                "total_chunks": len(chunks),
            } for i in range(len(chunks))],
        )

        return self.layer1.count()

    def query_abstracts(self, query_text: str, n_results: int = 3) -> dict:
        count = self.layer1.count()
        if count == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        return self.layer1.query(
            query_texts=[query_text],
            n_results=min(n_results, count),
        )

    def query_chunks(self, query_text: str, n_results: int = 5) -> dict:
        count = self.layer2.count()
        if count == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        return self.layer2.query(
            query_texts=[query_text],
            n_results=min(n_results, count),
        )

    def get_paper_by_id(self, arxiv_id: str) -> Optional[dict]:
        result = self.layer1.get(ids=[arxiv_id])
        if not result["ids"]:
            return None
        return {
            "id": result["ids"][0],
            "document": result["documents"][0],
            "metadata": result["metadatas"][0],
        }

    def get_chunks_by_arxiv_id(self, arxiv_id: str) -> list[dict]:
        result = self.layer2.get(where={"arxiv_id": arxiv_id})
        chunks = []
        for i, chunk_id in enumerate(result["ids"]):
            chunks.append({
                "id": chunk_id,
                "document": result["documents"][i],
                "metadata": result["metadatas"][i],
            })
        chunks.sort(key=lambda x: x["metadata"]["chunk_index"])
        return chunks

    def list_all_papers(self) -> list[dict]:
        result = self.layer1.get()
        return [
            {
                "arxiv_id": result["ids"][i],
                "title": result["metadatas"][i].get("title", ""),
                "url": result["metadatas"][i].get("url", ""),
                "tags": result["metadatas"][i].get("tags", ""),
                "year": result["metadatas"][i].get("year", ""),
            }
            for i in range(len(result["ids"]))
        ]
