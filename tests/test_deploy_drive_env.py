import importlib.util
import os
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "deploy" / "resolve_drive_env.py"
SPEC = importlib.util.spec_from_file_location("resolve_drive_env", MODULE_PATH)
resolve_drive_env = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(resolve_drive_env)


def test_read_dotenv_supports_export_quotes_and_bearer(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n"
        "export GOOGLE_OAUTH_CLIENT_ID='client.apps.googleusercontent.com'\n"
        'GOOGLE_OAUTH_CLIENT_SECRET="GOCSPX-secret"\n'
        "GOOGLE_DRIVE_REFRESH_TOKEN=Bearer 1//refresh\n",
        encoding="utf-8",
    )

    values = resolve_drive_env.read_dotenv(env_file)

    assert values == {
        "GOOGLE_OAUTH_CLIENT_ID": "client.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "GOCSPX-secret",
        "GOOGLE_DRIVE_REFRESH_TOKEN": "1//refresh",
    }


def test_resolve_uses_complete_fallback_instead_of_mixing_partial_primary():
    primary = {"GOOGLE_CLIENT_ID": "primary-client"}
    fallback = {
        "GOOGLE_OAUTH_CLIENT_ID": "fallback-client",
        "GOOGLE_DRIVE_CLIENT_SECRET": "fallback-secret",
        "GOOGLE_OAUTH_REFRESH_TOKEN": "fallback-refresh",
    }

    resolved, missing = resolve_drive_env.resolve(primary, fallback)

    assert missing == []
    assert resolved == {
        "GOOGLE_CLIENT_ID": "fallback-client",
        "GOOGLE_CLIENT_SECRET": "fallback-secret",
        "GOOGLE_REFRESH_TOKEN": "fallback-refresh",
    }


def test_resolve_uses_complete_primary_set_atomically():
    primary = {
        "GOOGLE_CLIENT_ID": "primary-client",
        "GOOGLE_CLIENT_SECRET": "primary-secret",
        "GOOGLE_REFRESH_TOKEN": "primary-refresh",
    }
    fallback = {
        "GOOGLE_CLIENT_ID": "fallback-client",
        "GOOGLE_CLIENT_SECRET": "fallback-secret",
        "GOOGLE_REFRESH_TOKEN": "fallback-refresh",
    }

    resolved, missing = resolve_drive_env.resolve(primary, fallback)

    assert missing == []
    assert resolved == primary


def test_resolve_never_combines_two_partial_sets():
    resolved, missing = resolve_drive_env.resolve(
        {"GOOGLE_CLIENT_ID": "primary-client"},
        {
            "GOOGLE_CLIENT_SECRET": "fallback-secret",
            "GOOGLE_REFRESH_TOKEN": "fallback-refresh",
        },
    )

    assert resolved == {
        "GOOGLE_CLIENT_SECRET": "fallback-secret",
        "GOOGLE_REFRESH_TOKEN": "fallback-refresh",
    }
    assert missing == ["GOOGLE_CLIENT_ID"]


def test_deploy_preflights_before_cutover_and_has_rollback():
    script = (MODULE_PATH.parent / "run-docker.sh").read_text(encoding="utf-8")

    assert script.index("배포 전 Google Drive") < script.index("기존 컨테이너 백업")
    assert "rollback_deploy" in script
    assert 'sudo docker rename "$BACKUP_NAME" "$NAME"' in script


def test_resolve_reports_canonical_missing_names():
    resolved, missing = resolve_drive_env.resolve({}, {"GOOGLE_CLIENT_ID": "client"})

    assert resolved == {"GOOGLE_CLIENT_ID": "client"}
    assert missing == ["GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"]


def test_write_env_contains_only_canonical_drive_credentials(tmp_path):
    output = tmp_path / "drive.env"
    values = {
        "GOOGLE_CLIENT_ID": "client",
        "GOOGLE_CLIENT_SECRET": "secret",
        "GOOGLE_REFRESH_TOKEN": "refresh",
        "UNRELATED_SECRET": "must-not-be-copied",
    }

    resolve_drive_env.write_env(output, values, enable_writes=True)

    assert output.read_text(encoding="utf-8").splitlines() == [
        "GOOGLE_CLIENT_ID=client",
        "GOOGLE_CLIENT_SECRET=secret",
        "GOOGLE_REFRESH_TOKEN=refresh",
        "SEO_DRIVE_WRITES_ENABLED=1",
    ]
    if os.name != "nt":
        assert output.stat().st_mode & 0o777 == 0o600
