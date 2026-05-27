"""
Daily Oranje — WK 2026 Scorito Video Agent
Genereert automatisch dagelijkse Scorito tips videos voor TikTok/Reels
Kosten: €0
"""

import os
import re
import math
import asyncio
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from groq import Groq
import edge_tts
from moviepy import AudioFileClip, VideoClip

# ─── CONFIG ───────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output_videos"
LOGO_PATH  = BASE_DIR / "Logo.png"
FONT_TITLE = str(BASE_DIR / "fonts" / "BebasNeue-Regular.ttf")
FONT_BODY  = str(BASE_DIR / "fonts" / "Anton-Regular.ttf")

TTS_VOICE = "nl-NL-MaartenNeural"
TTS_RATE  = "+30%"

TABLE_DURATION = 4.0  # seconden eindtabel na audio

WIDTH, HEIGHT = 1080, 1920
FPS = 24

ORANJE       = (255, 102, 0)
WIT          = (255, 255, 255)
VELD_GROEN   = (8, 28, 8)
GRIJS        = (160, 160, 160)
ROOD_ACCENT  = (220, 38, 38)
GROEN_ACCENT = (34, 197, 94)
GOUD         = (255, 215, 0)
ZILVER       = (192, 192, 192)
BRONS        = (184, 115, 51)

# ─── CUSTOM SCRIPT (laat leeg voor AI-generatie) ──────────────────────────────
CUSTOM_SCRIPT = """
Hier voorspellingen van groep F. Hiermee ga ik je rijk maken en kan je je vrienden inmaken met Scorito.
Nederland - Japan: 1-1, Japan is veel beter maar door een gelukje pakt Nederland nog een punt mee.
Nederland - Zweden: 2-1, Nederland opnieuw matig, maar Zweden nog veel slechter. Gyökeres kan beter op tafeltennis gaan.
Japan - Zweden: 2-1, Deze wedstrijd schreeuwt: beide teams scoren. Japan trekt aan het langste eind.
Japan - Tunesië: 3-1, Tunesië weet een doelpunt te maken maar is vrij kansloos.
Zweden - Tunesië: 1-0, Een bijzonder saaie wedstrijd.
Nederland - Tunesië: 4-0, Nederland krijgt eindelijk de smaak te pakken en buigt Tunesië voorover.
Nederland 1, Japan 2, Zweden 3, en Tunesië 4.
Volg om rijk te worden dit WK!
"""

# ─── GROEPEN ──────────────────────────────────────────────────────────────────
GROEPEN = [
    {
        "naam": "Groep F",
        "teams": ["Nederland", "Japan", "Zweden", "Tunesië"],
        "context": (
            "Nederland is favoriet maar Japan is gevaarlijk (versloeg Duitsland en Spanje op WK 2022). "
            "Frenkie de Jong is fit en onmisbaar op het middenveld. "
            "Dumfries is de uitblinker op rechtsback. "
            "Weghorst is beperkt in de opbouw. Memphis is inconsistent. "
            "Verwachte eindstand: 1. Nederland, 2. Japan, 3. Zweden, 4. Tunesië."
        ),
        "eindstand": [
            {"pos": 1, "country": "NEDERLAND", "flag": "NL", "kleur": GOUD},
            {"pos": 2, "country": "JAPAN",     "flag": "JP", "kleur": ZILVER},
            {"pos": 3, "country": "ZWEDEN",    "flag": "SE", "kleur": BRONS},
            {"pos": 4, "country": "TUNESIË",   "flag": "TN", "kleur": GRIJS},
        ],
    },
]


# ─── SCRIPT ───────────────────────────────────────────────────────────────────
def clean_script(text: str) -> str:
    text = re.sub(r'-{3,}', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def generate_script(groep: dict) -> str:
    client = Groq(api_key=GROQ_API_KEY)
    prompt = f"""
Je bent een Nederlandse voetbalanalist die Scorito WK 2026 tips geeft op TikTok.
Schrijf een gesproken video script van precies 45-55 seconden voor {groep['naam']}.
Teams: {', '.join(groep['teams'])}.
Context: {groep['context']}

Stijl: extreem direct, grof en vermakelijk. Kroegpraat. Geen diplomatische taal.
Gebruik hyperbool. Maak spelers belachelijk als ze het verdienen. Prijs goede spelers overdreven op.

Verplichte onderdelen in deze volgorde:
1. Hook - 1 pakkende zin die direct aanvalt
2. Alle 6 uitslagen met exacte scores (bijv. "Nederland - Japan: 1-1")
3. Eindstand van de groep (1e t/m 4e)
4. 2 spelers om NOOIT in Scorito te zetten - maak ze belachelijk
5. 2 spelers die je ABSOLUUT moet hebben - prijs ze de hemel in
6. CTA - volg voor de volgende groep

Schrijf ALLEEN de gesproken tekst. Geen aanwijzingen, geen haakjes, geen uitleg.
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    script = response.choices[0].message.content
    script = re.sub(r'\*+', '', script)
    script = re.sub(r'#+\s*', '', script)
    return script.strip()


# ─── AUDIO + WORD TIMINGS ─────────────────────────────────────────────────────
async def _audio_and_timing_async(script: str, path: str) -> list:
    communicate = edge_tts.Communicate(script, TTS_VOICE, rate=TTS_RATE,
                                       boundary="WordBoundary")
    timings = []
    audio_bytes = bytearray()
    async for event in communicate.stream():
        if event["type"] == "audio":
            audio_bytes.extend(event["data"])
        elif event["type"] == "WordBoundary":
            timings.append({
                "word":  event["text"],
                "start": event["offset"] / 10_000_000,
                "end":   (event["offset"] + event["duration"]) / 10_000_000,
            })
    with open(path, "wb") as f:
        f.write(bytes(audio_bytes))
    return timings


def generate_audio(script: str, path: str) -> list:
    return asyncio.run(_audio_and_timing_async(script, path))


# ─── ACHTERGROND: VOETBALVELD ─────────────────────────────────────────────────
def make_pitch_background() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), VELD_GROEN)
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    lc = (255, 255, 255, 38)
    lw = 6
    mx, my = 80, 160

    draw.rectangle([mx, my, WIDTH - mx, HEIGHT - my], outline=lc, width=lw)
    draw.line([(mx, HEIGHT // 2), (WIDTH - mx, HEIGHT // 2)], fill=lc, width=lw)
    cr, cx, cy = 215, WIDTH // 2, HEIGHT // 2
    draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], outline=lc, width=lw)
    draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=lc)
    ca = 45
    draw.arc([mx - ca, my - ca, mx + ca, my + ca], 0, 90, fill=lc, width=lw)
    draw.arc([WIDTH - mx - ca, my - ca, WIDTH - mx + ca, my + ca], 90, 180, fill=lc, width=lw)
    draw.arc([mx - ca, HEIGHT - my - ca, mx + ca, HEIGHT - my + ca], 270, 360, fill=lc, width=lw)
    draw.arc([WIDTH - mx - ca, HEIGHT - my - ca, WIDTH - mx + ca, HEIGHT - my + ca], 180, 270, fill=lc, width=lw)
    pa_w, pa_h = 480, 280
    draw.rectangle([(WIDTH - pa_w) // 2, my, (WIDTH + pa_w) // 2, my + pa_h], outline=lc, width=lw)
    draw.rectangle([(WIDTH - pa_w) // 2, HEIGHT - my - pa_h, (WIDTH + pa_w) // 2, HEIGHT - my], outline=lc, width=lw)
    sb_w, sb_h = 210, 115
    draw.rectangle([(WIDTH - sb_w) // 2, my, (WIDTH + sb_w) // 2, my + sb_h], outline=lc, width=lw)
    draw.rectangle([(WIDTH - sb_w) // 2, HEIGHT - my - sb_h, (WIDTH + sb_w) // 2, HEIGHT - my], outline=lc, width=lw)
    sp_r = 9
    sp_y_top = int(my + pa_h * 0.72)
    sp_y_bot = int(HEIGHT - my - pa_h * 0.72)
    draw.ellipse([cx - sp_r, sp_y_top - sp_r, cx + sp_r, sp_y_top + sp_r], fill=lc)
    draw.ellipse([cx - sp_r, sp_y_bot - sp_r, cx + sp_r, sp_y_bot + sp_r], fill=lc)
    ar = 155
    draw.arc([cx - ar, my + pa_h - ar, cx + ar, my + pa_h + ar], 0, 180, fill=lc, width=lw)
    draw.arc([cx - ar, HEIGHT - my - pa_h - ar, cx + ar, HEIGHT - my - pa_h + ar], 180, 360, fill=lc, width=lw)

    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


# ─── VLAGGEN ──────────────────────────────────────────────────────────────────
def draw_flag(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int, code: str):
    r = 8  # border radius approximation via outline
    if code == "NL":
        s = h // 3
        draw.rectangle([x, y,     x+w, y+s],   fill=(174, 28, 40))
        draw.rectangle([x, y+s,   x+w, y+2*s], fill=(255, 255, 255))
        draw.rectangle([x, y+2*s, x+w, y+h],   fill=(33, 70, 139))

    elif code == "JP":
        draw.rectangle([x, y, x+w, y+h], fill=(255, 255, 255))
        cr = int(min(w, h) * 0.3)
        draw.ellipse([x+w//2-cr, y+h//2-cr, x+w//2+cr, y+h//2+cr], fill=(188, 0, 45))

    elif code == "SE":
        draw.rectangle([x, y, x+w, y+h], fill=(0, 106, 167))
        bx = x + w * 5 // 16
        bw = max(w // 7, 8)
        bh = max(h // 5, 6)
        by = y + (h - bh) // 2
        draw.rectangle([x,  by, x+w, by+bh], fill=(254, 204, 2))
        draw.rectangle([bx, y,  bx+bw, y+h], fill=(254, 204, 2))

    elif code == "TN":
        draw.rectangle([x, y, x+w, y+h], fill=(231, 0, 19))
        cr  = int(min(w, h) * 0.28)
        cx2 = x + w // 2
        cy2 = y + h // 2
        draw.ellipse([cx2-cr, cy2-cr, cx2+cr, cy2+cr], fill=(255, 255, 255))
        # Crescent: grote witte cirkel minus verschoven rode cirkel
        cr2 = int(cr * 0.78)
        off = int(cr * 0.22)
        draw.ellipse([cx2-cr2+off, cy2-cr2, cx2+cr2+off, cy2+cr2], fill=(231, 0, 19))
        # Ster (vereenvoudigd vijfpuntig)
        sr, sx, sy = int(cr * 0.18), cx2 + int(cr * 0.38), cy2
        for i in range(5):
            a1 = -math.pi/2 + 2*math.pi*i/5
            a2 = -math.pi/2 + 2*math.pi*i/5 + math.pi/5
            outer = (sx + int(sr*math.cos(a1)), sy + int(sr*math.sin(a1)))
            inner = (sx + int(sr*0.4*math.cos(a2)), sy + int(sr*0.4*math.sin(a2)))
            draw.line([outer, (sx, sy), inner], fill=(231, 0, 19), width=2)

    else:
        draw.rectangle([x, y, x+w, y+h], fill=GRIJS)

    # Dunne rand om de vlag
    draw.rectangle([x, y, x+w-1, y+h-1], outline=(80, 80, 80), width=1)


# ─── VOETBAL ANIMATIE ─────────────────────────────────────────────────────────
def draw_football(draw: ImageDraw.Draw, cx: int, cy: int, r: int, angle: float):
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(228, 228, 228))
    pts = [
        (cx + int(r*0.35*math.cos(angle - math.pi/2 + 2*math.pi*i/5)),
         cy + int(r*0.35*math.sin(angle - math.pi/2 + 2*math.pi*i/5)))
        for i in range(5)
    ]
    draw.polygon(pts, fill=(18, 18, 18))
    for j in range(5):
        a  = angle - math.pi/2 + 2*math.pi*j/5 + math.pi/5
        px = cx + int(r*0.68*math.cos(a))
        py = cy + int(r*0.68*math.sin(a))
        pr = r * 0.28
        hpts = [
            (px + int(pr*math.cos(2*math.pi*i/6 + angle)),
             py + int(pr*math.sin(2*math.pi*i/6 + angle)))
            for i in range(6)
        ]
        draw.polygon(hpts, fill=(18, 18, 18))
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(50, 50, 50), width=2)


# ─── FRAME GENERATIE ──────────────────────────────────────────────────────────
def load_fonts():
    try:
        f_title = ImageFont.truetype(FONT_TITLE, 88)
        f_body  = ImageFont.truetype(FONT_BODY, 54)
        f_small = ImageFont.truetype(FONT_BODY, 36)
        f_badge = ImageFont.truetype(FONT_BODY, 30)
        f_table = ImageFont.truetype(FONT_BODY, 58)
        f_tpos  = ImageFont.truetype(FONT_TITLE, 80)
    except Exception:
        f_title = ImageFont.load_default(size=88)
        f_body  = ImageFont.load_default(size=54)
        f_small = ImageFont.load_default(size=36)
        f_badge = ImageFont.load_default(size=30)
        f_table = ImageFont.load_default(size=58)
        f_tpos  = ImageFont.load_default(size=80)
    return f_title, f_body, f_small, f_badge, f_table, f_tpos


def wrap_text(text: str, font, max_width: int, draw: ImageDraw.Draw) -> list:
    words = text.split()
    lines, current = [], []
    for word in words:
        test = " ".join(current + [word])
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def draw_outlined_text(draw, pos, text, font, fill, outline_width=4):
    x, y = pos
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x+dx, y+dy), text, font=font, fill=(0, 0, 0), anchor="mm")
    draw.text((x, y), text, font=font, fill=fill, anchor="mm")


def draw_karaoke_text(draw, lines: list, active_word_idx: int, f_body, start_y: int, line_h: int):
    space_w      = draw.textbbox((0, 0), " ", font=f_body)[2]
    word_counter = 0
    for line_i, line in enumerate(lines):
        y          = start_y + line_i * line_h
        words      = line.split()
        word_widths = [draw.textbbox((0, 0), w, font=f_body)[2] for w in words]
        total_w    = sum(word_widths) + space_w * max(0, len(words) - 1)
        x          = (WIDTH - total_w) // 2
        for word, ww in zip(words, word_widths):
            color = ORANJE if word_counter == active_word_idx else WIT
            draw_outlined_text(draw, (x + ww // 2, y), word, f_body, color)
            x += ww + space_w
            word_counter += 1


def detect_segment_type(text: str):
    t = text.lower()
    if re.search(r'\d\s*[-–]\s*\d', text):
        return "UITSLAG", ORANJE
    if any(w in t for w in ["nooit", "niet zetten", "vermijden", "belachelijk"]):
        return "VERMIJDEN", ROOD_ACCENT
    if any(w in t for w in ["absoluut", "must", "moet je hebben", "god", "goud"]):
        return "MUST HAVE", GROEN_ACCENT
    if any(w in t for w in ["eindstand", "eerste", "tweede", "derde", "vierde", "1.", "2.", "3.", "4."]):
        return "EINDSTAND", ORANJE
    if any(w in t for w in ["volg", "like", "rijk", "notificatie"]):
        return "VOLG ONS", ORANJE
    return None, None


def draw_badge(draw, text, x, y, font, color):
    bbox = draw.textbbox((x, y), text, font=font, anchor="lm")
    draw.rounded_rectangle([bbox[0]-14, bbox[1]-8, bbox[2]+14, bbox[3]+8],
                           radius=10, fill=color)
    draw.text((x, y), text, font=font, fill=WIT, anchor="lm")


def draw_header(draw, groep_naam, fonts):
    f_title, f_body, f_small, f_badge, f_table, f_tpos = fonts
    draw.rectangle([0, 0, WIDTH, 200], fill=ORANJE)
    draw.text((WIDTH // 2, 55), "SCORITO TIPS", font=f_small, fill=WIT, anchor="mm")
    try:
        efont = ImageFont.truetype("seguiemj.ttf", 60)
        draw.text((130, 148), "⚽", font=efont, anchor="mm")
    except Exception:
        pass
    draw.text((WIDTH // 2 + 20, 148), groep_naam.upper(), font=f_title, fill=WIT, anchor="mm")
    draw.polygon([(0, 192), (WIDTH, 208), (WIDTH, 218), (0, 202)], fill=WIT)


def create_static_frame(segment, groep_naam, logo, fonts,
                        active_word_idx, current_seg, total_segs, background) -> Image.Image:
    f_title, f_body, f_small, f_badge, f_table, f_tpos = fonts
    img  = background.copy()
    draw = ImageDraw.Draw(img)

    draw_header(draw, groep_naam, fonts)

    badge_label, badge_color = detect_segment_type(segment)
    if badge_label:
        draw_badge(draw, badge_label, 60, 270, f_badge, badge_color)

    padding = 80
    max_w   = WIDTH - padding * 2
    lines   = wrap_text(segment, f_body, max_w, draw)
    line_h  = 72
    total_h = len(lines) * line_h
    start_y = max((HEIGHT - total_h) // 2, 320)
    draw_karaoke_text(draw, lines, active_word_idx, f_body, start_y, line_h)

    datum = datetime.now().strftime("%d %b %Y").upper()
    draw.text((WIDTH // 2, HEIGHT - 100), f"DAILY ORANJE  •  {datum}",
              font=f_small, fill=GRIJS, anchor="mm")

    if logo is not None:
        size   = 100
        logo_r = logo.resize((size, size), Image.LANCZOS)
        lx, ly = 30, HEIGHT - size - 130
        img.paste(logo_r, (lx, ly), logo_r if logo_r.mode == "RGBA" else None)

    return img


# ─── EINDSTAND TABEL ──────────────────────────────────────────────────────────
def render_table_frame(background, fonts, logo, groep_naam, eindstand, t) -> np.ndarray:
    f_title, f_body, f_small, f_badge, f_table, f_tpos = fonts
    img  = background.copy()
    draw = ImageDraw.Draw(img)

    draw_header(draw, groep_naam, fonts)

    # Datum
    datum = datetime.now().strftime("%d %b %Y").upper()
    draw.text((WIDTH // 2, HEIGHT - 100), f"DAILY ORANJE  •  {datum}",
              font=f_small, fill=GRIJS, anchor="mm")

    # ── Fly-in: tabel schuift omhoog vanuit de onderkant ──────────────────────
    anim_dur  = 0.55
    progress  = min(1.0, t / anim_dur)
    ease      = 1 - (1 - progress) ** 3        # ease-out cubic
    target_y  = 280
    start_off = HEIGHT - target_y              # beginpositie (buiten beeld)
    slide_off = int(start_off * (1 - ease))   # neemt af naar 0

    panel_x   = 60
    panel_y   = target_y + slide_off
    panel_w   = WIDTH - 120
    row_h     = 155
    padding_v = 30
    panel_h   = len(eindstand) * row_h + padding_v * 2

    # Semi-transparant paneel
    panel = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 185))
    img_rgba = img.convert("RGBA")
    img_rgba.alpha_composite(panel, (panel_x, panel_y))
    img = img_rgba.convert("RGB")
    draw = ImageDraw.Draw(img)

    # Titel boven paneel
    draw.text((WIDTH // 2, panel_y - 28), "EINDSTAND",
              font=f_badge, fill=ORANJE, anchor="mm")

    # ── Rijen ──────────────────────────────────────────────────────────────────
    flag_w, flag_h = 110, 74
    for i, entry in enumerate(eindstand):
        ry  = panel_y + padding_v + i * row_h
        mid = ry + row_h // 2

        # Positienummer
        draw.text((panel_x + 52, mid), str(entry["pos"]),
                  font=f_tpos, fill=entry["kleur"], anchor="mm")

        # Vlag
        fx = panel_x + 100
        fy = mid - flag_h // 2
        draw_flag(draw, fx, fy, flag_w, flag_h, entry["flag"])

        # Landnaam
        draw_outlined_text(draw, (fx + flag_w + 34, mid),
                           entry["country"], f_table, WIT, outline_width=3)

        # Scheidingslijn (behalve na laatste rij)
        if i < len(eindstand) - 1:
            sep_y = ry + row_h
            draw.line([(panel_x + 10, sep_y), (panel_x + panel_w - 10, sep_y)],
                      fill=(80, 80, 80), width=1)

    # Logo
    if logo is not None:
        size   = 100
        logo_r = logo.resize((size, size), Image.LANCZOS)
        lx, ly = 30, HEIGHT - size - 130
        img_r  = img.convert("RGBA") if logo_r.mode == "RGBA" else img
        if logo_r.mode == "RGBA":
            img_r.paste(logo_r, (lx, ly), logo_r)
            img = img_r.convert("RGB")
        else:
            img.paste(logo_r, (lx, ly))

    return np.array(img)


# ─── VIDEO ASSEMBLAGE ─────────────────────────────────────────────────────────
def split_script(script: str) -> list:
    sentences = re.split(r"(?<=[.!?])\s+", script.strip())
    segments  = []
    for i in range(0, len(sentences), 2):
        block = " ".join(sentences[i : i + 2]).strip()
        if block:
            segments.append(block)
    return segments or [script]


def assign_timings_to_segments(word_timings: list, segments: list) -> list:
    result = []
    timing_idx = 0
    for seg in segments:
        count = len(re.findall(r'\S+', seg))
        seg_timings = [
            {**wt, "word_idx": local_i}
            for local_i, wt in enumerate(word_timings[timing_idx : timing_idx + count])
        ]
        timing_idx += count
        result.append({"text": seg, "timings": seg_timings})
    return result


def build_video(script, audio_path, groep_naam, output_path, word_timings, eindstand):
    logo           = Image.open(LOGO_PATH).convert("RGBA") if LOGO_PATH.exists() else None
    fonts          = load_fonts()
    background     = make_pitch_background()
    audio          = AudioFileClip(audio_path)
    audio_dur      = audio.duration
    total_duration = audio_dur + TABLE_DURATION
    segments       = split_script(script)
    seg_data       = assign_timings_to_segments(word_timings, segments)
    total_segs     = len(segments)

    events = []
    for seg_idx, seg in enumerate(seg_data):
        for wt in seg["timings"]:
            events.append({
                "start":    wt["start"],
                "word":     wt["word"],
                "word_idx": wt["word_idx"],
                "seg_idx":  seg_idx,
                "seg_text": seg["text"],
            })

    default_state = {"word": "", "word_idx": -1, "seg_idx": 0,
                     "seg_text": segments[0] if segments else ""}

    def get_active_state(t):
        for i, ev in enumerate(events):
            next_start = events[i + 1]["start"] if i + 1 < len(events) else float("inf")
            if ev["start"] <= t < next_start:
                return {"word": ev["word"], "word_idx": ev["word_idx"],
                        "seg_idx": ev["seg_idx"], "seg_text": ev["seg_text"]}
        return default_state

    static_cache: dict = {}

    def make_frame(t: float) -> np.ndarray:
        # ── Eindtabel fase ────────────────────────────────────────────────────
        if t >= audio_dur:
            table_t = t - audio_dur
            return render_table_frame(background, fonts, logo, groep_naam,
                                      eindstand, table_t)

        # ── Karaoke fase ──────────────────────────────────────────────────────
        state = get_active_state(t)
        key   = (state["seg_idx"], state["word_idx"])

        if key not in static_cache:
            static_cache[key] = create_static_frame(
                state["seg_text"], groep_naam, logo, fonts,
                state["word_idx"], state["seg_idx"], total_segs, background,
            )

        img  = static_cache[key].copy()
        draw = ImageDraw.Draw(img)

        # Animerende voetbal
        speed   = 0.6
        x_cycle = (t * speed) % 2.0
        bx      = 80 + int((WIDTH - 160) * (x_cycle if x_cycle <= 1.0 else 2.0 - x_cycle))
        by      = HEIGHT - 300 - int(60 * abs(math.sin(math.pi * t * 2.5)))
        draw_football(draw, bx, by, r=38, angle=t * speed * 2 * math.pi)

        # Progress bar
        bar_h = 10
        draw.rectangle([0, HEIGHT - bar_h, WIDTH, HEIGHT], fill=(30, 30, 30))
        draw.rectangle([0, HEIGHT - bar_h, int(WIDTH * t / audio_dur), HEIGHT], fill=ORANJE)

        return np.array(img)

    print(f"  Frames renderen ({FPS}fps × {total_duration:.1f}s = ~{int(FPS * total_duration)} frames)...")
    video = VideoClip(make_frame, duration=total_duration).with_audio(audio)
    video.write_videofile(str(output_path), fps=FPS, codec="libx264",
                          audio_codec="aac", logger=None)
    audio.close()
    video.close()


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    groep      = GROEPEN[0]
    datum      = datetime.now().strftime("%Y%m%d_%H%M")
    naam       = groep["naam"].replace(" ", "_")
    output     = OUTPUT_DIR / f"scorito_{naam}_{datum}.mp4"
    temp_audio = OUTPUT_DIR / f"_temp_audio_{datum}.mp3"

    if CUSTOM_SCRIPT.strip():
        print("Custom script gebruiken...")
        script = clean_script(CUSTOM_SCRIPT)
    else:
        print(f"Script genereren voor {groep['naam']}...")
        script = generate_script(groep)

    print(f"\n--- SCRIPT ---\n{script}\n--------------\n")

    print("Audio genereren + word timings ophalen...")
    word_timings = generate_audio(script, str(temp_audio))
    print(f"  {len(word_timings)} woorden getimed.")

    print("Video assembleren...")
    build_video(script, str(temp_audio), groep["naam"], output,
                word_timings, groep["eindstand"])

    temp_audio.unlink(missing_ok=True)
    print(f"\nKlaar! Video opgeslagen in: {output}")


if __name__ == "__main__":
    main()
