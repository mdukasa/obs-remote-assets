"""Draws the made-up venue used for OBS Remote's screenshots (no real camera footage or real people).

One large illustration of a hall is cropped into camera views and preset thumbnails, the way a PTZ camera
would frame them. Writes:
  - ../venue/venue.jpg          the whole hall, 3200x1800
  - ../venue/views/<view>.jpg   each camera view, 1920x1080 (and lectern-lower-third.jpg)
  - demo-data.js                base64 pictures for fake-obs.js (git-ignored)
Needs Pillow. The drawing is seeded, so it comes out the same every time.

    python pictures.py
"""
import base64
import io
import json
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
VENUE = os.path.join(os.path.dirname(HERE), "venue")
W, H = 3200, 1800
random.seed(7)


def font(size, bold=False):
    for name in (("segoeuib.ttf" if bold else "segoeui.ttf"), ("arialbd.ttf" if bold else "arial.ttf")):
        try:
            return ImageFont.truetype(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name), size)
        except OSError:
            pass
    return ImageFont.load_default()


def vgrad(d, box, top, bottom):
    x0, y0, x1, y1 = box
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        d.line([(x0, y), (x1, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))


def person(d, cx, base, s, suit, skin=(196, 150, 120), hair=(40, 32, 28)):
    """A simple standing/seated figure: shoulders at `base`, scale s."""
    d.rounded_rectangle([cx - 70 * s, base, cx + 70 * s, base + 220 * s], radius=int(40 * s), fill=suit)
    d.polygon([(cx - 18 * s, base), (cx + 18 * s, base), (cx, base + 60 * s)], fill=(235, 235, 235))
    d.rectangle([cx - 16 * s, base - 30 * s, cx + 16 * s, base + 4 * s], fill=skin)
    d.ellipse([cx - 38 * s, base - 120 * s, cx + 38 * s, base - 20 * s], fill=skin)
    d.chord([cx - 40 * s, base - 126 * s, cx + 40 * s, base - 50 * s], 180, 360, fill=hair)


def master():
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    vgrad(d, (0, 0, W, 260), (52, 48, 46), (86, 78, 70))           # ceiling
    vgrad(d, (0, 260, W, 1080), (206, 192, 170), (176, 160, 138))  # back wall
    for x in range(200, W, 400):                                   # ceiling lights
        d.ellipse([x - 60, 200, x + 60, 240], fill=(255, 244, 214))
    for x in (40, 2940):                                           # tall windows
        vgrad(d, (x, 360, x + 220, 960), (168, 196, 222), (120, 150, 178))
        d.rectangle([x, 360, x + 220, 960], outline=(120, 104, 86), width=14)
        d.line([(x + 110, 360), (x + 110, 960)], fill=(120, 104, 86), width=10)
    for x in range(300, 2900, 260):                                # wall panels
        d.line([(x, 300), (x, 1050)], fill=(190, 174, 150), width=4)
    # banner
    d.rectangle([560, 380, 900, 900], fill=(28, 70, 120))
    d.rectangle([560, 380, 900, 420], fill=(214, 168, 64))
    d.text((730, 560), "Community\nEvening", font=font(54, True), fill=(255, 255, 255), anchor="mm", align="center")
    d.text((730, 800), "2026", font=font(44), fill=(214, 168, 64), anchor="mm")
    # projection screen with a slide
    d.rectangle([1640, 330, 2580, 860], fill=(40, 40, 44))
    d.rectangle([1660, 350, 2560, 840], fill=(248, 248, 246))
    d.rectangle([1660, 350, 2560, 440], fill=(28, 70, 120))
    d.text((1700, 395), "Welcome", font=font(60, True), fill=(255, 255, 255), anchor="lm")
    for i, w in enumerate((640, 520, 700, 460)):
        y = 500 + i * 80
        d.ellipse([1710, y + 10, 1734, y + 34], fill=(214, 168, 64))
        d.rounded_rectangle([1760, y + 12, 1760 + w, y + 32], radius=10, fill=(170, 176, 186))
    # stage
    d.rectangle([380, 1000, 2820, 1110], fill=(122, 82, 52))
    d.rectangle([380, 1000, 2820, 1020], fill=(150, 104, 68))
    vgrad(d, (0, 1080, W, H), (150, 60, 58), (110, 40, 40))        # carpet
    # plants
    for x in (460, 2700):
        d.rectangle([x - 50, 900, x + 50, 1000], fill=(80, 60, 50))
        for a in range(0, 360, 30):
            r = math.radians(a)
            d.ellipse([x + 70 * math.cos(r) - 60, 800 + 50 * math.sin(r) - 50, x + 70 * math.cos(r) + 60, 800 + 50 * math.sin(r) + 50],
                      fill=(54 + a // 12, 120, 70))
    # speaker behind the lectern, chair and a seated guest
    person(d, 1250, 640, 1.25, (36, 44, 66))
    d.polygon([(1130, 760), (1370, 760), (1340, 1000), (1160, 1000)], fill=(104, 70, 44))
    d.rectangle([1110, 740, 1390, 775], fill=(134, 92, 58))
    d.ellipse([1236, 690, 1262, 716], fill=(30, 30, 30)); d.line([(1249, 716), (1249, 760)], fill=(30, 30, 30), width=6)
    d.rounded_rectangle([1520, 820, 1640, 1000], radius=12, fill=(70, 70, 76))
    person(d, 1580, 730, 0.95, (120, 46, 50))
    # audience rows: heads get bigger toward the camera
    for row in range(6):
        y = 1180 + row * 110
        s = 0.55 + row * 0.16
        step = int(150 * s)
        off = random.randint(0, step)
        for x in range(-off, W + step, step):
            d.rounded_rectangle([x - 60 * s, y, x + 60 * s, y + 200 * s], radius=int(20 * s), fill=(58, 52, 60))
            tone = random.choice([(196, 150, 120), (150, 104, 76), (224, 182, 150), (110, 74, 54)])
            hair = random.choice([(40, 32, 28), (90, 64, 40), (200, 200, 196), (30, 30, 30), (120, 40, 50)])
            d.ellipse([x - 34 * s, y - 70 * s, x + 34 * s, y + 6 * s], fill=hair if random.random() < 0.8 else tone)
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    # soft vignette and a little sensor noise, so it reads as a camera picture
    v = Image.new("L", (W, H), 0)
    ImageDraw.Draw(v).ellipse([-W * 0.15, -H * 0.2, W * 1.15, H * 1.2], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(220))
    im = Image.composite(im, Image.new("RGB", (W, H), (20, 18, 16)), v)
    noise = Image.effect_noise((W, H), 10).convert("RGB")
    return Image.blend(im, noise, 0.04)


def shot(m, cx, cy, w, out_w=960):
    """A 16:9 view centred on (cx, cy), w master pixels wide."""
    h = w * 9 / 16
    x0 = min(max(cx - w / 2, 0), W - w); y0 = min(max(cy - h / 2, 0), H - h)
    return m.crop((int(x0), int(y0), int(x0 + w), int(y0 + h))).resize((out_w, out_w * 9 // 16), Image.LANCZOS)


def lower_third(im, title, sub):
    im = im.copy(); d = ImageDraw.Draw(im, "RGBA")
    w, h = im.size
    d.rectangle([int(w * .05), int(h * .74), int(w * .55), int(h * .88)], fill=(28, 70, 120, 230))
    d.rectangle([int(w * .05), int(h * .74), int(w * .06), int(h * .88)], fill=(214, 168, 64, 255))
    d.text((int(w * .08), int(h * .775)), title, font=font(int(h * .055), True), fill=(255, 255, 255))
    d.text((int(w * .08), int(h * .835)), sub, font=font(int(h * .036)), fill=(220, 226, 236))
    return im


def jpg(im, q=82):
    b = io.BytesIO(); im.save(b, "JPEG", quality=q); return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def main():
    m = master()
    views = {  # name: (cx, cy, width in master pixels)
        "wide": (1600, 760, 3200), "stage": (1600, 720, 2300), "lectern": (1290, 690, 820),
        "speaker": (1250, 640, 520), "screen": (2110, 600, 1050), "audience": (1600, 1420, 1900),
        "guest": (1520, 700, 760),
    }
    shots = {k: shot(m, *v) for k, v in views.items()}
    data = {
        # scene / source pictures (what OBS screenshots would return)
        "Main camera": jpg(lower_third(shots["lectern"], "Dr. Sam Lee", "Guest speaker")),
        "Wide shot": jpg(shots["stage"]),
        "Slides": jpg(shots["screen"]),
        "CAM 1": jpg(shots["lectern"]),
        "CAM 2": jpg(shots["wide"]),
        # preset thumbnails per camera
        "presets": {
            "CAM 1": [("Lectern", "lectern"), ("Speaker close", "speaker"), ("Guest", "guest"), ("Stage", "stage"),
                      ("Screen", "screen"), ("Audience", "audience")],
            "CAM 2": [("Wide", "wide"), ("Stage", "stage"), ("Audience", "audience")],
        },
        "thumbs": {k: jpg(v.resize((320, 180), Image.LANCZOS), 75).split(",", 1)[1] for k, v in shots.items()},
    }
    with open(os.path.join(HERE, "demo-data.js"), "w", encoding="utf-8") as f:
        f.write("// made by pictures.py: illustrated demo pictures, no real footage\nwindow.DEMO=" + json.dumps(data) + ";\n")
    os.makedirs(os.path.join(VENUE, "views"), exist_ok=True)
    m.save(os.path.join(VENUE, "venue.jpg"), quality=92)
    for k, v in views.items():
        shot(m, *v, out_w=1920).save(os.path.join(VENUE, "views", k + ".jpg"), quality=90)
    lower_third(shot(m, *views["lectern"], out_w=1920), "Dr. Sam Lee", "Guest speaker").save(
        os.path.join(VENUE, "views", "lectern-lower-third.jpg"), quality=90)
    print("wrote demo-data.js, venue/venue.jpg and venue/views/*.jpg")


if __name__ == "__main__":
    main()
