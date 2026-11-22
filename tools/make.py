"""Re-make the OBS Remote screenshots (../screenshots/*.png) with Microsoft Edge in headless mode.

    python pictures.py   # once: draws the made-up venue -> demo-data.js
    python make.py       # needs an obs-remote checkout: next to this repo, or set OBS_REMOTE=path

The app shots are the real www/index.html from obs-remote, connected to fake-obs.js instead of OBS. The
installer shot is terminal.html, a copy of what setup/install.ps1 prints, with a real QR code from setup/qr.py.
"""
import html
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


# ---- installer screenshot: the lines install.ps1 prints, with its console colours ----------------------
C = {"Gray": "#cccccc", "DarkGray": "#767676", "Cyan": "#61d6d6", "Green": "#16c60c", "Yellow": "#f9f1a5",
     "Red": "#e74856", "White": "#f2f2f2"}


def terminal_page(url="http://192.168.1.50:8765/", version="1.6.0"):
    out = []
    say = lambda t="", c="Gray": out.append(f'<span style="color:{C[c]}">{html.escape(t)}</span>')
    rule = lambda: say("  " + "-" * 66, "DarkGray")

    def step(n, label, state, detail):
        color = {"OK": "Green", "WARN": "Yellow", "INFO": "Gray"}[state]
        tag = {"OK": " OK ", "WARN": "NOTE", "INFO": " -- "}[state]
        num = f"[{n}/4]" if n else "     "
        out.append(html.escape(f"  {num} {label.ljust(22, '.')} ") + f'<span style="color:{C[color]}">{tag}</span>'
                   + html.escape(f"  {detail}"))

    hint = lambda t: say("              " + t, "Yellow")
    say(); say("  OBS Remote setup", "Cyan"); say("  ================", "Cyan")
    say("  Sets up the phone remote for OBS on this PC. It takes about a minute."); say()
    step(1, "Python", "OK", "version 3.12")
    step(2, "OBS remote control", "OK", "WebSocket server is on (port 4455)")
    step(0, "PTZ cameras", "OK", "obs-ptz 1.0.0")
    hint("In OBS: PTZ Controls dock > Settings > Websocket access = 'Control'.")
    say("              Windows will now ask for permission to let phones on this network connect. Click Yes.", "Cyan")
    step(3, "Windows Firewall", "OK", "phones on this network can connect")
    step(4, "OBS Remote server", "OK", f"running (version {version}), starts with Windows")
    say(); rule(); say("   ALL DONE!  Now on each phone:", "Green"); rule()
    say("   1. Connect the phone to the same Wi-Fi network as this PC.")
    say("   2. Point the phone's camera at this code and tap the link:"); say()
    rows = qr.rows(url)
    cell = 9  # px per module: one character is 1 module wide and 2 modules tall, like the real half-block QR
    svg = (f'<svg width="{len(rows[0]) * cell}" height="{len(rows) * cell}" shape-rendering="crispEdges">'
           f'<rect width="100%" height="100%" fill="#fff"/>'
           + "".join(f'<rect x="{x * cell}" y="{y * cell}" width="{cell}" height="{cell}"/>'
                     for y, r in enumerate(rows) for x, c in enumerate(r) if c == "1") + "</svg>")
    out.append('<span class="qr">' + svg + "</span>")
    say(); say(f"        {url}", "White"); say()
    say("   3. Enter the OBS WebSocket password.")
    say("      It's in OBS: Tools > WebSocket Server Settings > Show Connect Info.", "DarkGray")
    say("   4. Add it to the home screen, so it opens like an app.")
    say("      iPhone: Share > Add to Home Screen.   Android: menu > Add to Home screen.", "DarkGray")
    say(); rule()
    say("   To see this code again, open 'Phone address.html' next to Install.bat.")
    say("   Tip: give this PC a fixed IP address in your router, so the code never changes.", "DarkGray"); say()
    body = "\n".join(out)
    page = f"""<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;background:#0c0c0c}}
.win{{margin:0;background:#0c0c0c;width:860px}}
.bar{{height:34px;background:#2b2b2b;display:flex;align-items:center;padding:0 12px;gap:8px;font:13px "Segoe UI",sans-serif;color:#ddd}}
.bar i{{width:16px;height:16px;border-radius:3px;background:#012456;display:inline-block}}
.bar b{{flex:1;font-weight:400}} .bar span{{color:#999;letter-spacing:14px}}
pre{{margin:0;padding:6px 14px 10px;font:14.5px/18px "Cascadia Mono",Consolas,monospace;color:#ccc;white-space:pre}}
.qr{{display:inline-block;margin-left:54px;vertical-align:top}} .qr svg{{display:block}}
</style><div class="win"><div class="bar"><i></i><b>OBS Remote setup</b><span>–▢✕</span></div><pre>{body}</pre></div>"""
    path = os.path.join(HERE, "terminal.html")
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


def main():
    if not EDGE:
        sys.exit("Microsoft Edge not found")
    os.makedirs(OUT, exist_ok=True)
    demo_page()
    phone(os.path.join(OUT, "live.png"), 1000)
    phone(os.path.join(OUT, "camera.png"), 1000, "?tab=cam")
    trimmed(os.path.join(OUT, "installer.png"), terminal_page(), 860, 1060)


if __name__ == "__main__":
    main()
