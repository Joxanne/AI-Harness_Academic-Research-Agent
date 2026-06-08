import arxiv


def search_papers(query: str, max_results: int = 5) -> list[dict]:
    """Tool 1: 在 arXiv 搜尋學術論文。"""
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    results = []
    for paper in client.results(search):
        abstract = paper.summary.replace("\n", " ")
        if len(abstract) > 600:
            abstract = abstract[:600] + "..."

        arxiv_id = paper.entry_id.split("/abs/")[-1]

        results.append({
            "title": paper.title,
            "authors": [a.name for a in paper.authors[:3]],
            "abstract": abstract,
            "url": paper.entry_id,
            "arxiv_id": arxiv_id,
            "year": paper.published.year if paper.published else None,
        })

    return results
