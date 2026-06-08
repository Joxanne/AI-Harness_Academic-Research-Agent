# HW4 AI Harness — 詳細實作規劃

> 模型：gemini-3.1-flash-lite｜Frontend：Chainlit｜Memory：ChromaDB（兩層）｜API：arXiv

---

## 總覽：繳交物對應

| 繳交物 | 對應檔案 | 狀態 |
|--------|---------|------|
| 書面報告 | `report.md` | [ ] |
| Infographic | `infographic.html` | [ ] |
| 對話記錄 | `log.md` | [x] 持續更新 |
| 程式碼 | `src/` | [ ] |

---

## Phase 1：環境建置

### 1-1 目錄結構建立

```text
HW4_Survey of DRL/
├── src/
│   ├── __init__.py
│   ├── app.py
│   ├── agent.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── arxiv_search.py
│   │   ├── summarizer.py
│   │   ├── knowledge_base.py
│   │   └── context_expander.py
│   └── memory/
│       ├── __init__.py
│       └── chroma_store.py
├── vectorstore/          # ChromaDB 持久化目錄（自動產生）
│   ├── layer1/           # 摘要層索引
│   └── layer2/           # 區塊層索引
├── .env                  # API 金鑰（不進版本控制）
├── .env.example          # 金鑰範本
├── requirements.txt
├── infographic.html
├── report.md
├── plan.md               # 本檔案
├── log.md
└── CLAUDE.MD
```

### 1-2 requirements.txt 內容

- `chainlit` — 前端互動介面
- `google-generativeai` — Gemini API
- `chromadb` — 向量資料庫
- `arxiv` — arXiv API Python wrapper
- `requests` — HTTP 請求
- `python-dotenv` — 環境變數載入
- `langchain-text-splitters` — 文字切塊（layer2 用）

### 1-3 .env.example

```
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## Phase 2：記憶層實作（ChromaDB 兩層架構）

### 2-1 `src/memory/chroma_store.py`

**Layer 1（摘要層）**

- Collection 名稱：`paper_abstracts`
- 每筆文件代表一篇論文
- metadata 欄位：`title`、`authors`、`arxiv_id`、`url`、`tags`、`year`
- 用途：判斷「是否已有相關論文」

**Layer 2（區塊層）**

- Collection 名稱：`paper_chunks`
- 每篇論文摘要切成數個 chunk（每塊約 300 字）
- metadata 欄位：`arxiv_id`、`chunk_index`、`total_chunks`
- 用途：細粒度回答問題（RAG 查詢時使用）

**提供的方法：**

- `add_paper(title, abstract, arxiv_id, url, tags, year)` — 存入 layer1 + 切塊存入 layer2
- `query_abstracts(query_text, n_results)` → 回傳相似論文列表
- `query_chunks(query_text, n_results)` → 回傳相似段落列表
- `get_paper_by_id(arxiv_id)` → 取得單篇論文完整資料
- `list_all_papers()` → 列出所有已存論文

---

## Phase 3：工具實作（5 個 Tools）

### 3-1 Tool 1：`src/tools/arxiv_search.py`

**函式：** `search_papers(query: str, max_results: int = 5)`

**流程：**

1. 使用 `arxiv` 套件搜尋
2. 回傳格式：`[{title, authors, abstract, url, arxiv_id, year}]`
3. 限制 abstract 最多 500 字

**對應作業要求：** Tool use / function calling 機制說明

---

### 3-2 Tool 2：`src/tools/summarizer.py`

**函式：** `summarize_paper(title: str, abstract: str)`

**流程：**

1. 將 title + abstract 傳給 Gemini
2. 要求輸出結構化摘要（研究問題、方法、結論、關鍵詞）
3. 回傳繁體中文摘要字串

**備註：** 此工具本身也呼叫 Gemini，展示 LLM 可作為工具內部邏輯

---

### 3-3 Tool 3：`src/tools/knowledge_base.py`（儲存端）

**函式：** `save_to_knowledge_base(title: str, abstract: str, arxiv_id: str, url: str, tags: list[str], year: int)`

**流程：**

1. 呼叫 `chroma_store.add_paper()`
2. 存入 layer1（摘要）+ layer2（切塊）
3. 回傳確認訊息與已存論文數量

---

### 3-4 Tool 4：`src/tools/knowledge_base.py`（查詢端）

**函式：** `query_knowledge_base(question: str, use_chunks: bool = True)`

**流程：**

1. 先用 layer1 查摘要，找到最相關論文（top 3）
2. 若 `use_chunks=True`，再用 layer2 查對應的細粒度段落
3. 合併結果，回傳給 agent

**對應作業要求：** memory 設計 + RAG 流程

---

### 3-5 Tool 5：`src/tools/context_expander.py`

**函式：** `expand_context(arxiv_id: str, chunk_index: int)`

**流程：**

1. 從 layer2 取得指定 chunk 的前後各一個 chunk
2. 合併為完整段落回傳
3. 用於補充 RAG 查詢結果的上下文

**參考來源：** local-ai-knowledge-agent 的 `context_expander.py` 概念

---

## Phase 4：Agent Orchestrator

### 4-1 `src/agent.py`

**核心：Gemini function calling**

Gemini 原生支援 `tools` 參數，我們將 5 個工具定義為 `FunctionDeclaration`，讓模型自行決定呼叫順序。

**信心度路由邏輯（Confidence Router）**

```
使用者問題
    ↓
先查 layer1（query_abstracts）
    ↓
若相似度 > 閾值 → 直接用 KB 回答（Tool 4）
若相似度 < 閾值 → 去 arXiv 搜尋（Tool 1 → Tool 2 → Tool 3）
```

閾值設定：ChromaDB distance < 0.7 視為「有足夠資料」

**Agent 主流程：**

1. 接收 Chainlit 傳入的訊息
2. 組裝 system prompt（說明角色、工具用途）
3. 呼叫 Gemini with tools
4. 解析工具呼叫結果，執行對應 Python 函式
5. 將工具結果回傳給 Gemini 繼續推理
6. 回傳最終答案

**System Prompt 要點：**

- 角色：學術研究助理
- 語言：繁體中文
- 優先使用知識庫，不足再搜尋
- 每次回答須標注資料來源（論文標題 + arXiv URL）

---

## Phase 5：Chainlit 前端

### 5-1 `src/app.py`

**功能：**

- `@cl.on_chat_start`：初始化 agent，歡迎訊息
- `@cl.on_message`：接收訊息 → 呼叫 agent → 串流輸出
- 工具執行時使用 `cl.Step` 顯示每個工具呼叫過程（工具名稱、輸入、輸出）
- 支援 Markdown 格式輸出（論文清單、摘要等）

**Chainlit 特色功能展示：**

- 工具呼叫步驟視覺化（Tools 執行過程可展開查看）
- 串流文字輸出
- 對話歷史保存（session 層級）

---

## Phase 6：Infographic

### 6-1 `infographic.html`

**內容：** 系統架構全覽（單頁靜態 HTML，無需伺服器）

**視覺元素：**

1. **系統架構圖**（中央）— 使用 CSS Flexbox 繪製的方塊流程圖
   - User → Chainlit → Gemini Orchestrator → Tool Dispatcher → 各 Tools → ChromaDB
2. **工具清單卡片**（左側）— 5 個工具各一張卡片，說明功能
3. **RAG 兩層架構圖**（右側）— layer1/layer2 示意
4. **Agent Workflow 流程圖**（下方）— 信心度路由決策樹
5. **Evaluation 方法**（角落區塊）

**技術：** 純 HTML + CSS（無外部框架），確保可離線開啟

---

## Phase 7：書面報告

### 7-1 `report.md`

**章節結構（對應 request.md 評分標準）：**

1. **問題定義與應用背景**（約 0.5 頁）
   - 學術研究的資訊爆炸問題
   - AI Harness 可如何解決

2. **AI Harness 系統設計**（約 1 頁）
   - 整體架構說明（LLM + tools + memory）
   - 各元件職責

3. **Tools 設計**（約 1 頁）
   - 5 個工具逐一說明（輸入、輸出、設計理由）
   - Function calling 機制說明

4. **Workflow / Agent 流程**（約 1 頁）
   - 信心度路由邏輯
   - 多步驟任務執行範例（以對話範例呈現）

5. **Evaluation 方法**（約 0.5 頁）
   - 回答準確性（人工評估 + 來源核對）
   - 工具呼叫次數（效率指標）
   - 知識庫查詢成功率

---

## Phase 8：驗證與收尾

### 8-1 功能測試清單

- [ ] arXiv 搜尋回傳正確結果
- [ ] 摘要工具產生結構化中文輸出
- [ ] ChromaDB 存入 + 查詢兩層皆正常
- [ ] 信心度路由：有資料時不重複搜尋
- [ ] Chainlit 工具步驟視覺化正常顯示
- [ ] Infographic 可在瀏覽器直接開啟

### 8-2 log.md 最終更新

- 記錄完整實作過程、遇到的問題與解決方式

---

## 實作順序（建議）

```
Phase 1（環境）→ Phase 2（ChromaDB）→ Phase 3（Tools）
    → Phase 4（Agent）→ Phase 5（Chainlit）
    → Phase 6（Infographic）→ Phase 7（報告）→ Phase 8（驗收）
```

每個 Phase 完成後更新 log.md 與 CLAUDE.MD 的繳交項目狀態。
