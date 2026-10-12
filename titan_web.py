# titan_web.py — AUTO-PATCHER + TUNNEL + MANUAL ENGINE BOOT
import os
import sys
import time
import threading
import subprocess

# ============================================================
# STEP 1: Set env untuk Chrome & libs SEBELUM import selenium
# ============================================================
LIBS_PATH = "/home/container/libs/usr/lib/x86_64-linux-gnu"
CHROME_PATH = "/home/container/chrome-linux64/chrome-headless-shell"
CHROMEDRIVER_PATH = "/home/container/chromedriver"

os.environ["LD_LIBRARY_PATH"] = LIBS_PATH + ":" + os.environ.get("LD_LIBRARY_PATH", "")
os.environ["CHROME_PATH"] = CHROME_PATH
os.environ["CHROMEDRIVER_PATH"] = CHROMEDRIVER_PATH

print("=" * 70)
print("  TITAN WEB — ALL-IN-ONE LAUNCHER v2")
print("=" * 70)
print(f"  Chrome binary : {CHROME_PATH}")
print(f"  Chromedriver  : {CHROMEDRIVER_PATH}")
print(f"  Libs path     : {LIBS_PATH}")
print("=" * 70)

# ============================================================
# STEP 2: Patch selenium SEBELUM app.py import
# ============================================================
print("\n[PATCH] Patching selenium Chrome Options & Service...")

import selenium.webdriver.chrome.options
import selenium.webdriver.chrome.service

_orig_options_init = selenium.webdriver.chrome.options.Options.__init__
def _patched_options_init(self, *args, **kwargs):
    _orig_options_init(self, *args, **kwargs)
    self.binary_location = CHROME_PATH
selenium.webdriver.chrome.options.Options.__init__ = _patched_options_init

_orig_service_init = selenium.webdriver.chrome.service.Service.__init__
def _patched_service_init(self, executable_path=None, *args, **kwargs):
    if not executable_path or not os.path.exists(str(executable_path)):
        executable_path = CHROMEDRIVER_PATH
    _orig_service_init(self, executable_path=executable_path, *args, **kwargs)
selenium.webdriver.chrome.service.Service.__init__ = _patched_service_init

print("  ✅ selenium patched")

# ============================================================
# STEP 3: Start cloudflared tunnel di background
# ============================================================
CF_PATH = "/home/container/cf"
CF_HOME = "/home/container/.cloudflared"
TUNNEL_ID = "fa41612f-13f2-46af-ba03-3668bd0b396a"
CONFIG_FILE = os.path.join(CF_HOME, "config.yml")
CF_LOG = "/home/container/cf.log"

def start_tunnel():
    if not os.path.exists(CF_PATH):
        print("[TUNNEL] ❌ cloudflared binary not found — skip")
        return
    if not os.path.exists(CONFIG_FILE):
        print(f"[TUNNEL] ❌ config not found — skip")
        return
    try:
        print(f"[TUNNEL] Starting cloudflared (Tunnel ID: {TUNNEL_ID})")
        log_f = open(CF_LOG, "w")
        proc = subprocess.Popen(
            [CF_PATH, "tunnel", "--config", CONFIG_FILE, "--protocol", "http2", "run"],
            stdout=log_f, stderr=subprocess.STDOUT, cwd="/home/container"
        )
        print(f"[TUNNEL] ✅ cloudflared PID: {proc.pid}")
    except Exception as e:
        print(f"[TUNNEL] ❌ Failed: {e}")

threading.Thread(target=start_tunnel, daemon=True).start()
time.sleep(2)

# ============================================================
# STEP 4: Import app.py & MANUALLY BOOT ENGINE
# ============================================================
print("\n[APP] Importing app.py...")
try:
    import app as titan_app
    print("  ✅ app.py imported successfully")
    
    flask_app = getattr(titan_app, "app", None)
    if flask_app is None:
        print("  ❌ Flask app object not found in app.py")
        sys.exit(1)
    
    # MANUAL ENGINE BOOT (karena import tidak menjalankan __main__ block)
    print("\n[ENGINE] Manual boot — instantiate QuantumMonitor...")
    try:
        QuantumMonitor = getattr(titan_app, "QuantumMonitor", None)
        WingoMasterBrain = getattr(titan_app, "WingoMasterBrain", None)
        
        if QuantumMonitor and WingoMasterBrain:
            brain = WingoMasterBrain()
            engine_instance = QuantumMonitor(brain)
            
            # Attach ke titan_app module agar route /api/* bisa akses
            titan_app.engine = engine_instance
            
            # Start background threads
            engine_instance.is_running = True
            threading.Thread(target=engine_instance.start_browser, daemon=True).start()
            threading.Thread(target=engine_instance.monitor_loop, daemon=True).start()
            print("  ✅ Engine INSTANTIATED & STARTED")
            print("  ✅ Titan_app.engine attached")
        else:
            print("  ⚠️  QuantumMonitor / WingoMasterBrain class not found in app.py")
            print(f"     QuantumMonitor: {QuantumMonitor is not None}")
            print(f"     WingoMasterBrain: {WingoMasterBrain is not None}")
    except Exception as e:
        import traceback
        print(f"  ⚠️  Engine boot failed: {e}")
        print(traceback.format_exc())
    
    # Jalankan Flask
    server_port = int(os.environ.get("SERVER_PORT", os.environ.get("PORT", "3004")))
    print(f"\n[RUN] Starting Flask on port {server_port}")
    print("=" * 70)
    flask_app.run(host="0.0.0.0", port=server_port, debug=False, use_reloader=False, threaded=True)
    
except Exception as e:
    import traceback
    print(f"\n❌ FATAL ERROR: {e}")
    print(traceback.format_exc())
    sys.exit(1)