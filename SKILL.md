---
name: douyin-author-scraper
description: "Use when the user wants to scrape a single Douyin AUTHOR's homepage — the author's follower count (粉丝量) plus a selected slice of their posts (skipping pinned videos), including like/comment/collect counts, the image/video files, and the posts' comments — and write it all to a Feishu bitable. This is author-page scraping ONLY; for keyword search use the separate douyin-scraper skill."
user-invocable: true
---

# Douyin Author Homepage Scraper

Single purpose: given one author's homepage URL, scrape

1. **粉丝量 (follower count)** and the rest of the author profile, and
2. a selected slice of the author's posts — **skipping pinned videos** — with
   their 点赞/评论/收藏 counts, the real **image/video files**, and each post's
   **comments (L1 + L2)** —

and write everything to a **5-table Feishu bitable**. Keyword search is NOT part
of this skill; that lives in the separate `douyin-scraper` skill.

## What gets written (5 tables)

| 表 | 内容 |
|---|---|
| **作者信息** | the author profile: 用户ID / 昵称 / 简介 / **粉丝数** / 关注数 / 获赞数 / 作品数 / 主页链接 / 爬取时间 |
| **视频作品** | selected video posts — 点赞/评论/收藏/分享 + **作品封面 & 作品视频(.mp4) as real attachments** |
| **图文作品** | selected image/note posts — **作品封面 & 作品图片(all images) as attachments** |
| **一级评论** | first-level comments of the selected posts |
| **二级评论** | second-level (reply) comments — carries 父评论ID / 回复对象 / 所属一级评论作者 |

Rules (kept identical to the douyin data-model agreement):
- Media are uploaded as Feishu **attachments** (type 17), not URLs.
- Link fields (`作品链接` / `作者主页` / `主页链接`) show the **raw URL** (type 15), built with `storage.feishu.url_field(url)`.
- Every record carries a `来源` field = the author homepage URL, so multiple authors can share one bitable.

## Which posts (avoiding pinned videos)

Pinned videos sit at the top of a homepage and carry the API's `is_top` flag.
The selector **drops detected pinned posts and keeps the next 5**. If the API
does not return `is_top`, it falls back to **skipping the first 3** as pinned —
i.e. the **4th–8th** posts. Both are tunable (`--recent-count`, `--skip-top`).

## Run it

```bash
# One shot: create a NEW 5-table bitable AND scrape the author (profile + posts + comments)
python main.py scrape-author "https://www.douyin.com/user/MS4wLjABAAAA..." --folder <folder_token_or_url>

# Keep 8 non-pinned posts; skip 3 pinned on the fallback path
python main.py scrape-author "<homepage_url>" --folder <folder> --recent-count 8 --skip-top 3

# Only build the 5 empty tables / skip comments / force headless / capture L2 replies
python main.py scrape-author "<url>" --folder <folder> --structure-only
python main.py scrape-author "<url>" --folder <folder> --no-comments
python main.py scrape-author "<url>" --folder <folder> --headless      # 默认带界面，加此参数强制无头
python main.py scrape-author "<url>" --folder <folder> --ui-comments   # incl. 二级评论
```

Omit `--folder` to create the bitable in the app's own space. Creating inside a
folder needs the self-built app to be a collaborator with edit rights on it
(`drive:drive` + `bitable:app`), otherwise Feishu returns `DriveNodePermNotAllow`.

**Reuse an existing bitable:** set `FEISHU_APP_TOKEN` + `AUTHOR_TABLE_ID` +
`VIDEO_TABLE_ID` / `IMAGE_TABLE_ID` / `COMMENT_L1_TABLE_ID` / `COMMENT_L2_TABLE_ID`
and `DOUYIN_AUTHOR_URL` in `.env`, then run `python pipeline.py`.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env      # fill FEISHU_* and DOUYIN_COOKIE, or run: python main.py login
```

| Variable | Required | Notes |
|---|---|---|
| `DOUYIN_COOKIE` | yes | login cookie; or run `python main.py login` to capture it |
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` | yes | self-built Feishu app |
| `FEISHU_APP_TOKEN` | reuse-only | set when reusing an existing bitable |
| `AUTHOR_TABLE_ID` / `VIDEO_TABLE_ID` / `IMAGE_TABLE_ID` / `COMMENT_L1_TABLE_ID` / `COMMENT_L2_TABLE_ID` | reuse-only | when reusing an existing bitable |
| `AUTHOR_RECENT_COUNT` / `AUTHOR_TOP_SKIP` | no | default 5 / 3 |

**Security:** never log, print, or paste the cookie into comments. If `.env` is
missing, configure it on the runtime directly.

## How fan count is obtained

Read from `/user/profile/other/` over plain HTTP first; if that endpoint is
signature-blocked, it retries from a browser context, then falls back to the
`follower_count` embedded in one of the author's posts.

## Notes & limits

- Play count is always 0 from the Web API (Douyin blocks it for third parties).
- Reply (L2) comments come from the UI-click scraper (`--ui-comments`); the raw
  reply API is `bd-ticket-guard`'d and returns empty to hand-built requests.
- Browser defaults to headed (visible) to reduce anti-bot detection risk; pass `--headless` only if needed.
- Cookies expire after ~60 days — re-run `python main.py login`.
