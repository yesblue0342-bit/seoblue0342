#!/usr/bin/env python3
"""Build a minimal Google Drive env file from app and Stella dotenv files.

Only the three OAuth values required by seoblue0342 and an optional non-secret
write flag are written. Values are never printed, and the primary app
configuration always takes precedence.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


ALIASES = {
    "GOOGLE_CLIENT_ID": ("GOOGLE_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_DRIVE_CLIENT_ID"),
    "GOOGLE_CLIENT_SECRET": (
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_OAUTH_CLIENT_SECRET",
        "GOOGLE_DRIVE_CLIENT_SECRET",
    ),
    "GOOGLE_REFRESH_TOKEN": (
        "GOOGLE_REFRESH_TOKEN",
        "GOOGLE_DRIVE_REFRESH_TOKEN",
        "GOOGLE_OAUTH_REFRESH_TOKEN",
        "DRIVE_REFRESH_TOKEN",
    ),
}


def normalize(value: str | None) -> str:
    normalized = str(value or "").strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"'", '"'}:
        normalized = normalized[1:-1].strip()
    return re.sub(r"^Bearer\s+", "", normalized, flags=re.IGNORECASE).strip()


def read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            values[key] = normalize(value)
    return values


def _resolve_one(source: dict[str, str]) -> dict[str, str]:
    return {
        canonical: value
        for canonical, aliases in ALIASES.items()
        if (value := next((source.get(alias, "") for alias in aliases if source.get(alias, "")), ""))
    }


def resolve(primary: dict[str, str], fallback: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Select one complete credential set; never mix fields from two OAuth clients."""
    primary_set = _resolve_one(primary)
    if len(primary_set) == len(ALIASES):
        return primary_set, []
    fallback_set = _resolve_one(fallback)
    if len(fallback_set) == len(ALIASES):
        return fallback_set, []
    missing = [name for name in ALIASES if not fallback_set.get(name)]
    return fallback_set, missing


def write_env(path: Path, values: dict[str, str], enable_writes: bool = False) -> None:
    for value in values.values():
        if "\n" in value or "\r" in value:
            raise ValueError("OAuth 환경변수에 줄바꿈이 포함되어 있습니다.")
    content = "".join(f"{key}={values[key]}\n" for key in ALIASES)
    if enable_writes:
        content += "SEO_DRIVE_WRITES_ENABLED=1\n"
    path.write_text(content, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--fallback", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--enable-writes", action="store_true")
    args = parser.parse_args()

    resolved, missing = resolve(read_dotenv(args.primary), read_dotenv(args.fallback))
    if missing:
        print(
            "Google Drive OAuth 설정 누락: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 2
    write_env(args.output, resolved, enable_writes=args.enable_writes)
    print("Google Drive OAuth 설정 3개를 안전하게 준비했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
