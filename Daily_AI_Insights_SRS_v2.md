# AI 產業每日決策情報系統

## Software Requirements Specification (SRS)

Version: 2.0  
Last Updated: 2026-05-12  
Owner: Captain Balung

---

# 1. 專案概述 (Project Overview)

## 1.1 專案名稱

**Daily AI Insights — AI 產業每日決策情報系統**

---

## 1.2 專案願景

打造一個具備：

* 自動化資訊蒐集
* AI 深度分析
* 專家觀點生成
* 歷史知識累積
* 趨勢脈絡追蹤

的 AI 情報基礎設施平台。

系統需每日自動產生具備高訊噪比的 AI 產業決策情報，並同步發布至：

* Web Portal
* Email Newsletter
* GitHub Archive

---

## 1.3 核心價值

### 主要目標

* 將碎片化 AI 新聞轉換為決策情報
* 建立長期 AI 趨勢資料庫
* 建立個人品牌型 AI 媒體
* 建立未來 RAG / AI Agent 可使用之知識資產

---

## 1.4 產品定位

本產品定位為：

> 「AI 產業分析型情報媒體」

而非單純新聞聚合器。

核心差異化：

* 台灣 AI 政策追蹤
* 教育科技視角
* 金融市場連動分析
* 專家觀點摘要
* 長期趨勢分析

---

# 2. 系統架構 (System Architecture)

## 2.1 系統架構總覽

系統採用：

* Serverless Architecture
* GitHub Actions Workflow
* Static Hosting Architecture

---

## 2.2 Pipeline Flow

```text
Sources
  ↓
Collector
  ↓
Normalizer
  ↓
Deduplicator
  ↓
Scoring Engine
  ↓
LLM Summarizer
  ↓
Insight Generator
  ↓
Formatter
  ↓
Publisher
```

---

## 2.3 核心模組

|模組|功能|
|-|-|
|Collector|抓取 RSS / API / GitHub / HN|
|Normalizer|統一資料格式|
|Deduplicator|移除重複新聞|
|Scoring Engine|新聞評分與排序|
|Summarizer|AI 摘要生成|
|Insight Generator|專家觀點生成|
|Formatter|HTML / JSON / Markdown|
|Publisher|GitHub Pages / Email 發布|

---

# 3. 資料來源系統 (Data Sources)

## 3.1 Tier 1 — 高可信度來源

### 巨頭與底層模型

* OpenAI Blog
* Anthropic News
* Google AI Blog
* Google The Keyword
* Hugging Face Blog

---

## 3.2 Tier 2 — 技術與研究社群

* Hacker News
* GitHub Trending
* arXiv AI Papers
* Papers With Code

---

## 3.3 Tier 3 — 教育與政策

* EdSurge
* 台灣國科會 RSS
* 原住民族委員會公告

---

## 3.4 Tier 4 — 金融市場

* Yahoo Finance
* Alpha Vantage
* Polygon.io（未來）

---

# 4. 資訊過濾與評分系統

## 4.1 評分模型

每篇新聞需計算以下分數：

|欄位|範圍|
|-|-|
|relevance|0-10|
|novelty|0-10|
|impact|0-10|
|taiwan_related|0-10|
|market_signal|0-10|

---

## 4.2 最終分數公式

```python
final_score =
    relevance * 0.30 +
    novelty * 0.20 +
    impact * 0.30 +
    taiwan_related * 0.10 +
    market_signal * 0.10
```

---

## 4.3 選稿條件

### 條件

* final_score >= 7.0
* source_confidence >= 0.6

---

## 4.4 去重機制

### Deduplication Strategy

```yaml
dedup:
  - url_hash
  - title_similarity
  - embedding_similarity
```

---

## 4.5 Embedding Similarity

### 規格

* 使用 Gemini Embedding 或 sentence-transformers
* Cosine Similarity > 0.88 視為重複新聞

---

# 5. AI 處理系統 (AI Processing)

## 5.1 AI 任務拆分

|任務|模型|
|-|-|
|分類|Gemini Flash|
|摘要|Gemini Pro|
|Insight|Gemini Pro|
|Embedding|Gemini Embedding|

---

## 5.2 Prompt Governance

### Prompt Rules

```yaml
tone:
  - analytical
  - concise
  - professional

forbidden:
  - clickbait
  - unsupported speculation
  - exaggerated claims
```

---

## 5.3 AI Output Contract

所有 LLM 回傳必須符合：

```json
{
  "title": "",
  "summary": "",
  "insight": "",
  "importance": "",
  "market_impact": "",
  "tags": []
}
```

---

## 5.4 專家觀點規則

每則新聞必須包含至少一種：

* 教育科技分析
* 媒體設計分析
* 金融市場分析
* AI 生態分析
* 台灣政策分析

---

# 6. 趨勢追蹤系統 (Trend Tracking)

## 6.1 跨日脈絡分析

系統需分析：

* 最近 7 日
* 最近 14 日
* 最近 30 日

的主題變化。

---

## 6.2 Narrative Tracking

範例：

```text
OpenAI
→ Agents
→ MCP
→ AI Operating System
```

---

## 6.3 熱門主題追蹤

系統需追蹤：

* 重複出現關鍵字
* 快速增長主題
* 新興模型
* 開源框架

---

# 7. 內容分類系統

## 7.1 六大核心分類

1. 🏢 巨頭動向與市場脈動
2. 🛠️ 開發者工具與 AI Agent
3. 🎵 生成式多媒體與創作
4. 📚 教育科技與應用創新
5. 🧠 底層架構與開源模型
6. ⚖️ 法律倫理與社會衝擊

---

## 7.2 每日內容規格

每個分類：

* 2~3 則新聞
* 至少 1 則專家觀點
* 至少 1 則高可信來源

---

# 8. Email Delivery System

## 8.1 發送時間

每日：

* 09:00 AM (UTC+8)

---

## 8.2 Email 格式

### HTML 版本

* Responsive Design
* Dark Mode Support
* 卡片式 Layout

---

### Plain Text 版本

需提供：

* Markdown fallback
* 全展開摘要

---

## 8.3 Email 限制

|項目|限制|
|-|-|
|最大大小|500 KB|
|圖片|避免大量 inline image|
|JS|禁止|

---

## 8.4 Email Client 相容性

需測試：

* Gmail
* Outlook
* Apple Mail
* Mobile Gmail

---

# 9. Portal & Archive System

## 9.1 Hosting

* GitHub Pages

---

## 9.2 功能需求

### 首頁

* 今日 AI 看板
* 市場指標
* 最新情報

---

### 歷史檔案

* 日期搜尋
* Tag Filter
* 分類篩選

---

## 9.3 SEO

需支援：

* OpenGraph
* Twitter Card
* Sitemap
* Structured Data

---

# 10. Data Schema

## 10.1 JSON Schema

```json
{
  "schema_version": "2.0",
  "generated_at": "",
  "pipeline_version": "",
  "date": "",
  "dashboard": {},
  "sections": []
}
```

---

## 10.2 Article Schema

```json
{
  "title": "",
  "summary": "",
  "insight": "",
  "importance": "",
  "source_url": "",
  "source_name": "",
  "confidence_score": 0,
  "final_score": 0,
  "tags": [],
  "embedding_id": ""
}
```

---

# 11. Observability & Monitoring

## 11.1 Metrics

需記錄：

```yaml
metrics:
  - articles_fetched
  - articles_filtered
  - generation_time
  - email_success_rate
  - api_token_usage
```

---

## 11.2 Logging

需保存：

* pipeline logs
* AI response logs
* publish logs

---

## 11.3 Alerting

發送警告條件：

* Email 發送失敗
* 今日新聞數量不足
* AI generation failed
* GitHub publish failed

---

# 12. Failure Recovery

## 12.1 Retry Policy

```yaml
retry_policy:
  max_retry: 3
  backoff: exponential
```

---

## 12.2 Fallback Strategy

```yaml
fallbacks:
  - cached_data
  - previous_successful_run
```

---

# 13. Security

## 13.1 Secrets Management

需保護：

* Gemini API Key
* SMTP Credentials
* SendGrid API Key

---

## 13.2 GitHub Secrets

所有憑證：

* 不可 hardcode
* 必須存於 GitHub Secrets

---

# 14. Cost Control

## 14.1 成本限制

```yaml
daily_token_budget:
monthly_budget:
```

---

## 14.2 模型策略

### 高成本模型

* 僅用於摘要與 Insight

### 低成本模型

* 分類
* Ranking
* Metadata

---

# 15. 技術堆棧

|類別|技術|
|-|-|
|Language|Python 3.x|
|Workflow|GitHub Actions|
|Frontend|Vanilla JS|
|CSS|Tailwind CSS|
|AI Models|Gemini|
|Hosting|GitHub Pages|
|Email|SMTP / SendGrid|
|Storage|JSON + SQLite|

---

# 16. GitHub Actions Workflow

## 16.1 Workflow 拆分

### fetch.yml

負責：

* RSS
* API
* GitHub Trending

---

### process.yml

負責：

* AI Processing
* Ranking
* Dedup

---

### publish.yml

負責：

* Email
* GitHub Pages
* Archive Update

---

# 17. Non-functional Requirements

|項目|目標|
|-|-|
|Availability|99%|
|Daily Runtime|< 15 min|
|Email Success Rate|> 95%|
|Max Memory Usage|< 2GB|

---

# 18. Future Roadmap

## Phase 1 — MVP

* RSS Aggregation
* AI Summarization
* Daily Email

---

## Phase 2 — Intelligence Layer

* Trend Tracking
* Narrative Analysis
* Taiwan Policy Radar

---

## Phase 3 — AI Agent

* Autonomous Topic Discovery
* Self Evaluation
* Dynamic Source Expansion

---

# 19. Acceptance Criteria

## MVP 驗收標準

### 必要條件

1. 每日 09:00 前完成更新
2. Email 成功送達
3. GitHub Pages 正常更新
4. JSON schema 驗證成功
5. 每則新聞包含 AI Insight

---

## 品質條件

* 重複新聞率 < 10%
* AI hallucination rate < 5%
* Email Rendering 正常

---

# 20. Long-term Vision

本系統最終目標並非：

> 「AI 新聞摘要工具」

而是：

> 「具備長期記憶、脈絡推理與決策輔助能力的 AI Intelligence Infrastructure」

