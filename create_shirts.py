"""
Daily Oranje — WK 2026 Shirt Designs
Genereert 3 PNG-bestanden klaar voor Printful (4500x5400px, transparante achtergrond)
"""

from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = r"C:\Users\niels\Claude agent\shirt_designs"
FONT_DIR = r"C:\Users\niels\Claude agent\fonts"
os.makedirs(OUT_DIR, exist_ok=True)

W, H = 4500, 5400  # Printful standaard front-print canvas
ORANJE = (255, 102, 0)      # #FF6600
WIT    = (255, 255, 255)
ZWART  = (0, 0, 0)

BEBAS  = os.path.join(FONT_DIR, "BebasNeue-Regular.ttf")
ANTON  = os.path.join(FONT_DIR, "Anton-Regular.ttf")

def center_x(draw, text, font, canvas_w):
    """Return x position to center text horizontally."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    return (canvas_w - tw) // 2

def fit_font(font_path, text, max_w, max_size=900):
    """Return largest font that fits within max_w pixels."""
    for size in range(max_size, 60, -10):
        f = ImageFont.truetype(font_path, size)
        dummy = Image.new("RGBA", (1, 1))
        d = ImageDraw.Draw(dummy)
        bbox = d.textbbox((0, 0), text, font=f)
        if bbox[2] - bbox[0] <= max_w:
            return f
    return ImageFont.truetype(font_path, 60)

# ──────────────────────────────────────────────────────────────
# SHIRT 1 — "The Clean Kit"
# Oranje shirt: "26" groot + "NEDERLAND" smal eronder
# ──────────────────────────────────────────────────────────────
def make_shirt1():
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    MARGIN = 300  # afstand van de randen

    # "26" zo groot mogelijk
    f_26 = fit_font(BEBAS, "26", W - MARGIN * 2, max_size=1800)
    x_26 = center_x(draw, "26", f_26, W)
    y_26 = 900
    draw.text((x_26, y_26), "26", font=f_26, fill=WIT)

    # Hoogte van "26" bepalen
    bbox_26 = draw.textbbox((x_26, y_26), "26", font=f_26)
    y_after_26 = bbox_26[3] + 80

    # "NEDERLAND" — breed gespatieerd
    nederland_letters = "N E D E R L A N D"
    f_ned = fit_font(BEBAS, nederland_letters, W - MARGIN * 2, max_size=220)
    x_ned = center_x(draw, nederland_letters, f_ned, W)
    draw.text((x_ned, y_after_26), nederland_letters, font=f_ned, fill=WIT)

    path = os.path.join(OUT_DIR, "shirt1_clean_kit.png")
    img.save(path, "PNG")
    print(f"OK Shirt 1 opgeslagen: {path}")

# ──────────────────────────────────────────────────────────────
# SHIRT 2 — "Een Leeuw Buigt Nooit"
# Zwart shirt: geometrische leeuwenkop (oranje) + tekst (wit)
# ──────────────────────────────────────────────────────────────
def draw_geometric_lion(draw, cx, cy, size):
    """
    Heraldische leeuwenkop — strak, vectorstijl, oranje silhouet.
    Opgebouwd uit vlakken zonder cartoon-ogen/neus.
    """
    import math
    s = size

    # ── MANEN: grote gelaagde driehoeken (buiten) ────────────
    # Laag 1: brede buitenmanen
    mane_pts_outer = []
    spikes = 16
    for i in range(spikes):
        angle_tip   = math.radians(360 / spikes * i - 90)
        angle_base1 = math.radians(360 / spikes * (i - 0.42) - 90)
        angle_base2 = math.radians(360 / spikes * (i + 0.42) - 90)
        ro  = s * 1.10   # punt
        rb  = s * 0.74   # basis
        tip   = (cx + ro * math.cos(angle_tip),   cy + ro * math.sin(angle_tip))
        base1 = (cx + rb * math.cos(angle_base1), cy + rb * math.sin(angle_base1))
        base2 = (cx + rb * math.cos(angle_base2), cy + rb * math.sin(angle_base2))
        draw.polygon([tip, base1, base2], fill=ORANJE)

    # Laag 2: binnenste manen-ring (fills de gaten op)
    mane_r2 = int(s * 0.75)
    draw.ellipse([cx-mane_r2, cy-mane_r2, cx+mane_r2, cy+mane_r2], fill=ORANJE)

    # ── HOOFD: breed zeshoek-achtig vlak ─────────────────────
    hw = int(s * 0.58)   # halve breedte hoofd
    hh = int(s * 0.65)   # halve hoogte hoofd
    # Hoofd als afgeronde veelhoek (breed voorhoofd, smaller kaak)
    head_pts = [
        (cx - hw * 0.60, cy - hh),          # linker voorhoofd
        (cx + hw * 0.60, cy - hh),          # rechter voorhoofd
        (cx + hw,        cy - hh * 0.30),   # rechter slaap
        (cx + hw * 0.80, cy + hh * 0.45),   # rechter wang
        (cx + hw * 0.42, cy + hh),          # rechter kaak
        (cx,             cy + hh * 1.08),   # kin (punt)
        (cx - hw * 0.42, cy + hh),          # linker kaak
        (cx - hw * 0.80, cy + hh * 0.45),   # linker wang
        (cx - hw,        cy - hh * 0.30),   # linker slaap
    ]
    draw.polygon(head_pts, fill=ORANJE)

    # ── OREN: puntige driehoeken bovenop hoofd ───────────────
    ear_w = int(s * 0.18)
    ear_h = int(s * 0.28)
    for sign in [-1, 1]:
        ex = cx + sign * int(s * 0.36)
        ey = cy - hh
        draw.polygon([
            (ex,           ey - ear_h),
            (ex - ear_w,   ey + ear_h // 3),
            (ex + ear_w,   ey + ear_h // 3),
        ], fill=ORANJE)

    # ── SNUIT: lichte veelhoek onder midden van hoofd ────────
    snout_w = int(s * 0.34)
    snout_h = int(s * 0.26)
    snout_y = cy + int(s * 0.12)
    snout_pts = [
        (cx,              snout_y - snout_h * 0.2),   # top midden
        (cx + snout_w,    snout_y),
        (cx + snout_w * 0.7, snout_y + snout_h),
        (cx - snout_w * 0.7, snout_y + snout_h),
        (cx - snout_w,    snout_y),
    ]
    draw.polygon(snout_pts, fill=(220, 90, 0))

    # ── NEUS: kleine donkere driehoek ────────────────────────
    nose_y = snout_y - int(s * 0.06)
    nose_w = int(s * 0.11)
    nose_h = int(s * 0.09)
    draw.polygon([
        (cx,           nose_y),
        (cx - nose_w,  nose_y + nose_h),
        (cx + nose_w,  nose_y + nose_h),
    ], fill=(140, 45, 0))

    # ── OGEN: witte amandelvorm met zwarte pupil ──────────────
    eye_w  = int(s * 0.13)
    eye_h  = int(s * 0.08)
    pupil_r = int(s * 0.045)
    for sign in [-1, 1]:
        ex = cx + sign * int(s * 0.22)
        ey = cy - int(s * 0.08)
        # Amandeloog (polygon)
        eye_pts = [
            (ex,           ey - eye_h),
            (ex + sign * eye_w * 0.5, ey - eye_h * 0.3),
            (ex + sign * eye_w, ey),
            (ex + sign * eye_w * 0.5, ey + eye_h * 0.3),
            (ex,           ey + eye_h),
            (ex - sign * eye_w * 0.5, ey + eye_h * 0.3),
            (ex - sign * eye_w * 0.2, ey),
            (ex - sign * eye_w * 0.5, ey - eye_h * 0.3),
        ]
        draw.polygon(eye_pts, fill=WIT)
        draw.ellipse([ex-pupil_r, ey-pupil_r, ex+pupil_r, ey+pupil_r], fill=ZWART)

    # ── WENKBRAUWEN: schuine zware balken ────────────────────
    bw = int(s * 0.20)
    bh = int(s * 0.06)
    for sign in [-1, 1]:
        ex = cx + sign * int(s * 0.22)
        ey = cy - int(s * 0.22)
        slant = int(s * 0.06) * sign
        draw.polygon([
            (ex - bw // 2,  ey + slant),
            (ex + bw // 2,  ey - slant),
            (ex + bw // 2,  ey - slant + bh),
            (ex - bw // 2,  ey + slant + bh),
        ], fill=(160, 50, 0))

def make_shirt2():
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    MARGIN = 280

    # ── Leeuw centraal bovenaan ───────────────────────────────
    lion_size = 820
    lion_cx   = W // 2
    lion_cy   = 1350
    draw_geometric_lion(draw, lion_cx, lion_cy, lion_size)

    # ── "EEN LEEUW BUIGT NOOIT" ───────────────────────────────
    main_text = "EEN LEEUW\nBUIGT NOOIT"
    lines = main_text.split("\n")

    f_main = fit_font(ANTON, "BUIGT NOOIT", W - MARGIN * 2, max_size=520)
    y_text = lion_cy + lion_size + 140

    for line in lines:
        x = center_x(draw, line, f_main, W)
        draw.text((x, y_text), line, font=f_main, fill=WIT)
        bbox = draw.textbbox((x, y_text), line, font=f_main)
        y_text = bbox[3] + 30

    # ── Dunne scheidingslijn ──────────────────────────────────
    y_line = y_text + 50
    line_margin = 600
    draw.rectangle([line_margin, y_line, W - line_margin, y_line + 8], fill=WIT)

    # ── "NEDERLAND — WK 2026" ─────────────────────────────────
    sub = "NEDERLAND  —  WK 2026"
    f_sub = fit_font(BEBAS, sub, W - MARGIN * 2 - 200, max_size=200)
    x_sub = center_x(draw, sub, f_sub, W)
    draw.text((x_sub, y_line + 55), sub, font=f_sub, fill=WIT)

    path = os.path.join(OUT_DIR, "shirt2_leeuw_buigt_nooit.png")
    img.save(path, "PNG")
    print(f"OK Shirt 2 opgeslagen: {path}")

# ──────────────────────────────────────────────────────────────
# SHIRT 3 — "IK HAD 'M OPGESTELD"
# Oranje shirt: witte tekst, badge-stijl
# ──────────────────────────────────────────────────────────────
def make_shirt3():
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    MARGIN = 220

    # ── Hoofd-slogan ──────────────────────────────────────────
    line1 = "IK HAD 'M"
    line2 = "OPGESTELD"

    f_main = fit_font(BEBAS, line2, W - MARGIN * 2, max_size=900)

    # Bereken totale hoogte om alles verticaal te centreren
    dummy_bbox1 = ImageDraw.Draw(Image.new("RGBA", (1,1))).textbbox((0,0), line1, font=f_main)
    dummy_bbox2 = ImageDraw.Draw(Image.new("RGBA", (1,1))).textbbox((0,0), line2, font=f_main)
    line_h = dummy_bbox1[3] - dummy_bbox1[1]

    # Start y zodat het blok verticaal goed zit (iets boven midden)
    y_start = int(H * 0.18)

    # Regel 1
    x1 = center_x(draw, line1, f_main, W)
    draw.text((x1, y_start), line1, font=f_main, fill=WIT)
    bbox1 = draw.textbbox((x1, y_start), line1, font=f_main)
    y2 = bbox1[3] + 20

    # Regel 2
    x2 = center_x(draw, line2, f_main, W)
    draw.text((x2, y2), line2, font=f_main, fill=WIT)
    bbox2 = draw.textbbox((x2, y2), line2, font=f_main)
    y_after_main = bbox2[3]

    # ── Badge-blok met subline ────────────────────────────────
    sub  = "Bondscoach  —  Keuken & Bank  —  WK 2026"
    f_sub = fit_font(BEBAS, sub, W - MARGIN * 2, max_size=160)
    x_sub = center_x(draw, sub, f_sub, W)

    badge_pad_x = 80
    badge_pad_y = 38
    sub_bbox = draw.textbbox((x_sub, 0), sub, font=f_sub)
    sub_w = sub_bbox[2] - sub_bbox[0]
    sub_h = sub_bbox[3] - sub_bbox[1]

    badge_y_top    = y_after_main + 100
    badge_y_bottom = badge_y_top + sub_h + badge_pad_y * 2
    badge_x_left   = x_sub - badge_pad_x
    badge_x_right  = x_sub + sub_w + badge_pad_x

    # Dunne witte border (geen fill — badge-stijl)
    border_w = 6
    draw.rectangle([badge_x_left,            badge_y_top,
                    badge_x_right,           badge_y_top + border_w], fill=WIT)
    draw.rectangle([badge_x_left,            badge_y_bottom - border_w,
                    badge_x_right,           badge_y_bottom], fill=WIT)
    draw.rectangle([badge_x_left,            badge_y_top,
                    badge_x_left + border_w, badge_y_bottom], fill=WIT)
    draw.rectangle([badge_x_right - border_w, badge_y_top,
                    badge_x_right,             badge_y_bottom], fill=WIT)

    # Subline tekst
    draw.text((x_sub, badge_y_top + badge_pad_y), sub, font=f_sub, fill=WIT)

    path = os.path.join(OUT_DIR, "shirt3_ik_had_m_opgesteld.png")
    img.save(path, "PNG")
    print(f"OK Shirt 3 opgeslagen: {path}")

def make_preview(filename, bg_color, label):
    """Plak het print-PNG op een gekleurde shirt-achtergrond voor preview."""
    src_path = os.path.join(OUT_DIR, filename)
    design = Image.open(src_path).convert("RGBA")

    # Verkleinen naar preview-formaat
    PW, PH = 1500, 1800
    preview = Image.new("RGBA", (PW, PH), bg_color + (255,))

    # Schaal design naar 60% van preview-breedte
    scale = 0.60
    new_w = int(PW * scale)
    new_h = int(design.height * new_w / design.width)
    design_small = design.resize((new_w, new_h), Image.LANCZOS)

    # Centreer horizontaal, begin op 15% van hoogte
    x = (PW - new_w) // 2
    y = int(PH * 0.10)
    preview.paste(design_small, (x, y), design_small)

    # Label onderaan
    try:
        f_lbl = ImageFont.truetype(BEBAS, 55)
    except:
        f_lbl = ImageFont.load_default()
    d = ImageDraw.Draw(preview)
    lbl_x = center_x(d, label, f_lbl, PW)
    d.text((lbl_x, PH - 100), label, font=f_lbl, fill=(200, 200, 200, 200))

    out = os.path.join(OUT_DIR, "PREVIEW_" + filename)
    preview.save(out, "PNG")
    print(f"OK Preview: {out}")

# ── RUN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Daily Oranje — Shirts genereren...\n")
    make_shirt1()
    make_shirt2()
    make_shirt3()

    print("\nPreviews genereren...")
    make_preview("shirt1_clean_kit.png",          ORANJE, "SHIRT 1 — THE CLEAN KIT")
    make_preview("shirt2_leeuw_buigt_nooit.png",  ZWART,  "SHIRT 2 — EEN LEEUW BUIGT NOOIT")
    make_preview("shirt3_ik_had_m_opgesteld.png", ORANJE, "SHIRT 3 — IK HAD M OPGESTELD")

    print(f"\nAlle designs staan in: {OUT_DIR}")
    print("Printful-bestanden: 4500x5400px PNG transparant")
