#!/usr/bin/env python3
"""Sync CURSOR_SESSION_TOKEN in .env from Chrome, then restart usage-tracker.

Never prints the token. stdout is a JSON object with suffix/length only.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from hashlib import pbkdf2_hmac
from pathlib import Path

COOKIE_NAME = "WorkosCursorSessionToken"
ENV_KEY = "CURSOR_SESSION_TOKEN"
LAUNCHD_LABEL = "com.usage-tracker.menubar"
PROCESS_PATTERN = "usage_tracker.main"
SALT = b"saltysalt"
PBKDF2_ITERATIONS = 1003
KEY_LENGTH = 16
IV_HEX = "20" * 16
HASH_PREFIX_DB_VERSION = 24

APP_SUPPORT = Path.home() / "Library" / "Application Support"
CHROMIUM_SOURCES = (
    (APP_SUPPORT / "Google" / "Chrome", "Chrome Safe Storage"),
    (APP_SUPPORT / "Microsoft Edge", "Microsoft Edge Safe Storage"),
    (APP_SUPPORT / "BraveSoftware" / "Brave-Browser", "Brave Safe Storage"),
    (APP_SUPPORT / "Arc" / "User Data", "Arc Safe Storage"),
    (APP_SUPPORT / "Vivaldi", "Vivaldi Safe Storage"),
)


@dataclass(frozen=True)
class FoundToken:
    value: str
    source: str
    updated_utc: int


def _die(message: str, code: int = 1) -> None:
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    raise SystemExit(code)


def _find_project_root(start: Path) -> Path:
    candidates = (start, *start.parents, Path(__file__).resolve(), *Path(__file__).resolve().parents)
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if (path / "pyproject.toml").exists() and (path / ".env.example").exists():
            return path
    _die("usage-tracker 프로젝트 루트를 찾지 못했습니다")


def _normalize_token(raw: str) -> str:
    token = raw.strip().strip('"').strip("'")
    if not token:
        raise ValueError("토큰이 비어 있습니다")
    if "::" in token and "%3A%3A" not in token:
        token = token.replace("::", "%3A%3A", 1)
    if not token.startswith("user_"):
        raise ValueError("WorkosCursorSessionToken 형식이 아닙니다 (user_ 로 시작해야 함)")
    return token


def _profile_cookie_dbs(base_dir: Path) -> list[Path]:
    if not base_dir.exists():
        return []
    profiles: list[Path] = []
    default = base_dir / "Default"
    if default.is_dir():
        profiles.append(default)
    try:
        numbered = [
            child
            for child in base_dir.iterdir()
            if child.is_dir() and child.name.startswith("Profile ")
        ]
        profiles.extend(sorted(numbered, key=lambda p: p.stat().st_mtime, reverse=True))
    except OSError:
        pass
    if not profiles and base_dir.is_dir():
        profiles.append(base_dir)

    found: list[Path] = []
    for profile in profiles:
        for rel in ("Network/Cookies", "Cookies"):
            candidate = profile / rel
            if candidate.exists():
                found.append(candidate)
                break
    return found


def _keychain_passphrase(service: str) -> bytes | None:
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-w", "-s", service],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    passphrase = result.stdout.strip()
    return passphrase.encode("utf-8") if passphrase else None


def _derive_aes_key(passphrase: bytes) -> bytes:
    return pbkdf2_hmac("sha1", passphrase, SALT, PBKDF2_ITERATIONS, dklen=KEY_LENGTH)


def _unpad_pkcs7(data: bytes) -> bytes | None:
    if not data:
        return None
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 16:
        return None
    if data[-pad_len:] != bytes([pad_len]) * pad_len:
        return None
    return data[:-pad_len]


def _decrypt_v10(encrypted_value: bytes, aes_key: bytes, db_version: int) -> str | None:
    if encrypted_value[:3] != b"v10" or len(encrypted_value) <= 3:
        return None
    try:
        result = subprocess.run(
            [
                "openssl",
                "enc",
                "-aes-128-cbc",
                "-d",
                "-K",
                aes_key.hex(),
                "-iv",
                IV_HEX,
                "-nopad",
            ],
            input=encrypted_value[3:],
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout:
        return None
    decrypted = _unpad_pkcs7(result.stdout)
    if decrypted is None:
        return None
    if db_version >= HASH_PREFIX_DB_VERSION and len(decrypted) > 32:
        decrypted = decrypted[32:]
    try:
        return decrypted.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _copy_db(src: Path) -> Path:
    fd, tmp_name = tempfile.mkstemp(prefix="cursor-cookies-", suffix=".sqlite")
    os.close(fd)
    tmp = Path(tmp_name)
    shutil.copy2(src, tmp)
    tmp.chmod(0o600)
    return tmp


def _read_cookie_db(db_path: Path, aes_key: bytes) -> FoundToken | None:
    tmp: Path | None = None
    try:
        tmp = _copy_db(db_path)
        conn = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
        try:
            try:
                row = conn.execute(
                    "SELECT value FROM meta WHERE key = 'version'"
                ).fetchone()
                db_version = int(row[0]) if row else 0
            except (sqlite3.Error, TypeError, ValueError):
                db_version = 0
            rows = conn.execute(
                """
                SELECT host_key, value, CAST(encrypted_value AS BLOB), last_update_utc
                FROM cookies
                WHERE name = ?
                ORDER BY last_update_utc DESC
                """,
                (COOKIE_NAME,),
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)

    for host, value, encrypted, updated in rows:
        token = value or None
        if not token and encrypted:
            token = _decrypt_v10(encrypted, aes_key, db_version)
        if not token:
            continue
        try:
            normalized = _normalize_token(token)
        except ValueError:
            continue
        return FoundToken(value=normalized, source=f"chrome:{host}", updated_utc=int(updated or 0))
    return None


def _extract_from_browsers() -> FoundToken:
    best: FoundToken | None = None
    keychain_denied = False
    found_db = False
    for base_dir, service in CHROMIUM_SOURCES:
        dbs = _profile_cookie_dbs(base_dir)
        if not dbs:
            continue
        found_db = True
        passphrase = _keychain_passphrase(service)
        if passphrase is None:
            keychain_denied = True
            continue
        aes_key = _derive_aes_key(passphrase)
        for db_path in dbs:
            found = _read_cookie_db(db_path, aes_key)
            if found is None:
                continue
            if best is None or found.updated_utc > best.updated_utc:
                best = found
    if best is not None:
        return best
    if keychain_denied:
        _die("Keychain에서 브라우저 암호를 읽지 못했습니다. 허용 대화상자를 확인하세요.")
    if not found_db:
        _die("Chrome 쿠키 DB를 찾지 못했습니다.")
    _die("브라우저에서 WorkosCursorSessionToken 쿠키를 찾지 못했습니다. cursor.com에 로그인했는지 확인하세요.")


def _read_env_token(env_path: Path) -> str:
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{ENV_KEY}="):
            return line.split("=", 1)[1]
    return ""


def _write_env_token(env_path: Path, token: str) -> None:
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        example = env_path.with_name(".env.example")
        lines = example.read_text(encoding="utf-8").splitlines() if example.exists() else []

    replaced = False
    new_lines: list[str] = []
    for line in lines:
        if line.startswith(f"{ENV_KEY}="):
            new_lines.append(f"{ENV_KEY}={token}")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.insert(0, f"{ENV_KEY}={token}")
        if new_lines[1:] and new_lines[1] != "":
            new_lines.insert(1, "")

    text = "\n".join(new_lines)
    if not text.endswith("\n"):
        text += "\n"
    env_path.write_text(text, encoding="utf-8")
    try:
        env_path.chmod(0o600)
    except OSError:
        pass


def _app_pids() -> list[int]:
    result = subprocess.run(
        ["pgrep", "-f", PROCESS_PATTERN],
        capture_output=True,
        text=True,
    )
    pids: list[int] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return pids


def _launchd_target() -> str:
    return f"gui/{os.getuid()}/{LAUNCHD_LABEL}"


def _launchd_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"


def _kickstart_launchd() -> bool:
    target = _launchd_target()
    plist = _launchd_plist()
    if not plist.exists():
        return False
    kicked = subprocess.run(
        ["launchctl", "kickstart", "-k", target],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if kicked.returncode == 0:
        return True
    subprocess.run(["launchctl", "bootout", target], capture_output=True, timeout=20)
    boot = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist)],
        capture_output=True,
        text=True,
        timeout=20,
    )
    return boot.returncode == 0


def _start_from_venv(project_root: Path) -> subprocess.Popen[bytes] | None:
    python = project_root / ".venv" / "bin" / "python3.12"
    if not python.exists():
        python = project_root / ".venv" / "bin" / "python3"
    if not python.exists():
        return None
    log_dir = Path.home() / "Library" / "Logs" / "usage-tracker"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout = (log_dir / "stdout.log").open("ab")
    stderr = (log_dir / "stderr.log").open("ab")
    return subprocess.Popen(
        [str(python), "-m", "usage_tracker.main"],
        cwd=str(project_root),
        stdout=stdout,
        stderr=stderr,
        start_new_session=True,
    )


def _restart_app(project_root: Path) -> dict[str, object]:
    if _kickstart_launchd():
        time.sleep(2)
        pids = _app_pids()
        if pids:
            return {"restarted": True, "method": "launchd", "pid": pids[0]}
        return {
            "restarted": False,
            "method": "launchd",
            "error": "launchd 재시작 후 프로세스가 없습니다",
        }

    for pid in _app_pids():
        subprocess.run(["kill", str(pid)], capture_output=True, timeout=5)
    time.sleep(1)
    leftover = _app_pids()
    for pid in leftover:
        subprocess.run(["kill", "-9", str(pid)], capture_output=True, timeout=5)

    started = _start_from_venv(project_root)
    if started is None:
        return {
            "restarted": False,
            "method": "venv",
            "error": ".venv python을 찾지 못했습니다",
        }
    time.sleep(2)
    pids = _app_pids()
    if pids:
        return {"restarted": True, "method": "venv", "pid": pids[0]}
    return {
        "restarted": False,
        "method": "venv",
        "error": "앱 프로세스가 시작되지 않았습니다",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Update CURSOR_SESSION_TOKEN in .env")
    parser.add_argument("--env", type=Path, help="Path to .env (default: project root)")
    parser.add_argument(
        "--from-stdin",
        action="store_true",
        help="Read token from stdin instead of Chrome cookies",
    )
    args = parser.parse_args()

    project_root = _find_project_root(Path.cwd())
    env_path = args.env.expanduser().resolve() if args.env else project_root / ".env"

    if args.from_stdin:
        raw = sys.stdin.read()
        try:
            token = _normalize_token(raw)
        except ValueError as exc:
            _die(str(exc))
        source = "stdin"
    else:
        found = _extract_from_browsers()
        token = found.value
        source = found.source

    previous = _read_env_token(env_path)
    changed = previous != token
    if changed:
        _write_env_token(env_path, token)

    restart = _restart_app(project_root)
    payload: dict[str, object] = {
        "ok": True,
        "changed": changed,
        "source": source,
        "env": str(env_path),
        "length": len(token),
        "suffix": token[-8:],
        **restart,
    }
    print(json.dumps(payload, ensure_ascii=False))
    if not restart.get("restarted"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
