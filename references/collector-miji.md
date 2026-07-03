# 抖音作者主页采集技能秘籍：安装、配置、运行、验收

这份秘籍给安装和使用 `douyin-author-homepage-collector` 的人看。它不是 `SKILL.md` 的复制版，而是一份可执行手册：拿到 zip 后怎么安装，怎么让 Codex 识别技能，怎么配置飞书和浏览器登录态，怎么指定作者主页和目标集合，最后怎样判断交付是否完成。

## 一、这个技能包是什么

`douyin-author-homepage-collector` 用于在 Codex 中采集抖音作者主页数据，并写入飞书多维表格。它特别处理这些容易出错的场景：

- 作者可以先给名字，也可以直接给主页 URL；
- 目标可以是主页原始顺序、去掉置顶后、或置顶集合；
- 作品可以是视频或图文；
- 可采作者信息、作品信息、一级评论、二级评论、媒体附件；
- 结果必须写入飞书，并提供目标筛选报告；
- 使用用户已登录的有头 Chrome，不把 headless 或未登录浏览器当最终路径。

技能包里应该包含：

| 路径 | 作用 |
|---|---|
| `SKILL.md` | Codex 触发和执行时读取的核心规则 |
| `agents/openai.yaml` | Codex 技能列表展示信息 |
| `references/collector-miji.md` | 本秘籍，给人安装、使用、排错 |
| `scripts/select_author_targets.py` | 按主页原始顺序、置顶集合、非置顶集合选择目标作品 |
| `scripts/build_skill_zip.py` | 生成可分发 zip，自动排除密钥、Cookie、运行目录、Chrome profile |
| `main.py`、`pipeline.py`、`core/`、`storage/` | 当前采集代码 |

> 正确 zip 的顶层目录必须是 `douyin-author-homepage-collector/`。如果解压后顶层叫 `repo/`，说明拿到的是旧包，应该重新下载新版。

## 二、安装方式

### 方式 A：从飞书下载 zip 安装

1. 下载技能包：`douyin-author-homepage-collector.zip`
2. 解压到 Codex 技能目录：

```bash
mkdir -p ~/.codex/skills
unzip douyin-author-homepage-collector.zip -d ~/.codex/skills
ls ~/.codex/skills/douyin-author-homepage-collector/SKILL.md
```

3. 重新打开 Codex，或开启一个新线程，让 Codex 重新加载本地 skills。
4. 验证技能可用：在 Codex 中要求它使用 `douyin-author-homepage-collector` 采集一个作者主页，Codex 应该能主动说明目标集合、Chrome 登录态和飞书写入要求。

### 方式 B：从 GitHub 安装

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/IXYTYXI/codex_get_douyin_name_skill.git \
  ~/.codex/skills/douyin-author-homepage-collector
```

如果之前已经装过旧版：

```bash
cd ~/.codex/skills/douyin-author-homepage-collector
git pull
```

更新后同样需要重新打开 Codex 或开启新线程。

## 三、安装 Python 运行依赖

如果只让 Codex 读取技能规则，不一定需要手动装依赖；如果要在本机直接跑采集代码，需要进入技能目录安装依赖：

```bash
cd ~/.codex/skills/douyin-author-homepage-collector
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Mac 上如需控制本机 Google Chrome，需要确认 Chrome 路径存在：

```bash
ls "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

## 四、配置飞书

默认目标是把结果写到用户指定的飞书文件夹或多维表格。常见配置有两种。

### 推荐：使用 Codex 背后的 lark-cli / 飞书应用配置

如果本机 Codex 已配置飞书 Lark 应用，优先复用该配置，不要求用户在聊天里粘贴 `FEISHU_APP_ID` 或 `FEISHU_APP_SECRET`。

检查方式：

```bash
lark-cli config current
lark-cli auth whoami --as user
```

如果需要授权，按 lark-cli 提示完成 user 身份授权。写入云空间文件夹、创建多维表格、回读 Base 记录都需要对应 scope。

### 备用：使用 `.env`

复制示例配置：

```bash
cp .env.example .env
```

填写：

```bash
FEISHU_APP_ID=...
FEISHU_APP_SECRET=...
```

不要把 `.env`、token、Cookie、Chrome profile 打进 zip，也不要发给别人。

## 五、配置抖音登录态

推荐使用已登录的有头 Chrome。不要把无头浏览器、未登录浏览器、只读 DOM 当最终采集路径。

### 方式 A：使用本机 Chrome profile

适合“不想开 9222 端口”的场景：

```bash
python main.py scrape-author "https://www.douyin.com/user/SEC_UID" \
  --folder "https://guanghe.feishu.cn/drive/folder/ZvZ0fN9YdlYt26dGCMDcDjo3nMc" \
  --name "抖音作者主页采集" \
  --chrome-profile
```

注意：

- 这是有头 Chrome，不是 headless。
- 如果系统提示 Chrome profile 被占用，需要先退出正在运行的 Chrome，再由脚本打开同一个本机资料目录；通常不需要重新登录抖音。
- 不要让脚本关闭用户无关窗口；采集结束后只关闭它自己控制的上下文。

### 方式 B：使用已有 CDP Chrome

适合用户明确愿意用 `9222` 的场景：

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.douyin-cdp-profile"
```

登录抖音后运行：

```bash
python main.py scrape-author "https://www.douyin.com/user/SEC_UID" \
  --folder "https://guanghe.feishu.cn/drive/folder/ZvZ0fN9YdlYt26dGCMDcDjo3nMc" \
  --name "抖音作者主页采集" \
  --cdp http://localhost:9222
```

规则：

- 不要同时开多个 CDP Chrome。
- 不要把 Chrome Dev 当默认路径，除非用户明确指定。
- 不读取、不导出、不保存 Cookie、localStorage、sessionStorage、token、密码。

### 方式 C：Cookie 模式只作为旧兼容

仓库里仍有 `python main.py login` 和 `DOUYIN_COOKIE` 兼容路径，但这不是推荐交付方式。给别人分发技能包时，不能包含 `cookies.json` 或 `.env`。

## 六、如何给 Codex 下任务

推荐直接把作者主页 URL 给 Codex：

```text
使用 douyin-author-homepage-collector。
采集这 3 个作者主页：
1. https://www.douyin.com/user/...
2. https://www.douyin.com/user/...
3. https://www.douyin.com/user/...

目标：每个作者的置顶集合原始顺序第 4-8 条，一共最多 5 条。
需要：作者信息、作品信息、一级评论、二级评论、视频/图文媒体。
写入飞书文件夹：https://guanghe.feishu.cn/drive/folder/ZvZ0fN9YdlYt26dGCMDcDjo3nMc
使用我本机已登录的有头 Chrome，不要使用无头浏览器。
```

如果只有作者名字，也可以这样给：

```text
作者名字：
1. 清华凌霄学习舅
2. 于泽老师的思维课
3. 成祥老师带你重学英语

先解析到作者主页 URL，再采集每个作者置顶集合原始顺序第 4-8 条。
```

Codex 必须先把名字解析成主页 URL，并在报告里记录选择的 URL。名字存在多个候选时，应说明候选和选择依据。

## 七、目标集合口径

这是本技能最重要的部分。用户说“第 4-8 条”时，必须先确认集合。

| 用户说法 | 集合 | 切片 |
|---|---|---|
| 主页原始顺序第 4-8 条 | 作者主页/API 返回的全部作品原始顺序 | `works[3:8]` |
| 去掉置顶后第 4-8 条 | 过滤掉置顶作品后的集合 | `non_pinned[3:8]` |
| 置顶集合第 4-8 条 | 只包含带 `is_top` 或可见“置顶”标签的作品 | `pinned[3:8]` |

关键规则：

- “置顶集合第 4-8 条”不是“去掉置顶后第 4-8 条”。
- “排在顶部”不等于“置顶”，优先看接口字段 `is_top`，其次看卡片可见“置顶”标签。
- 置顶集合不足 4 条时，目标结果就是 0 条，不允许拿非置顶作品补数。
- `--skip-top` 只能表达“跳过前 N 条”，不能表达“置顶集合第 4-8 条”。

## 八、使用目标选择脚本

当已经有作者主页作品 JSON 时，用脚本选择目标，避免手写切片出错：

```bash
python scripts/select_author_targets.py \
  --input runs/<run_id>/author_homepages \
  --collection pinned \
  --start 4 \
  --end 8 \
  --output runs/<run_id>/targets.json
```

输出包含：

- `selected`：真正命中的目标作品；
- `reports`：每个作者的集合数量、目标区间、目标数量、短缺原因；
- `target_rule`：本次规则，便于写入飞书 `目标筛选报告`。

如果 `selected` 为空但 `reports` 显示 `shortage`，这不是脚本失败，而是目标集合不足。

## 九、飞书输出要求

推荐创建或使用以下表：

| 表 | 内容 |
|---|---|
| `作者信息` | 用户ID、昵称、简介、关注数、粉丝数、获赞数、作品数、主页链接、爬取时间 |
| `视频作品` | 目标视频作品，直链必须是 `/video/{id}` |
| `图文作品` | 目标图文作品，直链必须是 `/note/{id}` |
| `一级评论` | 目标作品的一层评论 |
| `二级评论` | 二级回复 |
| `目标筛选报告` | 作者、目标规则、集合、集合总数、目标数量、短缺/失败原因 |

作者信息是必采项。粉丝数、关注数、获赞数、作品数采不到时留空并写失败原因，不要写 `0` 冒充真实值。

作品表建议补充这些字段：

- `目标集合`：`homepage_all`、`pinned`、`non_pinned`
- `目标集合序号`：集合内 1-based 位置
- `目标状态`：`target`、`shortage`、`diagnostic_only`、或失败原因
- `run_id`
- `采集时间`

## 十、标准运行产物

每次采集应建立独立目录：

```text
runs/<run_id>/
```

建议产物：

| 文件 | 用途 |
|---|---|
| `run_config.json` | 作者、目标规则、Chrome 模式、飞书目标 |
| `run_manifest.json` | 实际执行参数、表 ID、字段映射、开始/结束时间 |
| `author_homepages/*.json` | 每个作者主页作品集合 |
| `targets.json` | 目标选择结果 |
| `comments_batch_*.json` | 评论写入批次 |
| `media_tasks.json` | 媒体下载/上传任务队列 |
| `media_report.json` | 媒体任务终态 |
| `final_report.json` | 最终验收报告 |

不要删除 manifest、targets、批次 JSON、媒体报告和最终报告。可以清理临时媒体文件和临时上传文件。

## 十一、回读验收

写入飞书后必须回读验证，不能只看本地 JSON 或 `batch_create` 成功。

至少核对：

- 作者信息记录数；
- 视频作品记录数；
- 图文作品记录数；
- 一级评论记录数；
- 二级评论记录数；
- `目标筛选报告` 是否每个作者都有一行；
- 作者粉丝数、关注数、获赞数、作品数是否非伪造；
- 作品链接是否为 `/video/{id}` 或 `/note/{id}`；
- 媒体附件字段是否是真实上传文件；
- 目标集合和序号是否符合用户原话。

如果缺少飞书回读 scope，最终状态只能写 `未完成-缺少回读授权`，不能说完成。

## 十二、常见错误

| 错误 | 后果 | 正确处理 |
|---|---|---|
| 把“置顶集合第 4-8 条”理解成“去掉置顶后第 4-8 条” | 作品集合全错 | 重建 pinned 集合，重新采集 |
| 置顶不足 8 条还硬凑 5 条 | 伪造数据 | 目标为 0，写短缺报告 |
| 用 `--skip-top 3` 代替 `pinned[3:8]` | 口径错误 | 先构建 pinned 集合再切片 |
| 作者粉丝数写 0 | 误导验收 | 采不到就留空并报告原因 |
| 只写本地 JSON | 没有交付 | 写入飞书并给出 Base 链接 |
| 只看写入返回，不回读 | 验收不完整 | 从 Base 回读关键字段 |
| 把 URL 写进附件字段 | 媒体未交付 | 下载真实文件后上传附件 |
| 运行包里带 `.env`、Cookie 或 Chrome profile | 泄露风险 | 重新打包并排除敏感文件 |

## 十三、完成回复模板

只有验收门槛满足，最终回复才可以说“完成”。

```text
本次状态：{完成/部分完成/失败}
run_id：{run_id}
作者数：{author_count}
目标规则：{例如：每个作者置顶集合原始顺序第 4-8 条}

作者信息：写入 {author_record_count} 条
作品：视频 {video_count} 条，图文 {image_count} 条
评论：一级 {comment_count} 条，二级 {reply_count} 条
目标筛选报告：{report_count} 条
媒体：成功 {media_success_count}，失败 {media_failed_count}
飞书回读：{通过/未通过/缺少 scope}

Base 链接：{base_url}
执行报告：{final_report_path_or_doc}
失败摘要：{failure_summary}
```

如果状态不是“完成”，不得省略失败摘要。

## 十四、重新打包和发布

修改技能后生成新版 zip：

```bash
python scripts/build_skill_zip.py --output dist/douyin-author-homepage-collector.zip
```

打包后检查：

```bash
python - <<'PY'
import zipfile
p = "dist/douyin-author-homepage-collector.zip"
with zipfile.ZipFile(p) as z:
    names = z.namelist()
    print(names[:10])
    assert all(n.startswith("douyin-author-homepage-collector/") for n in names)
    forbidden = [".env", "cookies.json", "runs/", "chrome-cdp-profile/", ".git/", "tests/"]
    assert not any(any(x in n for x in forbidden) for n in names)
PY
```

上传新版 zip 到飞书指定文件夹，覆盖旧文件，并在秘籍文档里更新下载链接。发布到 GitHub 时，确保 zip、飞书文档、仓库 README 说的是同一个版本。
