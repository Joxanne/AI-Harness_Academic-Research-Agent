## Homework 4 — AI Harness Systems Design and Analysis (Syllabus Version)
### 一、課程目標（Objective）
本作業旨在引導學生理解現代 AI Harness（AI 系統編排） 之設計方法，重點不在模型訓練，而在於 AI 系統如何透過 function calling、工具整合與 workflow orchestration 執行複雜任務。

學生將學習：

- LLM 作為系統控制器（system controller）的角色
- 工具使用（tool use / function calling）機制
- 多步驟 agent workflow 設計
- AI 系統架構設計與資料流規劃
- 基本 evaluation 與系統優化概念

---
### 二、作業內容（Requirements）
學生需選定一個 AI 應用場景（如：搜尋助理、客服系統、資料分析代理、教育助理等），並完成一個 AI Harness 系統設計。

設計內容須包含：

- AI 應用問題定義與使用情境
- AI system architecture（LLM + tools + memory）
- function calling / tool usage 機制說明
- 至少 3 個工具（API / function）設計
- agent workflow（多步驟任務執行流程）
- evaluation 方法（如何衡量系統效果）
- AI orchestration（流程控制與決策方式）

---

### 三、繳交項目（Deliverables）
學生需繳交以下三項內容：

#### 1. 書面報告（必交）
- 2–5 頁（A4 或 IEEE 格式皆可）
- 內容須涵蓋：
    - 問題定義與應用背景
    - AI Harness 系統設計
    - tools 設計（至少 3 個）
    - workflow / agent 流程說明
    - evaluation 方法

---
#### 2. 資訊圖表（Infographic，必交）
需以視覺化方式呈現系統設計，內容包含：

- AI system architecture（LLM、tools、memory）
- orchestration / workflow flow
- function calling 或 tool chain 流程
- 可包含 sequence diagram 或 pipeline 視覺化

--- 
#### 3. log.md（必交）
需記錄 AI 輔助設計與開發過程，包括：

- 與 AI 的互動紀錄（prompt / chat history）
- 系統設計迭代過程
- 架構調整與設計決策
- 問題分析與修正過程

---
### 四、評量方式（Evaluation Criteria）參考 Only
**評分項目	        比例**
AI 系統設計完整性	35%
Tool / Orchestration 設計	25%
Workflow 與邏輯清晰度	20%
Infographic 視覺表達	10%
log.md 設計過程紀錄	10%

---

### 五、注意事項
- 重點在於 system design 思維，而非模型訓練或演算法推導
- 必須清楚描述 AI 如何進行 tool use 與 decision-making
- 鼓勵創新設計與實際應用導向
- 所有設計需具備邏輯一致性與可解釋性
- 可使用現有 AI frameworks（如 LangChain / LangGraph 等）作為參考，但非必要