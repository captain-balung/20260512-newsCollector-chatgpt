# Daily AI Insights — AI 產業每日決策情報系統

> 自動化 AI 情報基礎設施 — 蒐集、評分、摘要、敘事追蹤、Email、Portal。
> 完整規格見 [`Daily_AI_Insights_SRS_v2.md`](./Daily_AI_Insights_SRS_v2.md)。

## TL;DR

```bash
pip install -r requirements.txt
cp .env.example .env                # USE_MOCK=1 預設,本機完全可跑
python -m scripts.run_pipeline smoke
```

完成後:

* `data/archive/<date>.json` — 當日完整 JSON
* `docs/index.html`、`docs/archive/<date>/index.html` — Portal
* `docs/search-index.json` — 給 Portal client-side 搜尋
* `data/db/state.sqlite` — SQLite 狀態(dedup / 趨勢 / 敘事 / 候選來源)

## 模式切換

| 環境變數 | 行為 |
|---|---|
| `USE_MOCK=1` | 全 mock:`AIClient` 回傳 stub JSON、Email 不真寄、Embedding 用 md5 雜湊。離線可跑。 |
| `USE_MOCK=0` + `GEMINI_API_KEY` | 走真 Gemini。預算守門員依 `DAILY_TOKEN_BUDGET` 控制。 |
| `USE_MOCK=0` + SMTP secrets | 走真 Gmail SMTP 寄發。 |

## Pipeline 步驟

```
fetch → normalize → dedup (url / title / embedding) → score → AI enrich
      → section → trends/narratives/discovery → archive → publish → email → alert
```

CLI:

```bash
python -m scripts.run_pipeline fetch     # 抓取 → data/cache
python -m scripts.run_pipeline process   # 處理 → data/archive
python -m scripts.run_pipeline publish   # 出版 docs/ + email
python -m scripts.run_pipeline all       # 一次全跑
python -m scripts.run_pipeline smoke     # 用 tests/fixtures 離線 smoke
```

## 設定檔

* `config/sources.yaml` — Tier 1–4 來源清單
* `config/scoring.yaml` — 5 軸權重、選稿門檻、dedup 設定
* `config/prompts.yaml` — Prompt 模板(summarize / insight / classify / narrative)
* `config/settings.yaml` — 6 大分類、趨勢視窗、NFR

## GitHub Actions

`.github/workflows/daily.yml` 主排程(每日 09:00 UTC+8 = 01:00 UTC):

1. `fetch.yml` — 抓取 + 上傳 cache artefact
2. `process.yml` — 跑 AI、寫 SQLite cache、上傳 edition artefact
3. `publish.yml` — 渲染 `docs/`、寄信、commit、`deploy-pages`

需要在 repo Secrets 設:`GEMINI_API_KEY`、`SMTP_USER`、`SMTP_PASSWORD`、`SMTP_FROM`、
`EMAIL_TO`、`SITE_BASE_URL`、`ALERT_WEBHOOK_URL`(可選)、`DAILY_TOKEN_BUDGET`(可選)。

## 模組對應 SRS 章節

| 模組 | SRS |
|---|---|
| `src/pipeline/collector.py` | §2.3, §3 |
| `src/pipeline/normalizer.py` | §2.3 |
| `src/pipeline/deduplicator.py` | §4.4, §4.5 |
| `src/pipeline/scorer.py` | §4.1–§4.3 |
| `src/pipeline/summarizer.py` | §5.1–§5.4 |
| `src/pipeline/formatter.py` | §10 |
| `src/pipeline/publisher.py` | §9, §16 publish.yml |
| `src/emailer/sender.py` | §8 |
| `src/trend/*` | §6 (Phase 2) |
| `src/agent/*` | Phase 3 |
| `src/observability/*` | §11 |
| `src/recovery/*`, `src/cost/budget.py` | §12, §14 |

## 測試

```bash
python -m pytest tests/ -W ignore::DeprecationWarning
```

8 tests 含:normalizer / scorer / deduplicator / publisher / pipeline smoke。

## 已知 todo

* `gemini-2.5-pro` 模型 id 預設為佔位 — 上線前依 Google 官方公布調整。
* `DAILY_TOKEN_BUDGET` 預設空(不限),建議上線前訂上限。
* `config/sources.yaml` 的 `original_peoples_council` (原住民族委員會) 已從預設來源拿掉,如需追蹤可手動補回。
* `src/agent/source_expander.py` 寫入 SQLite candidate 表但目前 Portal 還沒前端面板呈現。
