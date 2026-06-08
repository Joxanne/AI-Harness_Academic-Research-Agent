# CLAUDE.MD — AIoT HW4: Survey of Deep Reinforcement Learning

**確保每次執行任何步驟前，先閱讀這份檔案**

---

## 專案說明

此目錄為碩士課程 AIoT HW4 的作業。  
**作業主題：AI Harness 系統設計**（目錄名稱 Survey of DRL 為舊名，以 request.md 為準）

### 應用場景

智慧學術研究助理（Academic Research Agent）

使用者輸入研究問題，LLM 作為 orchestrator 決策並呼叫工具完成多步驟任務。

### 技術棧

- **LLM：** Google Gemini `gemini-3.1-flash-lite`
- **Frontend：** Chainlit（AI agent 互動介面）
- **Memory：** ChromaDB（向量資料庫 RAG）
- **Paper API：** arXiv API（免費、無需金鑰）
- **語言：** Python；報告語言：中文

### 專案結構

```text
src/
  app.py                # Chainlit 入口
  agent.py              # LLM orchestrator + tool dispatcher
  tools/
    arxiv_search.py     # Tool 1: 搜尋論文
    summarizer.py       # Tool 2: 摘要論文
    knowledge_base.py   # Tool 3/4: 儲存/查詢知識庫
  memory/
    chroma_store.py     # ChromaDB 封裝
infographic.html        # 系統架構視覺化
report.md               # 書面報告（中文）
requirements.txt
```

### 繳交項目狀態

- [x] 書面報告（report.md）
- [x] Infographic（infographic.html）
- [x] log.md（持續更新）
- [x] 實作程式碼（src/）
- [x] **功能測試通過**（2026-06-08）

### 系統相容性修補（已套用於 src/app.py）

Python 3.14 + Chainlit 2.11 + uvicorn 在 Windows 上有兩個已知相容性問題，均已在 `src/app.py` 頂部以 monkey-patch 修復：

1. **sniffio patch** — uvicorn 以空 contextvars.Context 建立 ASGI 任務，導致 sniffio 無法偵測 async library。修復：偵測失敗時 fallback 用 `get_running_loop()`。
2. **current_task patch** — `nest_asyncio.apply()`（Chainlit CLI）將 `_CTask` 換成 `_PyTask`，但 C builtin `asyncio.current_task` 不追蹤 `_PyTask`，在空 context 任務中回傳 `None`，導致 anyio CancelScope 崩潰。修復：將 `asyncio.current_task` 換成 `_py_current_task`，並直接修補 anyio 模組的 binding。

---

## 對話記錄機制

### 規則

1. **每次對話開始時**，先讀取 `log.md`（若存在），了解歷史脈絡與進度。
2. **每次對話結束（或完成重要步驟）後**，更新 `log.md`，記錄本次對話的關鍵內容。
3. 記錄格式應包含：日期、討論主題、做出的決策、產出的內容、待處理事項。
4. 此機制目的是確保即使模型上下文被壓縮或重新開啟對話，仍能從記錄檔恢復完整的工作脈絡。

### 對話記錄檔位置

```text
c:\資工人生\碩士\AIoT\HW4_Survey of DRL\log.md
```

### 記錄格式範本

```markdown
## [日期] 對話摘要

**主題：** ...
**討論內容：**
- ...
**決策與結論：**
- ...
**產出：**
- ...
**待處理：**
- ...
```

---

## 注意事項

- 對話記錄檔為純 Markdown，不可刪除或覆蓋，只能追加新的對話摘要。
- 若 `log.md` 不存在，第一次對話時自動建立並記錄。
- 每次完成任何有意義的步驟後，立即更新記錄，不要等到對話結束才一次補寫。
