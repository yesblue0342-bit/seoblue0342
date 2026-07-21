import os
import sqlite3
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import webapp
from auth import init_auth_db, seed_initial_users
from drive_service import DriveClient, DriveError


DRIVE_ENV_NAMES = (
    "GOOGLE_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_DRIVE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_OAUTH_CLIENT_SECRET",
    "GOOGLE_DRIVE_CLIENT_SECRET",
    "GOOGLE_REFRESH_TOKEN",
    "GOOGLE_DRIVE_REFRESH_TOKEN",
    "GOOGLE_OAUTH_REFRESH_TOKEN",
    "DRIVE_REFRESH_TOKEN",
)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SEO_INITIAL_PASSWORD", "admin")
    webapp.app.config.update(
        TESTING=True,
        AUTH_DB_PATH=str(tmp_path / "auth.db"),
        SESSION_COOKIE_SECURE=False,
    )
    webapp.app.secret_key = "test-session-secret"
    with webapp.app.app_context():
        init_auth_db()
        assert seed_initial_users() == 2
    with webapp.app.test_client() as test_client:
        yield test_client


def csrf(client):
    client.get("/login")
    with client.session_transaction() as session:
        return session["csrf_token"]


def login(client, username="admin", password="admin"):
    return client.post(
        "/login",
        data={"username": username, "password": password, "csrf_token": csrf(client)},
        follow_redirects=False,
    )


def change_password(client, current="admin", new="strong-pass-123"):
    with client.session_transaction() as session:
        token = session["csrf_token"]
    return client.post(
        "/account/password",
        data={
            "current_password": current,
            "new_password": new,
            "confirm_password": new,
            "csrf_token": token,
        },
        follow_redirects=False,
    )


def test_seeded_accounts_are_hashed_and_force_password_change(client):
    with sqlite3.connect(webapp.app.config["AUTH_DB_PATH"]) as conn:
        rows = conn.execute(
            "SELECT username, password_hash, must_change_password FROM users ORDER BY username"
        ).fetchall()
    assert [row[0] for row in rows] == ["admin", "yesblue0342"]
    assert all(row[1] != "admin" and row[1].startswith("scrypt:") for row in rows)
    assert all(row[2] == 1 for row in rows)

    response = login(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/account/password")
    protected = client.get("/g-drive")
    assert protected.status_code == 302
    assert protected.headers["Location"].endswith("/account/password")


def test_password_change_unlocks_app_and_invalidates_old_password(client):
    login(client)
    response = change_password(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/g-drive")
    assert client.get("/g-drive").status_code == 200

    with client.session_transaction() as session:
        token = session["csrf_token"]
    client.post("/logout", data={"csrf_token": token})
    old_login = login(client, password="admin")
    assert old_login.status_code == 200
    new_login = login(client, password="strong-pass-123")
    assert new_login.status_code == 302


def test_protected_api_requires_login_password_change_and_csrf(client):
    assert client.get("/api/g-drive/files").status_code == 401
    login(client)
    assert client.get("/api/g-drive/files").status_code == 403
    change_password(client)
    response = client.post("/api/g-drive/delete", json={"file_id": "abc", "confirm": True})
    assert response.status_code == 400
    assert "보안 토큰" in response.get_json()["error"]


def test_delete_requires_explicit_confirmation(client, monkeypatch):
    class FakeDrive:
        configured = True

        def trash(self, file_id):
            return {"id": file_id, "trashed": True}

    login(client)
    change_password(client)
    monkeypatch.setattr(webapp, "get_drive_client", lambda: FakeDrive())
    with client.session_transaction() as session:
        token = session["csrf_token"]
    missing = client.post(
        "/api/g-drive/delete",
        json={"file_id": "abc"},
        headers={"X-CSRF-Token": token},
    )
    assert missing.status_code == 400
    confirmed = client.post(
        "/api/g-drive/delete",
        json={"file_id": "abc", "confirm": True},
        headers={"X-CSRF-Token": token},
    )
    assert confirmed.status_code == 200
    assert confirmed.get_json()["file"]["trashed"] is True


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data


def drive_client(monkeypatch):
    for name in DRIVE_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "refresh")
    client = DriveClient()
    client._access_token = "access"
    client._expires_at = time.time() + 3600
    return client


def test_drive_requires_complete_oauth_configuration(monkeypatch):
    for name in DRIVE_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")

    client = DriveClient()

    assert client.configured is False
    with pytest.raises(DriveError, match="환경변수가 설정되지") as exc:
        client.list_files()
    assert exc.value.status == 503


def test_drive_accepts_and_normalizes_stella_oauth_aliases(monkeypatch):
    for name in DRIVE_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", ' "client.apps.googleusercontent.com" ')
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", " 'GOCSPX-secret' ")
    monkeypatch.setenv("GOOGLE_DRIVE_REFRESH_TOKEN", 'Bearer 1//refresh')

    client = DriveClient()

    assert client.configured is True
    assert client.client_id == "client.apps.googleusercontent.com"
    assert client.client_secret == "GOCSPX-secret"
    assert client.refresh_token == "1//refresh"


@pytest.mark.parametrize(
    ("oauth_error", "message"),
    [
        ("invalid_client", "ID와 Secret 조합"),
        ("invalid_grant", "만료 또는 폐기"),
        ("temporarily_unavailable", "서버 자격증명"),
    ],
)
def test_drive_oauth_errors_are_safe_and_actionable(monkeypatch, oauth_error, message):
    client = drive_client(monkeypatch)
    client._access_token = ""
    client.http.post = lambda *args, **kwargs: FakeResponse(
        status_code=400,
        data={"error": oauth_error, "error_description": "sensitive provider detail"},
    )

    with pytest.raises(DriveError, match=message) as exc:
        client.list_files()
    assert exc.value.status == 503
    assert "sensitive" not in str(exc.value)


def test_drive_verify_connection_confirms_full_scope(monkeypatch):
    client = drive_client(monkeypatch)
    client._scope = "openid https://www.googleapis.com/auth/drive"
    client.http.request = lambda *args, **kwargs: FakeResponse(
        data={"user": {"permissionId": "permission"}}
    )

    result = client.verify_connection(require_full_access=True)

    assert result == {"connected": True, "fullAccess": True}


def test_drive_verify_connection_rejects_limited_scope(monkeypatch):
    client = drive_client(monkeypatch)
    client._scope = "https://www.googleapis.com/auth/drive.file"
    client.http.request = lambda *args, **kwargs: FakeResponse(
        data={"user": {"permissionId": "permission"}}
    )
    client.http.get = lambda *args, **kwargs: FakeResponse(
        data={"scope": "https://www.googleapis.com/auth/drive.file"}
    )

    with pytest.raises(DriveError, match="전체 접근 OAuth scope") as exc:
        client.verify_connection(require_full_access=True)
    assert exc.value.status == 403


def test_health_reports_drive_configuration_and_write_flag(client, monkeypatch):
    class FakeDrive:
        configured = True
        writes_enabled = True

    monkeypatch.setattr(webapp, "get_drive_client", lambda: FakeDrive())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json()["drive_configured"] is True
    assert response.get_json()["drive_writes_enabled"] is True


def test_drive_list_maps_folders_and_escapes_search(monkeypatch):
    client = drive_client(monkeypatch)
    captured = {}

    def request(method, url, **kwargs):
        captured.update(method=method, url=url, params=kwargs.get("params"))
        return FakeResponse(
            data={
                "files": [
                    {
                        "id": "folder1",
                        "name": "문서",
                        "mimeType": "application/vnd.google-apps.folder",
                    }
                ]
            }
        )

    client.http.request = request
    result = client.list_files(search="O'Reilly")
    assert result["files"][0]["isFolder"] is True
    assert "name contains 'O\\'Reilly'" in captured["params"]["q"]
    assert captured["params"]["spaces"] == "drive"


def test_drive_write_is_disabled_by_default(monkeypatch):
    client = drive_client(monkeypatch)
    with pytest.raises(DriveError, match="비활성화") as exc:
        client.create_folder("root", "새 폴더")
    assert exc.value.status == 403


def test_drive_permission_error_is_user_safe(monkeypatch):
    client = drive_client(monkeypatch)
    client.http.request = lambda *args, **kwargs: FakeResponse(status_code=403)
    with pytest.raises(DriveError, match="권한이 부족") as exc:
        client.list_files()
    assert exc.value.status == 403
