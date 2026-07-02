import asyncio
import httpx
from typing import Optional
from urllib.parse import urlencode
from config.settings import DEFAULT_HEADERS, PROXY_URL, REQUEST_DELAY, REQUEST_MAX_RETRIES
from core.throttle import jittered_delay, backoff_delay


class DouyinClient:
    """HTTP client wrapper with rate limiting and retry."""

    def __init__(self, cookies: str = ""):
        self._cookies = cookies
        kwargs = {
            "headers": {**DEFAULT_HEADERS, "Cookie": cookies} if cookies else DEFAULT_HEADERS,
            "timeout": 30.0,
            "follow_redirects": True,
        }
        if PROXY_URL:
            kwargs["proxy"] = PROXY_URL
        self._client = httpx.AsyncClient(**kwargs)
        self._delay = REQUEST_DELAY

    def update_cookies(self, cookies: str):
        self._cookies = cookies
        self._client.headers["Cookie"] = cookies

    async def get(self, url: str, params: Optional[dict] = None, retries: int = None) -> dict:
        retries = REQUEST_MAX_RETRIES if retries is None else retries
        for attempt in range(retries):
            try:
                await asyncio.sleep(jittered_delay(self._delay))
                resp = await self._client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, Exception) as e:
                print(f"[Request error] attempt {attempt + 1}/{retries}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(backoff_delay(attempt + 1, self._delay))
        return {}

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


class BrowserClient:
    """Drop-in replacement for DouyinClient that routes API calls through a
    Playwright page's fetch() — inherits the browser session's cookies.

    Use when connected to an already-logged-in Chrome via CDP.
    """

    def __init__(self, page):
        self._page = page
        self._delay = REQUEST_DELAY

    async def get(self, url: str, params: Optional[dict] = None, retries: int = None) -> dict:
        retries = REQUEST_MAX_RETRIES if retries is None else retries
        if params:
            sep = '&' if '?' in url else '?'
            url = f"{url}{sep}{urlencode(params)}"
        for attempt in range(retries):
            try:
                await asyncio.sleep(jittered_delay(self._delay))
                data = await asyncio.wait_for(self._page.evaluate(
                    """async (url) => {
                        try {
                            const resp = await fetch(url, {
                                headers: {'Accept': 'application/json',
                                          'Referer': 'https://www.douyin.com/'},
                                credentials: 'include',
                            });
                            return await resp.json();
                        } catch (e) { return {status_code: -1, error: e.message}; }
                    }""", url
                ), timeout=30)
                return data or {}
            except Exception as e:
                print(f"[Browser request error] attempt {attempt + 1}/{retries}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(backoff_delay(attempt + 1, self._delay))
        return {}

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass
