---
name: douyin-author-homepage-collector
description: Use when collecting Douyin author homepage data into Feishu/Lark Base, especially author profile stats, pinned or non-pinned work slices, comments, media, target-selection reports, or validation using a logged-in visible Chrome session.
---

# Douyin Author Homepage Collector

Collect Douyin author homepage data with an explicit target-selection contract, then write auditable results to Feishu/Lark Base. The core rule: never infer the user's slice rule. Record the exact collection, ordering, and slice before collecting.

For user-facing installation, configuration, usage, troubleshooting, packaging, and handoff guidance, read `references/collector-miji.md`. Do this when the user asks for a "秘籍", install guide, zip package instructions, or how another Codex user should run the skill.

## Required Inputs

Confirm or discover these before writing data:

- Author homepage URLs. If the user gives names, resolve them to author URLs first and record the chosen URLs.
- Target rule: define **collection**, **order**, and **slice**.
- Whether comments, replies, and original media attachments are required.
- Feishu target: create a new Base in the requested folder, or use a provided Base/table mapping.
- Browser state: use a logged-in, visible Chrome session. Headless collection is not an acceptable final path.

## Target-Selection Contract

Always restate and persist the target rule in `run_manifest.json` and the Feishu report table.

Use these terms exactly:

| User wording | Collection | Slice logic |
|---|---|---|
| `主页原始顺序第4-8条` | all visible/API works in homepage order | `works[3:8]` |
| `去掉置顶后第4-8条` | works after filtering out pinned items | `non_pinned[3:8]` |
| `置顶视频/置顶集合第4-8条` | only works carrying `is_top` or visible `置顶` tag | `pinned[3:8]` |

Do not substitute another collection when the requested collection is too small. If `pinned.length < 4`, the target result is zero rows; write a report explaining the shortage instead of using non-pinned works.

## Browser Rules

- Use the user's normal logged-in, visible Chrome when requested. Do not switch to Chrome Dev unless explicitly asked.
- Do not open multiple CDP windows. Reuse or release one controlled tab. Do not close the user's unrelated browser windows or tabs.
- Never read, print, export, or store cookies, localStorage, sessionStorage, passwords, tokens, or Chrome profile files.
- Prefer Douyin web APIs from the logged-in browser context when available. Calls must inherit the browser session, for example `credentials: include`, without exposing secrets.
- If the available Chrome control surface is read-only and cannot run `fetch`/`XMLHttpRequest`, DOM extraction is only a diagnostic or degraded path. Mark it as `降级采集`, and do not claim API-complete collection.
- CAPTCHA, login, and risk checks are user-handled gates. Stop and ask the user to resolve them in the visible Chrome tab.

## Data Model

Create or use separate Feishu tables:

| Table | Required content |
|---|---|
| `作者信息` | 用户ID, 昵称, 简介, 关注数, 粉丝数, 获赞数, 作品数, 主页链接, 爬取时间 |
| `视频作品` | selected video works only; direct `/video/{id}` links; counts; selection fields |
| `图文作品` | selected note/image works only; direct `/note/{id}` links; counts; selection fields |
| `一级评论` | first-level comments for selected or diagnostic works |
| `二级评论` | replies when requested and available |
| `目标筛选报告` | one row per author with target rule, collection count, target count, and shortage/failure reason |

Add these fields to work tables when target slicing matters:

- `目标集合`: `homepage_all`, `pinned`, or `non_pinned`
- `目标集合序号`: 1-based position inside that collection
- `目标状态`: `target`, `diagnostic_only`, `shortage`, or failure reason

Author profile stats are mandatory. Do not fill `0` for 粉丝数/关注数/获赞数/作品数 unless the real page/API value is actually zero. If parsing fails, leave the field blank and report the parse failure.

## Collection Workflow

1. Create a run directory: `runs/<run_id>/`.
2. Save `run_config.json` with author URLs, target rule, Feishu target, browser mode, and requested deliverables.
3. Connect to logged-in visible Chrome and confirm the account is not at a login/risk page.
4. For each author:
   - Fetch or parse the author profile segment.
   - Build ordered collections: `homepage_all`, `pinned`, `non_pinned`.
   - Select targets only from the requested collection.
   - If the collection is too short, produce zero target works and a `目标筛选报告` row.
5. For selected targets, collect direct work links, metadata, comments, replies, and media as requested.
6. Write Feishu records. Media must be uploaded as attachment fields when requested; URLs are not a substitute for original media attachments.
7. Read Feishu back to verify record counts and required fields. If readback scopes are missing, report the exact missing scopes and do not mark the run complete.
8. Write `final_report.json` with status, counts, target rule, shortages, degraded paths, and Feishu URLs.

## Feishu Rules

- Put generated files in the user-specified folder when one is provided.
- Use `--as user` by default with `lark-cli`; only use bot identity when the user explicitly wants bot-owned resources or user access is impossible and acceptable.
- Batch writes may prove only that `batch_create` accepted records. Completion still requires readback unless the user accepts a scope-limited result.
- If `base:record:retrieve` or related scopes are missing, ask the user to reauthorize instead of silently skipping verification.

## Acceptance Gates

Claim `完成` only when all are true:

- The target rule in the report exactly matches the user's wording.
- Every written work belongs to the requested target collection and slice.
- Shortages are represented as report rows, not substituted data.
- Author stats are populated or explicitly reported as parse/API failures.
- Work links are direct `/video/{id}` or `/note/{id}` URLs.
- Comments/replies/media required by the user were attempted and their terminal status is recorded.
- Feishu readback confirms table counts and required fields, or the final status is explicitly `未完成-缺少回读授权`.

## Common Failure Modes

- Confusing `置顶集合第4-8条` with `去掉置顶后第4-8条`. These are opposite filters; stop and fix the target rule before writing.
- Writing all visible works to Feishu during a slice request. Only diagnostic tables may contain non-target works, and they must be marked `diagnostic_only`.
- Filling author stats with zeros because parsing was not wired into the final writer. Reparse from the profile API/page segment or leave blank with an error.
- Treating DOM-only extraction as complete API collection. Label it degraded and explain which browser limitation caused it.
- Creating a Base but not writing a `目标筛选报告`. The report is required whenever collection size, pinned status, or target slicing affects output.
