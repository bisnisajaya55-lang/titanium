# ============================================================================
# TITANIUM OMEGA - CENTRAL SERVER (SECURED)
# ============================================================================
import os
import re
import sys
import time
import json
import shutil
import hashlib
import hmac
import secrets
import threading
import subprocess
import logging
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
from flask import (Flask, request, jsonify, send_file, session,
                   redirect, url_for, render_template_string, abort)
from flask_cors import CORS
from werkzeug.security import check_password_hash

# ============================================================================
# CONFIG
# ============================================================================
CF_PATH = "/home/container/cf"
CF_HOME = "/home/container/.cloudflared"
TUNNEL_ID = "fa41612f-13f2-46af-ba03-3668bd0b396a"
DOMAIN = "autog.my.id"
PORT = int(os.environ.get("SERVER_PORT", os.environ.get("PORT", 3004)))
CF_LOG = "/home/container/cf.log"
CONFIG_FILE = os.path.join(CF_HOME, "config.yml")

# === [SECURITY PATCH v35.3] External Secrets Loader ===
_SECRETS_CACHE = None
def _load_secrets():
    global _SECRETS_CACHE
    if _SECRETS_CACHE is not None:
        return _SECRETS_CACHE
    import json as _json, os as _os
    _secrets_path = "/home/container/secrets.json"
    _fallback = {
        "CF_TUNNEL_TOKEN": "",
        "MEMBER_BOT_TOKEN": "",
        "MEMBER_BOT_USERNAME": "titan_member_notif_bot",
        "ADMIN_PASSWORD_HASH": "",
        "OWNER_MASTER_KEY": "",
    }
    try:
        if _os.path.exists(_secrets_path):
            with open(_secrets_path, "r") as _f:
                _loaded = _json.load(_f)
            _fallback.update(_loaded)
            print(f"[SECURITY] Loaded secrets.json ✅")
        else:
            print(f"[SECURITY] ⚠️  secrets.json NOT FOUND! Upload to /home/container/secrets.json")
    except Exception as _e:
        print(f"[SECURITY] ⚠️  Failed to load secrets.json: {_e}")
    _SECRETS_CACHE = _fallback
    return _fallback

_SECRETS = _load_secrets()

# === TUNNEL TOKEN (dari secrets.json) ===
CF_TUNNEL_TOKEN = _SECRETS.get("CF_TUNNEL_TOKEN", "")

# === MEMBER NOTIFICATION BOT (dari secrets.json) ===
MEMBER_BOT_TOKEN = _SECRETS.get("MEMBER_BOT_TOKEN", "")
MEMBER_BOT_USERNAME = _SECRETS.get("MEMBER_BOT_USERNAME", "titan_member_notif_bot")

# === FORCE JOIN CHANNELS (wajib diikuti member) ===
# Format:
#   id   = @username_telegram (untuk API cek member)
#   name = nama yang ditampilkan ke member (bisa pakai emoji)
#   url  = link lengkap https://t.me/username
FORCE_CHANNELS = [
    {"id": "@prediksi55five1menit", "name": "📢 Channel Prediksi VIP", "url": "https://t.me/prediksi55five1menit"},
    {"id": "@ProfitCuan55FIVE", "name": "👥 Grup Komunitas 55Five", "url": "https://t.me/ProfitCuan55FIVE"},
]

# Set True untuk aktifkan Force Join
FORCE_JOIN_ENABLED = True

EXE_TARGET = "titan_omega.exe"
STATIC_DIR = "static"
LICENSE_DB = "central_licenses.json"
REGISTRATION_DB = "central_registrations.json"
SECURITY_LOG = "security.log"

# ============================================================================
# ADMIN SECURITY
# ============================================================================
# Ganti hash di bawah dengan hasil dari STEP 1
ADMIN_PASSWORD_HASH = _SECRETS.get("ADMIN_PASSWORD_HASH", "")
ADMIN_USERNAME = "owner_titanium"   # opsional, untuk login 2-field

# Secret key — WAJIB ganti dengan random string
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

# Session timeout (menit)
SESSION_LIFETIME = 30

# Rate limit: max attempts sebelum lock
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 15 * 60  # 15 menit dalam detik

# In-memory store untuk rate limiting (per-IP)
_login_attempts = defaultdict(list)
_ip_blacklist = {}

# === RATE LIMITING UNTUK API ===
_api_calls = defaultdict(list)
API_RATE_LIMIT = 60  # max 60 request per menit per IP
API_WINDOW = 60  # dalam detik

def check_api_rate_limit(ip):
    """Cek apakah IP sudah melebihi batas request"""
    now = time.time()
    _api_calls[ip] = [t for t in _api_calls[ip] if now - t < API_WINDOW]
    if len(_api_calls[ip]) >= API_RATE_LIMIT:
        return False
    _api_calls[ip].append(now)
    return True

# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(SECURITY_LOG),
        logging.StreamHandler()
    ]
)
sec_log = logging.getLogger("security")

def log_security(event, ip, detail=""):
    sec_log.warning(f"[SECURITY] {event} | IP={ip} | {detail}")

# === MEMBER NOTIFICATION HELPER ===
def send_member_tg(chat_id, text):
    """Kirim pesan Telegram ke member"""
    if not MEMBER_BOT_TOKEN or MEMBER_BOT_TOKEN == "ISI_TOKEN_MEMBER_BOT_DISINI":
        return False
    try:
        import requests as _req
        r = _req.post(
            f"https://api.telegram.org/bot{MEMBER_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        return r.ok
    except Exception as e:
        print(f"[MEMBER TG ERROR] {e}")
        return False

def find_reg_by_uid(uid):
    """Cari registrasi berdasarkan UID"""
    regs = load_db(REGISTRATION_DB)
    for rid, r in regs.items():
        if str(r.get("uid", "")).strip() == str(uid).strip():
            return rid, r
    return None, None

# ============================================================================
# CLOUDFLARE TUNNEL
# ============================================================================
def write_config():
    os.makedirs(CF_HOME, exist_ok=True)
    config = f"""tunnel: {TUNNEL_ID}
credentials-file: {CF_HOME}/{TUNNEL_ID}.json

ingress:
  - hostname: {DOMAIN}
    service: http://localhost:{PORT}
  - hostname: www.{DOMAIN}
    service: http://localhost:{PORT}
  - hostname: bot.{DOMAIN}
    service: http://localhost:5000
  - service: http_status:404
"""
    with open(CONFIG_FILE, "w") as f:
        f.write(config)
    print(f"[INIT] Config written")

def start_cloudflared(max_wait=180):
    # Tunggu cloudflared binary tersedia (mungkin sedang didownload titan_deps)
    import time as _t_cf
    waited = 0
    while not os.path.exists(CF_PATH) and waited < max_wait:
        print(f"[INIT] Menunggu binary cloudflared... ({waited}s / {max_wait}s)")
        _t_cf.sleep(5)
        waited += 5
    
    if not os.path.exists(CF_PATH):
        print(f"[INIT] ❌ cloudflared TIDAK DITEMUKAN setelah {max_wait}s. Tunnel skip.")
        return
    
    try:
        # Pastikan executable
        try:
            os.chmod(CF_PATH, 0o755)
        except: pass
        
        log_f = open(CF_LOG, "w")
        proc = subprocess.Popen(
            [CF_PATH, "tunnel", "--no-autoupdate", "run", "--token", CF_TUNNEL_TOKEN],
            stdout=log_f, stderr=subprocess.STDOUT, cwd="/home/container"
        )
        print(f"[INIT] ✅ cloudflared running (PID: {proc.pid})")
    except Exception as e:
        print(f"[INIT] cloudflared failed: {e}")

def boot_cloudflared():
    time.sleep(2)
    write_config()
    start_cloudflared()
    # Watchdog: cek cloudflared masih hidup, restart kalau mati
    import time as _t_wd
    while True:
        _t_wd.sleep(60)
        try:
            # Cek proses cloudflared masih ada
            _ps = subprocess.run(["pgrep", "-f", "cloudflared"], capture_output=True)
            if _ps.returncode != 0:  # Process not found
                print("[WATCHDOG] cloudflared mati! Restart...")
                start_cloudflared(max_wait=30)
        except:
            pass

threading.Thread(target=boot_cloudflared, daemon=True).start()

# ============================================================================
# FLASK APP
# ============================================================================
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# Session cookie security
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE=None,      # Lebih toleran untuk cross-site
    SESSION_COOKIE_DOMAIN=None,         # Auto-detect
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=SESSION_LIFETIME),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # Max 5 MB upload
)

CORS(app, resources={r"/api/*": {"origins": [f"https://{DOMAIN}"]}})

# ============================================================================
# SECURITY HELPERS
# ============================================================================
def get_client_ip():
    """Ambil IP asli client (via Cloudflare header)."""
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"

def is_locked_out(ip):
    """Cek apakah IP sedang di-lockout."""
    if ip in _ip_blacklist:
        if time.time() < _ip_blacklist[ip]:
            return True
        else:
            del _ip_blacklist[ip]
    return False

def record_failed_login(ip):
    """Catat percobaan login gagal."""
    now = time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < LOCKOUT_DURATION]
    _login_attempts[ip].append(now)

    if len(_login_attempts[ip]) >= MAX_LOGIN_ATTEMPTS:
        _ip_blacklist[ip] = now + LOCKOUT_DURATION
        log_security("BRUTE_FORCE_BLOCKED", ip,
                     f"{len(_login_attempts[ip])} attempts, locked {LOCKOUT_DURATION}s")
        return True
    return False

def clear_login_attempts(ip):
    _login_attempts.pop(ip, None)

def sanitize(text, max_len=200):
    """Bersihkan input user."""
    if not text:
        return ""
    text = str(text).strip()[:max_len]
    # Hanya izinkan huruf, angka, @, ., -, _, spasi
    text = re.sub(r'[<>"\';\\]', '', text)
    return text

def generate_csrf_token():
    """Generate CSRF token unik per-session."""
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(32)
    return session["_csrf"]

def validate_csrf(token):
    # Khusus untuk register/verify: kalau session tidak ada (cookie diblok),
    # tetap izinkan asal token ada. Rate limiting tetap melindungi.
    if not token:
        return False
    session_csrf = session.get("_csrf")
    if not session_csrf:
        # Session hilang (browser blokir cookie) - izinkan jika token terlihat valid
        # Minimal 32 karakter hex
        if len(str(token)) >= 16:
            return True
        return False
    return hmac.compare_digest(token, session_csrf)

# Security headers
@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # [FIX-1] Allow cross-origin ke bot.autog.my.id (admin panel fetch API dari bot server)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' https://bot.autog.my.id; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com; "
        "img-src 'self' data: https://bot.autog.my.id; "
        "connect-src 'self' https://bot.autog.my.id https://api.telegram.org; "
        "frame-ancestors 'none'"
    )
    return response

def check_owner_mode():
    """Cek apakah server berjalan dalam mode OWNER (HARDCODED)"""
    return True  # Server SELALU dalam mode owner

# Admin decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = get_client_ip()
        
        # CEK BANNED IP
        if is_locked_out(ip):
            log_security("BANNED_IP_ACCESS_ATTEMPT", ip, f"path={request.path}")
            abort(429)
        
        # === CEK OWNER ACCESS KEY VIA URL (dari secrets.json) ===
        admin_key = request.args.get('key', '')
        OWNER_MASTER_KEY = _SECRETS.get("OWNER_MASTER_KEY", "")
        if admin_key and admin_key == OWNER_MASTER_KEY and check_owner_mode():
            session["is_admin"] = True
            session["last_active"] = time.time()
            session.permanent = True
            log_security("OWNER_KEY_LOGIN", ip, "via_access_key")
        
        if not session.get("is_admin"):
            log_security("UNAUTHORIZED_ADMIN_ACCESS", ip, f"path={request.path}")
            return redirect(url_for("admin_login"))
        
        # Cek session expiry
        last_active = session.get("last_active", 0)
        if time.time() - last_active > SESSION_LIFETIME * 60:
            session.clear()
            log_security("SESSION_EXPIRED", ip)
            return redirect(url_for("admin_login"))
        
        # CEK USER AGENT (anti bot/scraper)
        ua = request.headers.get("User-Agent", "")
        if not ua or any(bot in ua.lower() for bot in ["curl", "wget", "python-requests", "bot"]):
            log_security("BOT_UA_BLOCKED", ip, f"UA={ua[:50]}")
            abort(403)
        
        session["last_active"] = time.time()
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# DATA HELPERS
# ============================================================================
def load_db(p):
    if os.path.exists(p):
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db(p, d):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=2)
    os.replace(tmp, p)   # atomic write

def generate_offline_sig(expiry_yyyymmdd, account_id, hwid):
    salt = "TITANIUM_VIP_ULTRA_SECURE_SALT_2026"
    exp_c = str(expiry_yyyymmdd).strip().upper()
    acc_c = str(account_id).strip().upper()
    hw_c = str(hwid).strip().upper()
    raw = f"{exp_c}:{acc_c}:{hw_c}:{salt}"
    return hashlib.sha256(raw.encode()).hexdigest()[:10].upper()

def normalize_and_rename():
    if not os.path.isdir(STATIC_DIR):
        os.makedirs(STATIC_DIR, exist_ok=True)
        return None
    exe_path = os.path.join(STATIC_DIR, EXE_TARGET)
    if not os.path.exists(exe_path):
        for fname in os.listdir(STATIC_DIR):
            if fname.lower().endswith(".exe"):
                old_path = os.path.join(STATIC_DIR, fname)
                try:
                    shutil.move(old_path, exe_path)
                    print(f"[AUTO-RENAME] {fname} -> {EXE_TARGET}")
                except Exception as e:
                    print(f"[AUTO-RENAME] Gagal: {e}")
                    return old_path
                break
    return exe_path if os.path.exists(exe_path) else None

# ============================================================================
# PUBLIC ROUTES
# ============================================================================
@app.route('/')
def landing():
    return """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Titanium Omega — Panduan Bermain Profesional</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #05060a; color: #fff; overflow-x: hidden; line-height: 1.6; }
  .bg-grid { position: fixed; inset: 0; z-index: 0; background-image: linear-gradient(rgba(255,68,68,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,68,68,0.03) 1px, transparent 1px); background-size: 40px 40px; pointer-events: none; }
  .glow { position: fixed; width: 600px; height: 600px; border-radius: 50%; filter: blur(150px); opacity: 0.35; pointer-events: none; z-index: 0; }
  .glow-1 { background: #ff4444; top: -200px; left: -200px; }
  .glow-2 { background: #00ff9d; bottom: -200px; right: -200px; opacity: 0.25; }
  .container { position: relative; z-index: 1; max-width: 1100px; margin: 0 auto; padding: 0 20px; }
  .nav { display: flex; justify-content: space-between; align-items: center; padding: 20px 0; border-bottom: 1px solid rgba(255,255,255,0.06); }
  .logo { display: flex; align-items: center; gap: 10px; font-weight: 900; font-size: 1.1rem; letter-spacing: 2px; }
  .logo-icon { width: 36px; height: 36px; border-radius: 8px; background: linear-gradient(135deg, #ff4444, #ff0088); display: flex; align-items: center; justify-content: center; font-size: 1.1rem; box-shadow: 0 0 20px rgba(255,68,68,0.5); }
  .nav-links { display: flex; gap: 25px; align-items: center; }
  .nav-links a { color: #aaa; text-decoration: none; font-size: 0.85rem; font-weight: 600; transition: 0.2s; }
  .nav-links a:hover { color: #fff; }
  .hero { padding: 80px 0 60px; text-align: center; }
  .badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(0,255,157,0.1); border: 1px solid rgba(0,255,157,0.3); color: #00ff9d; padding: 6px 16px; border-radius: 50px; font-size: 0.7rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 25px; }
  .badge-dot { width: 6px; height: 6px; border-radius: 50%; background: #00ff9d; animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; box-shadow: 0 0 0 0 rgba(0,255,157,0.7); } 50% { opacity: 0.7; box-shadow: 0 0 0 8px rgba(0,255,157,0); } }
  h1.hero-title { font-size: clamp(2rem, 6vw, 3.5rem); font-weight: 900; letter-spacing: -1px; line-height: 1.1; margin-bottom: 20px; }
  .hero-title .accent { background: linear-gradient(135deg, #ff4444 0%, #ff0088 50%, #ffaa00 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
  .hero-subtitle { font-size: 1.05rem; color: #888; max-width: 600px; margin: 0 auto 40px; }
  .btn-group { display: flex; gap: 15px; justify-content: center; flex-wrap: wrap; }
  .btn { display: inline-flex; align-items: center; gap: 10px; padding: 15px 30px; border-radius: 12px; text-decoration: none; font-weight: 700; font-size: 0.9rem; transition: all 0.3s; border: none; cursor: pointer; }
  .btn-primary { background: linear-gradient(135deg, #00ff9d, #00d97e); color: #000; box-shadow: 0 8px 30px rgba(0,255,157,0.35); }
  .btn-primary:hover { transform: translateY(-2px); }
  .btn-secondary { background: rgba(255,255,255,0.05); color: #fff; border: 1px solid rgba(255,255,255,0.15); }
  .btn-secondary:hover { background: rgba(255,255,255,0.1); }
  .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; padding: 60px 0; }
  .feature { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 25px; transition: 0.3s; }
  .feature:hover { border-color: rgba(255,68,68,0.3); transform: translateY(-5px); }
  .feature-icon { font-size: 2rem; margin-bottom: 12px; }
  .feature h3 { font-size: 1rem; margin-bottom: 8px; color: #fff; }
  .feature p { font-size: 0.85rem; color: #888; }
  .footer { padding: 30px 0; text-align: center; color: #555; font-size: 0.75rem; border-top: 1px solid rgba(255,255,255,0.05); margin-top: 40px; }
  .footer a { color: #888; text-decoration: none; }
  .cta-section { background: linear-gradient(135deg, rgba(255,68,68,0.1), rgba(0,255,157,0.05)); border: 1px solid rgba(255,68,68,0.2); border-radius: 20px; padding: 50px 30px; text-align: center; margin: 60px 0; }
  .cta-section h2 { font-size: 1.8rem; margin-bottom: 15px; }
  .cta-section p { color: #aaa; margin-bottom: 30px; }
  @media (max-width: 640px) { .nav-links { display: none; } }
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="glow glow-1"></div>
<div class="glow glow-2"></div>
<div class="container">
  <nav class="nav">
    <div class="logo"><div class="logo-icon">👑</div><span>TITANIUM OMEGA</span></div>
    <div class="nav-links">
      <a href="#features">Fitur</a>
      <a href="#reflinks">Link Referral</a>
      <a href="/register">Daftar</a>
    </div>
  </nav>
  
  <section class="hero">
    <div class="badge"><span class="badge-dot"></span>Sistem Aktif 24/7</div>
    <h1 class="hero-title">Software VIP <span class="accent">GRATIS</span><br>Untuk Downline Kami</h1>
    <p class="hero-subtitle">
      Dapatkan akses <b style="color:#00ff9d;">GRATIS 100%</b> ke software analisis AI eksklusif. 
      Cukup daftar melalui link referral resmi kami dan lakukan deposit pertama Anda.
    </p>
    <div class="btn-group">
      <a href="#reflinks" class="btn btn-primary">🎁 Lihat Link Referral</a>
      <a href="/register" class="btn btn-secondary">📝 Sudah Deposit? Daftar VIP</a>
    </div>
  </section>

  <!-- SECTION LINK REFERRAL -->
  <section id="reflinks" style="padding: 60px 0; text-align: center;">
    <h2 style="font-size: 1.8rem; margin-bottom: 15px;">🔗 Link Daftar</h2>
    <p style="color: #888; margin-bottom: 40px;">Daftar melalui salah satu link di bawah, lalu lakukan deposit pertama Anda.</p>
    
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; max-width: 1000px; margin: 0 auto;">
      
      <a href="https://www.vokzila.com/#/register?invitationCode=78843597" target="_blank" style="display: block; background: linear-gradient(135deg, rgba(255,68,68,0.15), rgba(255,0,136,0.05)); border: 2px solid #ff4444; border-radius: 16px; padding: 25px 20px; text-decoration: none; color: #fff; transition: 0.3s; text-align: center;">
        <div style="font-size: 2rem; margin-bottom: 10px;">🎰</div>
        <div style="font-size: 1.1rem; font-weight: 900; letter-spacing: 1px;">LINK ALTERNATIF 1</div>
        <div style="font-size: 0.75rem; color: #ff8888; margin-top: 8px;">Klik untuk Daftar →</div>
      </a>
      
      <a href="https://www.nuxpira.com/#/register?invitationCode=78843597" target="_blank" style="display: block; background: linear-gradient(135deg, rgba(0,255,157,0.15), rgba(0,200,150,0.05)); border: 2px solid #00ff9d; border-radius: 16px; padding: 25px 20px; text-decoration: none; color: #fff; transition: 0.3s; text-align: center;">
        <div style="font-size: 2rem; margin-bottom: 10px;">🚀</div>
        <div style="font-size: 1.1rem; font-weight: 900; letter-spacing: 1px;">LINK ALTERNATIF 2</div>
        <div style="font-size: 0.75rem; color: #88ffbb; margin-top: 8px;">Klik untuk Daftar →</div>
      </a>
      
      <a href="https://www.krelmod.com/#/register?invitationCode=78843597" target="_blank" style="display: block; background: linear-gradient(135deg, rgba(0,170,255,0.15), rgba(0,100,200,0.05)); border: 2px solid #00aaff; border-radius: 16px; padding: 25px 20px; text-decoration: none; color: #fff; transition: 0.3s; text-align: center;">
        <div style="font-size: 2rem; margin-bottom: 10px;">💎</div>
        <div style="font-size: 1.1rem; font-weight: 900; letter-spacing: 1px;">LINK ALTERNATIF 3</div>
        <div style="font-size: 0.75rem; color: #88ccff; margin-top: 8px;">Klik untuk Daftar →</div>
      </a>
      
      <a href="https://www.gruzeno.com/#/register?invitationCode=78843597" target="_blank" style="display: block; background: linear-gradient(135deg, rgba(255,170,0,0.15), rgba(255,100,0,0.05)); border: 2px solid #ffaa00; border-radius: 16px; padding: 25px 20px; text-decoration: none; color: #fff; transition: 0.3s; text-align: center;">
        <div style="font-size: 2rem; margin-bottom: 10px;">👑</div>
        <div style="font-size: 1.1rem; font-weight: 900; letter-spacing: 1px;">LINK ALTERNATIF 4</div>
        <div style="font-size: 0.75rem; color: #ffcc88; margin-top: 8px;">Klik untuk Daftar →</div>
      </a>
      
    </div>
    
    <div style="margin-top: 40px; background: rgba(0,255,157,0.05); border: 1px dashed rgba(0,255,157,0.3); border-radius: 12px; padding: 20px; max-width: 700px; margin-left: auto; margin-right: auto;">
      <div style="font-size: 1.5rem; margin-bottom: 10px;">🎁</div>
      <div style="font-weight: 900; color: #00ff9d; font-size: 1rem; margin-bottom: 8px;">CARA DAPAT AKSES GRATIS</div>
      <div style="font-size: 0.85rem; color: #ccc; line-height: 1.8; text-align: left;">
        <b style="color: #ffaa00;">1.</b> Daftar melalui salah satu link di atas<br>
        <b style="color: #ffaa00;">2.</b> Lakukan deposit pertama (minimal Rp 50.000)<br>
        <b style="color: #ffaa00;">3.</b> Catat UID akun Anda<br>
        <b style="color: #ffaa00;">4.</b> Isi form pendaftaran di bawah dengan UID Anda<br>
        <b style="color: #ffaa00;">5.</b> Admin akan verifikasi & aktifkan akses VIP GRATIS
      </div>
    </div>
  </section>

  <section id="features" class="features">
    <div class="feature">
      <div class="feature-icon">🤖</div>
      <h3>AI Analysis Engine</h3>
      <p>Algoritma neural network menganalisis ribuan pola historis secara real-time untuk memberikan prediksi dengan akurasi tinggi.</p>
    </div>
    <div class="feature">
      <div class="feature-icon">📊</div>
      <h3>Live Statistics</h3>
      <p>Dashboard dengan statistik lengkap: win rate, profit tracking, dan audit log yang bisa diakses kapan saja.</p>
    </div>
    <div class="feature">
      <div class="feature-icon">⚡</div>
      <h3>Auto-Sync System</h3>
      <p>Data ter-sinkronisasi secara otomatis setiap periode tanpa perlu refresh manual.</p>
    </div>
    <div class="feature">
      <div class="feature-icon">🔒</div>
      <h3>Hardware Lock Security</h3>
      <p>Setiap lisensi terkunci ke perangkat Anda. Aman dari penyalahgunaan pihak lain.</p>
    </div>
    <div class="feature">
      <div class="feature-icon">📱</div>
      <h3>Multi-Device Support</h3>
      <p>Akses dari PC, laptop, atau smartphone. Satu lisensi untuk semua perangkat Anda.</p>
    </div>
    <div class="feature">
      <div class="feature-icon">🎯</div>
      <h3>Signal Telegram</h3>
      <p>Terima sinyal prediksi langsung di Telegram, tanpa perlu buka dashboard terus-menerus.</p>
    </div>
  </section>

  <section class="cta-section">
    <h2>Siap Memulai?</h2>
    <p>Daftar sekarang dan dapatkan akses VIP untuk pengalaman bermain yang lebih terukur.</p>
    <div class="btn-group">
      <a href="/register" class="btn btn-primary">🚀 Mulai Sekarang</a>
      <a href="https://t.me/raniwealth" target="_blank" class="btn btn-secondary">💬 Hubungi Admin</a>
    </div>
  </section>

  <div class="footer">
    © 2026 Titanium Omega · Powered by AI Neural Engine
  </div>
</div>
</body>
</html>"""

# ============================================================================
# REGISTRATION
# ============================================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        csrf = generate_csrf_token()
        return render_template_string("""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Daftar Member — Titanium Omega</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: -apple-system, sans-serif; background: #05060a; color: #fff; padding: 40px 20px; min-height: 100vh; background-image: linear-gradient(rgba(255,68,68,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,68,68,0.02) 1px, transparent 1px); background-size: 40px 40px; }
  .box { max-width: 520px; margin:0 auto; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 20px; padding: 40px; box-shadow: 0 20px 60px rgba(0,0,0,0.5); }
  .header { text-align: center; margin-bottom: 30px; }
  .icon { width: 60px; height: 60px; background: linear-gradient(135deg, #ff4444, #ff0088); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; margin: 0 auto 15px; box-shadow: 0 0 30px rgba(255,68,68,0.5); }
  h1 { font-size: 1.3rem; letter-spacing: 2px; margin-bottom: 5px; }
  .desc { color: #888; font-size: 0.8rem; }
  .field { margin-bottom: 18px; }
  label { display: block; color: #aaa; font-size: 0.72rem; font-weight: 700; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 1px; }
  .hint { font-size: 0.65rem; color: #666; margin-top: 5px; display: block; }
  input { width: 100%; padding: 13px 15px; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 10px; font-size: 0.9rem; transition: 0.2s; font-family: inherit; }
  input:focus { outline: none; border-color: #00ff9d; box-shadow: 0 0 0 3px rgba(0,255,157,0.1); }
  button { width: 100%; padding: 15px; background: linear-gradient(135deg, #00ff9d, #00d97e); color: #000; border: none; font-weight: 900; border-radius: 10px; cursor: pointer; font-size: 0.9rem; letter-spacing: 1px; margin-top: 10px; transition: 0.2s; }
  button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,255,157,0.3); }
  .back { text-align: center; margin-top: 20px; }
  .back a { color: #666; font-size: 0.75rem; text-decoration: none; transition: 0.2s; }
  .back a:hover { color: #fff; }
  .alert { background: rgba(255,68,68,0.1); border: 1px solid rgba(255,68,68,0.3); color: #ff6666; padding: 12px; border-radius: 10px; font-size: 0.78rem; margin-bottom: 20px; display: none; }
</style>
</head>
<body>
<div class="box">
  <div class="header">
    <div class="icon">👤</div>
    <h1>PENDAFTARAN MEMBER</h1>
    <p class="desc">Isi data dengan benar. License key akan dikirim setelah approval.</p>
  </div>
  
  <div class="alert" id="alert"></div>
  
  <form method="POST" id="regForm" enctype="multipart/form-data">
    <input type="hidden" name="csrf_token" value="{{ csrf }}">
    
    <div class="field">
      <label>👤 Status Anda</label>
      <select name="member_status" id="memberStatus" required style="width: 100%; padding: 13px 15px; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 10px; font-size: 0.9rem;" onchange="toggleStatus(this.value)">
        <option value="">-- Pilih Status --</option>
        <option value="existing">Saya sudah pernah daftar & deposit di website Anda</option>
        <option value="new">Saya belum pernah daftar (akan daftar dulu)</option>
      </select>
    </div>
    
    <div id="newMemberNotice" style="display: none; background: rgba(255,170,0,0.1); border: 1px solid #ffaa00; color: #ffcc66; padding: 15px; border-radius: 10px; font-size: 0.8rem; margin-bottom: 18px; line-height: 1.6;">
      <b>📌 Silakan daftar dulu via link di bawah:</b><br>
      <a href="https://www.vokzila.com/#/register?invitationCode=78843597" target="_blank" style="color: #00ff9d;">Vokzila</a> · 
      <a href="https://www.nuxpira.com/#/register?invitationCode=78843597" target="_blank" style="color: #00ff9d;">Nuxpira</a> · 
      <a href="https://www.krelmod.com/#/register?invitationCode=78843597" target="_blank" style="color: #00ff9d;">Krelmod</a> · 
      <a href="https://www.gruzeno.com/#/register?invitationCode=78843597" target="_blank" style="color: #00ff9d;">Gruzeno</a><br>
      <span style="font-size: 0.75rem; color: #888;">Setelah daftar & deposit, kembali ke halaman ini dan isi form di bawah.</span>
    </div>
    
    <div class="field">
      <label>🎮 UID Akun Game</label>
      <input name="uid_55five" placeholder="Contoh: 597" required maxlength="50" pattern="[A-Za-z0-9]+" autocomplete="off">
      <span class="hint">ID akun game Anda</span>
    </div>
    
    <div class="field">
      <label>📧 Gmail Aktif</label>
      <input name="email" type="email" placeholder="nama@gmail.com" required maxlength="100" autocomplete="off">
    </div>
    
    <div class="field">
      <label>📱 No. HP WhatsApp</label>
      <input name="phone" placeholder="08xxxxxxxxxx" required maxlength="20" pattern="[0-9+]+" autocomplete="off">
    </div>
    
    <div class="field">
      <label>🔗 Website Referral</label>
      <select name="referral_website" required style="width: 100%; padding: 13px 15px; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 10px; font-size: 0.9rem;">
        <option value="">-- Pilih Website --</option>
        <option value="vokzila">Vokzila (Link Alternatif 1)</option>
        <option value="nuxpira">Nuxpira (Link Alternatif 2)</option>
        <option value="krelmod">Krelmod (Link Alternatif 3)</option>
        <option value="gruzeno">Gruzeno (Link Alternatif 4)</option>
      </select>
    </div>
    
    <div class="field">
      <label>💰 Total Deposit Terakhir</label>
      <input name="deposit_amount" type="number" placeholder="Contoh: 50000" required min="50000" autocomplete="off">
      <span class="hint">Minimal Rp 50.000</span>
    </div>
    
    <div class="field">
      <label>📸 Bukti Deposit (Screenshot)</label>
      <input name="deposit_proof" type="file" accept="image/*" required style="padding: 10px;">
      <span class="hint">Upload screenshot bukti deposit terakhir</span>
    </div>
    
    <button type="submit">🚀 KIRIM PENDAFTARAN</button>
  </form>
  
  <script>
  function toggleStatus(val) {
    const notice = document.getElementById('newMemberNotice');
    notice.style.display = (val === 'new') ? 'block' : 'none';
  }
  </script>
  
  <div class="back">
    <a href="/">← Kembali ke Beranda</a>
  </div>
</div>

<script>
document.getElementById('regForm').addEventListener('submit', function(e) {
    const btn = this.querySelector('button');
    btn.innerText = '⏳ MENGIRIM...';
    btn.disabled = true;
});
</script>
</body>
</html>""", csrf=csrf)

    # POST
    ip = get_client_ip()
    if not validate_csrf(request.form.get("csrf_token")):
        log_security("CSRF_FAIL_REGISTER", ip)
        abort(403)

    uid = sanitize(request.form.get("uid_55five"), 50)
    email = sanitize(request.form.get("email"), 100)
    phone = sanitize(request.form.get("phone"), 20)
    ref_site = sanitize(request.form.get("referral_website"), 20)
    member_status = sanitize(request.form.get("member_status"), 20)
    try:
        deposit_amt = int(request.form.get("deposit_amount", 0))
    except:
        deposit_amt = 0

    if not all([uid, email, phone, ref_site, member_status]):
        abort(400)
    
    if deposit_amt < 50000:
        return "Minimal deposit Rp 50.000 diperlukan untuk verifikasi.", 400
    
    # Simpan bukti deposit
    proof_filename = ""
    if "deposit_proof" in request.files:
        f = request.files["deposit_proof"]
        if f and f.filename:
            safe_name = re.sub(r'[^a-zA-Z0-9._-]', '', f.filename)
            proof_filename = f"proof_{uid}_{int(datetime.now().timestamp())}_{safe_name}"
            proof_dir = "/home/container/static/proofs"
            os.makedirs(proof_dir, exist_ok=True)
            f.save(os.path.join(proof_dir, proof_filename))

    regs = load_db(REGISTRATION_DB)
    rid = f"REG-{int(datetime.now().timestamp())}"
    regs[rid] = {
        "uid": uid, "email": email, "phone": phone,
        "referral_website": ref_site,
        "deposit_amount": deposit_amt,
        "deposit_proof": proof_filename,
        "member_status": member_status,
        "registered_at": datetime.now().isoformat(),
        "ip": ip,
        "status": "PENDING",
        "type": "DOWNLINE_VIP",
        # [PATCH O] UID Lock History untuk audit
        "uid_history": [{"uid": uid, "at": datetime.now().isoformat(), "ip": ip}],
        "violations": []
    }
    save_db(REGISTRATION_DB, regs)
    log_security("NEW_REGISTRATION", ip, f"uid={uid}")
    
    # Halaman sukses yang lebih rapi
    return """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Pendaftaran Berhasil</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family: -apple-system, sans-serif; background: #05060a; color: #fff; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
  .box { max-width: 500px; background: rgba(0,255,157,0.05); border: 1px solid rgba(0,255,157,0.3); border-radius: 20px; padding: 50px 40px; text-align: center; box-shadow: 0 20px 60px rgba(0,255,157,0.1); }
  .check { width: 80px; height: 80px; background: linear-gradient(135deg, #00ff9d, #00d97e); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 2.5rem; margin: 0 auto 25px; box-shadow: 0 0 40px rgba(0,255,157,0.5); animation: pop 0.5s ease-out; }
  @keyframes pop { 0% { transform: scale(0); } 80% { transform: scale(1.1); } 100% { transform: scale(1); } }
  h1 { color: #00ff9d; font-size: 1.5rem; margin-bottom: 15px; }
  p { color: #aaa; line-height: 1.7; margin-bottom: 10px; }
  .steps { background: rgba(0,0,0,0.3); border-radius: 12px; padding: 20px; margin: 25px 0; text-align: left; }
  .step { display: flex; gap: 12px; margin-bottom: 12px; font-size: 0.85rem; }
  .step:last-child { margin-bottom: 0; }
  .step-num { background: #00ff9d; color: #000; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 0.7rem; flex-shrink: 0; }
  .btn { display: inline-block; padding: 13px 25px; background: #00ff9d; color: #000; text-decoration: none; border-radius: 10px; font-weight: 700; margin-top: 15px; transition: 0.2s; }
  .btn:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,255,157,0.3); }
</style>
</head>
<body>
<div class="box">
  <div class="check">✅</div>
  <h1>Pendaftaran Diterima!</h1>
  <p>Terima kasih telah mendaftar. Data Anda sedang diproses oleh admin.</p>
  
  <div class="steps">
    <div class="step"><span class="step-num">1</span><span>Chat bot Telegram: <b>@titan_member_notif_bot</b></span></div>
    <div class="step"><span class="step-num">2</span><span>Kirim perintah: <b>/daftar UID_ANDA</b></span></div>
    <div class="step"><span class="step-num">3</span><span>Tunggu approval admin (5-30 menit)</span></div>
    <div class="step"><span class="step-num">4</span><span>License Key otomatis masuk ke Telegram Anda!</span></div>
  </div>
  
  <p style="font-size: 0.8rem;">Estimasi approval: <b style="color: #ffaa00;">5-30 menit</b></p>
  
  <a href="/" class="btn">← Kembali ke Beranda</a>
</div>
</body>
</html>"""

# ============================================================================
# OWNER SETTINGS API — [PATCH A1.3]
# ============================================================================
SETTINGS_FILE = "/home/container/owner_settings.json"

_DEFAULT_SETTINGS_CS = {
    "alt_link_55five": "https://www.vokzila.com",
    "alt_link_backup": "https://www.nuxpira.com",
    "force_autobet": False,
    "default_bet_amount": 1000
}

def _load_settings_cs():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
            return {**_DEFAULT_SETTINGS_CS, **data}
    except: pass
    return dict(_DEFAULT_SETTINGS_CS)

def _save_settings_cs(data):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except: return False

@app.route('/api/settings/get', methods=['GET'])
def api_settings_get_cs():
    """[PATCH A1.3] Get settings (public)"""
    try:
        settings = _load_settings_cs()
        return jsonify({
            "status": "ok",
            "alt_link_55five": settings.get("alt_link_55five", ""),
            "alt_link_backup": settings.get("alt_link_backup", ""),
            "force_autobet": settings.get("force_autobet", False),
            "default_bet_amount": settings.get("default_bet_amount", 1000),
            "updated_at": settings.get("updated_at", None)
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route('/api/settings/update', methods=['POST'])
def api_settings_update_cs():
    """[PATCH A1.3] Update settings — owner only"""
    try:
        admin_key = request.args.get('key', '')
        OWNER_MASTER_KEY = _SECRETS.get("OWNER_MASTER_KEY", "")
        if not admin_key or admin_key != OWNER_MASTER_KEY:
            log_security("SETTINGS_UNAUTHORIZED", get_client_ip(), "attempted settings update")
            return jsonify({"status": "error", "msg": "Unauthorized"}), 403
        
        data = request.json or {}
        current = _load_settings_cs()
        
        if "alt_link_55five" in data:
            url = str(data["alt_link_55five"]).strip()
            if url and (url.startswith("http://") or url.startswith("https://")):
                current["alt_link_55five"] = url
            else:
                return jsonify({"status": "error", "msg": "Invalid URL format"}), 400
        
        if "alt_link_backup" in data:
            url = str(data["alt_link_backup"]).strip()
            if url and (url.startswith("http://") or url.startswith("https://")):
                current["alt_link_backup"] = url
        
        if "force_autobet" in data:
            current["force_autobet"] = bool(data["force_autobet"])
        
        if "default_bet_amount" in data:
            try:
                current["default_bet_amount"] = max(400, int(data["default_bet_amount"]))
            except: pass
        
        # [PATCH A2.3] Force mode setting
        if "force_mode" in data:
            mode = str(data["force_mode"]).strip().lower()
            if mode in ("1m", "3m", "5m", "off"):
                current["force_mode"] = mode
                log_security("MODE_CHANGED", get_client_ip(), f"force_mode={mode}")
        
        if "auto_reset_sync" in data:
            current["auto_reset_sync"] = bool(data["auto_reset_sync"])
        
        from datetime import datetime as _dt_cs
        current["updated_at"] = _dt_cs.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if _save_settings_cs(current):
            log_security("SETTINGS_UPDATED", get_client_ip(), f"link={current.get('alt_link_55five','')[:40]}")
            return jsonify({"status": "ok", "settings": current, "msg": "Settings saved"})
        return jsonify({"status": "error", "msg": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

# ============================================================================
# VERIFY API
# ============================================================================
# ============================================================
# [PATCH G7.1] AUTO-EXPIRE LICENSE BAWAHAN (30 hari no deposit)
# ============================================================
DOWNLINE_EXPIRE_DAYS = 30
AUTOEXPIRE_CHECK_INTERVAL = 6 * 3600  # 6 jam

def _auto_expire_downline_check():
    """Cek semua license bawahan yang tidak depo > 30 hari, auto-suspend."""
    try:
        lics = load_db(LICENSE_DB)
        if not lics:
            return 0
        
        from datetime import datetime, timedelta
        now = datetime.now()
        expired_count = 0
        to_notify = []
        
        for key, lic in lics.items():
            # Skip yang sudah inactive
            if not lic.get("active", True):
                continue
            
            # Skip license bukan bawahan (misalnya VIP berbayar)
            lic_type = str(lic.get("type", "")).upper()
            if "BAWAHAN" not in lic_type and "DOWNLINE" not in lic_type:
                # Cek juga via buyer_name pattern — kalau ada
                # Default treat sebagai bawahan kalau tidak ada flag khusus
                pass
            
            # Cek last_deposit_at
            lda = lic.get("last_deposit_at")
            if not lda:
                # Belum pernah di-set → skip (jangan suspend, biar owner set dulu)
                continue
            
            try:
                lda_dt = datetime.strptime(lda, "%Y-%m-%d %H:%M:%S") if len(lda) > 10 else datetime.strptime(lda, "%Y-%m-%d")
            except:
                try:
                    lda_dt = datetime.strptime(lda[:10], "%Y-%m-%d")
                except:
                    continue
            
            days_since = (now - lda_dt).days
            if days_since > DOWNLINE_EXPIRE_DAYS:
                # Auto-suspend
                lic["active"] = False
                lic["suspended_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
                lic["suspended_reason"] = f"Auto-expired: no deposit for {days_since} days (last: {lda[:10]})"
                lic["auto_expired"] = True
                expired_count += 1
                to_notify.append({
                    "uid": lic.get("account_id", "?"),
                    "days": days_since,
                    "last": lda[:10],
                    "key_prefix": key[:30]
                })
                log_security("AUTO_EXPIRE", "system", f"key={key[:20]}, uid={lic.get('account_id')}, days={days_since}")
        
        if expired_count > 0:
            save_db(LICENSE_DB, lics)
            print(f"[G7-AUTOEXPIRE] {expired_count} license auto-suspended")
            # Notif owner
            try:
                import requests as _req_ae
                notify_text = f"🚫 <b>AUTO-EXPIRE: {expired_count} LICENSE BAWAHAN</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                for n in to_notify[:10]:
                    notify_text += f"• UID <code>{n['uid']}</code> — {n['days']} hari no depo (last: {n['last']})\n"
                if len(to_notify) > 10:
                    notify_text += f"\n<i>... dan {len(to_notify) - 10} lainnya</i>"
                notify_text += "\n\n💡 Buka admin panel untuk re-activate atau update tanggal depo."
                
                # Kirim ke channel owner
                token = ""
                chat_id = ""
                try:
                    if os.path.exists("titan_config.json"):
                        with open("titan_config.json") as _f:
                            _cfg = json.load(_f)
                            token = _cfg.get("tg_config", {}).get("token", "")
                            chat_id = _cfg.get("tg_config", {}).get("chat_id", "")
                except: pass
                
                if token and chat_id:
                    _req_ae.post(f"https://api.telegram.org/bot{token}/sendMessage",
                                 json={"chat_id": chat_id, "text": notify_text, "parse_mode": "HTML"},
                                 timeout=10)
            except Exception as _ne:
                print(f"[G7] Notif error: {_ne}")
        
        return expired_count
    except Exception as e:
        print(f"[G7-AUTOEXPIRE] Error: {e}")
        return 0


def _auto_expire_worker():
    """Background thread untuk cek auto-expire tiap 6 jam."""
    import time as _t_ae
    _t_ae.sleep(120)  # Tunggu 2 menit pertama
    while True:
        try:
            _auto_expire_downline_check()
        except Exception as _e:
            print(f"[G7-WORKER] Error: {_e}")
        _t_ae.sleep(AUTOEXPIRE_CHECK_INTERVAL)


# Jalankan worker thread
try:
    import threading as _th_ae
    _th_ae.Thread(target=_auto_expire_worker, daemon=True).start()
    print("[G7] Auto-expire worker started ✅ (cek tiap 6 jam)")
except Exception as _e:
    print(f"[G7] Worker error: {_e}")


# Endpoint: Owner update tanggal depo terakhir member
@app.route('/api/admin/update_deposit', methods=['POST'])
def api_admin_update_deposit():
    """[PATCH G7.1] Owner update tanggal depo terakhir member."""
    try:
        data = request.json or {}
        admin_key = str(data.get("key", "")).strip()
        key = str(data.get("license_key", "")).strip()
        
        OWNER_MASTER_KEY = _SECRETS.get("OWNER_MASTER_KEY", "")
        if admin_key != OWNER_MASTER_KEY:
            return jsonify({"status": "error", "msg": "Unauthorized"}), 403
        
        if not key:
            return jsonify({"status": "error", "msg": "license_key required"}), 400
        
        lics = load_db(LICENSE_DB)
        if key not in lics:
            return jsonify({"status": "error", "msg": "License not found"}), 404
        
        from datetime import datetime as _dt_dep, timedelta as _td_dep
        now = _dt_dep.now()
        # Custom tanggal atau default hari ini
        deposit_date = str(data.get("deposit_date", "")).strip()
        if deposit_date:
            try:
                _dt_dep.strptime(deposit_date, "%Y-%m-%d")
                new_date = deposit_date
            except:
                return jsonify({"status": "error", "msg": "Format tanggal salah. Pakai YYYY-MM-DD"}), 400
        else:
            new_date = now.strftime("%Y-%m-%d %H:%M:%S")
        
        lics[key]["last_deposit_at"] = new_date
        lics[key]["active"] = True  # Re-activate
        lics[key]["auto_expired"] = False
        lics[key].pop("suspended_at", None)
        lics[key].pop("suspended_reason", None)
        # Perpanjang expiry +30 hari
        try:
            old_expiry = _dt_dep.strptime(lics[key].get("expiry", "2030-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
            new_expiry = (now + _td_dep(days=DOWNLINE_EXPIRE_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
            lics[key]["expiry"] = new_expiry
        except: pass
        
        save_db(LICENSE_DB, lics)
        log_security("DEPOSIT_UPDATED", get_client_ip(), f"key={key[:30]}, date={new_date}")
        
        return jsonify({
            "status": "ok",
            "msg": f"Deposit updated. License aktif sampai {lics[key].get('expiry', '')}",
            "last_deposit_at": new_date,
            "expiry": lics[key].get("expiry", "")
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500


# Endpoint: Manual run auto-expire check (untuk test)
@app.route('/api/admin/run_autoexpire', methods=['POST'])
def api_admin_run_autoexpire():
    """[PATCH G7.1] Manual trigger auto-expire check."""
    try:
        data = request.json or {}
        admin_key = str(data.get("key", "")).strip()
        OWNER_MASTER_KEY = _SECRETS.get("OWNER_MASTER_KEY", "")
        if admin_key != OWNER_MASTER_KEY:
            return jsonify({"status": "error", "msg": "Unauthorized"}), 403
        
        count = _auto_expire_downline_check()
        return jsonify({"status": "ok", "expired_count": count, "msg": f"{count} license di-suspend"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route('/api/central_verify', methods=['POST'])
def central_verify():
    ip = get_client_ip()
    d = request.json or {}
    key = str(d.get("key", "")).strip()[:200]
    acc = str(d.get("account_id", "")).strip()[:50]
    hwid = str(d.get("hwid", "")).strip()[:64]

    lics = load_db(LICENSE_DB)
    if key not in lics:
        log_security("VERIFY_FAIL_NOTFOUND", ip, f"key={key[:20]}")
        return jsonify({"status": "error", "msg": "License not found"}), 404
    lic = lics[key]
    if not lic.get("active", True):
        log_security("VERIFY_FAIL_SUSPENDED", ip)
        return jsonify({"status": "error", "msg": "Suspended"}), 403
    if lic.get("account_id") and lic["account_id"] != acc:
        log_security("VERIFY_FAIL_UID", ip)
        return jsonify({"status": "error", "msg": "UID mismatch"}), 403
    # [PATCH D2] Device tracking — max 3 devices per license
    devices = lic.get("devices", [])
    # Migrate: kalau ada hwid tapi belum ada devices
    if not devices and lic.get("hwid") and lic["hwid"] != "ANYHWID":
        devices = [str(lic["hwid"]).upper()]
        lic["devices"] = devices
        lics[key] = lic
        save_db(LICENSE_DB, lics)
    
    hwid_upper = str(hwid[:12]).upper()
    saved_hwid = lic.get("hwid")
    
    # Kalau license pakai ANYHWID → izinkan, tapi track device
    if not saved_hwid or saved_hwid == "ANYHWID":
        if hwid_upper and hwid_upper not in devices:
            if len(devices) >= 3:
                log_security("DEVICE_LIMIT_HIT", ip, f"key={key[:20]}, count={len(devices)}")
                return jsonify({"status": "error", "msg": "Device limit tercapai (max 3). Hubungi admin @raniwealth"}), 403
            devices.append(hwid_upper)
            lic["devices"] = devices
            lics[key] = lic
            save_db(LICENSE_DB, lics)
    else:
        # HWID spesifik — cek device list
        if hwid_upper != str(saved_hwid).upper() and hwid_upper not in devices:
            if len(devices) >= 2:
                log_security("DEVICE_LIMIT_HIT", ip, f"key={key[:20]}, count={len(devices)}")
                return jsonify({"status": "error", "msg": "Device limit tercapai (max 2). Hubungi admin @raniwealth"}), 403
            devices.append(hwid_upper)
            lic["devices"] = devices
            lics[key] = lic
            save_db(LICENSE_DB, lics)
    return jsonify({"status": "ok", "msg": "Valid",
                    "license": {"expiry": lic.get("expiry"),
                                "buyer_name": lic.get("buyer_name", "MEMBER")}})

# ============================================================================
# DOWNLOAD
# ============================================================================
@app.route('/download')
def download():
    exe_path = normalize_and_rename()
    if exe_path and os.path.exists(exe_path):
        return send_file(exe_path, as_attachment=True, download_name=EXE_TARGET)
    return "Software belum dirilis.", 404

# ============================================================================
# TELEGRAM MEMBER BOT WEBHOOK
# ============================================================================
def is_member_of_chat(chat_id, user_id):
    """Cek apakah user sudah join channel/grup"""
    try:
        import requests as _req
        r = _req.get(
            f"https://api.telegram.org/bot{MEMBER_BOT_TOKEN}/getChatMember",
            params={"chat_id": chat_id, "user_id": user_id},
            timeout=5
        )
        if r.ok:
            result = r.json().get("result", {})
            status = result.get("status", "")
            return status in ["creator", "administrator", "member", "restricted"]
    except: pass
    return False

def send_force_join(chat_id, name="Member"):
    """Kirim pesan wajib join channel"""
    rows = []
    for ch in FORCE_CHANNELS:
        rows.append([{"text": ch["name"], "url": ch["url"]}])
    rows.append([{"text": "✅ Sudah Join, Cek Ulang", "callback_data": "check_join"}])
    
    markup = {"inline_keyboard": rows}
    text = f"""👋 Halo <b>{name}</b>!

<b>🔒 AKSES TERKUNCI</b>

Untuk menggunakan bot ini, Anda wajib bergabung dengan channel & grup kami terlebih dahulu.

<b>📌 Silakan join:</b>
"""
    for ch in FORCE_CHANNELS:
        text += f"\n• {ch['name']}"
    
    text += "\n\n<b>Setelah join, klik tombol ✅ di bawah untuk verifikasi.</b>"
    
    try:
        import requests as _req
        _req.post(
            f"https://api.telegram.org/bot{MEMBER_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "reply_markup": markup},
            timeout=10
        )
    except: pass

def send_main_menu(chat_id, name="Member", first_time=False):
    """Kirim menu utama dengan tombol"""
    markup = {
        "inline_keyboard": [
            [{"text": "📝 Daftar VIP", "callback_data": "menu_daftar"}],
            [{"text": "📊 Cek Status", "callback_data": "menu_status"}],
            [{"text": "🔑 Lupa Akses", "callback_data": "menu_forgot"}],
            [{"text": "📖 Bantuan", "callback_data": "menu_help"}],
            [{"text": "📢 Channel Prediksi", "url": FORCE_CHANNELS[0]["url"]}],
        ]
    }
    
    if first_time:
        text = f"""🎉 <b>Selamat Datang di TITANIUM OMEGA, {name}!</b>

<b>🤖 BOT MEMBER VIP</b>

Bot ini untuk notifikasi otomatis saat akun VIP Anda disetujui.

━━━━━━━━━━━━━━━━━━━━
<b>✨ FITUR:</b>
• 📝 Daftar & kaitkan akun game
• 📊 Cek status pendaftaran real-time
• 🔑 Kirim ulang License Key ke Telegram
• 📢 Update sinyal & info

━━━━━━━━━━━━━━━━━━━━
<b>👇 Pilih menu di bawah:</b>"""
    else:
        text = f"👋 <b>Halo {name}!</b>\n\nPilih menu di bawah:"
    
    try:
        import requests as _req
        _req.post(
            f"https://api.telegram.org/bot{MEMBER_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "reply_markup": markup},
            timeout=10
        )
    except: pass

def answer_callback(callback_id, text=""):
    """Answer callback query"""
    try:
        import requests as _req
        _req.post(
            f"https://api.telegram.org/bot{MEMBER_BOT_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": text},
            timeout=5
        )
    except: pass

@app.route('/webhook/tg-member', methods=['POST'])
def webhook_tg_member():
    """Terima pesan dari member bot Telegram"""
    try:
        update = request.json or {}
        
        # === HANDLE CALLBACK (tombol) ===
        if "callback_query" in update:
            cb = update["callback_query"]
            chat_id = cb["message"]["chat"]["id"]
            user_id = cb["from"]["id"]
            data = cb.get("data", "")
            name = cb["from"].get("first_name", "Member")
            
            # Cek force join dulu
            if FORCE_JOIN_ENABLED and data != "check_join":
                missing = []
                for ch in FORCE_CHANNELS:
                    if not is_member_of_chat(ch["id"], user_id):
                        missing.append(ch["name"])
                if missing:
                    answer_callback(cb["id"], "❌ Belum join semua channel!")
                    send_force_join(chat_id, name)
                    return jsonify({"ok": True})
            
            # Route callback
            if data == "check_join":
                missing = []
                for ch in FORCE_CHANNELS:
                    if not is_member_of_chat(ch["id"], user_id):
                        missing.append(ch["name"])
                if missing:
                    answer_callback(cb["id"], "❌ Masih ada yang belum di-join")
                    send_force_join(chat_id, name)
                else:
                    answer_callback(cb["id"], "✅ Verifikasi berhasil!")
                    send_main_menu(chat_id, name, first_time=True)
            
            elif data == "menu_daftar":
                answer_callback(cb["id"])
                send_member_tg(chat_id, """📝 <b>DAFTAR / KAITKAN AKUN</b>

Untuk mengaitkan akun game Anda dengan Telegram ini, kirim perintah:

<code>/daftar UID_ANDA</code>

<b>Contoh:</b> <code>/daftar 4564</code>

━━━━━━━━━━━━━━━━━━━━
<b>💡 Info:</b>
• UID adalah ID akun game Anda
• Pastikan Anda sudah daftar di https://autog.my.id/register
• Setelah dikaitkan, License Key akan dikirim otomatis ke chat ini""")
            
            elif data == "menu_status":
                answer_callback(cb["id"])
                send_member_tg(chat_id, """📊 <b>CEK STATUS</b>

Kirim perintah:
<code>/status UID_ANDA</code>

<b>Contoh:</b> <code>/status 4564</code>

Bot akan cek status pendaftaran Anda secara real-time.""")
            
            elif data == "menu_forgot":
                answer_callback(cb["id"])
                send_member_tg(chat_id, """🔑 <b>LUPA AKSES</b>

Kirim perintah:
<code>/lupa UID_ANDA</code>

<b>Contoh:</b> <code>/lupa 4564</code>

License Key akan dikirim ulang ke chat ini (kalau akun sudah approved).""")
            
            elif data == "menu_back":
                answer_callback(cb["id"])
                send_main_menu(chat_id, name)
            
            elif data == "menu_help":
                answer_callback(cb["id"])
                send_member_tg(chat_id, """📖 <b>BANTUAN</b>

<b>Perintah tersedia:</b>
• /start — Menu utama
• /daftar UID — Kaitkan akun
• /status UID — Cek status
• /lupa UID — Kirim ulang License Key
• /help — Menu ini

━━━━━━━━━━━━━━━━━━━━
<b>❓ Butuh bantuan?</b>
Hubungi: @raniwealth""")
            
            return jsonify({"ok": True})
        
        # === HANDLE MESSAGE (teks biasa) ===
        if "message" not in update:
            return jsonify({"ok": True})
        
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = (msg.get("text") or "").strip()
        name = msg["chat"].get("first_name", "Member")
        
        # === CEK FORCE JOIN UNTUK SEMUA PERINTAH ===
        if FORCE_JOIN_ENABLED:
            missing = []
            for ch in FORCE_CHANNELS:
                if not is_member_of_chat(ch["id"], user_id):
                    missing.append(ch["name"])
            if missing:
                send_force_join(chat_id, name)
                return jsonify({"ok": True})
        
        if text.startswith("/start"):
            send_main_menu(chat_id, name, first_time=True)
        
        elif text.startswith("/daftar"):
            parts = text.split()
            if len(parts) < 2:
                send_member_tg(chat_id, "❌ Format salah.\n\nContoh: <code>/daftar 4564</code>")
            else:
                uid = parts[1].strip()
                rid, reg = find_reg_by_uid(uid)
                
                if not rid:
                    send_member_tg(chat_id, f"❌ UID <b>{uid}</b> tidak ditemukan.\n\nPastikan Anda sudah daftar di:\nhttps://autog.my.id/register")
                else:
                    # Simpan chat_id ke registrasi
                    regs = load_db(REGISTRATION_DB)
                    regs[rid]["telegram_chat_id"] = chat_id
                    regs[rid]["telegram_name"] = name
                    save_db(REGISTRATION_DB, regs)
                    
                    status = reg.get("status", "PENDING")
                    if status == "APPROVED":
                        key = reg.get("license_key", "")
                        lics = load_db(LICENSE_DB)
                        expiry = lics.get(key, {}).get("expiry", "-")
                        send_member_tg(chat_id, f"""✅ <b>UID {uid} sudah AKTIF!</b>

🔑 License Key:
<code>{key}</code>

📅 Expiry: <b>{expiry}</b>""")
                        # Kirim tombol akses
                        try:
                            import requests as _req
                            _req.post(
                                f"https://api.telegram.org/bot{MEMBER_BOT_TOKEN}/sendMessage",
                                json={
                                    "chat_id": chat_id,
                                    "text": "👇 Klik tombol untuk akses:",
                                    "reply_markup": {"inline_keyboard": [
                                        [{"text": "📱 Buka Dashboard Member", "url": f"https://bot.autog.my.id/member?key={key}"}],
                                        [{"text": "🔙 Menu Utama", "callback_data": "menu_back"}]
                                    ]}
                                },
                                timeout=10
                            )
                        except: pass
                    else:
                        send_member_tg(chat_id, f"""✅ UID <b>{uid}</b> berhasil dikaitkan.

Status: <b>{status}</b>

Tunggu approval dari admin. Anda akan menerima License Key otomatis di chat ini.""")
        
        elif text.startswith("/status"):
            parts = text.split()
            if len(parts) < 2:
                send_member_tg(chat_id, "Format: <code>/status UID_ANDA</code>")
            else:
                uid = parts[1].strip()
                rid, reg = find_reg_by_uid(uid)
                if not reg:
                    send_member_tg(chat_id, f"❌ UID {uid} tidak ditemukan.")
                else:
                    status = reg.get("status", "PENDING")
                    if status == "APPROVED":
                        key = reg.get("license_key", "")
                        send_member_tg(chat_id, f"""✅ <b>APPROVED</b>

👤 UID: <b>{uid}</b>
🔑 Key: <code>{key}</code>

📱 bot.autog.my.id/member?key={key}""")
                    elif status == "REJECTED":
                        reason = reg.get("reject_reason", "Tidak memenuhi syarat")
                        send_member_tg(chat_id, f"""❌ <b>REJECTED</b>

👤 UID: <b>{uid}</b>
📝 Alasan: {reason}""")
                    else:
                        send_member_tg(chat_id, f"""⏳ <b>PENDING</b>

👤 UID: <b>{uid}</b>

Tunggu approval admin.""")
        
        elif text.startswith("/lupa"):
            parts = text.split()
            if len(parts) < 2:
                send_member_tg(chat_id, "📝 Format: <code>/lupa UID_ANDA</code>\n\nContoh: <code>/lupa 4564</code>")
            else:
                uid = parts[1].strip()
                rid, reg = find_reg_by_uid(uid)
                if not reg:
                    send_member_tg(chat_id, f"❌ UID <b>{uid}</b> tidak ditemukan.")
                else:
                    status = reg.get("status", "PENDING")
                    if status == "APPROVED":
                        key = reg.get("license_key", "")
                        lics = load_db(LICENSE_DB)
                        expiry = lics.get(key, {}).get("expiry", "-")
                        send_member_tg(chat_id, f"""🔑 <b>AKSES ANDA</b>

👤 UID: <b>{uid}</b>
🔑 License Key:
<code>{key}</code>

📅 Expiry: <b>{expiry}</b>

📱 <a href="https://bot.autog.my.id/member?key={key}">Klik untuk akses Dashboard</a>""")
                    elif status == "REJECTED":
                        send_member_tg(chat_id, f"❌ Akun Anda di-reject.\n\nAlasan: {reg.get('reject_reason', '-')}")
                    else:
                        send_member_tg(chat_id, f"⏳ Akun Anda masih <b>PENDING</b>.\n\nTunggu approval admin.")
        
        elif text.startswith("/help"):
            send_member_tg(chat_id, """📖 <b>PERINTAH TERSEDIA</b>

/start - Menu utama
/daftar UID - Kaitkan akun
/status UID - Cek status
/lupa UID - Kirim ulang License Key
/help - Menu ini

❓ Support: @raniwealth""")
        
        return jsonify({"ok": True})
    except Exception as e:
        print(f"[WEBHOOK ERROR] {e}")
        return jsonify({"ok": True})

# ============================================================================
# PUBLIC: CEK STATUS PENDAFTARAN
# ============================================================================
@app.route('/status')
def check_status_public():
    return render_template_string("""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cek Status — Titanium Omega</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#05060a;color:#fff;padding:40px 20px;min-height:100vh;background-image:linear-gradient(rgba(0,255,157,0.02) 1px,transparent 1px),linear-gradient(90deg,rgba(0,255,157,0.02) 1px,transparent 1px);background-size:40px 40px}
.box{max-width:520px;margin:0 auto;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:20px;padding:40px;box-shadow:0 20px 60px rgba(0,0,0,0.5)}
h1{font-size:1.3rem;letter-spacing:2px;margin-bottom:8px;text-align:center;color:#00ff9d}
.desc{color:#888;font-size:0.8rem;text-align:center;margin-bottom:25px}
label{display:block;color:#aaa;font-size:0.72rem;font-weight:700;margin-bottom:6px;text-transform:uppercase;letter-spacing:1px}
input{width:100%;padding:14px;background:#0d1117;border:1px solid #30363d;color:#fff;border-radius:10px;font-size:0.95rem;margin-bottom:15px}
input:focus{outline:none;border-color:#00ff9d;box-shadow:0 0 0 3px rgba(0,255,157,0.1)}
button{width:100%;padding:15px;background:linear-gradient(135deg,#00ff9d,#00d97e);color:#000;border:none;font-weight:900;border-radius:10px;cursor:pointer;font-size:0.9rem;letter-spacing:1px}
button:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(0,255,157,0.3)}
.back{text-align:center;margin-top:20px}
.back a{color:#666;font-size:0.75rem;text-decoration:none}
#result{display:none;margin-top:20px;padding:18px;border-radius:12px;font-size:0.85rem;line-height:1.6}
.status-pending{background:rgba(234,179,8,0.1);border:1px solid #eab308;color:#facc15}
.status-approved{background:rgba(0,255,157,0.1);border:1px solid #00ff9d;color:#00ff9d}
.status-rejected{background:rgba(255,68,68,0.1);border:1px solid #ff4444;color:#ff8888}
</style>
</head>
<body>
<div class="box">
<h1>📋 CEK STATUS PENDAFTARAN</h1>
<p class="desc">Masukkan UID Game Anda untuk cek status</p>

<label>🎮 UID Game</label>
<input type="text" id="uid" placeholder="Contoh: 4564" autocomplete="off">
<button onclick="checkStatus()">🔍 CEK STATUS</button>

<div id="result"></div>

<div class="back"><a href="/">← Kembali ke Beranda</a></div>
</div>

<script>
async function checkStatus() {
    const uid = document.getElementById('uid').value.trim();
    if (!uid) { alert('Isi UID dulu!'); return; }
    const r = document.getElementById('result');
    r.style.display = 'block';
    r.className = '';
    r.innerText = '⏳ Memeriksa...';
    
    try {
        const res = await fetch('/api/check_status?uid=' + encodeURIComponent(uid));
        const d = await res.json();
        
        if (d.status === 'PENDING') {
            r.className = 'status-pending';
            r.innerHTML = '<b>⏳ MENUNGGU APPROVAL</b><br><br>UID: <b>' + uid + '</b><br>Waktu daftar: ' + (d.registered_at || '-') + '<br><br>Mohon tunggu admin mereview data Anda (5-30 menit).';
        } else if (d.status === 'APPROVED') {
            r.className = 'status-approved';
            r.innerHTML = '<b>✅ AKUN VIP ANDA AKTIF</b><br><br>UID: <b>' + uid + '</b><br>🔑 License Key:<br><code style="background:#000;padding:8px;border-radius:6px;display:block;margin:8px 0;font-size:0.7rem;word-break:break-all">' + (d.license_key || '-') + '</code><br>📅 Expiry: ' + (d.expiry || '-') + '<br><br><a href="https://bot.autog.my.id/member?key=' + d.license_key + '" style="color:#00ff9d;font-weight:bold">→ BUKA DASHBOARD MEMBER</a>';
        } else if (d.status === 'REJECTED') {
            r.className = 'status-rejected';
            r.innerHTML = '<b>❌ PENDAFTARAN DITOLAK</b><br><br>UID: <b>' + uid + '</b><br>Alasan: ' + (d.reason || 'Tidak memenuhi syarat') + '<br><br>Hubungi admin untuk info lebih lanjut: @raniwealth';
        } else {
            r.className = 'status-rejected';
            r.innerText = d.msg || 'UID tidak ditemukan';
        }
    } catch(e) {
        r.className = 'status-rejected';
        r.innerText = '⚠️ Gagal koneksi. Coba lagi.';
    }
}
</script>
</body>
</html>""")

@app.route('/api/check_status')
def api_check_status():
    uid = request.args.get('uid', '').strip()
    if not uid:
        return jsonify({"status": "error", "msg": "UID required"}), 400
    
    rid, reg = find_reg_by_uid(uid)
    if not reg:
        return jsonify({"status": "NOT_FOUND", "msg": "UID tidak ditemukan"}), 404
    
    status = reg.get("status", "PENDING")
    result = {
        "status": status,
        "registered_at": reg.get("registered_at", "")[:19],
        "license_key": reg.get("license_key", ""),
        "expiry": ""
    }
    
    if status == "REJECTED":
        result["reason"] = reg.get("reject_reason", "")
    elif status == "APPROVED":
        # Ambil expiry dari license DB
        lics = load_db(LICENSE_DB)
        key = reg.get("license_key", "")
        if key in lics:
            result["expiry"] = lics[key].get("expiry", "")
    
    return jsonify(result)

# ============================================================================
# PUBLIC: LUPA AKSES
# ============================================================================
@app.route('/forgot')
def forgot_access():
    return render_template_string("""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lupa Akses — Titanium Omega</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#05060a;color:#fff;padding:40px 20px;min-height:100vh}
.box{max-width:520px;margin:0 auto;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:20px;padding:40px}
h1{font-size:1.3rem;letter-spacing:2px;margin-bottom:8px;text-align:center;color:#ffaa00}
.desc{color:#888;font-size:0.8rem;text-align:center;margin-bottom:25px}
label{display:block;color:#aaa;font-size:0.72rem;font-weight:700;margin-bottom:6px;text-transform:uppercase;letter-spacing:1px}
input{width:100%;padding:14px;background:#0d1117;border:1px solid #30363d;color:#fff;border-radius:10px;font-size:0.95rem;margin-bottom:15px}
input:focus{outline:none;border-color:#ffaa00}
button{width:100%;padding:15px;background:linear-gradient(135deg,#ffaa00,#ff8c00);color:#000;border:none;font-weight:900;border-radius:10px;cursor:pointer;font-size:0.9rem;letter-spacing:1px}
.back{text-align:center;margin-top:20px}
.back a{color:#666;font-size:0.75rem;text-decoration:none}
#result{display:none;margin-top:20px;padding:18px;border-radius:12px;font-size:0.85rem;line-height:1.6;background:rgba(0,170,255,0.1);border:1px solid #00aaff;color:#88ccff}
.info{background:rgba(255,170,0,0.08);border-left:3px solid #ffaa00;padding:12px 15px;border-radius:6px;margin-bottom:20px;font-size:0.8rem;line-height:1.6;color:#ccc}
</style>
</head>
<body>
<div class="box">
<h1>🔐 LUPA AKSES</h1>
<p class="desc">Kirim ulang License Key ke Telegram Anda</p>

<div class="info">
<b>📌 Cara Pakai:</b><br>
1. Pastikan Anda sudah chat bot Telegram <b>@titan_member_notif_bot</b><br>
2. Dan kirim <code>/daftar UID_ANDA</code> ke bot tersebut<br>
3. Isi form di bawah, kunci akan dikirim ke Telegram Anda
</div>

<label>🎮 UID Game Anda</label>
<input type="text" id="uid" placeholder="Contoh: 4564" autocomplete="off">
<button onclick="requestReset()">📤 KIRIM KE TELEGRAM</button>

<div id="result"></div>

<div class="back"><a href="/">← Kembali ke Beranda</a></div>
</div>

<script>
async function requestReset() {
    const uid = document.getElementById('uid').value.trim();
    if (!uid) { alert('Isi UID dulu!'); return; }
    const r = document.getElementById('result');
    r.style.display = 'block';
    r.innerText = '⏳ Memproses...';
    
    try {
        const res = await fetch('/api/forgot_access?uid=' + encodeURIComponent(uid));
        const d = await res.json();
        r.innerText = d.msg || 'Permintaan diproses.';
    } catch(e) {
        r.innerText = '⚠️ Gagal koneksi. Coba lagi.';
    }
}
</script>
</body>
</html>""")

@app.route('/api/forgot_access')
def api_forgot_access():
    uid = request.args.get('uid', '').strip()
    if not uid:
        return jsonify({"msg": "❌ UID wajib diisi"})
    
    rid, reg = find_reg_by_uid(uid)
    if not reg:
        return jsonify({"msg": f"❌ UID {uid} tidak ditemukan."})
    
    chat_id = reg.get("telegram_chat_id")
    if not chat_id:
        return jsonify({"msg": f"⚠️ UID {uid} belum dikaitkan dengan Telegram.\n\nSilakan chat bot @{MEMBER_BOT_USERNAME} dan kirim:\n/daftar {uid}"})
    
    status = reg.get("status", "PENDING")
    if status == "APPROVED":
        key = reg.get("license_key", "")
        msg = f"""🔑 <b>RESET AKSES ANDA</b>

👤 UID: <b>{uid}</b>
🔑 License Key:
<code>{key}</code>

📱 Akses: bot.autog.my.id/member?key={key}"""
        if send_member_tg(chat_id, msg):
            return jsonify({"msg": f"✅ Kunci berhasil dikirim ke Telegram Anda!"})
        else:
            return jsonify({"msg": "⚠️ Gagal kirim. Hubungi admin @raniwealth"})
    elif status == "REJECTED":
        return jsonify({"msg": f"❌ Akun Anda di-reject. Alasan: {reg.get('reject_reason', '-')}"})
    else:
        return jsonify({"msg": f"⏳ Akun Anda masih PENDING. Tunggu approval admin."})

# ============================================================================
# ADMIN LOGIN (RATE LIMITED + CSRF)
# ============================================================================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    ip = get_client_ip()

    if is_locked_out(ip):
        remaining = int(_ip_blacklist[ip] - time.time())
        log_security("LOGIN_ATTEMPT_LOCKED", ip)
        return f"""<html><body style='font-family:sans-serif;background:#05060a;color:#fff;text-align:center;padding:80px'>
        <h1 style='color:#ff4444'>⛔ AKSES DIBLOKIR</h1>
        <p>Terlalu banyak percobaan login gagal.</p>
        <p>Coba lagi dalam <b>{remaining}</b> detik.</p></body></html>""", 429

    if request.method == 'POST':
        if not validate_csrf(request.form.get("csrf_token")):
            log_security("CSRF_FAIL_LOGIN", ip)
            abort(403)

        password = request.form.get("password", "")

        # Timing attack protection: selalu proses hash
        valid = check_password_hash(ADMIN_PASSWORD_HASH, password)

        if valid:
            clear_login_attempts(ip)
            session.clear()
            session["is_admin"] = True
            session["last_active"] = time.time()
            session.permanent = True
            log_security("LOGIN_SUCCESS", ip)
            return redirect(url_for("admin"))
        else:
            locked = record_failed_login(ip)
            attempts = len(_login_attempts[ip])
            log_security("LOGIN_FAIL", ip, f"attempts={attempts}")
            
            # TAMBAHAN: Auto-ban IP yang mencurigakan
            if attempts >= 10:
                _ip_blacklist[ip] = time.time() + 3600  # Ban 1 jam
                log_security("PERMANENT_BAN_1H", ip, f"too many attempts: {attempts}")
            elif attempts >= 7:
                _ip_blacklist[ip] = time.time() + 900   # Ban 15 menit
                log_security("TEMP_BAN_15M", ip, f"attempts: {attempts}")
            
            time.sleep(1.5)  # delay lebih lama
            error = "Terlalu banyak percobaan. Akun dikunci 15 menit." if locked else "Password salah!"
            csrf = generate_csrf_token()
            return render_template_string("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Admin Login</title>
<style>* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,sans-serif; background:#05060a; color:#fff; display:flex; align-items:center; justify-content:center; min-height:100vh; }
.box { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:40px; width:380px; }
h1 { color:#ff4444; font-size:1.3rem; letter-spacing:2px; margin-bottom:8px; text-align:center; }
p.sub { color:#666; font-size:0.75rem; text-align:center; margin-bottom:25px; }
input { width:100%; padding:14px; background:#0d1117; border:1px solid #30363d; color:#fff; border-radius:8px; font-size:0.95rem; margin-bottom:15px; }
input:focus { outline:none; border-color:#00ff9d; }
button { width:100%; padding:14px; background:linear-gradient(135deg,#00ff9d,#00d97e); color:#000; border:none; font-weight:900; border-radius:8px; cursor:pointer; letter-spacing:1px; }
.err { background:rgba(255,68,68,0.1); border:1px solid #ff4444; color:#ff6666; padding:10px; border-radius:8px; font-size:0.78rem; margin-bottom:15px; text-align:center; }
</style></head><body>
<div class="box">
  <h1>🔒 ADMIN LOGIN</h1>
  <p class="sub">Restricted Area</p>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf }}">
    <input type="password" name="password" placeholder="Password" required autofocus>
    <button type="submit">MASUK</button>
  </form>
</div></body></html>""", error=error, csrf=csrf), 401

    # GET
    csrf = generate_csrf_token()
    return render_template_string("""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Admin Login</title>
<style>* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,sans-serif; background:#05060a; color:#fff; display:flex; align-items:center; justify-content:center; min-height:100vh; }
.box { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:40px; width:380px; }
h1 { color:#ff4444; font-size:1.3rem; letter-spacing:2px; margin-bottom:8px; text-align:center; }
p.sub { color:#666; font-size:0.75rem; text-align:center; margin-bottom:25px; }
input { width:100%; padding:14px; background:#0d1117; border:1px solid #30363d; color:#fff; border-radius:8px; font-size:0.95rem; margin-bottom:15px; }
input:focus { outline:none; border-color:#00ff9d; }
button { width:100%; padding:14px; background:linear-gradient(135deg,#00ff9d,#00d97e); color:#000; border:none; font-weight:900; border-radius:8px; cursor:pointer; letter-spacing:1px; }
</style></head><body>
<div class="box">
  <h1>🔒 ADMIN LOGIN</h1>
  <p class="sub">Restricted Area</p>
  <form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf }}">
    <input type="password" name="password" placeholder="Password" required autofocus>
    <button type="submit">MASUK</button>
  </form>
</div></body></html>""", csrf=csrf)

@app.route('/admin/logout')
def admin_logout():
    ip = get_client_ip()
    session.clear()
    log_security("LOGOUT", ip)
    return redirect(url_for("admin_login"))

# ============================================================================
# ADMIN PANEL (PROTECTED)
# ============================================================================
@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin():
    ip = get_client_ip()

    if request.method == 'POST':
        if not validate_csrf(request.form.get("csrf_token")):
            log_security("CSRF_FAIL_ADMIN", ip, request.form.get("action", ""))
            abort(403)

        action = request.form.get("action")
        lics = load_db(LICENSE_DB)
        regs = load_db(REGISTRATION_DB)

        if action == "approve":
            rid = request.form.get("rid", "")
            try:
                days = max(1, min(3650, int(request.form.get("days", 30))))
            except ValueError:
                days = 30
            
            # Cek apakah ini downline VIP (dapat akses gratis)
            reg_data = regs.get(rid, {})
            if reg_data.get("type") == "DOWNLINE_VIP":
                days = 365  # Free 1 tahun untuk downline
                log_security("VIP_DOWNLINE_APPROVED", ip, 
                            f"uid={reg_data.get('uid')}, ref={reg_data.get('referral_website')}, "
                            f"deposit={reg_data.get('deposit_amount')}")
            reg = regs.get(rid)
            if reg:
                uid = reg['uid']
                # HWID opsional (kalau tidak ada, pakai ANYHWID)
                raw_hwid = reg.get('hwid', '') or 'ANYHWID'
                hwid_short = str(raw_hwid)[:12].upper() or 'ANYHWID'
                acc_clean = "".join(c for c in uid if c.isalnum()).upper() or "ANYID"
                expiry_dt = datetime.now() + timedelta(days=days)
                expiry_yyyymmdd = expiry_dt.strftime("%Y%m%d")
                expiry_str = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
                sig = generate_offline_sig(expiry_yyyymmdd, acc_clean, hwid_short)
                key = f"TITAN-VIP-{expiry_yyyymmdd}-{acc_clean}-{hwid_short}-{sig}"
                # [PATCH O2.1] Auto-generate member_token untuk API distribution
                import secrets as _secrets_o2
                _member_token = _secrets_o2.token_urlsafe(32)
                lics[key] = {"buyer_name": uid, "account_id": acc_clean,
                             "hwid": hwid_short, "expiry": expiry_str, "active": True,
                             "member_token": _member_token,
                             "last_seen": None,
                             "last_prediction": None}
                regs[rid]["status"] = "APPROVED"
                regs[rid]["license_key"] = key
                regs[rid]["approved_at"] = datetime.now().isoformat()
                save_db(LICENSE_DB, lics)
                save_db(REGISTRATION_DB, regs)
                log_security("LICENSE_APPROVED", ip, f"uid={uid}, days={days}")
                
                # === KIRIM NOTIFIKASI OTOMATIS VIA TELEGRAM ===
                try:
                    member_chat_id = reg.get("telegram_chat_id")
                    if member_chat_id:
                        # Kirim tombol akses
                        try:
                            import requests as _req_n
                            _req_n.post(
                                f"https://api.telegram.org/bot{MEMBER_BOT_TOKEN}/sendMessage",
                                json={{
                                    "chat_id": member_chat_id,
                                    "text": "👇 Klik tombol untuk akses dashboard:",
                                    "reply_markup": {{"inline_keyboard": [
                                        [{{"text": "🚀 AKSES DASHBOARD VIP", "url": f"https://bot.autog.my.id/member-login?uid={{uid}}"}}],
                                        [{{"text": "📞 Hubungi Support", "url": "https://t.me/raniwealth"}}]
                                    ]}}
                                }},
                                timeout=10
                            )
                        except: pass
                        # Kirim pesan utama
                        send_member_tg(member_chat_id, notif_msg)
                        # Kirim tombol akses
                        try:
                            import requests as _req_n
                            _req_n.post(
                                f"https://api.telegram.org/bot{MEMBER_BOT_TOKEN}/sendMessage",
                                json={
                                    "chat_id": member_chat_id,
                                    "text": "👇 Klik tombol untuk akses dashboard:",
                                    "reply_markup": {"inline_keyboard": [
                                        [{"text": "🚀 AKSES DASHBOARD VIP", "url": f"https://bot.autog.my.id/member-login?uid={uid}"}],
                                        [{"text": "📞 Hubungi Support", "url": "https://t.me/raniwealth"}]
                                    ]}
                                },
                                timeout=10
                            )
                        except: pass
                        log_security("MEMBER_NOTIFIED", ip, f"uid={uid}, chat={member_chat_id}")
                except Exception as _notif_err:
                    print(f"[NOTIF ERROR] {_notif_err}")
                    log_security("NOTIF_ERROR", ip, str(_notif_err)[:100])

        elif action == "reject":
            rid = request.form.get("rid", "")
            reason = sanitize(request.form.get("reason", "Tidak memenuhi syarat"), 500)
            if rid in regs:
                reg_data = regs[rid]
                reg_data["status"] = "REJECTED"
                reg_data["reject_reason"] = reason
                reg_data["rejected_at"] = datetime.now().isoformat()
                save_db(REGISTRATION_DB, regs)
                log_security("REGISTRATION_REJECTED", ip, f"uid={reg_data.get('uid')}, reason={reason[:50]}")
                
                # Kirim notifikasi Telegram ke member (kalau ada chat_id)
                try:
                    member_chat = reg_data.get("telegram_chat_id")
                    if member_chat:
                        reject_msg = f"""❌ <b>PENDAFTARAN DITOLAK</b>

👤 Game ID: <b>{reg_data.get('uid')}</b>
📝 Alasan: {reason}

Silakan hubungi admin untuk info lebih lanjut: @raniwealth"""
                        send_member_tg(member_chat, reject_msg)
                except: pass
        
        elif action == "toggle":
            k = request.form.get("key", "")
            if k in lics:
                lics[k]["active"] = not lics[k].get("active", True)
                save_db(LICENSE_DB, lics)
                log_security("LICENSE_TOGGLED", ip, f"key={k[:30]}, active={lics[k]['active']}")

        elif action == "delete":
            k = request.form.get("key", "")
            if k in lics:
                del lics[k]
                save_db(LICENSE_DB, lics)
                log_security("LICENSE_DELETED", ip, f"key={k[:30]}")
        
        elif action == "reset_hwid":
            k = request.form.get("key", "")
            if k in lics:
                lics[k]["hwid"] = None
                lics[k]["devices"] = []
                save_db(LICENSE_DB, lics)
                log_security("LICENSE_HWID_RESET", ip, f"key={k[:30]}")
        
        elif action == "reset_devices":
            k = request.form.get("key", "")
            if k in lics:
                lics[k]["devices"] = []
                save_db(LICENSE_DB, lics)
                log_security("LICENSE_DEVICES_RESET", ip, f"key={k[:30]}")
        
        elif action == "reset_devices":
            k = request.form.get("key", "")
            if k in lics:
                lics[k]["devices"] = []
                save_db(LICENSE_DB, lics)
                log_security("LICENSE_DEVICES_RESET", ip, f"key={k[:30]}")
        
        elif action == "extend":
            k = request.form.get("key", "")
            try:
                days = max(1, min(3650, int(request.form.get("days", 30))))
            except ValueError:
                days = 30
            if k in lics:
                try:
                    old_expiry = datetime.strptime(lics[k]["expiry"], "%Y-%m-%d %H:%M:%S")
                    new_expiry = old_expiry + timedelta(days=days)
                except:
                    new_expiry = datetime.now() + timedelta(days=days)
                lics[k]["expiry"] = new_expiry.strftime("%Y-%m-%d %H:%M:%S")
                save_db(LICENSE_DB, lics)
                log_security("LICENSE_EXTENDED", ip, f"key={k[:30]}, +{days}d")
        
        elif action == "resend_key":
            # Kirim ulang license key ke member (via WA/Email manual oleh admin)
            k = request.form.get("key", "")
            if k in lics:
                lic = lics[k]
                log_security("LICENSE_RESEND", ip, f"key={k[:30]}, uid={lic.get('buyer_name')}")
                # Info ini akan muncul di flash message, admin kirim manual ke member
        
        elif action == "reset_expiry":
            # Reset expiry jadi 1 tahun dari sekarang
            k = request.form.get("key", "")
            if k in lics:
                new_expiry = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
                lics[k]["expiry"] = new_expiry
                save_db(LICENSE_DB, lics)
                log_security("LICENSE_EXPIRY_RESET", ip, f"key={k[:30]}")
        
        elif action == "regenerate":
            k = request.form.get("key", "")
            if k in lics:
                lic = lics[k]
                uid = lic.get("account_id", "ANYID")
                hwid_short = lic.get("hwid", "ANYHWID")
                try:
                    expiry_dt = datetime.strptime(lic["expiry"], "%Y-%m-%d %H:%M:%S")
                except:
                    expiry_dt = datetime.now() + timedelta(days=30)
                expiry_yyyymmdd = expiry_dt.strftime("%Y%m%d")
                sig = generate_offline_sig(expiry_yyyymmdd, uid, hwid_short)
                new_key = f"TITAN-VIP-{expiry_yyyymmdd}-{uid}-{hwid_short}-{sig}"
                
                del lics[k]
                lics[new_key] = lic
                save_db(LICENSE_DB, lics)
                log_security("LICENSE_REGENERATED", ip, f"old={k[:20]}, new={new_key[:20]}")

    lics = load_db(LICENSE_DB)
    regs = load_db(REGISTRATION_DB)
    csrf = generate_csrf_token()

    h = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin Panel</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,sans-serif; background:#05060a; color:#fff; padding:30px 20px; line-height:1.5; }
.container { max-width:1000px; margin:0 auto; }
.header { display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:15px; margin-bottom:25px; }
h1 { color:#ff4444; font-size:1.3rem; letter-spacing:2px; }
h2 { color:#00ff9d; font-size:0.9rem; letter-spacing:1.5px; margin:25px 0 12px; }
.logout { background:rgba(255,68,68,0.15); border:1px solid #ff4444; color:#ff4444; padding:8px 16px; border-radius:8px; text-decoration:none; font-size:0.75rem; font-weight:700; }
.card { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:18px; margin-bottom:10px; }
.card b { color:#fff; }
.card code { background:#0d1117; padding:3px 8px; border-radius:4px; color:#00ff9d; font-size:0.78rem; font-family:monospace; }
button { padding:6px 14px; background:#00ff9d; color:#000; border:none; font-weight:900; border-radius:6px; cursor:pointer; font-size:0.72rem; margin-left:6px; }
button.danger { background:#ff4444; color:#fff; }
input.days { padding:6px 8px; background:#0d1117; border:1px solid #30363d; color:#fff; border-radius:6px; width:70px; }
.empty { color:#555; font-style:italic; font-size:0.85rem; }
.status-pending { color:#eab308; font-weight:bold; font-size:0.7rem; }
.status-active { color:#00ff9d; font-weight:bold; }
.status-suspended { color:#ff4444; font-weight:bold; }
</style></head><body>
<div class="container">
  <div class="header">
        <h1>🔒 ADMIN PANEL</h1>
        <div style="display:flex; gap:10px;">
            <a href="https://bot.autog.my.id/api/admin/backup_export?key=MASTER_OWNER_TITAN" 
               style="background:rgba(0,255,157,0.15); border:1px solid #00ff9d; color:#00ff9d; padding:8px 16px; border-radius:8px; text-decoration:none; font-size:0.75rem; font-weight:900;">📦 BACKUP ZIP</a>
            <a href="/admin/logout" class="logout">LOGOUT</a>
        </div>
    </div>
    """
    
    # [PATCH F3] Health Widget — Monitoring Real-Time
    h += """
    <h2 style="color:#00ff9d; margin-top:20px;">💚 SYSTEM HEALTH — REAL-TIME MONITOR</h2>
    <div id="health-widget" class="card" style="background:rgba(0,255,157,0.05); border-color:rgba(0,255,157,0.3);">
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:12px;">
            <div style="background:#000; padding:12px; border-radius:8px; border:1px solid #1a1a24;">
                <div style="font-size:0.6rem; color:#888; text-transform:uppercase; letter-spacing:1px;">Engine</div>
                <div id="h-engine" style="font-size:1rem; color:#fff; font-weight:900; font-family:'Orbitron';">⏳</div>
            </div>
            <div style="background:#000; padding:12px; border-radius:8px; border:1px solid #1a1a24;">
                <div style="font-size:0.6rem; color:#888; text-transform:uppercase; letter-spacing:1px;">Uptime</div>
                <div id="h-uptime" style="font-size:0.9rem; color:#00ff9d; font-weight:900; font-family:'Orbitron';">--:--:--</div>
            </div>
            <div style="background:#000; padding:12px; border-radius:8px; border:1px solid #1a1a24;">
                <div style="font-size:0.6rem; color:#888; text-transform:uppercase; letter-spacing:1px;">Members</div>
                <div id="h-members" style="font-size:1rem; color:#fff; font-weight:900; font-family:'Orbitron';">0 / 0</div>
                <div style="font-size:0.55rem; color:#666;">online / total</div>
            </div>
            <div style="background:#000; padding:12px; border-radius:8px; border:1px solid #1a1a24;">
                <div style="font-size:0.6rem; color:#888; text-transform:uppercase; letter-spacing:1px;">TG Queue</div>
                <div id="h-tg" style="font-size:1rem; color:#ffaa00; font-weight:900; font-family:'Orbitron';">0</div>
            </div>
            <div style="background:#000; padding:12px; border-radius:8px; border:1px solid #1a1a24;">
                <div style="font-size:0.6rem; color:#888; text-transform:uppercase; letter-spacing:1px;">Version</div>
                <div id="h-version" style="font-size:0.75rem; color:#00aaff; font-weight:900; font-family:'Orbitron';">-</div>
            </div>
        </div>
        <div style="text-align:right; font-size:0.6rem; color:#444; margin-top:8px;">
            Last updated: <span id="h-last">-</span> · <span style="color:#00ff9d;">Auto-refresh tiap 30s</span>
        </div>
    </div>
    
    <script>
    async function refreshHealth() {
        try {
            const r = await fetch('https://bot.autog.my.id/api/health?t=' + Date.now());
            const d = await r.json();
            document.getElementById('h-engine').innerHTML = d.engine_online ? '<span style="color:#00ff9d;">● ONLINE</span>' : '<span style="color:#ff4444;">● OFFLINE</span>';
            const up = d.uptime_seconds || 0;
            const hh = Math.floor(up/3600).toString().padStart(2,'0');
            const mm = Math.floor((up%3600)/60).toString().padStart(2,'0');
            const ss = (up%60).toString().padStart(2,'0');
            document.getElementById('h-uptime').innerText = hh+':'+mm+':'+ss;
            document.getElementById('h-members').innerHTML = '<span style="color:#00ff9d;">' + d.members_online_5min + '</span> / ' + d.members_total;
            document.getElementById('h-tg').innerText = d.tg_queue_size;
            document.getElementById('h-last').innerText = new Date().toLocaleTimeString();
        } catch(e) {
            document.getElementById('h-engine').innerHTML = '<span style="color:#ff4444;">ERR</span>';
        }
    }
    
    async function loadVersion() {
        try {
            const r = await fetch('https://bot.autog.my.id/api/version');
            const d = await r.json();
            document.getElementById('h-version').innerText = d.version || '-';
        } catch(e) {}
    }
    
    refreshHealth();
    loadVersion();
    setInterval(refreshHealth, 30000);
    </script>
    """
    
    h += """<h2>⏳ PENDAFTAR PENDING</h2>
  <div style="margin: 15px 0; display: flex; gap: 10px;">
    <button type="button" onclick="showPendingTab('new')" id="tab-new" style="background:#ffaa00;color:#000;padding:8px 16px;border-radius:6px;font-weight:900;border:none;cursor:pointer;">🆕 NEW MEMBER</button>
    <button type="button" onclick="showPendingTab('old')" id="tab-old" style="background:#333;color:#aaa;padding:8px 16px;border-radius:6px;font-weight:900;border:none;cursor:pointer;">👤 MEMBER LAMA</button>
  </div>"""

    # Count per category
    count_new = sum(1 for r in regs.values() if r.get("status") == "PENDING" and r.get("member_status") == "new")
    count_old = sum(1 for r in regs.values() if r.get("status") == "PENDING" and r.get("member_status") != "new")
    
    h += f"""<div id="count-new" data-count="{count_new}" style="display:none;"></div>
    <div id="count-old" data-count="{count_old}" style="display:none;"></div>"""
    
    pending_count = 0
    for rid, r in regs.items():
        if r.get("status") == "PENDING":
            pending_count += 1
            status_label = "🆕 NEW MEMBER" if r.get("member_status") == "new" else "👤 MEMBER LAMA"
            data_cat = "new" if r.get("member_status") == "new" else "old"
            status_color = "#ffaa00" if r.get("member_status") == "new" else "#00ff9d"
            
            proof_html = ""
            if r.get("deposit_proof"):
                proof_html = f"<br>📸 <b>Bukti Deposit:</b> <a href='/static/proofs/{r['deposit_proof']}' target='_blank' style='color:#00aaff;'>Lihat Screenshot</a>"
            
            h += f"""<div class="card pending-card" data-cat="{data_cat}">
                <div style="background:{status_color};color:#000;padding:3px 10px;border-radius:4px;display:inline-block;font-size:0.7rem;font-weight:900;margin-bottom:8px;">{status_label}</div><br>
                <b>UID:</b> {r['uid']} | <b>Email:</b> {r['email']} | <b>HP:</b> {r['phone']}<br>
                <b>Website:</b> <span style='color:#00ff9d;'>{r.get('referral_website','-').upper()}</span> | <b>Deposit:</b> <span style='color:#ffaa00;'>Rp {r.get('deposit_amount',0):,}</span>{proof_html}<br>
                <b>Waktu:</b> {r.get('registered_at','?')[:19]}
                <div style='margin-top:10px;'>
                <form method='POST' style='display:inline'>
                    <input type='hidden' name='csrf_token' value='{csrf}'>
                    <input type='hidden' name='action' value='approve'>
                    <input type='hidden' name='rid' value='{rid}'>
                    <input type='hidden' name='days' value='365'>
                    <button style='background:#00ff9d;color:#000;'>🎁 APPROVE VIP 1 TAHUN</button>
                </form>
                <button onclick="document.getElementById('reject-{rid}').style.display='block';" style='background:#ff4444;color:#fff;margin-left:6px;'>❌ REJECT</button>
                </div>
                <div id='reject-{rid}' style='display:none;margin-top:10px;'>
                <form method='POST'>
                    <input type='hidden' name='csrf_token' value='{csrf}'>
                    <input type='hidden' name='action' value='reject'>
                    <input type='hidden' name='rid' value='{rid}'>
                    <input type='text' name='reason' placeholder='Alasan penolakan...' required style='width:70%;padding:8px;background:#0d1117;border:1px solid #ff4444;color:#fff;border-radius:6px;'>
                    <button style='background:#ff4444;color:#fff;'>KIRIM PENOLAKAN</button>
                </form>
                </div>
            </div>"""
    if pending_count == 0:
        h += "<div class='empty'>Tidak ada pendaftar baru.</div>"

    # === SEARCH & FILTER BAR ===
    h += """
    <div style="margin: 20px 0; display: flex; gap: 10px; flex-wrap: wrap;">
        <input type="text" id="search-license" placeholder="🔍 Cari License Key, Nama, atau Game ID..." 
               style="flex: 1; min-width: 250px; padding: 12px 15px; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 8px; font-size: 0.85rem;"
               oninput="filterLicenses()">
        <select id="filter-status" onchange="filterLicenses()"
                style="padding: 12px 15px; background: #0d1117; border: 1px solid #30363d; color: #fff; border-radius: 8px; font-size: 0.85rem;">
            <option value="all">Semua Status</option>
            <option value="active">Aktif</option>
            <option value="suspended">Suspended</option>
        </select>
    </div>
    <script>
    function filterLicenses() {
        const query = document.getElementById('search-license').value.toLowerCase();
        const status = document.getElementById('filter-status').value;
        const cards = document.querySelectorAll('.license-card');
        cards.forEach(card => {
            const text = card.innerText.toLowerCase();
            const dataStatus = card.getAttribute('data-status');
            const matchQuery = !query || text.includes(query);
            const matchStatus = status === 'all' || dataStatus === status;
            card.style.display = (matchQuery && matchStatus) ? 'block' : 'none';
        });
    }
    </script>
    """
    # [PATCH A1.4] OWNER SETTINGS SECTION
    h += """
    <h2 style="color:#ffaa00; margin-top:30px;">⚙️ OWNER SETTINGS — LINK ALTERNATIF 55FIVE</h2>
    <div class="card" style="background:rgba(255,170,0,0.05); border-color:rgba(255,170,0,0.3);">
        <div style="font-size:0.85rem; color:#ccc; margin-bottom:15px;">
            🔗 Ganti link 55five kapan saja. Member akan otomatis dapat link baru tanpa perlu Anda kirim ulang.
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin-bottom:15px;">
            <div>
                <label style="display:block; font-size:0.7rem; color:#ffaa00; font-weight:bold; margin-bottom:6px;">🌐 LINK UTAMA (aktif):</label>
                <input type="text" id="setting_link_main" placeholder="https://www.vokzila.com" 
                       style="width:100%; padding:10px; background:#000; border:1px solid #ffaa00; color:#fff; border-radius:6px; font-size:0.8rem; font-family:monospace;">
            </div>
            <div>
                <label style="display:block; font-size:0.7rem; color:#00ff9d; font-weight:bold; margin-bottom:6px;">🔄 LINK BACKUP (fallback):</label>
                <input type="text" id="setting_link_backup" placeholder="https://www.nuxpira.com"
                       style="width:100%; padding:10px; background:#000; border:1px solid #00ff9d; color:#fff; border-radius:6px; font-size:0.8rem; font-family:monospace;">
            </div>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:15px; margin-bottom:15px;">
            <div>
                <label style="display:block; font-size:0.7rem; color:#aaa; font-weight:bold; margin-bottom:6px;">💰 DEFAULT BET (Rp):</label>
                <input type="number" id="setting_bet_amount" min="400" max="1000000" step="100"
                       style="width:100%; padding:10px; background:#000; border:1px solid #30363d; color:#fff; border-radius:6px; font-size:0.8rem;">
            </div>
            <div>
                <label style="display:block; font-size:0.7rem; color:#aaa; font-weight:bold; margin-bottom:6px;">🤖 FORCE AUTO-BET:</label>
                <label style="display:flex; align-items:center; gap:8px; padding:10px; background:#000; border:1px solid #30363d; border-radius:6px; cursor:pointer;">
                    <input type="checkbox" id="setting_force_autobet" style="width:18px; height:18px; accent-color:#00ff9d;">
                    <span style="font-size:0.75rem; color:#ccc;">Paksa semua member ON auto-bet</span>
                </label>
            </div>
        </div>

        <div style="display:grid; grid-template-columns:2fr 1fr; gap:15px; margin-bottom:15px;">
            <div>
                <label style="display:block; font-size:0.7rem; color:#a855f7; font-weight:bold; margin-bottom:6px;">🎯 FORCE MODE (Paksa Mode WinGo):</label>
                <select id="setting_force_mode" style="width:100%; padding:10px; background:#000; border:1px solid #a855f7; color:#fff; border-radius:6px; font-size:0.8rem; font-family:'Orbitron';">
                    <option value="1m">🚀 WINGO 1 MENIT (Recommended)</option>
                    <option value="3m">⏱️ WINGO 3 MENIT</option>
                    <option value="5m">⏰ WINGO 5 MENIT</option>
                    <option value="off">⚙️ OFF (Manual)</option>
                </select>
                <div style="font-size:0.6rem; color:#666; margin-top:4px;">Bot akan otomatis paksa mode ini, apapun yang dibuka browser.</div>
            </div>
            <div>
                <label style="display:block; font-size:0.7rem; color:#00aaff; font-weight:bold; margin-bottom:6px;">🔄 AUTO RESET SYNC:</label>
                <label style="display:flex; align-items:center; gap:8px; padding:10px; background:#000; border:1px solid #00aaff; border-radius:6px; cursor:pointer; height:42px;">
                    <input type="checkbox" id="setting_auto_reset" checked style="width:18px; height:18px; accent-color:#00aaff;">
                    <span style="font-size:0.7rem; color:#ccc;">Auto reset saat mode ganti</span>
                </label>
            </div>
        </div>
        <div style="display:flex; gap:10px;">
            <button type="button" onclick="saveOwnerSettings()" style="flex:1; padding:12px; background:#00ff9d; color:#000; border:none; font-weight:900; border-radius:6px; cursor:pointer; font-family:'Orbitron'; font-size:0.75rem;">
                💾 SIMPAN SETTINGS
            </button>
            <button type="button" onclick="testLinkAlt()" style="flex:1; padding:12px; background:#00aaff; color:#fff; border:none; font-weight:900; border-radius:6px; cursor:pointer; font-family:'Orbitron'; font-size:0.75rem;">
                🧪 TEST LINK
            </button>
        </div>
        <div id="settings_status" style="margin-top:12px; padding:10px; border-radius:6px; font-size:0.75rem; display:none;"></div>
        <div style="font-size:0.65rem; color:#666; margin-top:10px; line-height:1.5;">
            💡 Tips: Simpan link baru kapan saja tanpa restart server. Member akan otomatis dapat link baru saat refresh dashboard.
        </div>
    </div>
    
    <script>
    async function loadOwnerSettingsForm() {
        try {
            const r = await fetch('/api/settings/get');
            const d = await r.json();
            if (d.status === 'ok') {
                document.getElementById('setting_link_main').value = d.alt_link_55five || '';
                document.getElementById('setting_link_backup').value = d.alt_link_backup || '';
                document.getElementById('setting_bet_amount').value = d.default_bet_amount || 1000;
                document.getElementById('setting_force_autobet').checked = d.force_autobet === true;
                document.getElementById('setting_force_mode').value = d.force_mode || '1m';
                document.getElementById('setting_auto_reset').checked = d.auto_reset_sync !== false;
            }

        } catch(e) { console.error('Load settings error:', e); }
    }
    

    

    
    async function saveOwnerSettings() {
        const statusEl = document.getElementById('settings_status');
        statusEl.style.display = 'block';
        statusEl.style.background = 'rgba(0,170,255,0.1)';
        statusEl.style.color = '#00aaff';
        statusEl.innerText = '⏳ Menyimpan...';
        
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const OWNER_KEY = urlParams.get('key') || '';
            const payload = {
                alt_link_55five: document.getElementById('setting_link_main').value.trim(),
                alt_link_backup: document.getElementById('setting_link_backup').value.trim(),
                default_bet_amount: parseInt(document.getElementById('setting_bet_amount').value) || 1000,
                force_autobet: document.getElementById('setting_force_autobet').checked,
                force_mode: document.getElementById('setting_force_mode').value,
                auto_reset_sync: document.getElementById('setting_auto_reset').checked
            };
            const r = await fetch('/api/settings/update?key=' + encodeURIComponent(OWNER_KEY), {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            const d = await r.json();
            if (d.status === 'ok') {
                statusEl.style.background = 'rgba(0,255,157,0.15)';
                statusEl.style.color = '#00ff9d';
                statusEl.innerText = '✅ Settings tersimpan! Member akan dapat link baru pada refresh berikutnya.';
            } else {
                statusEl.style.background = 'rgba(255,68,68,0.15)';
                statusEl.style.color = '#ff6666';
                statusEl.innerText = '❌ ' + (d.msg || 'Gagal menyimpan');
            }
        } catch(e) {
            statusEl.style.background = 'rgba(255,68,68,0.15)';
            statusEl.style.color = '#ff6666';
            statusEl.innerText = '❌ Error: ' + e.message;
        }
    }
    
    function testLinkAlt() {
        const url = document.getElementById('setting_link_main').value.trim();
        if (!url) { alert('Isi link dulu!'); return; }
        window.open(url, '_blank');
    }
    
    document.addEventListener('DOMContentLoaded', loadOwnerSettingsForm);
    setTimeout(loadOwnerSettingsForm, 300);
    </script>
    """
    
    h += "<h2>✅ LISENSI AKTIF</h2>"
    active_count = 0
    for k, v in lics.items():
        active_count += 1
        status_class = "status-active" if v.get("active") else "status-suspended"
        status_text = "AKTIF" if v.get("active") else "SUSPENDED"
        data_status_val = "active" if v.get("active") else "suspended"
        # Info devices
        devices = v.get("devices", [])
        dev_count = len(devices)
        dev_badge = ""
        if dev_count > 2:
            dev_badge = f" <span style='background:#ff4444;color:#fff;padding:2px 6px;border-radius:4px;font-size:0.6rem;'>⚠️ {dev_count} DEVICES</span>"
        elif dev_count > 0:
            dev_badge = f" <span style='background:#00ff9d;color:#000;padding:2px 6px;border-radius:4px;font-size:0.6rem;'>{dev_count} DEVICES</span>"
        
        h += f"""<div class="card license-card" data-status="{data_status_val}">
            <span class="{status_class}">[{status_text}]</span> <code>{k}</code>{dev_badge}<br>
            <b>UID:</b> {v.get('buyer_name','?')} | <b>HWID:</b> <code>{str(v.get('hwid') or 'NOT LINKED')[:20]}</code> | <b>Expiry:</b> {v.get('expiry','?')}
            <br><b>Last Deposit:</b> <span style="color:#00ff9d;font-weight:bold;">{v.get('last_deposit_at', 'BELUM DI-SET')[:10] if v.get('last_deposit_at') else 'BELUM DI-SET'}</span>
            {f'<span style="background:rgba(255,68,68,0.2);color:#ff4444;padding:2px 6px;border-radius:3px;font-size:0.65rem;margin-left:6px;">AUTO-EXPIRED</span>' if v.get('auto_expired') else ''}
            <form method='POST' style='display:inline'>
                <input type='hidden' name='csrf_token' value='{csrf}'>
                <input type='hidden' name='action' value='toggle'>
                <input type='hidden' name='key' value='{k}'>
                <button>TOGGLE</button>
            </form>
            <form method='POST' style='display:inline' onsubmit="return confirm('Reset HWID lisensi ini? User akan bisa login di perangkat baru.')">
                <input type='hidden' name='csrf_token' value='{csrf}'>
                <input type='hidden' name='action' value='reset_hwid'>
                <input type='hidden' name='key' value='{k}'>
                <button style='background:#eab308;color:#000;'>RESET HWID</button>
            </form>
            <form method='POST' style='display:inline' onsubmit="return confirm('Reset SEMUA device ({len(v.get('devices', []))} device)? Member bisa login ulang dari HP baru.')">
                <input type='hidden' name='csrf_token' value='{csrf}'>
                <input type='hidden' name='action' value='reset_devices'>
                <input type='hidden' name='key' value='{k}'>
                <button style='background:#a855f7;color:#fff;'>RESET DEVICE ({len(v.get('devices', []))})</button>
            </form>
            <button style='background:#00ff9d;color:#000;' onclick="updateDeposit('{k}')">📅 UPDATE DEPO</button>
            <form method='POST' style='display:inline' onsubmit="return confirm('Perpanjang lisensi 30 hari?')">
                <input type='hidden' name='csrf_token' value='{csrf}'>
                <input type='hidden' name='action' value='extend'>
                <input type='hidden' name='key' value='{k}'>
                <input type='hidden' name='days' value='30'>
                <button style='background:#00ff9d;color:#000;'>+30 HARI</button>
            </form>
            <form method='POST' style='display:inline' onsubmit="return confirm('Regenerate key ini? Key lama akan dihapus dan diganti baru.')">
                <input type='hidden' name='csrf_token' value='{csrf}'>
                <input type='hidden' name='action' value='regenerate'>
                <input type='hidden' name='key' value='{k}'>
                <button style='background:#00aaff;color:#fff;'>REGEN</button>
            </form>
            <form method='POST' style='display:inline' onsubmit="return confirm('Reset daftar perangkat? Member bisa login dari HP baru.')">
                <input type='hidden' name='csrf_token' value='{csrf}'>
                <input type='hidden' name='action' value='reset_devices'>
                <input type='hidden' name='key' value='{k}'>
                <button style='background:#a855f7;color:#fff;'>RESET DEVICE</button>
            </form>
            <form method='POST' style='display:inline' onsubmit="return confirm('Hapus lisensi ini?')">
                <input type='hidden' name='csrf_token' value='{csrf}'>
                <input type='hidden' name='action' value='delete'>
                <input type='hidden' name='key' value='{k}'>
                <button class='danger'>DELETE</button>
            </form>
        </div>"""
    if active_count == 0:
        h += "<div class='empty'>Belum ada lisensi.</div>"

    # ===== OWNER ACCESS PANEL SECTION =====
    OWNER_KEY = _SECRETS.get("OWNER_MASTER_KEY", "")
    h += f"""
    <h2 style="margin-top:40px;">👑 OWNER ACCESS (KHUSUS ANDA)</h2>
    <div class="card" style="background:rgba(255,170,0,0.05); border-color:rgba(255,170,0,0.3);">
        <div style="font-size:0.75rem; color:#aaa; margin-bottom:10px;">🔑 Kunci akses owner Anda — JANGAN dibagikan:</div>
        <code style="display:block; background:#000; padding:10px; border-radius:6px; color:#ffaa00; font-family:monospace; font-size:0.7rem; word-break:break-all; border:1px dashed #ffaa00;">{OWNER_KEY}</code>
        <div style="margin-top:12px;">
            <a href="https://bot.autog.my.id/dashboard?key={OWNER_KEY}" target="_blank" style="display:inline-block; padding:8px 14px; background:#00ff9d; color:#000; text-decoration:none; border-radius:6px; font-size:0.7rem; font-weight:bold; margin-right:6px;">📊 Dashboard PC</a>
            <a href="https://bot.autog.my.id/member?key={OWNER_KEY}" target="_blank" style="display:inline-block; padding:8px 14px; background:#00aaff; color:#fff; text-decoration:none; border-radius:6px; font-size:0.7rem; font-weight:bold; margin-right:6px;">📱 Mobile</a>
            <a href="https://bot.autog.my.id/owner-panel?key={OWNER_KEY}" target="_blank" style="display:inline-block; padding:8px 14px; background:#ffaa00; color:#000; text-decoration:none; border-radius:6px; font-size:0.7rem; font-weight:bold;">👑 Owner Panel</a>
        </div>
        <div style="font-size:0.65rem; color:#666; margin-top:10px;">
            💡 Untuk akses dari HP baru: buka <b>bot.autog.my.id/owner-panel?key={OWNER_KEY[:20]}...</b> di HP tersebut.
        </div>
    </div>
    """

    h += """
    <script>
    // [PATCH G7.4] Update tanggal deposito member
    async function updateDeposit(licenseKey) {
        const today = new Date().toISOString().slice(0, 10);
        const inp = prompt(
            '📅 Update Tanggal Deposit Terakhir\\n\\n' +
            'Format: YYYY-MM-DD (contoh: ' + today + ')\\n' +
            'Kosongkan untuk pakai HARI INI.\\n\\n' +
            'License akan otomatis di-aktifkan + diperpanjang 30 hari.', today
        );
        if (inp === null) return; // User cancel
        
        const urlParams = new URLSearchParams(window.location.search);
        const OWNER_KEY = urlParams.get('key') || '';
        
        try {
            const r = await fetch('/api/admin/update_deposit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    key: OWNER_KEY,
                    license_key: licenseKey,
                    deposit_date: inp.trim()
                })
            });
            const d = await r.json();
            if (d.status === 'ok') {
                alert('✅ BERHASIL!\\n\\n' + d.msg);
                location.reload();
            } else {
                alert('❌ ' + (d.msg || 'Gagal'));
            }
        } catch(e) {
            alert('❌ Network error: ' + e.message);
        }
    }
    
    function showPendingTab(cat) {
        const cards = document.querySelectorAll('.pending-card');
        cards.forEach(c => {
            c.style.display = (c.getAttribute('data-cat') === cat) ? 'block' : 'none';
        });
        document.getElementById('tab-new').style.background = (cat === 'new') ? '#ffaa00' : '#333';
        document.getElementById('tab-new').style.color = (cat === 'new') ? '#000' : '#aaa';
        document.getElementById('tab-old').style.background = (cat === 'old') ? '#00ff9d' : '#333';
        document.getElementById('tab-old').style.color = (cat === 'old') ? '#000' : '#aaa';
    }
    // Default: tampilkan tab New Member
    document.addEventListener('DOMContentLoaded', () => showPendingTab('new'));
    </script>
    </div></body></html>"""
    return h

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    print(f"[CENTRAL SERVER] Starting on port {PORT}")
    print(f"[CENTRAL SERVER] Domain: https://{DOMAIN}")
    if "scrypt" not in ADMIN_PASSWORD_HASH:
        print("[SECURITY] ⚠️  ADMIN_PASSWORD_HASH belum diganti! Update segera.")
    try:
        exe_p = normalize_and_rename()
        if exe_p:
            print(f"[STARTUP] ✅ File siap: {EXE_TARGET}")
    except Exception as e:
        print(f"[STARTUP] Rename error: {e}")
    try:
        app.run(host="0.0.0.0", port=PORT)
    except Exception as e:
        print(f"[FATAL] Central Server crashed: {e}")
        import time
        while True:
            time.sleep(60)