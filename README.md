# Douyin Author Homepage Scraper

A standalone Multica skill that scrapes **one Douyin author's homepage** — the
author's **follower count (粉丝量)** plus a selected slice of their posts
(skipping pinned videos), including 点赞/评论/收藏 counts, the real image/video
files, and each post's comments — and writes it all to a **5-table Feishu
bitable** (作者信息 / 视频作品 / 图文作品 / 一级评论 / 二级评论).

> Single purpose: author-page scraping only. For keyword search, use the
> separate **douyin-scraper** skill.

## Quick start

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env         # fill FEISHU_* + DOUYIN_COOKIE, or: python main.py login

python main.py scrape-author "https://www.douyin.com/user/MS4wLjABAAAA..." --folder <folder>
```

## Post selection (skips pinned)

Drops posts flagged `is_top` and keeps the next 5; if the API omits `is_top`,
falls back to skipping the first 3 (=> the 4th–8th posts). Tune with
`--recent-count` / `--skip-top`.

See [SKILL.md](SKILL.md) for full documentation.

## License

MIT
