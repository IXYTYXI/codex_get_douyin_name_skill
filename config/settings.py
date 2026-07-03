import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _resolve_feishu_app_credentials() -> tuple[str, str]:
    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")
    if app_id and app_secret:
        return app_id, app_secret

    config_path = Path.home() / ".lark-cli" / "config.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return app_id, app_secret

    apps = data.get("apps") or []
    if isinstance(apps, dict):
        apps = list(apps.values())
    for app in apps:
        if not isinstance(app, dict):
            continue
        cli_app_id = app.get("appId") or app.get("app_id") or ""
        cli_app_secret = app.get("appSecret") or app.get("app_secret") or ""
        if cli_app_id and cli_app_secret:
            return app_id or cli_app_id, app_secret or cli_app_secret
    return app_id, app_secret


FEISHU_APP_ID, FEISHU_APP_SECRET = _resolve_feishu_app_credentials()
FEISHU_APP_TOKEN = os.getenv("FEISHU_APP_TOKEN", "")
FEISHU_TABLE_ID = os.getenv("FEISHU_TABLE_ID", "")

DOUYIN_COOKIE = os.getenv("DOUYIN_COOKIE", "")
PROXY_URL = os.getenv("PROXY_URL", "")
CDP_ENDPOINT = os.getenv("CDP_ENDPOINT", "")

MAX_PAGES = int(os.getenv("MAX_PAGES", "10"))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "2"))

# Anti-throttle pacing (see core/throttle.py)
REQUEST_JITTER = float(os.getenv("REQUEST_JITTER", "0.4"))    # ±fraction of REQUEST_DELAY
REQUEST_MAX_RETRIES = int(os.getenv("REQUEST_MAX_RETRIES", "3"))  # transport-error retries
BACKOFF_FACTOR = float(os.getenv("BACKOFF_FACTOR", "2.0"))    # exponential growth per retry
BACKOFF_MAX = float(os.getenv("BACKOFF_MAX", "30"))          # cap on a single backoff (s)
EMPTY_RETRY = int(os.getenv("EMPTY_RETRY", "2"))             # retries on empty/blocked page

DOUYIN_BASE_URL = "https://www.douyin.com"
DOUYIN_API_BASE = "https://www.douyin.com/aweme/v1/web"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.douyin.com/",
    "Accept": "application/json, text/plain, */*",
}

FEISHU_API_BASE = "https://open.feishu.cn/open-apis"
