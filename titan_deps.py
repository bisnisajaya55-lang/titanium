# -*- coding: utf-8 -*-
"""
TITAN DEPS — Self-Installing Dependencies (Long-Term Fix)
Cek & install otomatis: Chrome, Chromedriver, cloudflared, system libs, pip packages.
Menggantikan auto_bootstrap.py dan bootstrap_libs.py.
"""
import os
import sys
import io
import re
import gzip
import shutil
import subprocess
import urllib.request
import zipfile

BASE = "/home/container"
LIBS_DIR = f"{BASE}/libs"
CHROME_VERSION = "131.0.6778.204"  # Bisa diupdate kapan saja

# Daftar library yang dibutuhkan Chrome (sesuai Debian Bookworm/Bullseye)
REQUIRED_LIBS = [
    "libnss3", "libnspr4", "libatk1.0-0", "libatk-bridge2.0-0",
    "libatspi2.0-0", "libcups2", "libdrm2", "libgbm1",
    "libxkbcommon0", "libxcomposite1", "libxdamage1", "libxfixes3",
    "libxrandr2", "libpango-1.0-0", "libpangocairo-1.0-0", "libcairo2",
    "libasound2", "libgtk-3-0", "libgdk-pixbuf-2.0-0"
]

def log(m):
    print(f"[DEPS] {m}", flush=True)

def path_exists_big(p, min_size=1000):
    try:
        return os.path.exists(p) and os.path.getsize(p) >= min_size
    except Exception:
        return False

def download_to(url, dest_path, timeout=600):
    """Download dengan retry 3x + timeout panjang + UA."""
    import time as _t
    log(f"Download {url.split('/')[-1]}...")
    last_err = None
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "*/*",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                with open(dest_path, "wb") as f:
                    shutil.copyfileobj(resp, f)
            size = os.path.getsize(dest_path)
            log(f"   Berhasil download ({size:,} bytes)")
            return size
        except Exception as e:
            last_err = e
            log(f"   Attempt #{attempt} gagal: {str(e)[:80]}")
            if attempt < 3:
                _t.sleep(3)
            continue
    raise Exception(f"Gagal download setelah 3x: {last_err}")

# ============================================================
# 1. CARI URL PAKET DEBIAN TERBARU (Solusi 404)
# ============================================================
def get_debian_package_url(pkg_name, release="bookworm"):
    """Mencari URL .deb terbaru dari repository Debian secara dinamis."""
    url = f"http://deb.debian.org/debian/dists/{release}/main/binary-amd64/Packages.gz"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = gzip.decompress(resp.read()).decode('utf-8', errors='ignore')
        
        # Regex untuk mencari Package dan Filename-nya
        pattern = re.compile(rf"Package: {pkg_name}\n(?:.*\n)*?Filename: (.*?)\n")
        match = pattern.search(data)
        if match:
            return f"http://deb.debian.org/debian/{match.group(1)}"
    except Exception as e:
        log(f"   Gagal fetch package list untuk {pkg_name}: {str(e)[:60]}")
    return None

# ============================================================
# 2. EKSTRAK .DEB TANPA ROOT
# ============================================================
def extract_deb(deb_path, out_dir):
    """Extract .deb menggunakan dpkg-deb atau ar+tar."""
    if shutil.which("dpkg-deb"):
        try:
            subprocess.check_call(["dpkg-deb", "-x", deb_path, out_dir],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass

    # Fallback: ar + tar
    tmp = deb_path + "_extract"
    os.makedirs(tmp, exist_ok=True)
    try:
        if shutil.which("ar"):
            subprocess.check_call(["ar", "x", deb_path], cwd=tmp,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for fname in os.listdir(tmp):
                if fname.startswith("data.tar"):
                    data_tar = os.path.join(tmp, fname)
                    subprocess.check_call(["tar", "-xf", data_tar, "-C", out_dir],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
    except Exception as e:
        log(f"   Extract gagal: {str(e)[:60]}")
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return False

def copy_libs(out_dir, libs_dir):
    """Cari file .so dari folder extracted dan pindah ke LIBS_DIR."""
    count = 0
    for root, dirs, files in os.walk(out_dir):
        for f in files:
            if f.endswith(".so") or ".so." in f:
                src = os.path.join(root, f)
                dst = os.path.join(libs_dir, f)
                if not os.path.exists(dst):
                    try:
                        shutil.copy2(src, dst)
                        count += 1
                    except Exception:
                        pass
    return count

# ============================================================
# 3. INSTALL SYSTEM LIBS
# ============================================================
def ensure_system_libs():
    os.makedirs(LIBS_DIR, exist_ok=True)
    
    # Cek apakah libs sudah ada (deteksi libnss3)
    if os.path.exists(LIBS_DIR) and any("libnss3" in f for f in os.listdir(LIBS_DIR)):
        log("✅ System libs sudah ada, skip download.")
        os.environ["LD_LIBRARY_PATH"] = LIBS_DIR
        return True

    log("Mengunduh system libs dari Debian (Dynamic URL)...")
    tmp_dir = f"{BASE}/_libs_tmp"
    os.makedirs(tmp_dir, exist_ok=True)
    total_extracted = 0

    for pkg_name in REQUIRED_LIBS:
        log(f"Proses: {pkg_name}...")
        
        # Cari URL terbaru
        url = get_debian_package_url(pkg_name)
        if not url:
            log(f"   ⚠️  {pkg_name} tidak ditemukan di repo, skip.")
            continue

        deb_path = os.path.join(tmp_dir, f"{pkg_name}.deb")
        
        # Download
        try:
            download_to(url, deb_path)
        except Exception as e:
            log(f"   Gagal download {pkg_name}: {str(e)[:60]}")
            continue

        # Extract
        extract_dir = os.path.join(tmp_dir, f"{pkg_name}_ext")
        os.makedirs(extract_dir, exist_ok=True)
        if extract_deb(deb_path, extract_dir):
            n = copy_libs(extract_dir, LIBS_DIR)
            if n > 0:
                log(f"   ✅ {pkg_name}: {n} libs")
                total_extracted += n
            else:
                log(f"   ⚠️  {pkg_name}: 0 libs extracted")
        
        # Cleanup
        try:
            os.remove(deb_path)
        except Exception:
            pass
        shutil.rmtree(extract_dir, ignore_errors=True)

    shutil.rmtree(tmp_dir, ignore_errors=True)
    log(f"Total libs extracted: {total_extracted}")
    
    # Set LD_LIBRARY_PATH untuk proses saat ini dan anaknya
    os.environ["LD_LIBRARY_PATH"] = LIBS_DIR
    log(f"LD_LIBRARY_PATH di-set ke: {LIBS_DIR}")
    return True

# ============================================================
# 4. PIP PACKAGES
# ============================================================
def ensure_pip_packages():
    req_file = f"{BASE}/requirements.txt"
    if not os.path.exists(req_file):
        log("requirements.txt tidak ada, skip pip install")
        return
    log("Cek pip packages...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet",
             "--prefix", ".local", "-r", req_file],
            timeout=600,
        )
        log("✅ pip packages OK")
    except Exception as e:
        log(f"⚠️  pip install error: {e}")

# ============================================================
# 5. CHROME & CHROMEDRIVER
# ============================================================
def ensure_chrome():
    dst_dir = f"{BASE}/chrome-linux64"
    chrome = f"{dst_dir}/chrome"
    shell = f"{dst_dir}/chrome-headless-shell"

    if path_exists_big(chrome, 10000000) or path_exists_big(shell, 10000000):
        log(f"✅ Chrome sudah ada.")
        return True

    url = f"https://storage.googleapis.com/chrome-for-testing-public/{CHROME_VERSION}/linux64/chrome-headless-shell-linux64.zip"
    tmp_zip = f"{BASE}/_chrome.zip"
    tmp_dir = f"{BASE}/_chrome_tmp"

    try:
        download_to(url, tmp_zip)
        log("Extract chrome...")
        with zipfile.ZipFile(tmp_zip, "r") as z:
            z.extractall(tmp_dir)

        extracted = f"{tmp_dir}/chrome-headless-shell-linux64"
        if not os.path.exists(extracted):
            raise Exception("Extract folder tidak ditemukan")

        if os.path.exists(dst_dir):
            shutil.rmtree(dst_dir, ignore_errors=True)
        shutil.move(extracted, dst_dir)

        for fn in os.listdir(dst_dir):
            fp = os.path.join(dst_dir, fn)
            if os.path.isfile(fp):
                os.chmod(fp, 0o755)

        if os.path.exists(shell) and not os.path.exists(chrome):
            shutil.copy2(shell, chrome)

        log(f"✅ Chrome terinstall: {chrome}")
        return True
    except Exception as e:
        log(f"⚠️  Chrome download error: {e}")
        return False
    finally:
        try: os.remove(tmp_zip)
        except: pass
        shutil.rmtree(tmp_dir, ignore_errors=True)

def ensure_chromedriver():
    dst = f"{BASE}/chromedriver"
    if path_exists_big(dst, 1000000):
        log(f"✅ Chromedriver sudah ada.")
        return True

    url = f"https://storage.googleapis.com/chrome-for-testing-public/{CHROME_VERSION}/linux64/chromedriver-linux64.zip"
    tmp_zip = f"{BASE}/_cd.zip"
    tmp_dir = f"{BASE}/_cd_tmp"

    try:
        download_to(url, tmp_zip)
        log("Extract chromedriver...")
        with zipfile.ZipFile(tmp_zip, "r") as z:
            z.extractall(tmp_dir)

        src = f"{tmp_dir}/chromedriver-linux64/chromedriver"
        if not os.path.exists(src):
            raise Exception("Chromedriver binary tidak ditemukan")

        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)
        log(f"✅ Chromedriver terinstall: {dst}")
        return True
    except Exception as e:
        log(f"⚠️  Chromedriver error: {e}")
        return False
    finally:
        try: os.remove(tmp_zip)
        except: pass
        shutil.rmtree(tmp_dir, ignore_errors=True)

# ============================================================
# 6. CLOUDFLARED
# ============================================================
def ensure_cloudflared():
    dst = f"{BASE}/cf"
    if path_exists_big(dst, 1000000):
        log(f"✅ cloudflared sudah ada.")
        return True

    url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    try:
        download_to(url, dst)
        os.chmod(dst, 0o755)
        log(f"✅ cloudflared terinstall: {dst}")
        return True
    except Exception as e:
        log(f"⚠️  cloudflared error: {e}")
        return False

# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60, flush=True)
    print("  TITAN DEPS BOOTSTRAP v2.0 (Long-Term Fix)", flush=True)
    print("=" * 60, flush=True)

    os.makedirs(BASE, exist_ok=True)

    ensure_pip_packages()
    ensure_chrome()
    ensure_chromedriver()
    ensure_cloudflared()
    ensure_system_libs()

    print("=" * 60, flush=True)
    print("  BOOTSTRAP COMPLETE ✅", flush=True)
    print("=" * 60, flush=True)

if __name__ == "__main__":
    main()