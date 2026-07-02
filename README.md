# Douyin Author Homepage Collector

A Codex skill package for collecting Douyin author homepage data into
Feishu/Lark Base with an explicit target-selection contract. It handles author
profile stats, pinned/non-pinned/homepage work slices, comments, media
requirements, shortage reporting, and visible Chrome session rules.

## Quick start

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env         # fill FEISHU_* + DOUYIN_COOKIE, or: python main.py login

python main.py scrape-author "https://www.douyin.com/user/MS4wLjABAAAA..." --folder <folder>
```

## Target selection

Do not assume "第4-8条" means one fixed thing. The skill distinguishes:

- `主页原始顺序第4-8条`: all works in homepage order, `works[3:8]`
- `去掉置顶后第4-8条`: non-pinned works only, `non_pinned[3:8]`
- `置顶集合第4-8条`: pinned works only, `pinned[3:8]`

If the requested collection is too small, write a shortage report instead of
substituting another collection.

## Package contents

- [SKILL.md](SKILL.md): Codex skill instructions.
- [references/collector-miji.md](references/collector-miji.md): handoff
  "秘籍" with operational rules and failure modes.
- [scripts/select_author_targets.py](scripts/select_author_targets.py): reusable
  target-slice helper for homepage/pinned/non-pinned selection.
- [scripts/build_skill_zip.py](scripts/build_skill_zip.py): creates a clean zip
  package while excluding cookies, `.env`, runs, Chrome profiles, and `.git`.

## License

MIT
