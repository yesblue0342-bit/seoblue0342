"""Server-side Google Drive API client used by the G-Drive app."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import BinaryIO
from urllib.parse import quote

import requests


FOLDER_MIME = "application/vnd.google-apps.folder"
GOOGLE_NATIVE_EXPORTS = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    ),
    "application/vnd.google-apps.drawing": ("image/png", ".png"),
}


class DriveError(RuntimeError):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


@dataclass
class DownloadResult:
    response: requests.Response
    filename: str
    content_type: str


def _escape_query(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


class DriveClient:
    api_base = "https://www.googleapis.com/drive/v3"
    upload_base = "https://www.googleapis.com/upload/drive/v3"

    def __init__(self) -> None:
        self.client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        self.client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
        self.refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN", "")
        self.writes_enabled = os.environ.get("SEO_DRIVE_WRITES_ENABLED", "0") == "1"
        self._access_token = ""
        self._expires_at = 0.0
        self._scope = ""
        self._lock = threading.Lock()
        self.http = requests.Session()

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def capabilities(self) -> dict:
        return {
            "configured": self.configured,
            "writesEnabled": self.writes_enabled,
            "scope": self._scope,
            "uploadLimitMb": 25,
        }

    def _token(self, force: bool = False) -> str:
        if not self.configured:
            raise DriveError("Google Drive 연결 환경변수가 설정되지 않았습니다.", 503)
        with self._lock:
            if not force and self._access_token and time.time() < self._expires_at - 60:
                return self._access_token
            try:
                response = self.http.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token",
                    },
                    timeout=15,
                )
            except requests.RequestException as exc:
                raise DriveError("Google 인증 서버에 연결하지 못했습니다.") from exc
            if response.status_code != 200:
                raise DriveError("Google Drive 인증에 실패했습니다. 서버 자격증명을 확인해 주세요.", 503)
            try:
                data = response.json()
            except ValueError as exc:
                raise DriveError("Google 인증 응답 형식이 올바르지 않습니다.", 503) from exc
            if not data.get("access_token"):
                raise DriveError("Google 인증 응답에 access token이 없습니다.", 503)
            self._access_token = data["access_token"]
            self._expires_at = time.time() + int(data.get("expires_in", 3600))
            self._scope = data.get("scope", self._scope)
            return self._access_token

    def _request(self, method: str, url: str, *, retry: bool = True, **kwargs) -> requests.Response:
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {self._token()}"
        try:
            response = self.http.request(method, url, headers=headers, timeout=30, **kwargs)
        except requests.RequestException as exc:
            raise DriveError("Google Drive API에 연결하지 못했습니다.") from exc
        if response.status_code == 401 and retry:
            self._token(force=True)
            headers.pop("Authorization", None)
            return self._request(method, url, retry=False, headers=headers, **kwargs)
        if response.status_code >= 400:
            message = "Google Drive 요청을 처리하지 못했습니다."
            if response.status_code == 403:
                message = "Google Drive 권한이 부족합니다. OAuth scope와 파일 권한을 확인해 주세요."
            elif response.status_code == 404:
                message = "요청한 파일 또는 폴더를 찾을 수 없습니다."
            elif response.status_code == 429:
                message = "Google Drive 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요."
            raise DriveError(message, response.status_code)
        return response

    def _json(self, method: str, path: str, **kwargs) -> dict:
        response = self._request(method, f"{self.api_base}{path}", **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise DriveError("Google Drive 응답 형식이 올바르지 않습니다.") from exc

    def list_files(self, folder_id: str = "root", search: str = "", page_token: str = "") -> dict:
        conditions = ["trashed = false"]
        if search:
            conditions.append(f"name contains '{_escape_query(search[:100])}'")
        else:
            conditions.append(f"'{_escape_query(folder_id or 'root')}' in parents")
        params = {
            "q": " and ".join(conditions),
            "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,size,parents,webViewLink,iconLink)",
            "orderBy": "folder,name",
            "pageSize": 100,
            "spaces": "drive",
        }
        if page_token:
            params["pageToken"] = page_token
        data = self._json("GET", "/files", params=params)
        files = data.get("files", [])
        for item in files:
            item["isFolder"] = item.get("mimeType") == FOLDER_MIME
        folder = {"id": folder_id or "root", "name": "내 드라이브"}
        if folder_id and folder_id != "root":
            folder = self._json(
                "GET",
                f"/files/{quote(folder_id, safe='')}",
                params={"fields": "id,name,parents"},
            )
        return {"folder": folder, "files": files, "nextPageToken": data.get("nextPageToken")}

    def get_file(self, file_id: str) -> dict:
        return self._json(
            "GET",
            f"/files/{quote(file_id, safe='')}",
            params={"fields": "id,name,mimeType,size,parents,modifiedTime"},
        )

    def download(self, file_id: str) -> DownloadResult:
        meta = self.get_file(file_id)
        mime = meta.get("mimeType", "application/octet-stream")
        name = meta.get("name", "download")
        if mime == FOLDER_MIME:
            raise DriveError("폴더는 직접 다운로드할 수 없습니다.", 400)
        if mime in GOOGLE_NATIVE_EXPORTS:
            export_mime, extension = GOOGLE_NATIVE_EXPORTS[mime]
            response = self._request(
                "GET",
                f"{self.api_base}/files/{quote(file_id, safe='')}/export",
                params={"mimeType": export_mime},
                stream=True,
            )
            if not name.lower().endswith(extension):
                name += extension
            mime = export_mime
        else:
            response = self._request(
                "GET",
                f"{self.api_base}/files/{quote(file_id, safe='')}",
                params={"alt": "media"},
                stream=True,
            )
        return DownloadResult(response=response, filename=name, content_type=mime)

    def _require_write(self) -> None:
        if not self.writes_enabled:
            raise DriveError("Drive 쓰기 기능이 서버 설정에서 비활성화되어 있습니다.", 403)

    def create_folder(self, parent_id: str, name: str) -> dict:
        self._require_write()
        return self._json(
            "POST",
            "/files",
            params={"fields": "id,name,mimeType,parents"},
            json={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id or "root"]},
        )

    def upload(self, parent_id: str, name: str, mime_type: str, stream: BinaryIO) -> dict:
        self._require_write()
        metadata = json.dumps({"name": name, "parents": [parent_id or "root"]}, ensure_ascii=False)
        payload = stream.read()
        response = self._request(
            "POST",
            f"{self.upload_base}/files",
            params={"uploadType": "multipart", "fields": "id,name,mimeType,size,parents"},
            files={
                "metadata": (None, metadata, "application/json; charset=UTF-8"),
                "file": (name, payload, mime_type or "application/octet-stream"),
            },
        )
        return response.json()

    def rename(self, file_id: str, name: str) -> dict:
        self._require_write()
        return self._json(
            "PATCH",
            f"/files/{quote(file_id, safe='')}",
            params={"fields": "id,name,mimeType,parents"},
            json={"name": name},
        )

    def move(self, file_id: str, target_parent: str) -> dict:
        self._require_write()
        meta = self.get_file(file_id)
        old = ",".join(meta.get("parents", []))
        return self._json(
            "PATCH",
            f"/files/{quote(file_id, safe='')}",
            params={
                "addParents": target_parent,
                "removeParents": old,
                "fields": "id,name,mimeType,parents",
            },
            json={},
        )

    def trash(self, file_id: str) -> dict:
        self._require_write()
        return self._json(
            "PATCH",
            f"/files/{quote(file_id, safe='')}",
            params={"fields": "id,name,trashed"},
            json={"trashed": True},
        )


_client: DriveClient | None = None


def get_drive_client() -> DriveClient:
    global _client
    if _client is None:
        _client = DriveClient()
    return _client


def reset_drive_client() -> None:
    global _client
    _client = None
