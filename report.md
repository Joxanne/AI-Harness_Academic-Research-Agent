# 智慧學術研究助理：AI Harness 系統設計

**課程：** AIoT  
**作業：** HW4 — AI Harness Systems Design  
**系統名稱：** Academic Research Agent  
**技術棧：** Google Gemini 3.1 Flash Lite · Chainlit · ChromaDB · arXiv API

---

## 一、問題定義與應用背景

### 1.1 問題描述

現代學術研究者面臨嚴峻的資訊過載挑戰。以 arXiv 為例，每日新增論文超過數千篇，研究者往往難以在有限時間內追蹤領域最新進展、比較不同方法的優劣，或從海量文獻中快速定位解答。

傳統做法仰賴手動搜尋與閱讀，效率低落且難以累積個人化知識庫。本系統旨在透過 AI Harness 架構，讓 LLM 作為智慧代理，自動化完成「搜尋 → 理解 → 記憶 → 回答」的完整研究輔助流程。

### 1.2 使用情境

- **情境 A：** 研究者輸入「深度強化學習的主要演算法有哪些？」→ 系統搜尋 arXiv、摘要整理並存入個人知識庫、直接用繁體中文回答
- **情境 B：** 再次詢問相關問題 → 系統偵測知識庫已有足夠資料，直接從本地 RAG 回答，無需重新搜尋（提升效率）
- **情境 C：** 深入追問特定論文細節 → 系統啟動 context_expander，取得更完整的段落上下文

---

## 二、AI Harness 系統設計

### 2.1 整體架構

本系統採用 **LLM as Controller** 架構，Gemini 模型作為中央協調器（Orchestrator），透過原生 Function Calling 機制動態決策工具呼叫順序。

```
使用者輸入
    ↓
Chainlit UI（互動前端）
    ↓
Gemini Orchestrator（gemini-3.1-flash-lite）
    ↓
Confidence Router
    ↙                    ↘
知識庫充足（RAG）        知識庫不足（搜尋流程）
    ↓                         ↓
Tool 4: query_kb     Tool 1: search_papers
Tool 5: expand_ctx   Tool 2: summarize_paper
                     Tool 3: save_to_kb
    ↘                    ↙
         ChromaDB 兩層向量索引
              ↓
         最終回答（附論文來源）
```

### 2.2 各元件職責

| 元件 | 角色 | 技術 |
|------|------|------|
| Gemini 3.1 Flash Lite | LLM Orchestrator，決策工具呼叫 | google-generativeai |
| Chainlit | 前端介面，工具步驟視覺化 | Python WebSocket |
| ChromaDB | 兩層向量資料庫，持久化知識庫 | HNSW + 餘弦距離 |
| arXiv API | 論文資料來源，免費無需金鑰 | arxiv Python 套件 |
| Sentence-Transformers | 多語言嵌入模型 | paraphrase-multilingual-MiniLM-L12-v2 |

### 2.3 Memory 設計

系統採用 **兩層 ChromaDB 架構**，靈感來自 local-ai-knowledge-agent 專案的 hierarchical indexing 設計：

**Layer 1（摘要層）— `paper_abstracts` Collection**

每篇論文以整篇摘要為一筆文件儲存。metadata 包含 title、arxiv_id、url、tags、year。用途為快速判斷知識庫是否已有足夠相關資料（Confidence Routing）。

**Layer 2（區塊層）— `paper_chunks` Collection**

每篇論文摘要切分為 300 字 chunk（overlap 50 字）。用途為細粒度 RAG，從具體段落中提取精準回答。

嵌入模型選用 `paraphrase-multilingual-MiniLM-L12-v2`，支援中文查詢對應英文論文內容的語意匹配。

---

## 三、Tools 設計

### 3.1 Function Calling 機制說明

本系統使用 Gemini 原生 Function Calling 機制。透過 `protos.FunctionDeclaration` 定義工具 schema，並於 `GenerativeModel` 初始化時注入，讓 LLM 在推理過程中自主判斷何時呼叫哪個工具、傳入什麼參數。

工具呼叫採用**手動執行模式**（非 automatic function calling），確保每次工具執行可透過 Chainlit 的 `cl.Step` 機制即時顯示給使用者，使 AI 決策過程完全透明。

呼叫迴圈流程：
1. 使用者訊息傳入 Gemini
2. 模型回傳包含 `function_call` 的回應
3. 系統執行對應 Python 函式，透過 `asyncio.to_thread` 避免阻塞事件迴圈
4. 將工具結果以 `FunctionResponse` 格式回傳 Gemini
5. 重複直到模型回傳純文字回答（最多 12 輪）

### 3.2 五個工具逐一說明

**Tool 1：`search_papers(query, max_results=5)`**

- **用途：** 在 arXiv 搜尋最新學術論文
- **輸入：** 英文搜尋關鍵字、最大回傳筆數
- **輸出：** 論文列表，每篇包含 title、authors、abstract（最多 600 字）、url、arxiv_id、year
- **設計理由：** arXiv API 免費、無需金鑰、涵蓋大量 CS/AI 論文

**Tool 2：`summarize_paper(title, abstract)`**

- **用途：** 將英文論文摘要整理為繁體中文結構化摘要
- **輸入：** 論文標題、英文摘要
- **輸出：** 包含「研究問題、研究方法、主要貢獻、關鍵詞」的中文摘要
- **設計理由：** 此工具本身也呼叫 Gemini，展示 LLM 可作為工具內部邏輯，降低使用者閱讀英文障礙

**Tool 3：`save_to_knowledge_base(title, abstract, arxiv_id, url, tags, year)`**

- **用途：** 將論文存入本地 ChromaDB（Layer1 + Layer2 同步建立）
- **輸入：** 論文完整 metadata
- **輸出：** 確認訊息 + 知識庫目前總論文數
- **設計理由：** 確保每次搜尋的結果都能累積為長期記憶，後續查詢直接命中本地 KB

**Tool 4：`query_knowledge_base(question, use_chunks=True)`**

- **用途：** 兩層 RAG 查詢，回傳相關論文與段落，並附 `kb_sufficient` 信心度旗標
- **輸入：** 查詢問題、是否啟用 chunk 層查詢
- **輸出：** papers 列表、chunks 列表、min_distance、kb_sufficient
- **設計理由：** `kb_sufficient` 旗標是 Confidence Router 的核心，讓 Gemini 自主判斷是否需要觸發新搜尋

**Tool 5：`expand_context(arxiv_id, chunk_index)`**

- **用途：** 取得指定 chunk 的前後相鄰段落，擴展上下文
- **輸入：** arXiv ID、目標段落索引
- **輸出：** 合併後的擴展文字
- **設計理由：** 解決 RAG 系統常見的「段落邊界截斷」問題，提供更完整的語境

---

## 四、Workflow 與 Agent 流程

### 4.1 Confidence Router 決策邏輯

系統的核心決策機制是**信心度路由**。每次收到問題，Agent 必須先呼叫 `query_knowledge_base` 執行 Layer1 快速掃描。依據回傳的 `min_distance` 值判斷：

- `distance < 0.7`（kb_sufficient = True）：知識庫有足夠相關資料 → 直接使用 Tool 4/5 回答，跳過 arXiv 搜尋
- `distance ≥ 0.7` 或無結果（kb_sufficient = False）：知識不足 → 觸發 Tool 1 → Tool 2 → Tool 3 完整搜尋流程

### 4.2 多步驟任務執行範例

**使用者輸入：** 「deep reinforcement learning 的主要演算法有哪些進展？」

| 步驟 | Agent 行為 | 工具呼叫 | 結果 |
|------|-----------|---------|------|
| 1 | 先查知識庫 | `query_knowledge_base("deep reinforcement learning")` | kb_sufficient=false（空庫） |
| 2 | 觸發搜尋 | `search_papers("deep reinforcement learning survey 2024")` | 5 篇論文 |
| 3 | 逐篇摘要 | `summarize_paper(title, abstract)` × 3 | 3 份中文摘要 |
| 4 | 存入知識庫 | `save_to_knowledge_base(...)` × 3 | 知識庫 3 篇 |
| 5 | 整合回答 | Gemini 直接生成 | 附 arXiv URL 的完整回答 |

**後續詢問：** 「剛才提到的 PPO 演算法詳細說明？」

| 步驟 | 行為 | 結果 |
|------|------|------|
| 1 | 查知識庫 | kb_sufficient=true（distance=0.42） |
| 2 | 擴展段落 | `expand_context(arxiv_id, chunk_index=2)` |
| 3 | 直接回答 | 無需重新搜尋 |

---

## 五、Evaluation 方法

### 5.1 回答準確性

採用**人工評估**方式，評分標準：

1. **來源核對：** 回答中引用的 arXiv URL 是否真實存在、論文標題是否正確
2. **內容一致性：** 回答內容是否與引用論文摘要描述一致，無幻覺（hallucination）
3. **完整性：** 是否回答了問題的所有面向

### 5.2 工具呼叫效率

統計每次對話的工具呼叫總次數，評估 Confidence Router 的效益：

- **目標：** 相同主題的第二次詢問，工具呼叫次數應從 ~5 次（含搜尋）降至 ~2 次（只用 KB）
- **指標：** `kb_sufficient=true` 的查詢比例（知識庫命中率）

### 5.3 知識庫成長曲線

追蹤隨對話進行，知識庫命中率的提升趨勢。預期知識庫累積到 20+ 篇論文後，命中率應超過 70%。

---

## 六、參考資料

- Google Generative AI Python SDK — Function Calling 官方文件
- Chainlit Documentation — cl.Step, on_message, user_session
- ChromaDB Documentation — PersistentClient, Collection, embedding_functions
- arxiv Python Package — Search, Client
- Joxanne/local-ai-knowledge-agent — Hierarchical RAG 與 Confidence Evaluator 設計靈感
