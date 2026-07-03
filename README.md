# Douyin Author Homepage Collector

A Codex skill package for collecting Douyin author homepage data into
Feishu/Lark Base with an explicit target-selection contract. It handles author
profile stats, pinned/non-pinned/homepage work slices, comments, media
requirements, shortage reporting, and visible Chrome session rules.

## Install the Codex skill

Download or build `douyin-author-homepage-collector.zip`, then unpack it into
your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
unzip douyin-author-homepage-collector.zip -d ~/.codex/skills
ls ~/.codex/skills/douyin-author-homepage-collector/SKILL.md
```

Restart Codex or start a new thread so the skill list refreshes.

For the full installation, Chrome, Feishu, target-selection, and acceptance
workflow, read [references/collector-miji.md](references/collector-miji.md).

## Runtime quick start

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env         # or reuse the configured local lark-cli app

python main.py scrape-author "https://www.douyin.com/user/MS4wLjABAAAA..." \
  --folder <folder> \
  --chrome-profile
```

`--chrome-profile` uses a visible local Chrome profile when possible. `--cdp
http://localhost:9222` is still available when the user explicitly wants CDP.
Cookie mode remains only for legacy compatibility and must not be distributed.

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
  "秘籍" with install, configuration, usage, target-selection, Feishu writeback,
  acceptance, and packaging instructions.
- [scripts/select_author_targets.py](scripts/select_author_targets.py): reusable
  target-slice helper for homepage/pinned/non-pinned selection.
- [scripts/build_skill_zip.py](scripts/build_skill_zip.py): creates a clean zip
  package while excluding cookies, `.env`, runs, Chrome profiles, tests, and
  `.git`. The zip top-level directory is read from `SKILL.md`'s `name`.

## License

MIT
