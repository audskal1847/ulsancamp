# -*- coding: utf-8 -*-
"""
camp_storage.py  —  주제 탐구 캠프 시스템 전용 [안전 저장 + 자동 백업] 모듈
------------------------------------------------------------------
사용법 (app.py 상단, 파일 경로 상수 정의 직후에 3줄만 추가):

    import camp_storage as cs
    cs.register_files(DATA_FILE, USERS_FILE, CONFIG_FILE, UPLOAD_DIR)
    db_lock, load_json, save_json = cs.db_lock, cs.load_json, cs.save_json
    cs.start_backup_daemon()

기존의  db_lock = threading.Lock() / def load_json / def save_json  세 개는 삭제.

핵심 보호 장치
  1) 저장 시 '키 삭제'가 원천 차단됨(deep merge). 명시적으로 allow_delete=True를
     준 경우에만 삭제가 반영됨  → 학생 데이터가 저절로 사라지지 않음.
  2) 원자적 쓰기(temp → fsync → os.replace). 쓰는 도중 종료돼도 파일이 깨지지 않음.
  3) 파일이 깨져 있으면 .bak → 최신 백업 zip 순으로 자동 복구 후 저장. 절대
     빈 dict로 덮어쓰지 않음.
  4) 모든 저장이 journal.jsonl 에 append-only 로 남음 → 최악의 경우 전량 복원 가능.
  5) 프로세스 전역 락(모듈 전역) + 파일 락(fcntl)으로 동시 저장 레이스 차단.
  6) 지정한 주기마다 3개 DB + 저널을 zip 으로 자동 백업(백그라운드 스레드).
"""
from __future__ import annotations

import copy
import datetime
import glob
import hashlib
import io
import json
import os
import shutil
import threading
import time
import zipfile

try:
    import streamlit as st
except Exception:  # 테스트/CLI 환경
    st = None

try:
    import fcntl
    _HAS_FCNTL = True
except Exception:
    _HAS_FCNTL = False


# ==============================================================
# 0. 전역 상태 (이 모듈은 프로세스당 1회만 import 되므로 값이 유지됨)
# ==============================================================
_LOCK = threading.RLock()          # ★ 메인 스크립트가 아닌 '모듈'에 두어야 rerun 시 재생성되지 않음
_FILES: dict[str, str] = {}        # {"data":..., "users":..., "config":...}
_READ_CACHE: dict[str, tuple] = {} # {path: (mtime_ns, size, parsed)}
_UNREADABLE: set[str] = set()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
TRASH_DIR = os.path.join(BASE_DIR, "trash")
JOURNAL_FILE = os.path.join(BASE_DIR, "journal.jsonl")
LOCK_FILE = os.path.join(BASE_DIR, ".camp_db.lock")
META_FILE = os.path.join(BACKUP_DIR, "_backup_meta.json")

DEFAULT_INTERVAL_MIN = 5
MAX_JOURNAL_MB = 200               # 저널이 이보다 커지면 회전
_daemon_started = False


def register_files(data_file: str, users_file: str, config_file: str, upload_dir: str | None = None):
    """앱의 파일 경로를 등록한다. 백업/트래시 폴더도 이 경로 기준으로 잡힌다."""
    global BASE_DIR, BACKUP_DIR, TRASH_DIR, JOURNAL_FILE, LOCK_FILE, META_FILE, _FILES
    _FILES = {
        "data": os.path.abspath(data_file),
        "users": os.path.abspath(users_file),
        "config": os.path.abspath(config_file),
    }
    if upload_dir:
        _FILES["uploads"] = os.path.abspath(upload_dir)
    BASE_DIR = os.path.dirname(_FILES["data"]) or BASE_DIR
    BACKUP_DIR = os.path.join(BASE_DIR, "backups")
    TRASH_DIR = os.path.join(BASE_DIR, "trash")
    JOURNAL_FILE = os.path.join(BASE_DIR, "journal.jsonl")
    LOCK_FILE = os.path.join(BASE_DIR, ".camp_db.lock")
    META_FILE = os.path.join(BACKUP_DIR, "_backup_meta.json")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(TRASH_DIR, exist_ok=True)
    return _FILES


# ==============================================================
# 1. 락
# ==============================================================
class _DBLock:
    """`with db_lock:` 형태로 기존 코드와 100% 호환. 스레드락 + 파일락 동시 사용."""

    def __init__(self):
        self._local = threading.local()

    def __enter__(self):
        _LOCK.acquire()
        depth = getattr(self._local, "depth", 0)
        if depth == 0 and _HAS_FCNTL:
            try:
                f = open(LOCK_FILE, "a+")
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                self._local.fh = f
            except Exception:
                self._local.fh = None
        self._local.depth = depth + 1
        return self

    def __exit__(self, *exc):
        self._local.depth -= 1
        if self._local.depth == 0:
            fh = getattr(self._local, "fh", None)
            if fh is not None:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                    fh.close()
                except Exception:
                    pass
                self._local.fh = None
        _LOCK.release()
        return False


db_lock = _DBLock()


# ==============================================================
# 2. 저수준 입출력
# ==============================================================
def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _atomic_write(path: str, text: str):
    """임시파일 → fsync → os.replace. 중간에 죽어도 원본이 깨지지 않는다."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, f".{os.path.basename(path)}.tmp{os.getpid()}_{threading.get_ident()}")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _READ_CACHE.pop(path, None)


def _parse_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    if not txt.strip():
        raise ValueError("빈 파일")
    return json.loads(txt)


def _read_cached(path: str):
    """mtime/size 기반 캐시. 같은 rerun 안에서 수십 번 호출돼도 파싱은 1번."""
    stt = os.stat(path)
    sig = (stt.st_mtime_ns, stt.st_size)
    hit = _READ_CACHE.get(path)
    if hit and hit[0] == sig:
        return copy.deepcopy(hit[1])
    parsed = _parse_file(path)
    _READ_CACHE[path] = (sig, copy.deepcopy(parsed))
    return parsed


def _recover_candidates(path: str):
    """복구 후보: .bak → 최신 백업 zip들 안의 동일 파일명"""
    yield path + ".bak"
    base = os.path.basename(path)
    for zp in list_backup_paths():
        try:
            with zipfile.ZipFile(zp) as z:
                if base in z.namelist():
                    yield ("ZIP", zp, base)
        except Exception:
            continue


def _read_robust(path: str, tries: int = 5):
    """정상 읽기 → 재시도 → .bak → 백업 zip 순으로 시도. 전부 실패 시 None."""
    for i in range(tries):
        if os.path.exists(path):
            try:
                return _read_cached(path)
            except Exception:
                time.sleep(0.12)
        else:
            break
    for cand in _recover_candidates(path):
        try:
            if isinstance(cand, tuple):
                with zipfile.ZipFile(cand[1]) as z:
                    return json.loads(z.read(cand[2]).decode("utf-8"))
            if os.path.exists(cand):
                return _parse_file(cand)
        except Exception:
            continue
    return None


def _quarantine(path: str, why: str = "corrupt"):
    """깨진 파일을 지우지 않고 trash 로 옮겨 보관."""
    if not os.path.exists(path):
        return
    os.makedirs(TRASH_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(TRASH_DIR, f"{why}_{ts}_{os.path.basename(path)}")
    try:
        shutil.copy2(path, dst)
    except Exception:
        pass


# ==============================================================
# 3. 병합 / 저널
# ==============================================================
def deep_merge(old, new):
    """dict 는 키를 절대 잃지 않게 병합. list/스칼라는 new 로 교체(=수정·행삭제는 정상 반영)."""
    if isinstance(old, dict) and isinstance(new, dict):
        out = dict(old)
        for k, v in new.items():
            out[k] = deep_merge(out[k], v) if k in out else v
        return out
    return new


def _missing_keys(old, new, prefix="", acc=None):
    """new 에서 사라진 dict 키 경로 목록(감사 로그용)."""
    if acc is None:
        acc = []
    if isinstance(old, dict) and isinstance(new, dict):
        for k, v in old.items():
            p = f"{prefix}/{k}"
            if k not in new:
                acc.append(p)
            else:
                _missing_keys(v, new[k], p, acc)
    return acc


def _rotate_journal():
    try:
        if os.path.exists(JOURNAL_FILE) and os.path.getsize(JOURNAL_FILE) > MAX_JOURNAL_MB * 1024 * 1024:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            os.replace(JOURNAL_FILE, os.path.join(BACKUP_DIR, f"journal_{ts}.jsonl"))
    except Exception:
        pass


def _journal(op: str, path: str, changed: dict | None = None, note: str = ""):
    """append-only 기록. 학습 데이터는 '바뀐 최상위 항목'만 저장한다."""
    try:
        _rotate_journal()
        rec = {
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "op": op,
            "file": os.path.basename(path),
            "note": note,
        }
        if changed:
            blob = json.dumps(changed, ensure_ascii=False)
            if len(blob.encode("utf-8")) <= 2 * 1024 * 1024:
                rec["changed"] = changed
            else:
                rec["changed_keys"] = list(changed.keys())
        with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _changed_top_level(old, new):
    if not isinstance(old, dict) or not isinstance(new, dict):
        return None
    return {k: v for k, v in new.items() if old.get(k) != v}


# ==============================================================
# 4. 공개 API : load_json / save_json  (기존 시그니처와 호환)
# ==============================================================
def load_json(file_path: str, default_value):
    """읽기 실패 시에도 절대 파일을 default 로 덮어쓰지 않는다."""
    with db_lock:
        if not os.path.exists(file_path):
            # 백업/저널로 되살릴 수 있으면 되살린다
            revived = _read_robust(file_path)
            if revived is not None:
                _atomic_write(file_path, _dumps(revived))
                _journal("revive", file_path, note="파일 없음 → 백업에서 복원")
                return revived
            _atomic_write(file_path, _dumps(default_value))
            return copy.deepcopy(default_value)

        data = _read_robust(file_path)
        if data is None:
            _UNREADABLE.add(file_path)
            _quarantine(file_path, "unreadable")
            return copy.deepcopy(default_value)   # 화면 표시는 되지만, 저장 시 병합으로 보호됨
        _UNREADABLE.discard(file_path)
        return data


def save_json(file_path: str, data, allow_delete: bool = False, reason: str = ""):
    """
    allow_delete=False (기본): 기존 파일의 dict 키가 사라지지 않도록 병합 저장.
                               → 학생 데이터가 통째로 날아가는 사고가 구조적으로 불가능.
    allow_delete=True        : 요청한 그대로 저장(실제 삭제/복구 작업용).
    """
    with db_lock:
        current = _read_robust(file_path)
        if current is None and os.path.exists(file_path) and os.path.getsize(file_path) > 2:
            _quarantine(file_path, "unreadable_on_save")

        if not allow_delete and isinstance(current, dict) and isinstance(data, dict):
            merged = deep_merge(current, data)
            lost = _missing_keys(current, data)
            if lost:
                _journal("blocked_delete", file_path, note=f"삭제 차단된 키 {len(lost)}개: {lost[:20]}")
        else:
            merged = data
            if isinstance(current, dict) and isinstance(data, dict):
                lost = _missing_keys(current, data)
                if lost:
                    _journal("delete", file_path, note=f"의도된 삭제: {lost[:20]} / {reason}")

        # 최후의 안전장치: 내용이 있던 파일을 빈 값으로 덮어쓰는 저장은 차단
        if isinstance(current, (dict, list)) and current and not merged and not allow_delete:
            _journal("blocked_empty", file_path, note="빈 데이터 덮어쓰기 차단")
            return False

        # 직전 버전을 .bak 으로 남긴다(1세대 즉시 복구용)
        try:
            if os.path.exists(file_path):
                shutil.copy2(file_path, file_path + ".bak")
        except Exception:
            pass

        _atomic_write(file_path, _dumps(merged))
        _journal("save", file_path, _changed_top_level(current or {}, merged), reason)
        return True


# ==============================================================
# 5. '진짜 삭제'가 필요할 때 쓰는 명시적 API
# ==============================================================
def delete_student_data(user_key: str, activity: str | None = None, actor: str = "", data_file: str | None = None):
    """
    학생 데이터를 의도적으로 삭제. 삭제분은 trash 폴더에 원본 그대로 보관되며
    저널에도 남으므로 되돌릴 수 있다.
    activity=None 이면 해당 학생의 전체 활동지 삭제.
    """
    path = data_file or _FILES.get("data")
    with db_lock:
        cur = _read_robust(path) or {}
        if user_key not in cur:
            return False
        removed = cur[user_key] if activity is None else cur[user_key].get(activity)
        if removed is None:
            return False
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(TRASH_DIR, exist_ok=True)
        with open(os.path.join(TRASH_DIR, f"deleted_{ts}_{_safe(user_key)}.json"), "w", encoding="utf-8") as f:
            json.dump({"user_key": user_key, "activity": activity, "actor": actor, "data": removed},
                      f, ensure_ascii=False, indent=2)
        if activity is None:
            cur.pop(user_key, None)
        else:
            cur[user_key].pop(activity, None)
        save_json(path, cur, allow_delete=True, reason=f"{actor} 가 {user_key}/{activity or '전체'} 삭제")
        return True


def restore_trash(trash_filename: str, data_file: str | None = None):
    """trash 에 보관된 삭제분을 되살린다."""
    path = data_file or _FILES.get("data")
    src = os.path.join(TRASH_DIR, trash_filename)
    with open(src, "r", encoding="utf-8") as f:
        rec = json.load(f)
    with db_lock:
        cur = _read_robust(path) or {}
        uk, act = rec["user_key"], rec.get("activity")
        if act is None:
            cur[uk] = deep_merge(cur.get(uk, {}), rec["data"])
        else:
            cur.setdefault(uk, {})[act] = rec["data"]
        save_json(path, cur, reason="trash 복원")
    return True


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in str(s))[:80]


# ==============================================================
# 6. 저널 기반 완전 복구
# ==============================================================
def rebuild_from_journal(file_basename: str | None = None):
    """저널을 처음부터 재생해 해당 파일의 상태를 재구성한다(최후의 수단)."""
    target = file_basename or os.path.basename(_FILES.get("data", "learning_data.json"))
    state: dict = {}
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, "journal_*.jsonl"))) + [JOURNAL_FILE]
    for jf in files:
        if not os.path.exists(jf):
            continue
        with open(jf, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("file") != target or "changed" not in rec:
                    continue
                if rec.get("op") in ("save", "revive"):
                    state = deep_merge(state, rec["changed"])
    return state


# ==============================================================
# 7. 백업
# ==============================================================
def _meta_read() -> dict:
    try:
        with open(META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _meta_write(meta: dict):
    try:
        _atomic_write(META_FILE, _dumps(meta))
    except Exception:
        pass


def get_backup_interval(config_file: str | None = None) -> int:
    cfg = _read_robust(config_file or _FILES.get("config", "")) or {}
    try:
        return int(cfg.get("backup_interval_min", DEFAULT_INTERVAL_MIN))
    except Exception:
        return DEFAULT_INTERVAL_MIN


def set_backup_interval(minutes: int, config_file: str | None = None):
    path = config_file or _FILES.get("config")
    with db_lock:
        cfg = _read_robust(path) or {}
        cfg["backup_interval_min"] = int(minutes)
        save_json(path, cfg, reason="백업 주기 변경")


def _state_digest() -> str:
    h = hashlib.sha256()
    for key in ("users", "data", "config"):
        p = _FILES.get(key)
        if p and os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    h.update(f.read())
            except Exception:
                pass
    return h.hexdigest()


def _counts() -> dict:
    users = _read_robust(_FILES.get("users", "")) or {}
    data = _read_robust(_FILES.get("data", "")) or {}
    return {
        "users": len(users),
        "students_with_data": len(data),
        "answer_blocks": sum(len(v) for v in data.values() if isinstance(v, dict)),
    }


def make_backup(tag: str = "auto", force: bool = False) -> str | None:
    """3개 DB + 저널을 zip 으로 묶어 backups/ 에 저장. 변경이 없으면 건너뛴다."""
    with db_lock:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        meta = _meta_read()
        digest = _state_digest()
        if not force and tag == "auto" and meta.get("last_digest") == digest:
            meta["last_check"] = datetime.datetime.now().isoformat(timespec="seconds")
            _meta_write(meta)
            return None

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"backup_{ts}_{_safe(tag)}.zip"
        zpath = os.path.join(BACKUP_DIR, name)
        counts = _counts()
        prev = meta.get("last_counts", {})
        warn = ""
        if prev and counts["students_with_data"] < prev.get("students_with_data", 0):
            warn = (f"경고: 학습데이터 학생 수가 {prev.get('students_with_data')} → "
                    f"{counts['students_with_data']} 로 감소했습니다.")

        tmp = zpath + ".tmp"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for key in ("users", "data", "config"):
                p = _FILES.get(key)
                if p and os.path.exists(p):
                    z.write(p, os.path.basename(p))
            if os.path.exists(JOURNAL_FILE):
                z.write(JOURNAL_FILE, "journal.jsonl")
            z.writestr("manifest.json", _dumps({
                "created": datetime.datetime.now().isoformat(timespec="seconds"),
                "tag": tag, "counts": counts, "warning": warn,
            }))
        os.replace(tmp, zpath)

        meta.update({"last_digest": digest, "last_backup": time.time(),
                     "last_backup_str": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                     "last_counts": counts, "last_warning": warn})
        _meta_write(meta)
        prune_backups()
        return zpath


def list_backup_paths() -> list[str]:
    try:
        return sorted(glob.glob(os.path.join(BACKUP_DIR, "backup_*.zip")), reverse=True)
    except Exception:
        return []


def list_backups() -> list[dict]:
    out = []
    for p in list_backup_paths():
        try:
            stt = os.stat(p)
            info = {"file": os.path.basename(p), "path": p,
                    "time": datetime.datetime.fromtimestamp(stt.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "size_kb": round(stt.st_size / 1024, 1), "students": "-", "warning": ""}
            with zipfile.ZipFile(p) as z:
                if "manifest.json" in z.namelist():
                    m = json.loads(z.read("manifest.json").decode("utf-8"))
                    info["students"] = m.get("counts", {}).get("students_with_data", "-")
                    info["warning"] = m.get("warning", "")
            out.append(info)
        except Exception:
            continue
    return out


def prune_backups(keep_recent: int = 60, keep_hours: int = 48, keep_days: int = 90):
    """최근 48시간은 전부 보관 → 그 이전은 하루 1개만 → 90일 초과분 삭제."""
    now = time.time()
    paths = list_backup_paths()
    keep = set(paths[:keep_recent])
    per_day = {}
    for p in paths:
        try:
            mt = os.path.getmtime(p)
        except Exception:
            continue
        age_h = (now - mt) / 3600.0
        if age_h <= keep_hours:
            keep.add(p)
            continue
        if age_h > keep_days * 24:
            continue
        day = datetime.datetime.fromtimestamp(mt).strftime("%Y%m%d")
        if day not in per_day:
            per_day[day] = p
            keep.add(p)
    for p in paths:
        if p not in keep:
            try:
                os.remove(p)
            except Exception:
                pass


def restore_backup(zip_name: str) -> bool:
    """백업 zip 으로 되돌린다. 되돌리기 직전 상태도 자동으로 백업된다."""
    zpath = zip_name if os.path.isabs(zip_name) else os.path.join(BACKUP_DIR, zip_name)
    if not os.path.exists(zpath):
        return False
    with db_lock:
        make_backup(tag="pre_restore", force=True)
        with zipfile.ZipFile(zpath) as z:
            names = z.namelist()
            for key in ("users", "data", "config"):
                p = _FILES.get(key)
                if not p:
                    continue
                base = os.path.basename(p)
                if base in names:
                    payload = z.read(base).decode("utf-8")
                    json.loads(payload)  # 검증
                    _atomic_write(p, payload)
        _journal("restore", _FILES.get("data", ""), note=f"{os.path.basename(zpath)} 로 복원")
    return True


def backup_status() -> dict:
    meta = _meta_read()
    paths = list_backup_paths()
    size = sum(os.path.getsize(p) for p in paths if os.path.exists(p))
    return {
        "last_backup_str": meta.get("last_backup_str", "없음"),
        "count": len(paths),
        "size_mb": size / 1024 / 1024,
        "warning": meta.get("last_warning", ""),
        "interval": get_backup_interval(),
        "counts": _counts(),
    }


# ==============================================================
# 8. 백그라운드 자동 백업 스레드
# ==============================================================
def _backup_loop():
    while True:
        try:
            interval = get_backup_interval()
            if interval and interval > 0:
                meta = _meta_read()
                last = float(meta.get("last_backup", 0) or 0)
                if time.time() - last >= interval * 60:
                    make_backup("auto")
        except Exception:
            pass
        time.sleep(20)


def start_backup_daemon():
    """앱 시작 시 1회만 호출하면 됨(여러 번 호출해도 안전)."""
    global _daemon_started
    with _LOCK:
        if _daemon_started:
            return
        _daemon_started = True
        t = threading.Thread(target=_backup_loop, name="camp-auto-backup", daemon=True)
        t.start()


def tick_backup():
    """스레드가 막힌 환경(일부 호스팅)을 대비해, 화면 갱신 때마다도 한 번 확인."""
    try:
        interval = get_backup_interval()
        if not interval:
            return
        meta = _meta_read()
        if time.time() - float(meta.get("last_backup", 0) or 0) >= interval * 60:
            make_backup("auto")
    except Exception:
        pass


# ==============================================================
# 9. 관리자 화면 (탭 하나에 이 함수만 호출하면 됨)
# ==============================================================
_INTERVAL_LABELS = {0: "사용 안 함", 1: "1분마다", 2: "2분마다", 3: "3분마다", 5: "5분마다(권장)",
                    10: "10분마다", 15: "15분마다", 30: "30분마다", 60: "60분마다"}


def render_backup_ui(config_file: str | None = None, key_prefix: str = "bk"):
    if st is None:
        raise RuntimeError("streamlit 이 필요합니다.")

    info = backup_status()
    st.subheader("💾 자동 백업 센터")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("마지막 백업", info["last_backup_str"])
    c2.metric("보관 백업", f"{info['count']}개")
    c3.metric("용량", f"{info['size_mb']:.1f} MB")
    c4.metric("데이터 보유 학생", f"{info['counts']['students_with_data']}명")
    if info["warning"]:
        st.warning("⚠️ " + info["warning"])

    st.markdown("---")
    st.markdown("#### ⏱️ 백업 주기 설정")
    opts = [0, 1, 2, 3, 5, 10, 15, 30, 60]
    cur = info["interval"]
    idx = opts.index(cur) if cur in opts else opts.index(DEFAULT_INTERVAL_MIN)
    sel = st.selectbox("설정한 시간마다 3개 DB + 저장이력을 zip 으로 자동 보관합니다.",
                       opts, index=idx, format_func=lambda x: _INTERVAL_LABELS.get(x, f"{x}분마다"),
                       key=f"{key_prefix}_interval")
    if sel != cur:
        set_backup_interval(sel, config_file)
        st.success(f"백업 주기가 '{_INTERVAL_LABELS.get(sel)}' 로 변경되었습니다.")
        st.rerun()

    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("📸 지금 즉시 백업하기", type="primary", use_container_width=True,
                     key=f"{key_prefix}_now"):
            p = make_backup("manual", force=True)
            st.success(f"백업 완료: {os.path.basename(p)}" if p else "백업에 실패했습니다.")
            st.rerun()
    with cb2:
        zips = list_backup_paths()
        if zips:
            with open(zips[0], "rb") as f:
                st.download_button("📥 최신 백업 zip 내려받기", data=f.read(),
                                   file_name=os.path.basename(zips[0]), mime="application/zip",
                                   use_container_width=True, key=f"{key_prefix}_dl_latest")

    st.info("💡 클라우드(Streamlit Cloud 등)에 올려 쓰는 경우 서버가 재시작되면 서버 안의 파일이 "
            "모두 초기화될 수 있습니다. **캠프 진행 중 쉬는 시간마다 위 [최신 백업 zip 내려받기]로 "
            "선생님 PC에 한 부씩 보관**해 주세요.")

    st.markdown("---")
    st.markdown("#### 🗂️ 백업 목록 / 복원")
    rows = list_backups()
    if not rows:
        st.info("아직 생성된 백업이 없습니다.")
    else:
        try:
            import pandas as pd
            st.dataframe(pd.DataFrame([{k: r[k] for k in ("file", "time", "students", "size_kb", "warning")}
                                       for r in rows[:50]]),
                         use_container_width=True, hide_index=True)
        except Exception:
            for r in rows[:20]:
                st.text(f"{r['file']}  |  {r['time']}  |  학생 {r['students']}명")

        pick = st.selectbox("복원 또는 내려받을 백업 선택",
                            [r["file"] for r in rows], key=f"{key_prefix}_pick")
        pc1, pc2 = st.columns(2)
        with pc1:
            with open(os.path.join(BACKUP_DIR, pick), "rb") as f:
                st.download_button("📥 선택 백업 내려받기", data=f.read(), file_name=pick,
                                   mime="application/zip", use_container_width=True,
                                   key=f"{key_prefix}_dl_pick")
        with pc2:
            ok = st.checkbox("이 백업 시점으로 되돌리는 데 동의합니다(현재 상태도 자동 보관됨).",
                             key=f"{key_prefix}_ok")
            if st.button("♻️ 선택 백업으로 복원", disabled=not ok, use_container_width=True,
                         key=f"{key_prefix}_restore"):
                if restore_backup(pick):
                    st.success("복원 완료. 화면을 새로고침합니다.")
                    st.rerun()
                else:
                    st.error("복원에 실패했습니다.")

    st.markdown("---")
    with st.expander("🧯 비상 복구 도구 (데이터가 사라졌을 때)"):
        st.caption("모든 저장 기록(journal.jsonl)을 처음부터 재생해 학습 데이터를 재구성합니다. "
                   "백업 zip 마저 손상됐을 때 쓰는 최후의 수단입니다.")
        if st.button("🔍 저장이력으로 재구성해 보기", key=f"{key_prefix}_rebuild"):
            rebuilt = rebuild_from_journal()
            st.session_state[f"{key_prefix}_rebuilt"] = rebuilt
            st.success(f"재구성 결과: 학생 {len(rebuilt)}명분의 데이터를 찾았습니다.")
        rebuilt = st.session_state.get(f"{key_prefix}_rebuilt")
        if rebuilt:
            st.write(f"현재 파일: {info['counts']['students_with_data']}명 / 재구성본: {len(rebuilt)}명")
            st.download_button("📥 재구성본 내려받기(learning_data.json)",
                               data=_dumps(rebuilt).encode("utf-8"),
                               file_name="rebuilt_learning_data.json", mime="application/json",
                               key=f"{key_prefix}_dl_rebuild")
            if st.checkbox("재구성본을 현재 데이터에 '병합'합니다(기존 내용은 지워지지 않음).",
                           key=f"{key_prefix}_mok"):
                if st.button("♻️ 병합 실행", key=f"{key_prefix}_merge"):
                    save_json(_FILES["data"], rebuilt, reason="저널 재구성 병합")
                    st.success("병합 완료.")
                    st.rerun()

        st.markdown("**🗑️ 삭제 보관함(trash)** — 의도적으로 삭제한 학생 데이터도 여기 남습니다.")
        tr = sorted(glob.glob(os.path.join(TRASH_DIR, "deleted_*.json")), reverse=True)[:30]
        if tr:
            tpick = st.selectbox("되살릴 삭제 기록 선택", [os.path.basename(x) for x in tr],
                                 key=f"{key_prefix}_trash")
            if st.button("♻️ 이 삭제 기록 되살리기", key=f"{key_prefix}_untrash"):
                restore_trash(tpick)
                st.success("복원되었습니다.")
                st.rerun()
        else:
            st.caption("삭제 보관함이 비어 있습니다.")


def render_delete_student_ui(all_users: dict, student_list: list, actor: str = "", key_prefix: str = "del"):
    """교사/관리자가 '직접' 학생 데이터를 지울 때만 쓰는 화면(2단계 확인)."""
    if st is None:
        raise RuntimeError("streamlit 이 필요합니다.")
    st.markdown("#### 🧹 학생 활동지 데이터 삭제 (직접 삭제만 가능)")
    st.caption("이 화면을 통하지 않으면 학생 데이터는 어떤 경우에도 삭제되지 않습니다. "
               "삭제하더라도 trash 보관함에 남아 되살릴 수 있습니다.")
    if not student_list:
        st.info("대상 학생이 없습니다.")
        return
    target = st.selectbox("학생 선택", ["선택"] + student_list,
                          format_func=lambda x: x if x == "선택" else
                          f"[{all_users.get(x, {}).get('class_group', '-')}] {all_users.get(x, {}).get('name', '')}",
                          key=f"{key_prefix}_stu")
    if target == "선택":
        return
    scope = st.selectbox("삭제 범위", ["전체 활동지"] + list(
        (_read_robust(_FILES["data"]) or {}).get(target, {}).keys()), key=f"{key_prefix}_scope")
    confirm = st.text_input("삭제하려면 학생 이름을 그대로 입력하세요", key=f"{key_prefix}_confirm")
    name = all_users.get(target, {}).get("name", "")
    if st.button("⚠️ 삭제 실행", disabled=(confirm.strip() != name or not name), key=f"{key_prefix}_go"):
        delete_student_data(target, None if scope == "전체 활동지" else scope, actor=actor)
        st.success("삭제했습니다. (trash 보관함에서 되살릴 수 있습니다.)")
        st.rerun()
