import httpx
import json
import math
import os
import subprocess
import tempfile
import time
import zlib
from typing import List, Optional
from config.settings import (
    FEISHU_APP_ID,
    FEISHU_APP_SECRET,
    FEISHU_APP_TOKEN,
    FEISHU_TABLE_ID,
    FEISHU_API_BASE,
)


class FeishuBitable:
    """Write data to Feishu multidimensional tables (Bitable)."""

    def __init__(
        self,
        app_id: str = "",
        app_secret: str = "",
        app_token: str = "",
        table_id: str = "",
    ):
        self.app_id = app_id or FEISHU_APP_ID
        self.app_secret = app_secret or FEISHU_APP_SECRET
        self.app_token = app_token or FEISHU_APP_TOKEN
        self.table_id = table_id or FEISHU_TABLE_ID
        self._tenant_token: str = ""
        self._client = httpx.Client(timeout=30.0)
        self._use_lark_cli = not isinstance(self.app_secret, str) or not self.app_secret

    def _get_tenant_token(self) -> str:
        if self._use_lark_cli:
            raise RuntimeError("tenant token is managed by lark-cli")
        if self._tenant_token:
            return self._tenant_token
        url = f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal"
        resp = self._client.post(
            url,
            json={"app_id": self.app_id, "app_secret": self.app_secret},
        )
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(
                f"Failed to get Feishu token: {data.get('msg', 'unknown error')}"
            )
        self._tenant_token = data["tenant_access_token"]
        return self._tenant_token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_tenant_token()}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def _cli_api(self, method: str, path: str, data: dict = None,
                 params: dict = None, files: dict = None) -> dict:
        args = [
            "lark-cli", "api", method, path,
            "--as", "user",
            "--format", "json",
        ]
        if data is not None:
            args.extend(["--data", json.dumps(data, ensure_ascii=False)])
        if params is not None:
            args.extend(["--params", json.dumps(params, ensure_ascii=False)])
        for field, file_path in (files or {}).items():
            cli_file_path = file_path
            if os.path.isabs(cli_file_path):
                cli_file_path = os.path.relpath(cli_file_path, os.getcwd())
            args.extend(["--file", f"{field}={cli_file_path}"])
        proc = None
        for attempt in range(5):
            proc = subprocess.run(args, capture_output=True, text=True)
            if proc.returncode == 0:
                break
            combined = proc.stderr.strip() or proc.stdout.strip()
            retryable = ["transport", "EOF", "timeout", "i/o timeout"]
            if not any(token in combined for token in retryable):
                break
            time.sleep(1.5 * (attempt + 1))
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
        out = json.loads(proc.stdout or "{}")
        if out.get("ok") is True:
            return {"code": 0, "data": out.get("data") or {}}
        return out

    def _api_get(self, path: str, params: dict = None) -> dict:
        if self._use_lark_cli:
            return self._cli_api("GET", path, params=params)
        resp = self._client.get(f"{FEISHU_API_BASE}{path.removeprefix('/open-apis')}", headers=self._headers(), params=params)
        return resp.json()

    def _api_post(self, path: str, data: dict = None) -> dict:
        if self._use_lark_cli:
            return self._cli_api("POST", path, data=data or {})
        resp = self._client.post(f"{FEISHU_API_BASE}{path.removeprefix('/open-apis')}", headers=self._headers(), json=data or {})
        return resp.json()

    def _api_delete(self, path: str, params: dict = None) -> dict:
        if self._use_lark_cli:
            return self._cli_api("DELETE", path, params=params)
        resp = self._client.delete(f"{FEISHU_API_BASE}{path.removeprefix('/open-apis')}", headers=self._headers(), params=params)
        return resp.json()

    def create_app(self, name: str, folder_token: str = "") -> dict:
        """Create a NEW Bitable app (multidimensional table file).

        ``folder_token`` places the new file inside a Drive folder (the app must
        be a collaborator with edit rights on that folder, otherwise Feishu
        returns ``DriveNodePermNotAllow``). Empty ``folder_token`` creates it in
        the app's own space.

        On success sets ``self.app_token`` to the new app and returns the app
        info dict: ``{app_token, default_table_id, url, name, ...}``.
        """
        body = {"name": name}
        if folder_token:
            body["folder_token"] = folder_token
        data = self._api_post("/open-apis/bitable/v1/apps", body)
        if data.get("code") != 0:
            raise RuntimeError(
                f"Failed to create bitable app: code={data.get('code')} "
                f"msg={data.get('msg')}"
            )
        app = data["data"]["app"]
        self.app_token = app["app_token"]
        print(f"[Feishu] Created bitable '{name}': {app.get('url', self.app_token)}")
        return app

    def delete_app(self, app_token: str = "") -> bool:
        """Delete a Bitable app via the Drive files API."""
        at = app_token or self.app_token
        data = self._api_delete(f"/open-apis/drive/v1/files/{at}", {"type": "bitable"})
        return data.get("code") == 0

    def create_full_bitable(self, name: str, folder_token: str = "") -> dict:
        """Create the canonical 4-table Douyin bitable and return all IDs.

        Tables: 视频作品 / 图文作品 / 一级评论 / 二级评论 (see SKILL.md data model).
        The auto-created default empty table is removed. Returns:
        {app_token, url, video_table_id, image_table_id,
         comment_l1_table_id, comment_l2_table_id}
        """
        app = self.create_app(name, folder_token)
        app_token = app["app_token"]
        default_table_id = app.get("default_table_id", "")

        video_tid = self.create_table("视频作品")
        self.setup_video_table(video_tid)
        image_tid = self.create_table("图文作品")
        self.setup_image_table(image_tid)
        l1_tid = self.create_table("一级评论")
        self.setup_comment_l1_table(l1_tid)
        l2_tid = self.create_table("二级评论")
        self.setup_comment_l2_table(l2_tid)

        # Remove the empty default table Feishu auto-creates.
        if default_table_id:
            try:
                self._api_delete(f"/open-apis/bitable/v1/apps/{app_token}/tables/{default_table_id}")
            except Exception:
                pass

        return {
            "app_token": app_token,
            "url": app.get("url", f"https://feishu.cn/base/{app_token}"),
            "video_table_id": video_tid,
            "image_table_id": image_tid,
            "comment_l1_table_id": l1_tid,
            "comment_l2_table_id": l2_tid,
        }

    def create_author_bitable(self, name: str, folder_token: str = "") -> dict:
        """Create the author-mode bitable: the canonical 4 post/comment tables
        PLUS a 作者信息 table that holds the author profile (粉丝量 etc.).

        Tables: 作者信息 / 视频作品 / 图文作品 / 一级评论 / 二级评论. Returns:
        {app_token, url, author_table_id, video_table_id, image_table_id,
         comment_l1_table_id, comment_l2_table_id}
        """
        app = self.create_app(name, folder_token)
        app_token = app["app_token"]
        default_table_id = app.get("default_table_id", "")

        author_tid = self.create_table("作者信息")
        self.setup_author_table(author_tid)
        video_tid = self.create_table("视频作品")
        self.setup_video_table(video_tid)
        image_tid = self.create_table("图文作品")
        self.setup_image_table(image_tid)
        l1_tid = self.create_table("一级评论")
        self.setup_comment_l1_table(l1_tid)
        l2_tid = self.create_table("二级评论")
        self.setup_comment_l2_table(l2_tid)

        # Remove the empty default table Feishu auto-creates.
        if default_table_id:
            try:
                self._api_delete(f"/open-apis/bitable/v1/apps/{app_token}/tables/{default_table_id}")
            except Exception:
                pass

        return {
            "app_token": app_token,
            "url": app.get("url", f"https://feishu.cn/base/{app_token}"),
            "author_table_id": author_tid,
            "video_table_id": video_tid,
            "image_table_id": image_tid,
            "comment_l1_table_id": l1_tid,
            "comment_l2_table_id": l2_tid,
        }

    def list_tables(self) -> list:
        """List all tables in the Bitable app."""
        data = self._api_get(f"/open-apis/bitable/v1/apps/{self.app_token}/tables")
        if data.get("code") != 0:
            print(f"[Feishu] List tables error: {data.get('msg')}")
            return []
        return data.get("data", {}).get("items", [])

    def create_table(self, name: str) -> str:
        """Create a new table and return its table_id."""
        data = self._api_post(
            f"/open-apis/bitable/v1/apps/{self.app_token}/tables",
            {"table": {"name": name}},
        )
        if data.get("code") != 0:
            raise RuntimeError(f"Failed to create table: {data.get('msg')}")
        table_id = data["data"]["table_id"]
        print(f"[Feishu] Created table '{name}' with ID: {table_id}")
        return table_id

    def add_fields(self, fields: List[dict], table_id: str = "") -> None:
        """
        Add fields to a table.
        Each field: {"field_name": "xxx", "type": 1}
        Types: 1=text, 2=number, 3=select, 5=datetime, 7=checkbox, 15=link, 17=attachment
        """
        tid = table_id or self.table_id
        for f in fields:
            data = self._api_post(
                f"/open-apis/bitable/v1/apps/{self.app_token}/tables/{tid}/fields",
                f,
            )
            if data.get("code") != 0:
                print(f"[Feishu] Add field '{f.get('field_name')}' error: {data.get('msg')}")

    def write_records(
        self, records: List[dict], table_id: str = ""
    ) -> int:
        """
        Batch write records to a table. Max 500 per batch.
        Each record is a dict of {field_name: value}.
        Returns number of records written.
        """
        tid = table_id or self.table_id
        total_written = 0

        for i in range(0, len(records), 500):
            batch = records[i : i + 500]
            payload = {"records": [{"fields": r} for r in batch]}
            data = self._api_post(
                f"/open-apis/bitable/v1/apps/{self.app_token}/tables/{tid}/records/batch_create",
                payload,
            )
            if data.get("code") != 0:
                print(
                    f"[Feishu] Batch write error (batch {i // 500 + 1}): "
                    f"{data.get('msg')}"
                )
            else:
                written = len(data.get("data", {}).get("records", []))
                total_written += written

        print(f"[Feishu] Written {total_written}/{len(records)} records to table {tid}")
        return total_written

    # Field types: 1=text 2=number 3=select 5=datetime 7=checkbox 15=url 17=attachment
    def setup_video_table(self, table_id: str = "") -> None:
        """Fields for the VIDEO posts table — cover & video are real attachments."""
        fields = [
            {"field_name": "作者", "type": 1},
            {"field_name": "作品正文", "type": 1},
            {"field_name": "作品链接", "type": 15},      # raw URL (link == text)
            {"field_name": "作者主页", "type": 15},      # raw URL (link == text)
            {"field_name": "作品封面", "type": 17},      # attachment (uploaded file)
            {"field_name": "作品视频", "type": 17},      # attachment (uploaded file)
            {"field_name": "点赞数", "type": 2},
            {"field_name": "评论数", "type": 2},
            {"field_name": "收藏数", "type": 2},
            {"field_name": "分享数", "type": 2},
            {"field_name": "发布时间", "type": 1},
            {"field_name": "话题标签", "type": 1},
            {"field_name": "来源", "type": 1},
            {"field_name": "爬取时间", "type": 1},
        ]
        self.add_fields(fields, table_id)

    def setup_image_table(self, table_id: str = "") -> None:
        """Fields for the IMAGE/note posts table — cover & images are attachments."""
        fields = [
            {"field_name": "作者", "type": 1},
            {"field_name": "作品正文", "type": 1},
            {"field_name": "作品链接", "type": 15},      # raw URL
            {"field_name": "作者主页", "type": 15},      # raw URL
            {"field_name": "作品封面", "type": 17},      # attachment
            {"field_name": "作品图片", "type": 17},      # attachment (multiple files)
            {"field_name": "点赞数", "type": 2},
            {"field_name": "评论数", "type": 2},
            {"field_name": "收藏数", "type": 2},
            {"field_name": "分享数", "type": 2},
            {"field_name": "发布时间", "type": 1},
            {"field_name": "话题标签", "type": 1},
            {"field_name": "来源", "type": 1},
            {"field_name": "爬取时间", "type": 1},
        ]
        self.add_fields(fields, table_id)

    def setup_user_table(self, table_id: str = "") -> None:
        """Create fields for the user data table."""
        fields = [
            {"field_name": "用户ID", "type": 1},
            {"field_name": "昵称", "type": 1},
            {"field_name": "简介", "type": 1},
            {"field_name": "粉丝数", "type": 2},
            {"field_name": "关注数", "type": 2},
            {"field_name": "获赞数", "type": 2},
            {"field_name": "作品数", "type": 2},
            {"field_name": "主页链接", "type": 15},
        ]
        self.add_fields(fields, table_id)

    def setup_author_table(self, table_id: str = "") -> None:
        """Fields for the 作者信息 table (author profile incl. 粉丝量).

        Same shape as the 用户 table plus 爬取时间. 主页链接 is a raw-URL field.
        """
        fields = [
            {"field_name": "用户ID", "type": 1},
            {"field_name": "昵称", "type": 1},
            {"field_name": "简介", "type": 1},
            {"field_name": "粉丝数", "type": 2},
            {"field_name": "关注数", "type": 2},
            {"field_name": "获赞数", "type": 2},
            {"field_name": "作品数", "type": 2},
            {"field_name": "主页链接", "type": 15},      # raw URL (link == text)
            {"field_name": "爬取时间", "type": 1},
        ]
        self.add_fields(fields, table_id)

    def setup_comment_l1_table(self, table_id: str = "") -> None:
        """Fields for the FIRST-level (一级评论) comment table."""
        fields = [
            {"field_name": "评论ID", "type": 1},
            {"field_name": "评论内容", "type": 1},
            {"field_name": "评论者昵称", "type": 1},
            {"field_name": "评论者ID", "type": 1},
            {"field_name": "所属作品ID", "type": 1},
            {"field_name": "所属作品描述", "type": 1},
            {"field_name": "点赞数", "type": 2},
            {"field_name": "回复数", "type": 2},
            {"field_name": "评论时间", "type": 1},
            {"field_name": "来源", "type": 1},
            {"field_name": "爬取时间", "type": 1},
        ]
        self.add_fields(fields, table_id)

    def setup_comment_l2_table(self, table_id: str = "") -> None:
        """Fields for the SECOND-level (二级评论 / reply) comment table."""
        fields = [
            {"field_name": "评论ID", "type": 1},
            {"field_name": "评论内容", "type": 1},
            {"field_name": "评论者昵称", "type": 1},
            {"field_name": "评论者ID", "type": 1},
            {"field_name": "父评论ID", "type": 1},
            {"field_name": "回复对象", "type": 1},
            {"field_name": "所属一级评论作者", "type": 1},
            {"field_name": "所属作品ID", "type": 1},
            {"field_name": "点赞数", "type": 2},
            {"field_name": "评论时间", "type": 1},
            {"field_name": "来源", "type": 1},
            {"field_name": "爬取时间", "type": 1},
        ]
        self.add_fields(fields, table_id)

    # Backwards-compatible alias (old name)
    def setup_comment_table(self, table_id: str = "") -> None:
        self.setup_comment_l1_table(table_id)

    def setup_trending_table(self, table_id: str = "") -> None:
        """Create fields for the trending data table."""
        fields = [
            {"field_name": "排名", "type": 2},
            {"field_name": "热搜词", "type": 1},
            {"field_name": "热度值", "type": 2},
            {"field_name": "标签", "type": 1},
            {"field_name": "视频数", "type": 2},
        ]
        self.add_fields(fields, table_id)

    def close(self):
        self._client.close()

    def delete_all_records(self, table_id: str = "") -> int:
        tid = table_id or self.table_id
        total_deleted = 0
        while True:
            data = self._api_get(
                f"/open-apis/bitable/v1/apps/{self.app_token}/tables/{tid}/records",
                {"page_size": 500},
            )
            items = data.get("data", {}).get("items", [])
            if not items:
                break
            record_ids = [item["record_id"] for item in items]
            self._api_post(
                f"/open-apis/bitable/v1/apps/{self.app_token}/tables/{tid}/records/batch_delete",
                {"records": record_ids},
            )
            total_deleted += len(record_ids)
        print(f"[Feishu] Deleted {total_deleted} records from table {tid}")
        return total_deleted

    def upload_file(self, file_path: str, parent_type: str = "bitable_image") -> str:
        """Upload a file to Feishu. Returns file_token. Uses chunked upload for files > 20MB."""
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        if self._use_lark_cli:
            if file_size <= 20 * 1024 * 1024:
                return self._upload_small_cli(file_path, file_name, file_size, parent_type)
            return self._upload_chunked_cli(file_path, file_name, file_size, parent_type)
        token = self._get_tenant_token()

        if file_size <= 20 * 1024 * 1024:
            return self._upload_small(file_path, file_name, file_size, parent_type, token)
        else:
            return self._upload_chunked(file_path, file_name, file_size, parent_type, token)

    def _upload_small_cli(self, file_path, file_name, file_size, parent_type):
        data = self._cli_api(
            "POST",
            "/open-apis/drive/v1/medias/upload_all",
            data={
                "file_name": file_name,
                "parent_type": parent_type,
                "parent_node": self.app_token,
                "size": str(file_size),
            },
            files={"file": file_path},
        )
        if data.get("code") != 0:
            print(f"[Feishu] Upload error: {data.get('msg')}")
            return ""
        return data.get("data", {}).get("file_token", "")

    def _upload_chunked_cli(self, file_path, file_name, file_size, parent_type):
        data = self._cli_api(
            "POST",
            "/open-apis/drive/v1/medias/upload_prepare",
            data={
                "file_name": file_name,
                "parent_type": parent_type,
                "parent_node": self.app_token,
                "size": file_size,
            },
        )
        if data.get("code") != 0:
            print(f"[Feishu] Upload prepare error: {data.get('msg')}")
            return ""

        upload_id = data["data"]["upload_id"]
        block_size = data["data"]["block_size"]
        block_num = data["data"]["block_num"]

        with open(file_path, "rb") as f, tempfile.TemporaryDirectory() as td:
            for i in range(block_num):
                chunk = f.read(block_size)
                if not chunk:
                    break
                checksum = str(zlib.adler32(chunk) & 0xFFFFFFFF)
                chunk_path = os.path.join(td, f"part_{i}")
                with open(chunk_path, "wb") as cf:
                    cf.write(chunk)
                part = self._cli_api(
                    "POST",
                    "/open-apis/drive/v1/medias/upload_part",
                    data={
                        "upload_id": upload_id,
                        "seq": str(i),
                        "size": str(len(chunk)),
                        "checksum": checksum,
                    },
                    files={"file": chunk_path},
                )
                if part.get("code") != 0:
                    print(f"[Feishu] Upload part {i} error: {part.get('msg')}")
                    return ""

        data = self._cli_api(
            "POST",
            "/open-apis/drive/v1/medias/upload_finish",
            data={"upload_id": upload_id, "block_num": block_num},
        )
        if data.get("code") != 0:
            print(f"[Feishu] Upload finish error: {data.get('msg')}")
            return ""
        return data.get("data", {}).get("file_token", "")

    def _upload_small(self, file_path, file_name, file_size, parent_type, token):
        headers = {"Authorization": f"Bearer {token}"}
        with open(file_path, "rb") as f:
            resp = self._client.post(
                f"{FEISHU_API_BASE}/drive/v1/medias/upload_all",
                headers=headers,
                data={
                    "file_name": file_name,
                    "parent_type": parent_type,
                    "parent_node": self.app_token,
                    "size": str(file_size),
                },
                files={"file": (file_name, f, "application/octet-stream")},
            )
        data = resp.json()
        if data.get("code") != 0:
            print(f"[Feishu] Upload error: {data.get('msg')}")
            return ""
        return data.get("data", {}).get("file_token", "")

    def _upload_chunked(self, file_path, file_name, file_size, parent_type, token):
        headers_json = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        headers_upload = {"Authorization": f"Bearer {token}"}

        resp = self._client.post(
            f"{FEISHU_API_BASE}/drive/v1/medias/upload_prepare",
            headers=headers_json,
            json={
                "file_name": file_name,
                "parent_type": parent_type,
                "parent_node": self.app_token,
                "size": file_size,
            },
        )
        data = resp.json()
        if data.get("code") != 0:
            print(f"[Feishu] Upload prepare error: {data.get('msg')}")
            return ""

        upload_id = data["data"]["upload_id"]
        block_size = data["data"]["block_size"]
        block_num = data["data"]["block_num"]

        with open(file_path, "rb") as f:
            for i in range(block_num):
                chunk = f.read(block_size)
                if not chunk:
                    break
                checksum = str(zlib.adler32(chunk) & 0xFFFFFFFF)
                resp = self._client.post(
                    f"{FEISHU_API_BASE}/drive/v1/medias/upload_part",
                    headers=headers_upload,
                    data={
                        "upload_id": upload_id,
                        "seq": str(i),
                        "size": str(len(chunk)),
                        "checksum": checksum,
                    },
                    files={"file": (f"part_{i}", chunk, "application/octet-stream")},
                    timeout=120.0,
                )
                d = resp.json()
                if d.get("code") != 0:
                    print(f"[Feishu] Upload part {i} error: {d.get('msg')}")
                    return ""

        resp = self._client.post(
            f"{FEISHU_API_BASE}/drive/v1/medias/upload_finish",
            headers=headers_json,
            json={"upload_id": upload_id, "block_num": block_num},
        )
        data = resp.json()
        if data.get("code") != 0:
            print(f"[Feishu] Upload finish error: {data.get('msg')}")
            return ""
        return data.get("data", {}).get("file_token", "")


def url_field(url: str):
    """Value for a Feishu URL field that DISPLAYS the raw link (link == text).

    Per the data-model agreement, link fields (作品链接 / 作者主页 / 主页链接) must
    show the URL itself, NOT a label like '查看作品'. Empty url -> "".
    """
    return {"link": url, "text": url} if url else ""


def video_to_feishu_record(video) -> dict:
    """Lightweight record (no media upload) for the quick `search` path.

    Links are raw URLs. The canonical full pipeline with real attachments is
    scrape_all.py / scrape-to-bitable — see SKILL.md "Feishu Data Model".
    """
    author_sec_uid = getattr(video, "author_sec_uid", "")
    homepage = f"https://www.douyin.com/user/{author_sec_uid}" if author_sec_uid else ""
    return {
        "作者": video.author_nickname,
        "作品正文": video.desc,
        "作品链接": url_field(video.post_url),
        "作者主页": url_field(homepage),
        "点赞数": video.digg_count,
        "评论数": video.comment_count,
        "收藏数": video.collect_count,
        "分享数": video.share_count,
        "发布时间": video.create_time,
        "话题标签": video.hashtags,
    }


def user_to_feishu_record(user) -> dict:
    return {
        "用户ID": user.uid,
        "昵称": user.nickname,
        "简介": user.signature,
        "粉丝数": user.follower_count,
        "关注数": user.following_count,
        "获赞数": user.total_favorited,
        "作品数": user.aweme_count,
        "主页链接": url_field(user.homepage_url),
    }


def author_to_feishu_record(user, crawl_time: str = "") -> dict:
    """Record for the 作者信息 table — author profile with 粉丝量 (follower count)."""
    return {
        "用户ID": user.uid,
        "昵称": user.nickname,
        "简介": user.signature,
        "粉丝数": user.follower_count,
        "关注数": user.following_count,
        "获赞数": user.total_favorited,
        "作品数": user.aweme_count,
        "主页链接": url_field(user.homepage_url),
        "爬取时间": crawl_time,
    }


def comment_to_feishu_record(comment) -> dict:
    return {
        "评论ID": comment.comment_id,
        "视频ID": comment.aweme_id,
        "评论内容": comment.text,
        "用户昵称": comment.user_nickname,
        "用户ID": comment.user_uid,
        "点赞数": comment.digg_count,
        "回复数": comment.reply_count,
        "发布时间": comment.create_time,
    }


def trending_to_feishu_record(item) -> dict:
    return {
        "排名": item.rank,
        "热搜词": item.title,
        "热度值": item.hot_value,
        "标签": item.label,
        "视频数": item.video_count,
    }
