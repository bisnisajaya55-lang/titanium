# -*- coding: utf-8 -*-
"""
AUTO-CLEANUP v2.0 — Anti-Bloat Guardian
Jalankan tiap 15 menit via app.py atau manual.
Fungsi:
  1. Trim audit JSON (keep last 500 entries)
  2. Rotate log > 2 MB (keep 500 KB terakhir)
  3. Clean Chrome cache
  4. Archive file besar > 5 MB
  5. Cleanup backup lama > 3 hari
"""
import os
import shutil
import time
import json
import gzip
from datetime import datetime

# ==========================================
# CONFIG (Ubah sesuai kebutuhan)
# ==========================================
CONTAINER = "/home/container"
ARCHIVE_DIR = os.path.join(CONTAINER, "archive")
BACKUP_DIR = os.path.join(CONTAINER, "backups")

# File JSONL yang di-trim (keep last N lines)
AUDIT_FILES = {
    os.path.join(CONTAINER, "TITAN_LOSS_AUDIT.json"): 500,
    os.path.join(CONTAINER, "TITAN_WIN_AUDIT.json"): 500,
    os.path.join(CONTAINER, "member_bet_logs.json"): 2000,
    os.path.join(CONTAINER, "uid_violations.json"): 200,
}

# File log yang di-rotate (max MB, keep KB)
LOG_FILES = {
    os.path.join(CONTAINER, "security.log"): (2, 500),
    os.path.join(CONTAINER, "cf.log"): (2, 500),
}

# Chrome cache folders — v2 (expanded to 18 targets)
CHROME_PROFILE = os.path.join(CONTAINER, ".titan_chrome_profile")
CHROME_SUBS = [
    # Cache folders (delete all)
    "Default/Cache", "Default/Code Cache", "Default/GPUCache",
    "Default/Service Worker", "ShaderCache", "GrShaderCache",
    "Default/DawnGraphiteCache", "Default/DawnWebGPUCache",
    "Default/Session Storage", "Default/Local Storage",
    # History files (big, safe to clear)
    "Default/History", "Default/History-journal",
    "Default/Media History", "Default/Media History-journal",
    "Default/Top Sites", "Default/Top Sites-journal",
    "Default/Visited Links", "Default/Favicons",
]
# Note: Cookies TIDAK dihapus — biar login session tetap

# Backup retention — v2 (naik dari 3 ke 5 hari untuk safety)
BACKUP_MAX_AGE_DAYS = 5

# File besar yang di-archive (> MB)
BIG_FILE_THRESHOLD_MB = 5

# File yang di-archive kalau besar
BIG_FILES = [
    os.path.join(CONTAINER, "brain_memory.json"),
    os.path.join(CONTAINER, "q_table.json"),
    os.path.join(CONTAINER, "brain_learned.json"),
]


# ==========================================
# HELPER
# ==========================================
def _log(msg):
    print(f"[CLEANUP {datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _ensure_archive():
    os.makedirs(ARCHIVE_DIR, exist_ok=True)


def _size_mb(path):
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except:
        return 0


def _archive_file(path, reason=""):
    """Pindah file ke archive dengan timestamp, gzip."""
    try:
        _ensure_archive()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.basename(path)
        dst_gz = os.path.join(ARCHIVE_DIR, f"{base}.{ts}.gz")

        with open(path, "rb") as f_in:
            with gzip.open(dst_gz, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        os.remove(path)
        _log(f"📦 Archived: {base} ({reason}) → archive/{os.path.basename(dst_gz)}")
        return True
    except Exception as e:
        _log(f"❌ Archive fail {path}: {e}")
        return False


# ==========================================
# 1. TRIM AUDIT JSON (by count + by size)
# ==========================================
def trim_audit_files():
    for fp, max_entries in AUDIT_FILES.items():
        if not os.path.exists(fp):
            continue
        try:
            _sz_mb = _size_mb(fp)
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            
            # Trim jika: > max_entries ATAU > 2 MB
            need_trim = len(lines) > max_entries or _sz_mb > 2.0
            
            if need_trim:
                # Archive dulu kalau > 2000 entries atau > 5 MB
                if len(lines) > max_entries * 4 or _sz_mb > 5.0:
                    _archive_file(fp, f"oversized {len(lines)} lines / {_sz_mb:.1f}MB")

                with open(fp, "w", encoding="utf-8") as f:
                    f.writelines(lines[-max_entries:])
                _log(f"✂️ Trimmed {os.path.basename(fp)}: {len(lines)} → {max_entries} ({_sz_mb:.1f}MB → <1MB)")
        except Exception as e:
            _log(f"❌ Trim fail {fp}: {e}")


# ==========================================
# 2. ROTATE LOG FILES
# ==========================================
def rotate_logs():
    for fp, (max_mb, keep_kb) in LOG_FILES.items():
        if not os.path.exists(fp):
            continue
        try:
            if _size_mb(fp) > max_mb:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                keep_bytes = keep_kb * 1024
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(f"[LOG ROTATED {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
                    f.write(content[-keep_bytes:])
                _log(f"🔄 Rotated {os.path.basename(fp)} (>{max_mb}MB → keep {keep_kb}KB)")
        except Exception as e:
            _log(f"❌ Rotate fail {fp}: {e}")


# ==========================================
# 3. CLEAN CHROME CACHE
# ==========================================
def clean_chrome_cache():
    if not os.path.exists(CHROME_PROFILE):
        return
    cleaned = 0
    for sub in CHROME_SUBS:
        target = os.path.join(CHROME_PROFILE, sub)
        if os.path.exists(target):
            try:
                shutil.rmtree(target, ignore_errors=True)
                os.makedirs(target, exist_ok=True)
                cleaned += 1
            except:
                pass
    if cleaned > 0:
        _log(f"🧹 Cleaned {cleaned} Chrome cache folders")


# ==========================================
# 4. CLEANUP BACKUPS LAMA
# ==========================================
def cleanup_old_backups():
    if not os.path.exists(BACKUP_DIR):
        return
    now = time.time()
    cutoff = BACKUP_MAX_AGE_DAYS * 86400
    removed = 0
    for item in os.listdir(BACKUP_DIR):
        fp = os.path.join(BACKUP_DIR, item)
        try:
            if (now - os.path.getmtime(fp)) > cutoff:
                if os.path.isdir(fp):
                    shutil.rmtree(fp, ignore_errors=True)
                else:
                    os.remove(fp)
                removed += 1
        except:
            pass
    if removed > 0:
        _log(f"🗑️ Removed {removed} backups older than {BACKUP_MAX_AGE_DAYS} days")


# ==========================================
# 5. ARCHIVE FILE BESAR
# ==========================================
def archive_big_files():
    for fp in BIG_FILES:
        if not os.path.exists(fp):
            continue
        try:
            if _size_mb(fp) > BIG_FILE_THRESHOLD_MB:
                _archive_file(fp, f"size {_size_mb(fp):.1f}MB")
        except Exception as e:
            _log(f"❌ Archive big fail {fp}: {e}")


# ==========================================
# 6. CLEANUP ARCHIVE LAMA (> 7 hari)
# ==========================================
def cleanup_old_archive():
    if not os.path.exists(ARCHIVE_DIR):
        return
    now = time.time()
    cutoff = 7 * 86400
    removed = 0
    for fn in os.listdir(ARCHIVE_DIR):
        fp = os.path.join(ARCHIVE_DIR, fn)
        try:
            if os.path.isfile(fp) and (now - os.path.getmtime(fp)) > cutoff:
                os.remove(fp)
                removed += 1
        except:
            pass
    if removed > 0:
        _log(f"🗑️ Removed {removed} archived files > 7 days")


# ==========================================
# 7. CLEANUP PYTHON CACHE (__pycache__ + *.pyc) — v2 NEW
# ==========================================
def cleanup_python_cache():
    """Hapus __pycache__ dan .pyc files — aman, akan dibuat ulang otomatis."""
    removed = 0
    for root, dirs, files in os.walk(CONTAINER):
        # Skip archive & backups (biar tidak buang waktu)
        if "archive" in root or "backups" in root:
            continue
        # Hapus folder __pycache__
        if "__pycache__" in dirs:
            target = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(target, ignore_errors=True)
                removed += 1
            except: pass
        # Hapus file .pyc
        for f in files:
            if f.endswith(".pyc") or f.endswith(".pyo"):
                try:
                    os.remove(os.path.join(root, f))
                    removed += 1
                except: pass
    if removed > 0:
        _log(f"🐍 Cleaned {removed} Python cache files/folders")


# ==========================================
# MAIN
# ==========================================
def run_cleanup():
    _log("=" * 50)
    _log("START Auto-Cleanup")
    _log("=" * 50)

    trim_audit_files()
    rotate_logs()
    clean_chrome_cache()
    cleanup_old_backups()
    archive_big_files()
    cleanup_old_archive()
    cleanup_python_cache()  # v2 NEW

    _log("=" * 50)
    _log("DONE Auto-Cleanup ✅")
    _log("=" * 50)


if __name__ == "__main__":
    run_cleanup()