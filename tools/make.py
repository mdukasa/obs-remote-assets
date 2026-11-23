"""Re-make the OBS Remote screenshots (../screenshots/*.png) with Microsoft Edge in headless mode.

    python pictures.py   # once: draws the made-up venue -> demo-data.js
    python make.py       # needs an obs-remote checkout: next to this repo, or set OBS_REMOTE=path

The app shots are the real www/index.html from obs-remote, connected to fake-obs.js instead of OBS. The setup
window shots (installer.png, setup-first-run.png) are the real setup/panel.html, fed a made-up status for a venue
PC at 192.168.1.50, with a real QR code from setup/qr.py (it decodes to http://192.168.1.50:8765/#pw=demo-password).
"""
import os
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # this assets repo
OUT = os.path.join(ROOT, "screenshots")
REPO = next((p for p in (os.environ.get("OBS_REMOTE"), os.path.join(os.path.dirname(ROOT), "obs-remote"),
                         os.path.join(os.path.dirname(ROOT), "obs_remote"))
             if p and os.path.exists(os.path.join(p, "www", "index.html"))), None)
if not REPO:
    sys.exit("Can't find obs-remote: clone it next to this repo, or set OBS_REMOTE to its folder.")
EDGE = next((p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                         r"C:\Program Files\Microsoft\Edge\Application\msedge.exe") if os.path.exists(p)), None)
sys.path.insert(0, os.path.join(REPO, "setup"))
import qr  # noqa: E402


def demo_page():
    with open(os.path.join(REPO, "www", "index.html"), encoding="utf-8") as f:
        page = f.read()
    marker = "<script>\n\"use strict\";"
    assert marker in page, "app script start not found"
    page = page.replace(marker, '<script src="demo-data.js"></script><script src="fake-obs.js"></script>\n' + marker, 1)
    path = os.path.join(HERE, "demo.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return path


# ---- setup window: the real setup/panel.html, with a made-up status instead of this PC's ----------------
def setup_status(first_run):
    """What setup/panel.py's /api/status would say on a made-up venue PC (192.168.1.50, router 192.168.1.1)."""
    url = "http://192.168.1.50:8765/"
    login = "#pw=demo-password"  # a made-up OBS login, like the real code carries
    ready = not first_run
    return {
        "version": "1.11.1", "port": 8765, "folder": r"C:\Users\venue\AppData\Local\Programs\OBS Remote",
        "data": r"C:\Users\venue\AppData\Local\OBS Remote",
        "obs": {"running": True, "ok": ready, "error": None if ready else "WebSocket server is off", "version": "32.2.2",
                "streaming": False, "recording": False, "ptz": {"ok": ready, "count": 3 if ready else 0, "error": None}},
        "ws": {"config": True, "enabled": ready, "port": 4455, "auth": True}, "password": "demo-password" if ready else "",
        "ptz": {"dll": "obs-ptz.dll", "version": "1.0.0", "ok": True} if ready else None,
        "ts": {"installed": ready, "running": ready, "ip": "100.64.10.20" if ready else None, "name": "venue-pc",
               "chosen": ready, "route": "192.168.1.50/32" if ready else None, "want": "192.168.1.50/32",
               "route_ok": ready, "stale": False, "dup": None, "key_off": True, "expires": ""},
        "firewall": {"ok": ready, "exists": ready},
        "server": {"answering": ready, "error": None if ready else "Connection refused", "startup": ready, "startmenu": ready},
        "lan": [{"alias": "Ethernet", "ip": "192.168.1.50", "dhcp": False, "gateway": "192.168.1.1"}],
        "codes": [{"label": "On this network (Ethernet)", "url": url, "folded": False, "svg": qr.svg(url + login, scale=7)}]
                 + ([{"label": "Over Tailscale", "url": "http://100.64.10.20:8765/", "folded": True,
                      "svg": qr.svg("http://100.64.10.20:8765/" + login, scale=7)}] if ready else []),
        "phones": [{"ip": "192.168.1.61", "ago": 25, "tailscale": False, "here": False, "name": None},
                   {"ip": "100.64.10.31", "ago": 610, "tailscale": True, "here": False, "name": "Sam's phone"}] if ready else [],
        "job": {"name": None, "running": False, "lines": [], "ok": None, "error": None, "done": None, "seq": 0},
    }


def setup_page(first_run=False):
    """setup/panel.html with fetch() answered from setup_status() instead of the setup window's own server."""
    import json
    with open(os.path.join(REPO, "setup", "panel.html"), encoding="utf-8") as f:
        page = f.read()
    shim = ("<script>const DEMO=%s;window.fetch=async u=>new Response(JSON.stringify(String(u).startsWith('/api/job')"
            "?DEMO.job:DEMO),{status:200,headers:{'Content-Type':'application/json'}});</script>\n"
            % json.dumps(setup_status(first_run)))
    marker = "<script>\nconst TOKEN"
    assert marker in page, "panel script start not found"
    page = page.replace(marker, shim + marker, 1).replace('src="/icon.svg"', 'src="icon.svg"')
    with open(os.path.join(REPO, "www", "icon.svg"), encoding="utf-8") as f:
        icon = f.read()
    with open(os.path.join(HERE, "icon.svg"), "w", encoding="utf-8") as f:
        f.write(icon)
    path = os.path.join(HERE, "setup-window%s.html" % ("-first-run" if first_run else ""))
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return path


def shoot(page, out, w, h, query=""):
    """Screenshot `page` with headless Edge. The demo's timers never stop, so Edge is killed once the file exists."""
    prof = tempfile.mkdtemp(prefix="obsr-shot-")
    url = "file:///" + page.replace("\\", "/") + query
    if os.path.exists(out):
        os.remove(out)
    p = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                          f"--user-data-dir={prof}", "--no-first-run", f"--window-size={w},{h}",
                          "--virtual-time-budget=6000", f"--screenshot={out}", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(240):
        if os.path.exists(out) and os.path.getsize(out) > 0:
            time.sleep(1)
            break
        time.sleep(0.25)
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
    if not os.path.exists(out):
        sys.exit(f"Edge made no screenshot of {page}")


def phone(out, h, query=""):
    """The app in a 390 px wide frame, like a phone. Windows won't make a window that narrow, so the frame
    sits in a wider window and the shot is cropped to it."""
    frame = os.path.join(HERE, "frame.html")
    with open(frame, "w", encoding="utf-8") as f:
        f.write(f'<!doctype html><body style="margin:0;background:#0d1117"><iframe src="demo.html{query}" '
                f'style="border:0;width:390px;height:{h}px;display:block"></iframe>')
    shoot(frame, out, 520, h)
    Image.open(out).crop((0, 0, 390 * 2, h * 2)).save(out, optimize=True)
    print("wrote", os.path.relpath(out, ROOT))


def trimmed(out, page, w, h):
    shoot(page, out, w, h)
    im = Image.open(out).convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((im.width - 1, im.height - 1)))
    box = ImageChops.difference(im, bg).getbbox()
    im = im.crop(box)
    pad = Image.new("RGB", (im.width, im.height + 24), bg.getpixel((0, 0)))  # keep the bottom margin trimming took
    pad.paste(im, (0, 0))
    pad.save(out, optimize=True)
    print("wrote", os.path.relpath(out, ROOT))


def framed(out, page, w, h, margin=20):
    """Shoot `page` in a w x h window (h chosen so the bottom edge falls between two cards), then trim the page's
    own margins and put an even `margin` (CSS px) of background round it."""
    shoot(page, out, w, h)
    im = Image.open(out).convert("RGB")
    bg_px = im.getpixel((im.width - 1, im.height - 1))
    box = ImageChops.difference(im, Image.new("RGB", im.size, bg_px)).getbbox()
    im = im.crop(box)
    m = margin * 2  # screenshots are at 2x
    pad = Image.new("RGB", (im.width + 2 * m, im.height + 2 * m), bg_px)
    pad.paste(im, (m, m))
    pad.save(out, optimize=True)
    print("wrote", os.path.relpath(out, ROOT), pad.size)


def main():
    if not EDGE:
        sys.exit("Microsoft Edge not found")
    os.makedirs(OUT, exist_ok=True)
    demo_page()
    phone(os.path.join(OUT, "live.png"), 1000)
    phone(os.path.join(OUT, "camera.png"), 1000, "?tab=cam")
    # installer.png keeps its name (older obs-remote READMEs link to it); since 1.11 it shows the setup window
    # Heights end each shot in the gap before the "Optional" heading.
    framed(os.path.join(OUT, "installer.png"), setup_page(), 880, 936)
    framed(os.path.join(OUT, "setup-first-run.png"), setup_page(first_run=True), 880, 712)


if __name__ == "__main__":
    main()
