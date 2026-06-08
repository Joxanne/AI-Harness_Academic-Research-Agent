# 對話記錄 — AIoT HW4: Survey of DRL

---

## [2026-06-08] 初始設定

**主題：** 建立 CLAUDE.MD 與對話記錄機制

**討論內容：**
- 使用者要求修改 CLAUDE.MD，確保 Claude 每次執行前先讀取此檔案
- 要求新增對話記錄機制，避免因模型上下文壓縮而遺忘對話進度

**決策與結論：**
- CLAUDE.MD 更新為包含專案說明、對話記錄規則、注意事項的完整文件
- 對話記錄儲存於 `log.md`（本檔案），每次對話結束後追加新摘要
- 記錄格式統一：日期、主題、討論內容、決策、產出、待處理

**產出：**
- 更新 `CLAUDE.MD` 完成
- 建立 `log.md`（本檔案）

**待處理：**
- HW4 DRL Survey 的實際內容尚未開始，待使用者提供作業要求

---

## [2026-06-08] 作業需求確認與架構規劃

**主題：** 閱讀 request.md，確認技術選型與應用場景

**討論內容：**

- 作業為 AI Harness 系統設計，非 DRL survey（目錄名稱為舊名）
- 確認應用場景：智慧學術研究助理（Academic Research Agent）
- 確認技術選型：Gemini lite、Chainlit、ChromaDB、arXiv API
- 討論 Streamlit vs Chainlit：建議 Chainlit（原生支援工具呼叫視覺化與串流）
- Infographic 以獨立 HTML 檔案生成

**決策與結論：**

- LLM：Google Gemini lite（model ID 待使用者確認）
- Frontend：Chainlit（取代 Streamlit）
- 報告語言：中文
- 繳交三項：report.md、infographic.html、log.md + src/ 程式碼

**產出：**

- CLAUDE.MD 更新完成（含技術棧、專案結構、繳交狀態）

**待處理：**

- 使用者確認 Gemini model ID（目前暫定 gemini-3 lite）
- 使用者確認架構規劃後開始實作程式碼

---

## [2026-06-08] 架構更新、GitHub 參考分析、詳細規劃建立

**主題：** 參考 local-ai-knowledge-agent、確認技術細節、建立 plan.md

**討論內容：**

- Gemini model ID 確認：`gemini-3.1-flash-lite`
- 使用者詢問是否可參考 GitHub 專案 Joxanne/local-ai-knowledge-agent
- 分析該 repo：兩層 RAG、信心度路由、上下文擴展等概念可借鑑
- 決定借鑑架構概念（不直接複製程式碼，因技術棧不同）
- 工具數量從 4 個增加至 5 個（新增 context_expander）

**決策與結論：**

- 採用兩層 ChromaDB 架構（layer1 摘要層 + layer2 區塊層）
- 加入信心度路由：distance < 0.7 時直接用 KB，否則去 arXiv 搜尋
- 報告語言：中文
- Infographic：純 HTML + CSS，無外部框架

**產出：**

- `plan.md` 建立完成（8 個 Phase，詳細至每個函式與欄位）

**待處理：**

- 等使用者確認 plan.md 後開始 Phase 1 實作

---

## [2026-06-08] 完整實作所有 Phase 1–8

**主題：** 依 plan.md 完整實作 AI Harness 系統

**討論內容：**

- 使用者設定 /goal，要求完成 plan.md 所有內容
- 確認 Gemini model ID：`gemini-3.1-flash-lite`

**決策與結論：**

- Phase 1：建立 requirements.txt、.env.example、所有 `__init__.py`
- Phase 2：實作 ChromaDB 兩層架構（layer1 摘要層 + layer2 區塊層），使用多語言嵌入模型
- Phase 3：實作 5 個工具（arxiv_search、summarizer、knowledge_base × 2、context_expander）
- Phase 4：實作 agent.py（Gemini function calling 迴圈 + 信心度路由，最多 12 輪工具呼叫）
- Phase 5：實作 app.py（Chainlit 前端，cl.Step 工具步驟視覺化）
- Phase 6：生成 infographic.html（深海軍藍主題，純 HTML/CSS，五個 Section 完整架構圖）
- Phase 7：撰寫 report.md（中文，六章，2000+ 字，含對話範例表格）
- Phase 8：更新 CLAUDE.MD 繳交狀態為全部完成

**產出：**

- `requirements.txt` — 7 個套件依賴
- `src/memory/chroma_store.py` — ChromaDB 兩層封裝
- `src/tools/arxiv_search.py` — Tool 1
- `src/tools/summarizer.py` — Tool 2
- `src/tools/knowledge_base.py` — Tool 3 + Tool 4
- `src/tools/context_expander.py` — Tool 5
- `src/agent.py` — Gemini orchestrator + function calling 迴圈
- `src/app.py` — Chainlit UI
- `infographic.html` — 互動式系統架構圖
- `report.md` — 書面報告

**待處理：**

- 使用者需建立 `.env` 並填入 GEMINI_API_KEY
- 執行 `pip install -r requirements.txt` 安裝依賴
- 啟動：`chainlit run src/app.py`
- 首次啟動會下載 sentence-transformers 模型（約 500MB）

---

## [2026-06-08] 除錯：Python 3.14 + nest_asyncio + uvicorn 相容性問題

**主題：** 修復 Chainlit 啟動後瀏覽器出現 500 錯誤（無法載入靜態檔案）

**錯誤現象：**
1. 第一階段：`sniffio.AsyncLibraryNotFoundError: unknown async library`
2. 第二階段（修補後）：`TypeError: cannot create weak reference to 'NoneType' object`

**根本原因診斷：**

uvicorn 建立 ASGI 請求任務時使用：
```python
task = self.loop.create_task(cycle.run_asgi(app), context=contextvars.Context())
```
`contextvars.Context()` 是空的 contextvars 隔離環境。

Chainlit CLI 在啟動前呼叫 `nest_asyncio.apply()`，此函式將 `asyncio.Task`（C 版本 `_CTask`）替換為 `asyncio.tasks._PyTask`（純 Python 版）。然而 `asyncio.current_task` 仍保持 C builtin 實作。

Python 3.14 的 C `current_task()` 讀取 C 層級的任務狀態（不由 `_PyTask.__step` 更新），在空的 contextvars 環境中回傳 `None`。

**影響鏈：**
- sniffio 的 asyncio 偵測依賴 `asyncio.current_task()` 回傳值 → 拋出 `AsyncLibraryNotFoundError`
- anyio 的 `CancelScope.__enter__` 呼叫 `current_task()` → 得到 `None` → `WeakKeyDictionary[None]` → `TypeError`

**修復措施（src/app.py 頂部）：**

**Fix 1（已在前一次）：** 修補 sniffio，偵測失敗時改用 `asyncio.get_running_loop()` fallback

**Fix 2（本次）：** 將 `asyncio.current_task` 替換為 Python 實作 `_py_current_task`，同時直接修補 anyio 已載入模組中的 binding：
```python
import asyncio.tasks as _tasks
if hasattr(_tasks, '_py_current_task') and asyncio.current_task is not _tasks._py_current_task:
    asyncio.current_task = _tasks.current_task = _tasks._py_current_task
    import anyio._backends._asyncio as _anyio_be
    _anyio_be.current_task = _tasks._py_current_task
```

**測試驗證：**
- 模擬 nest_asyncio + 空 Context + anyio.to_thread.run_sync → 修補後全部通過

**待處理：**
- 重新啟動 `chainlit run src/app.py` 確認瀏覽器不再出現 500 錯誤
- 若正常載入，進行完整功能測試（arXiv 搜尋、摘要、知識庫存取）

---

## [2026-06-08] 功能測試完成

**主題：** 端對端測試通過，系統正式完成

**測試結果：**
- Chainlit 介面正常載入（500 錯誤已完全解除）
- Agent 工具鏈全部執行成功：查詢知識庫（RAG）、搜尋 arXiv 論文、產生中文摘要、存入知識庫
- 瀏覽器剩餘的 400（avatar 圖片缺失）與 MIME 警告為純外觀問題，不影響功能

**最終系統狀態：**

| 項目 | 狀態 |
|------|------|
| Chainlit UI | ✅ 運行 |
| Gemini orchestrator | ✅ 運行 |
| arXiv 搜尋工具 | ✅ 運行 |
| 中文摘要工具 | ✅ 運行 |
| ChromaDB 知識庫存取 | ✅ 運行 |
| 知識庫存入工具 | ✅ 運行 |

**全部繳交項目：**
- report.md ✅
- infographic.html ✅
- src/（完整程式碼）✅
- log.md ✅
- 功能測試 ✅

**無待處理事項** — 專案完成。
