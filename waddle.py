"""
WADDLE  ·  Y2K kawaii desktop virtual pet
==========================================
Screen   : 480 × 320 px
Run      : python waddle.py
Deps     : pip install pygame numpy
Font     : Pixel7.ttf  (place next to this file — ships with the repo)

Optional background images (place next to waddle.py, any format pygame supports):
  360_F_438917562_...jpg  — holographic grid  (chill screen sky)
  wp9285390.png           — kawaii pastel      (unused slot)
  vibe.webp               — Y2K aesthetic      (boot screen)
"""

import pygame, math, random, sys, json, os
import urllib.request, urllib.parse, threading, datetime
import numpy as np
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

# ── LOCATION ──────────────────────────────────────────────────────────────────
# Change these to your city — used for live weather on the chill screen.
# Find lat/lon at: https://www.latlong.net/
LAT  = 35.9606
LON  = -83.9207
CITY = "Knoxville, TN"

# ── SCREEN ────────────────────────────────────────────────────────────────────
SW, SH = 480, 320
screen = pygame.display.set_mode((SW, SH))
pygame.display.set_caption("Waddle")
clock  = pygame.time.Clock()
FPS    = 30

# ── PHOTO BACKGROUNDS ─────────────────────────────────────────────────────────
_IMG_DIR = os.path.dirname(os.path.abspath(__file__)) or "."
def _load_img(name, size=(SW, SH)):
    try:
        path = os.path.join(_IMG_DIR, name)
        img  = pygame.image.load(path)
        return pygame.transform.smoothscale(img, size).convert()
    except Exception:
        return None

IMG_HOLO   = _load_img("chill.jpg")
IMG_KAWAII = _load_img("wp9285390.png")
IMG_VIBE   = _load_img("vibe.png")
IMG_BOOT   = _load_img("loading_screen.png")

def _load_img_native(path):
    """Load an image at its native resolution (no rescale), with alpha."""
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        return None

# Optional small figurine sprite — name it "figurine.png" and place next to waddle.py.
# Appears on the shelf in the code game room. Falls back to a drawn star if absent.
IMG_PIX_PENGUIN = _load_img_native(os.path.join(_IMG_DIR, "figurine.png"))

# ── SPRITE PREFETCH ───────────────────────────────────────────────────────────
# Small CC0 sprites downloaded once to the game folder on first launch.
_SPRITE_URLS = {
    'spr_heart.png':   'https://opengameart.org/sites/default/files/hearts16x16_1.png',
}
def _prefetch_sprites():
    for name, url in _SPRITE_URLS.items():
        dest = os.path.join(_IMG_DIR, name)
        if not os.path.exists(dest):
            try:
                with urllib.request.urlopen(url, timeout=8) as r:
                    raw = r.read()
                with open(dest, 'wb') as f: f.write(raw)
            except Exception:
                pass
threading.Thread(target=_prefetch_sprites, daemon=True).start()

# These may be None on first launch (prefetch not complete yet) — all usages fall back gracefully
IMG_HEART    = _load_img('spr_heart.png', size=(16,16))

# ── FONTS ─────────────────────────────────────────────────────────────────────
def pf(sz):
    for name in ["Pixel7.ttf","pixel7.ttf"]:
        if os.path.exists(name):
            try: return pygame.font.Font(name, sz)
            except: pass
    return pygame.font.SysFont("monospace", sz, bold=False)

F8  = pf(10)   # small labels
F_SM= pf(9)    # lighter-weight small — stat labels, dense terminal text
F11 = pf(13)   # body text
F14 = pf(16)   # medium
F18 = pf(20)   # large
F24 = pf(26)   # title/score
F32 = pf(34)   # big impact

def blit_c(surf, font, text, color, cx, y, aa=False):
    s = font.render(str(text), aa, color)
    surf.blit(s, (int(cx - s.get_width()//2), int(y)))
    return s.get_height()

def blit_l(surf, font, text, color, x, y, aa=False):
    s = font.render(str(text), aa, color)
    surf.blit(s, (int(x), int(y)))
    return s.get_height()

def blit_shadow_c(surf, font, text, color, cx, y, sh=(0,0,0,120)):
    """Blit centred text with a 1-pixel drop shadow for photo backgrounds."""
    sh_surf = pygame.Surface(font.size(str(text)), pygame.SRCALPHA)
    shadow  = font.render(str(text), False, sh[:3])
    sh_surf.blit(shadow, (0,0)); sh_surf.set_alpha(sh[3])
    s = font.render(str(text), False, color)
    surf.blit(sh_surf, (int(cx - s.get_width()//2)+1, int(y)+1))
    surf.blit(s,       (int(cx - s.get_width()//2),   int(y)))
    return s.get_height()

def blit_shadow_l(surf, font, text, color, x, y, sh=(0,0,0,120)):
    """Blit left-aligned text with a 1-pixel drop shadow for photo backgrounds."""
    s = font.render(str(text), False, color)
    shadow = font.render(str(text), False, sh[:3])
    sh_surf = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    sh_surf.blit(shadow, (0,0)); sh_surf.set_alpha(sh[3])
    surf.blit(sh_surf, (int(x)+1, int(y)+1))
    surf.blit(s,       (int(x),   int(y)))
    return s.get_height()

# ── COLOURS ───────────────────────────────────────────────────────────────────
BG_PINK  = (255, 215, 235)
BG_DREAM = (13,  7,   30)
BG_DODGE = (11,  3,   20)

PUR      = (125, 72,  205)
PUR_L    = (190, 150, 255)
PUR_D    = (62,  30,  140)
WHI      = (255, 255, 255)
TXT_DK   = (52,  16,  68)
TXT_MD   = (105, 55,  135)
TXT_LT   = (172, 135, 205)

WIN_BAR  = (210, 100, 195)   # hot-pink title bar (error.jpg reference)
WIN_BG   = (255, 238, 250)   # blush-pink window interior
WIN_BDR  = (225, 80,  200)   # vivid pink border
WIN_BTN  = (255, 60,  120)   # hot-pink close button

C_HNG    = (238, 72,  58)
C_HAP    = (220, 140, 255)
C_NRG    = (48,  188, 118)

# ── SOUND SYSTEM ──────────────────────────────────────────────────────────────
_RATE = 44100
def _make_tone(freq, dur, vol=0.22, wave='sine', decay=True):
    """Generate a tone as a pygame Sound object."""
    try:
        n   = int(_RATE * dur)
        t   = np.linspace(0, dur, n, False)
        if wave == 'sine':
            sig = np.sin(2 * np.pi * freq * t)
        elif wave == 'square':
            sig = np.sign(np.sin(2 * np.pi * freq * t))
        elif wave == 'tri':
            sig = 2 * np.arcsin(np.sin(2 * np.pi * freq * t)) / np.pi
        else:
            sig = np.sin(2 * np.pi * freq * t)
        if decay:
            env = np.linspace(1.0, 0.0, n) ** 1.4
            sig = sig * env
        sig = np.clip(sig * vol, -1.0, 1.0)
        samples = (sig * 32767).astype(np.int16)
        sound   = pygame.sndarray.make_sound(samples)
        return sound
    except Exception:
        return None

def _chord(freqs, dur, vol=0.18):
    try:
        n   = int(_RATE * dur)
        t   = np.linspace(0, dur, n, False)
        sig = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)
        env = np.linspace(1.0, 0.0, n) ** 1.2
        sig = np.clip(sig * env * vol, -1.0, 1.0)
        samples = (sig * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(samples)
    except Exception:
        return None

class Sounds:
    """Lazy-loaded sound effects. Call .play_X() anywhere."""
    _s = {}
    _ok = None

    @classmethod
    def _init(cls):
        if cls._ok is not None: return
        try:
            pygame.mixer.init(_RATE, -16, 1, 512)
            cls._ok = True
        except Exception:
            cls._ok = False

    @classmethod
    def _get(cls, key, fn):
        cls._init()
        if not cls._ok: return
        if key not in cls._s:
            cls._s[key] = fn()
        return cls._s[key]

    @classmethod
    def _play(cls, key, fn):
        s = cls._get(key, fn)
        if s: s.play()

    @classmethod
    def menu_beep(cls):
        cls._play('menu', lambda: _make_tone(660, 0.06, 0.15, 'square', decay=False))

    @classmethod
    def confirm(cls):
        cls._play('confirm', lambda: _chord([523, 659, 784], 0.18, 0.20))

    @classmethod
    def feed(cls):
        cls._play('feed', lambda: _chord([392, 523, 659], 0.25, 0.22))

    @classmethod
    def sad_boop(cls):
        cls._play('sad', lambda: _make_tone(220, 0.28, 0.18, 'sine'))

    @classmethod
    def happy_chime(cls):
        cls._play('happy_c', lambda: _chord([523, 659, 784, 1047], 0.30, 0.20))

    @classmethod
    def game_over(cls):
        cls._play('go', lambda: _make_tone(196, 0.55, 0.22, 'tri'))

    @classmethod
    def catch_fish(cls):
        cls._play('fish', lambda: _make_tone(880, 0.09, 0.18, 'sine'))

    @classmethod
    def boot_blip(cls):
        cls._play('boot', lambda: _make_tone(440, 0.05, 0.12, 'square', decay=False))

    @classmethod
    def boot_done(cls):
        cls._play('boot_d', lambda: _chord([261, 329, 392, 523], 0.55, 0.25))

    @classmethod
    def dream_win(cls):
        cls._play('dwin', lambda: _chord([659, 784, 1047], 0.35, 0.22))

    @classmethod
    def dream_lose(cls):
        cls._play('dlose', lambda: _make_tone(294, 0.30, 0.18, 'tri'))

    @classmethod
    def virus_alert(cls):
        cls._play('virus', lambda: _make_tone(140, 0.45, 0.24, 'square'))

# ── PIXEL PALETTE — Waddle sprite colours ────────────────────────────────────
# W_BD = body dark blue  W_BM = body mid   W_BH = body highlight
# W_WH = belly white     W_PK = blush pink W_OR = beak/feet orange
# W_OD = beak dark       W_EY = eye dark   W_SH = eye shine
# W_TR = transparent (None → skipped when drawing)
W_BD=(126,200,227); W_BM=(86,164,196); W_BH=(186,232,250)
W_WH=(255,240,252); W_PK=(255,148,188); W_OR=(255,200,96)
W_OD=(228,164,42);  W_EY=(30,14,48);   W_SH=(255,255,255)
W_TR=None

# ── HELPERS ───────────────────────────────────────────────────────────────────
def clamp_color(r, g, b):
    return (max(0,min(255,int(r))), max(0,min(255,int(g))), max(0,min(255,int(b))))

def draw_glass(surf, x, y, w, h, r=10, tint=(255,255,255), a=52):
    s = pygame.Surface((w,h), pygame.SRCALPHA)
    pygame.draw.rect(s, (*tint, a),   (0,0,w,h), border_radius=r)
    pygame.draw.rect(s, (*tint, 150), (0,0,w,h), 2, border_radius=r)
    # Top sheen — strong gradient covers top 45%
    sh = max(1, h*9//20)
    for i in range(sh):
        al = int(115 * (1 - i/sh)**1.2)
        pygame.draw.line(s, (255,255,255,al), (r+1,i+2),(w-r-1,i+2))
    # Bright centre glint at very top
    gw = max(8, w*2//5); gx2 = (w-gw)//2
    for i in range(min(4, sh)):
        pygame.draw.line(s, (255,255,255, max(0,175-i*42)), (gx2, i+3), (gx2+gw, i+3))
    # Subtle bottom inner shadow for depth
    if h > 14:
        for i in range(min(4, h//4)):
            ba = int(28*(1-i/4))
            pygame.draw.line(s,(0,0,0,ba),(r,h-2-i),(w-r,h-2-i))
    surf.blit(s,(int(x),int(y)))

def draw_win(surf, x, y, w, h, title="", r=10):
    """Y2K/kawaii window chrome. Returns inner content y."""
    x,y,w,h = int(x),int(y),int(w),int(h)
    # Drop shadow — offset (5,6), soft spread
    for si in range(3):
        sa = 45 - si*12
        sd = pygame.Surface((w+si*2, h+si*2), pygame.SRCALPHA)
        pygame.draw.rect(sd,(0,0,0,sa),(0,0,w+si*2,h+si*2),border_radius=r+si)
        surf.blit(sd,(x+4-si, y+6-si))
    # Window body — slightly warm white
    pygame.draw.rect(surf, WIN_BG,  (x,y,w,h), border_radius=r)
    pygame.draw.rect(surf, WIN_BDR, (x,y,w,h), 2, border_radius=r)
    # Title bar — 24px, gradient feel via two rects
    BAR=24
    pygame.draw.rect(surf, WIN_BAR,  (x,y,w,BAR), border_radius=r)
    pygame.draw.rect(surf, WIN_BAR,  (x,y+r,w,BAR-r))
    # Bar highlight gradient (lighter at top, fades down)
    for bi in range(6):
        ba = max(0, 80 - bi*14)
        hl = pygame.Surface((w-8, 1), pygame.SRCALPHA)
        hl.fill((255,255,255,ba))
        surf.blit(hl,(x+4, y+2+bi))
    # Window control buttons (X, □, -)
    for bi,(bc,bl) in enumerate([(WIN_BTN,'×'),((200,160,240),'□'),((220,180,250),'−')]):
        bx=x+w-18-(bi*17); by=y+5
        pygame.draw.rect(surf,bc,(bx,by,13,13),border_radius=4)
        pygame.draw.rect(surf,clamp_color(bc[0]-30,bc[1]-30,bc[2]-30),(bx,by,13,13),1,border_radius=4)
        # Glint on button
        gls = pygame.Surface((10,4),pygame.SRCALPHA)
        gls.fill((255,255,255,60))
        surf.blit(gls,(bx+2,by+2))
        xr = pygame.font.SysFont("monospace",8,bold=False).render(bl,False,WHI)
        surf.blit(xr,(bx+7-xr.get_width()//2, by+7-xr.get_height()//2))
    # Title text
    if title:
        tf = pygame.font.SysFont("monospace",9,bold=False).render(title,False,WHI)
        surf.blit(tf,(x+8, y+BAR//2-tf.get_height()//2))
    # Glass sheen on content body
    cb_h = h - BAR - 2
    if cb_h > 6:
        bsh = min(cb_h, cb_h//2+6)
        body_sh = pygame.Surface((w-6, bsh), pygame.SRCALPHA)
        for i in range(bsh):
            al = int(38*(1-(i/bsh)**0.65))
            pygame.draw.line(body_sh,(255,255,255,al),(2,i),(w-10,i))
        surf.blit(body_sh,(x+3, y+BAR+3))
    return y+BAR+6

def grid_bg(surf, col, sp=22, a=30):
    s = pygame.Surface((SW,SH), pygame.SRCALPHA)
    for x in range(0,SW,sp): pygame.draw.line(s,(*col,a),(x,0),(x,SH))
    for y in range(0,SH,sp): pygame.draw.line(s,(*col,a),(0,y),(SW,y))
    surf.blit(s,(0,0))

# ── SPRITE ────────────────────────────────────────────────────────────────────
PX = 7   # pixel size on the main pet screen (7 × 7 screen-pixels per grid cell)

def make_grid(mood, wing_up=False):
    """
    Build the 26×28 pixel grid that defines Waddle's appearance.
    Each cell maps to a colour constant (W_BD, W_WH, …) or W_TR (transparent).
    Mood changes eyes, beak, wing position, and blush intensity.
    The grid is then rasterised into a pygame Surface by get_spr().
    """
    GW,GH=26,28
    G=[[W_TR]*GW for _ in range(GH)]
    def s(r,c,col):
        if 0<=r<GH and 0<=c<GW: G[r][c]=col
    def fill(r,c1,c2,col):
        for c in range(max(0,c1),min(GW,c2+1)): s(r,c,col)
    def wings(br):
        fill(br,0,5,W_BD); s(br,0,W_BH); s(br,1,W_BH)
        fill(br+1,0,4,W_BD); fill(br+2,0,3,W_BD); fill(br+3,0,3,W_BM)
        fill(br,20,25,W_BD); s(br,24,W_BH); s(br,25,W_BH)
        fill(br+1,21,25,W_BD); fill(br+2,22,25,W_BD); fill(br+3,22,25,W_BM)

    fill(0,7,18,W_BD)
    fill(1,5,20,W_BD); s(1,5,W_BH); s(1,20,W_BH)
    fill(2,3,22,W_BD); s(2,3,W_BH); s(2,22,W_BH)
    fill(3,2,23,W_BD); s(3,2,W_BH); s(3,23,W_BH)
    for r in range(4,10): fill(r,2,23,W_BD)
    fill(9,3,22,W_BD)

    if mood=='happy': wings(13+(-2 if wing_up else 0))
    elif mood=='sad': wings(12)
    else:             wings(10)

    fill(10,4,21,W_BD); fill(10,9,16,W_WH)
    fill(11,3,22,W_BD); fill(11,8,17,W_WH)
    fill(12,3,22,W_BD); fill(12,7,18,W_WH)
    fill(13,3,22,W_BD); fill(13,7,18,W_WH)
    fill(14,3,22,W_BD); fill(14,7,18,W_WH)
    fill(15,3,22,W_BD); fill(15,8,17,W_WH)
    fill(16,4,21,W_BD); fill(16,9,16,W_WH)
    fill(17,5,20,W_BD); fill(17,10,15,W_WH)
    fill(18,6,19,W_BM)
    s(19,8,W_BM);s(19,9,W_BM);s(19,16,W_BM);s(19,17,W_BM)
    fill(20,6,12,W_OR); fill(20,13,19,W_OR)
    fill(21,7,12,W_OD); fill(21,13,18,W_OD)

    bc=(210,110,148) if mood=='sad' else W_PK
    for dr in range(3):
        for dc in range(3): s(9+dr,3+dc,bc); s(9+dr,20+dc,bc)
    if mood=='happy':
        # Extend blush outward — cols 2 and 23 are on the body at row 9-11
        for dr in range(3): s(9+dr,2,W_PK); s(9+dr,23,W_PK)

    if mood=='hungry':
        fill(7,11,14,W_OR); fill(8,10,15,W_OR); fill(9,11,14,W_OR)
        s(9,12,(255,95,125)); s(9,13,(255,95,125))
    else:
        fill(7,11,14,W_OR); fill(8,10,15,W_OR)

    def eye(er,ec):
        fill(er,ec,ec+3,W_EY); fill(er+1,ec-1,ec+4,W_EY)
        fill(er+2,ec-1,ec+4,W_EY); fill(er+3,ec,ec+3,W_EY)
        s(er,ec,W_SH); s(er,ec+1,W_SH); s(er+1,ec,W_SH)

    if mood=='happy':
        eye(3,5); eye(3,17)
        fill(6,5,8,W_BD); fill(6,17,20,W_BD)
    elif mood=='idle':
        eye(3,5); eye(3,17)
    elif mood=='sleepy':
        fill(5,5,8,W_EY); fill(6,4,9,W_EY); fill(4,4,9,W_BM)
        fill(5,17,20,W_EY); fill(6,16,21,W_EY); fill(4,16,21,W_BM)
    elif mood=='hungry':
        eye(2,5); eye(2,17)
    elif mood=='sad':
        fill(4,6,9,W_EY); fill(5,5,10,W_EY); fill(6,6,9,W_EY); s(4,6,W_SH)
        fill(4,16,19,W_EY); fill(5,15,20,W_EY); fill(6,16,19,W_EY); s(4,16,W_SH)
    elif mood=='excited':
        # Wide star eyes
        eye(3,5); eye(3,17)
        # Huge grin — fill mouth area with orange beak + happy curve
        fill(6,5,9,W_BD); fill(6,17,21,W_BD)
        pass  # no extra row-8 blush pixel
    return G

# Sprite surface cache
_cache = {}
def get_spr(mood, px, wing_up=False):
    k=(mood,px,wing_up)
    if k not in _cache:
        g=make_grid(mood,wing_up)
        s=pygame.Surface((26*px,28*px),pygame.SRCALPHA)
        for gy,row in enumerate(g):
            for gx,col in enumerate(row):
                if col: pygame.draw.rect(s,col,(gx*px,gy*px,px,px))
        _cache[k]=s
    return _cache[k]

def blit_spr(surf, mood, px, ox, oy, wing_up=False, sy=1.0):
    base=get_spr(mood,px,wing_up)
    if abs(sy-1.0)<0.015:
        surf.blit(base,(int(ox),int(oy)))
    else:
        w,h=base.get_size()
        nh=max(1,int(h*sy))
        sc=pygame.transform.scale(base,(w,nh))
        surf.blit(sc,(int(ox),int(oy+h//2-nh//2)))

# ── BACK-VIEW WADDLE (Dream screen) ──────────────────────────────────────────
def draw_waddle_back(surf, cx, cy, sc=1.0):
    """Draw Waddle from behind using smooth shapes."""
    cx,cy=int(cx),int(cy)
    def r(a): return max(1,int(a*sc))
    # Body
    pygame.draw.ellipse(surf,W_BM,(cx-r(17),cy-r(6),r(34),r(30)))
    pygame.draw.ellipse(surf,W_BD,(cx-r(15),cy-r(8),r(30),r(30)))
    # Head
    pygame.draw.circle(surf,W_BD,(cx,cy-r(22)),r(20))
    pygame.draw.circle(surf,W_BH,(cx-r(7),cy-r(30)),r(6))
    # Ear bumps
    pygame.draw.circle(surf,W_BD,(cx-r(16),cy-r(16)),r(6))
    pygame.draw.circle(surf,W_BD,(cx+r(16),cy-r(16)),r(6))
    # Wings on sides
    pygame.draw.ellipse(surf,W_BM,(cx-r(33),cy+r(2),r(18),r(12)))
    pygame.draw.ellipse(surf,W_BD,(cx-r(31),cy+r(1),r(16),r(10)))
    pygame.draw.ellipse(surf,W_BM,(cx+r(15),cy+r(2),r(18),r(12)))
    pygame.draw.ellipse(surf,W_BD,(cx+r(17),cy+r(1),r(16),r(10)))

# ── DESK SCENE ────────────────────────────────────────────────────────────────
def draw_desk(surf, cx, dy, frame, state):
    """
    Neon gaming desk — inspired by the cherry blossom gaming room reference.
    cx = horizontal centre, dy = desk surface y.
    """
    cx, dy = int(cx), int(dy)

    # ── Desk surface — wide, dark wood with neon pink underglow ──
    dw = 220; dh = 14
    dx = cx - dw//2
    # Underglow — soft neon pink bloom beneath desk
    for gi in range(22, 0, -2):
        ga = int(38 * (gi/22))
        ug = pygame.Surface((dw+gi*4, gi*3), pygame.SRCALPHA)
        pygame.draw.ellipse(ug, (255, 40, 140, ga), (0, 0, dw+gi*4, gi*3))
        surf.blit(ug, (dx - gi*2, dy + dh - gi))
    # Desk top — white/pink kawaii desk
    pygame.draw.rect(surf, (255, 235, 248), (dx, dy, dw, dh), border_radius=4)
    pygame.draw.rect(surf, (255, 255, 255), (dx, dy, dw, 3), border_radius=4)   # top highlight
    pygame.draw.rect(surf, (220, 130, 200), (dx, dy, dw, dh), 1, border_radius=4)
    # Desk legs
    for lx2 in [dx+12, dx+dw-22]:
        pygame.draw.rect(surf, (240, 190, 225), (lx2, dy+dh, 10, 30), border_radius=3)

    # ── Monitors — dual screen setup ──
    # Left monitor — white bezel, pink screen glow
    ml_x = cx - 96; ml_y = dy - 82; ml_w = 88; ml_h = 58
    pygame.draw.rect(surf, (255, 230, 245), (ml_x-3, ml_y-3, ml_w+6, ml_h+6), border_radius=6)   # bezel
    pygame.draw.rect(surf, (220, 120, 200), (ml_x-3, ml_y-3, ml_w+6, ml_h+6), 1, border_radius=6)
    scr_col = (200, 100, 180) if state == 'waiting' else (220, 80, 190)
    pygame.draw.rect(surf, scr_col, (ml_x, ml_y, ml_w, ml_h), border_radius=4)
    # Screen glow
    for sg in range(8, 0, -2):
        sgs = pygame.Surface((ml_w+sg*2, ml_h+sg*2), pygame.SRCALPHA)
        gc2 = (180, 60, 255) if state == 'waiting' else (255, 80, 200)
        pygame.draw.rect(sgs, (*gc2, int(18*(sg/8))), (0,0,ml_w+sg*2,ml_h+sg*2), border_radius=6+sg)
        surf.blit(sgs, (ml_x-sg, ml_y-sg))
    # Animated code lines on left screen — white for contrast
    for li in range(5):
        lw2 = 15 + (li*11 + frame//4) % 45
        pygame.draw.rect(surf, (255,240,255), (ml_x+6, ml_y+8+li*9, lw2, 2), border_radius=1)
    # Accent colour dot at start of each line
    for li in range(5):
        dc = [(255,120,210),(180,140,255),(255,120,200),(200,180,255),(220,100,255)][li]
        pygame.draw.rect(surf, dc, (ml_x+4, ml_y+7+li*9, 2, 4))
    # Monitor stand + base
    pygame.draw.rect(surf, (240, 190, 225), (ml_x+ml_w//2-5, ml_y+ml_h, 10, 10), border_radius=2)
    pygame.draw.rect(surf, (240, 190, 225), (ml_x+ml_w//2-14, ml_y+ml_h+10, 28, 4), border_radius=2)

    # Right monitor — white bezel, lofi desktop scene on screen
    mr_x = cx - 2; mr_y = dy - 78; mr_w = 82; mr_h = 54
    pygame.draw.rect(surf, (255, 230, 245), (mr_x-3, mr_y-3, mr_w+6, mr_h+6), border_radius=6)
    pygame.draw.rect(surf, (220, 120, 200), (mr_x-3, mr_y-3, mr_w+6, mr_h+6), 1, border_radius=6)
    # Screen: pastel gradient wallpaper (lofi night sky)
    for sy2 in range(mr_h):
        t2 = sy2/mr_h
        sc2 = (int(100-t2*30), int(60-t2*10), int(160+t2*20))
        pygame.draw.line(surf, sc2, (mr_x, mr_y+sy2), (mr_x+mr_w, mr_y+sy2))
    # Stars on screen
    for i in range(8):
        stx = mr_x+6 + (i*13)%68; sty = mr_y+4 + (i*7)%16
        fv = 0.5+0.5*math.sin(frame*0.09+i)
        pygame.draw.rect(surf,(220,200,255),(stx,sty,2,2))
    # Moon on screen
    pygame.draw.circle(surf,(255,245,170),(mr_x+mr_w-14, mr_y+10),6)
    pygame.draw.circle(surf,(80,50,130),(mr_x+mr_w-11, mr_y+8),5)   # crescent shadow
    # Desk line on screen
    pygame.draw.rect(surf,(80,55,110),(mr_x+2, mr_y+mr_h-14, mr_w-4, 2))
    # Mini lofi character on screen
    cx2 = mr_x+mr_w-20; cy2 = mr_y+mr_h-20
    pygame.draw.circle(surf,(255,210,175),(cx2,cy2),4)               # head
    pygame.draw.rect(surf,(180,120,220),(cx2-3,cy2+4,6,6))           # body
    pygame.draw.rect(surf,(40,28,60),(cx2-4,cy2-4,8,3))              # hair
    pygame.draw.arc(surf,(100,80,150),pygame.Rect(cx2-5,cy2-6,10,7),0,math.pi,2)  # headphones
    if (frame//8)%4 in (1,2): pygame.draw.rect(surf,(180,120,220),(cx2-3,cy2+3,6,7))  # breathe
    # Plant on screen left
    pygame.draw.rect(surf,(100,160,105),(mr_x+6,mr_y+mr_h-18,4,8))
    pygame.draw.circle(surf,(120,185,120),(mr_x+8,mr_y+mr_h-18),5)
    # Screen glow
    sg2=pygame.Surface((mr_w,mr_h),pygame.SRCALPHA)
    pygame.draw.rect(sg2,(140,100,220,18),(0,0,mr_w,mr_h),border_radius=4)
    surf.blit(sg2,(mr_x,mr_y))
    pygame.draw.rect(surf, (240,190,225), (mr_x+mr_w//2-5, mr_y+mr_h, 10, 10), border_radius=2)
    pygame.draw.rect(surf, (240,190,225), (mr_x+mr_w//2-14, mr_y+mr_h+10, 28, 4), border_radius=2)

    # ── Keyboard — white kawaii ──
    kb_x = cx - 52; kb_y = dy - 14; kb_w = 80; kb_h = 11
    pygame.draw.rect(surf, (255, 240, 250), (kb_x, kb_y, kb_w, kb_h), border_radius=3)
    pygame.draw.rect(surf, (220, 150, 205), (kb_x, kb_y, kb_w, kb_h), 1, border_radius=3)
    for ki in range(8):
        kc = [(255,80,200),(200,80,255),(230,100,255),(255,130,210)][ki%4]
        pygame.draw.rect(surf, kc, (kb_x+4+ki*9, kb_y+3, 7, 5), border_radius=1)
    # Keyboard glow
    kg = pygame.Surface((kb_w+10, 8), pygame.SRCALPHA)
    pygame.draw.ellipse(kg, (255,80,200,30), (0,0,kb_w+10,8))
    surf.blit(kg, (kb_x-5, kb_y+kb_h-2))

    # ── Small items on desk ──
    # Clock (like the 22:30 in ref image 1)
    clk_x = cx - dw//2 + 8; clk_y = dy - 24
    pygame.draw.rect(surf, (255, 220, 240), (clk_x, clk_y, 36, 20), border_radius=3)
    pygame.draw.rect(surf, (220, 100, 185), (clk_x, clk_y, 36, 20), 1, border_radius=3)
    import datetime as _dt
    now = _dt.datetime.now()
    tstr = now.strftime("%H:%M")
    clk_s = pygame.font.SysFont("monospace", 7, bold=False).render(tstr, False, (180,40,155))
    surf.blit(clk_s, (clk_x+18-clk_s.get_width()//2, clk_y+6))

    # Small cat figure (ref image 1 has white cat figures)
    cat_x = cx + dw//2 - 30; cat_y = dy - 18
    pygame.draw.ellipse(surf, (230, 220, 240), (cat_x, cat_y+6, 14, 10))   # body
    pygame.draw.circle(surf, (230, 220, 240), (cat_x+7, cat_y+4), 6)       # head
    pygame.draw.polygon(surf, (230,220,240), [(cat_x+2,cat_y+1),(cat_x+4,cat_y-4),(cat_x+6,cat_y+1)])  # ear L
    pygame.draw.polygon(surf, (230,220,240), [(cat_x+8,cat_y+1),(cat_x+10,cat_y-4),(cat_x+12,cat_y+1)]) # ear R
    pygame.draw.circle(surf, (80,40,100), (cat_x+5, cat_y+5), 1)           # eye L
    pygame.draw.circle(surf, (80,40,100), (cat_x+9, cat_y+5), 1)           # eye R

    # Headphones on desk edge
    hp_x = cx - dw//2 + 46; hp_y = dy - 12
    pygame.draw.arc(surf, (60,35,90), pygame.Rect(hp_x, hp_y-8, 22, 16), 0, math.pi, 4)
    pygame.draw.ellipse(surf, (80,50,120), (hp_x-2, hp_y+4, 8, 6))
    pygame.draw.ellipse(surf, (80,50,120), (hp_x+16, hp_y+4, 8, 6))

    # ── Gaming chair ── kawaii pink/white like Y2K ref
    ch_x = cx - 22; ch_top = dy - 110
    pygame.draw.rect(surf, (255, 195, 230), (ch_x, ch_top, 44, 35), border_radius=8)
    pygame.draw.rect(surf, (220, 100, 190), (ch_x, ch_top, 44, 35), 1, border_radius=8)
    # Headrest
    pygame.draw.rect(surf, (255, 215, 240), (ch_x+6, ch_top-10, 32, 14), border_radius=6)
    pygame.draw.rect(surf, (220, 100, 190), (ch_x+6, ch_top-10, 32, 14), 1, border_radius=6)
    # Chair accent stripe — hot pink
    pygame.draw.rect(surf, (255, 60, 160), (ch_x+2, ch_top+8, 6, 18), border_radius=3)
    pygame.draw.rect(surf, (255, 60, 160), (ch_x+36, ch_top+8, 6, 18), border_radius=3)

    # Waddle from behind (at desk)
    draw_waddle_back(surf, cx, dy - 20, sc=0.9)


# ── WEATHER ───────────────────────────────────────────────────────────────────
WMO={0:"Clear",1:"Mainly Clear",2:"Partly Cloudy",3:"Overcast",
     45:"Foggy",51:"Drizzle",53:"Drizzle",55:"Heavy Drizzle",
     61:"Light Rain",63:"Rain",65:"Heavy Rain",71:"Light Snow",
     73:"Snow",75:"Heavy Snow",80:"Showers",81:"Heavy Showers",
     95:"Thunderstorm",96:"Hail",99:"Heavy Hail"}
WMI={0:"*",1:"*",2:"~",3:"~",45:"?",51:".",53:".",55:".",
     61:".",63:"::",65:"::",71:"*",73:"*",75:"*",
     80:"::",81:"::",95:"!!",96:"!!",99:"!!"}
# Emoji fallback
WMIE={0:"☀",1:"🌤",2:"⛅",3:"☁",45:"🌫",51:"🌦",53:"🌦",55:"🌧",
      61:"🌦",63:"🌧",65:"🌧",71:"🌨",73:"❄",75:"❄",80:"🌦",
      81:"🌧",95:"⛈",96:"⛈",99:"⛈"}

def draw_wx_icon(surf, code, cx, cy, size=32):
    """Draw a cute pastel weather icon using shapes. code = WMO code."""
    # Colour palette
    SUN_Y=(255,228,80);  SUN_O=(255,190,40)
    CLOUD=(230,230,255); CLOUD_D=(200,205,240)
    RAIN =(110,170,255); SNOW =(220,235,255)
    LTNG =(255,228,60);  FOG  =(200,210,230)
    cx,cy,s = int(cx),int(cy),int(size)
    r = max(1,s//2)

    def _sun(x,y,r2):
        # Glow
        for gr in range(r2+6,r2,-1):
            a=int(28*(1-(gr-r2)/6))
            gs=pygame.Surface((gr*2,gr*2),pygame.SRCALPHA)
            pygame.draw.circle(gs,(*SUN_Y,a),(gr,gr),gr)
            surf.blit(gs,(x-gr,y-gr))
        pygame.draw.circle(surf,SUN_Y,(x,y),r2)
        pygame.draw.circle(surf,SUN_O,(x,y),r2,max(1,r2//5))
        # Rays
        for ang in range(0,360,45):
            rad=math.radians(ang); rd=r2+3; rl=r2+7
            pygame.draw.line(surf,SUN_O,
                (int(x+rd*math.cos(rad)),int(y+rd*math.sin(rad))),
                (int(x+rl*math.cos(rad)),int(y+rl*math.sin(rad))),2)

    def _cloud(x,y,r2,col=CLOUD,col2=CLOUD_D):
        pygame.draw.ellipse(surf,col,(x-r2,y-r2//2,r2*2,r2))
        pygame.draw.circle(surf,col,(x-r2//3,y-r2//3),r2*2//3)
        pygame.draw.circle(surf,col,(x+r2//3,y-r2//4),r2//2)
        pygame.draw.ellipse(surf,col2,(x-r2,y-r2//2,r2*2,r2),2)

    def _rain(x,y,n=3):
        for i in range(n):
            rx=x-n*4+i*8; ry=y+4
            pygame.draw.line(surf,RAIN,(rx,ry),(rx-3,ry+8),2)

    def _snow(x,y,n=3):
        for i in range(n):
            rx=x-n*4+i*8; ry=y+6
            pygame.draw.circle(surf,SNOW,(rx,ry),3)

    # Clear / sunny
    if code in (0,1):
        _sun(cx,cy,r)
    # Partly cloudy
    elif code==2:
        _sun(cx-s//5,cy-s//6,int(r*0.75))
        _cloud(cx+s//6,cy+s//8,int(r*0.85))
    # Overcast / fog
    elif code in (3,45):
        _cloud(cx-s//6,cy,int(r*0.82))
        _cloud(cx+s//6,cy+s//8,int(r*0.72),FOG,FOG)
    # Drizzle / light rain
    elif code in (51,53,55,61):
        _cloud(cx,cy-s//8,int(r*0.88))
        _rain(cx,cy+s//8,2)
    # Rain / showers
    elif code in (63,65,80,81):
        _cloud(cx,cy-s//8,int(r*0.88))
        _rain(cx,cy+s//8,4)
    # Snow
    elif code in (71,73,75):
        _cloud(cx,cy-s//8,int(r*0.88),SNOW,CLOUD_D)
        _snow(cx,cy+s//8,3)
    # Thunderstorm
    elif code in (95,96,99):
        _cloud(cx,cy-s//6,int(r*0.88))
        # Lightning bolt
        lx=cx-4; ly=cy+s//8
        pygame.draw.polygon(surf,LTNG,[(lx+8,ly),(lx+2,ly+10),(lx+6,ly+10),(lx,ly+20),(lx+10,ly+8),(lx+5,ly+8)])
    else:
        _sun(cx,cy,r)

class Weather:
    def __init__(self):
        self.ready=False; self.err=False
        self.temp="--"; self.feels="--"; self.cond="loading"
        self.hum="--"; self.hourly=[]; self.daily=[]; self._code=0
        threading.Thread(target=self._fetch,daemon=True).start()

    def _fetch(self):
        try:
            url=(f"https://api.open-meteo.com/v1/forecast"
                 f"?latitude={LAT}&longitude={LON}"
                 f"&current=temperature_2m,apparent_temperature,weathercode,relative_humidity_2m"
                 f"&hourly=temperature_2m,weathercode"
                 f"&daily=temperature_2m_max,temperature_2m_min,weathercode"
                 f"&temperature_unit=fahrenheit&timezone=America%2FNew_York&forecast_days=5")
            req=urllib.request.Request(url,headers={"User-Agent":"WaddlePet/5"})
            with urllib.request.urlopen(req,timeout=10) as resp:
                import json as _j; d=_j.loads(resp.read())
            c=d["current"]
            self.temp=f"{float(c['temperature_2m']):.0f}"
            self.feels=f"{float(c['apparent_temperature']):.0f}"
            code=int(c["weathercode"])
            self._code=code
            self.cond=WMO.get(code,"Unknown")
            self.hum=str(c["relative_humidity_2m"])
            hr=d["hourly"]
            try:
                from zoneinfo import ZoneInfo
                now_h=datetime.datetime.now(ZoneInfo("America/New_York")).hour
            except Exception:
                now_h=datetime.datetime.now().hour
            self.hourly=[]
            for i in range(now_h,min(now_h+4,len(hr["time"]))):
                hcode=int(hr["weathercode"][i])
                _hh=int(hr["time"][i].split("T")[1][:2])
                _ampm="am" if _hh<12 else "pm"
                _h12=_hh%12; _h12=12 if _h12==0 else _h12
                self.hourly.append({
                    "h":f"{_h12}{_ampm}",
                    "t":f"{float(hr['temperature_2m'][i]):.0f}",
                    "c":WMO.get(hcode,"")[:8]
                })
            dd=d["daily"]
            DAYS=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
            self.daily=[]
            for i in range(min(5,len(dd["time"]))):
                dow=datetime.date.fromisoformat(dd["time"][i]).weekday()
                dcode=int(dd["weathercode"][i])
                self.daily.append({
                    "d":DAYS[dow],
                    "hi":f"{float(dd['temperature_2m_max'][i]):.0f}",
                    "lo":f"{float(dd['temperature_2m_min'][i]):.0f}",
                    "c":WMO.get(dcode,"?")[:6],
                    "_code":dcode
                })
            self.ready=True
        except Exception:
            self.err=True; self.cond="offline"; self.ready=True


# ── TERMINAL LINES ────────────────────────────────────────────────────────────
TERM_LINES=[
    f"> loc: {CITY}",
    "> scanning for fish...  3 found",
    "> pinging moon... OK",
    "> code buffer: 94% full",
    "> happiness: nominal",
    "> energy recharging...",
    "> fish.exe loaded OK",
    "> mood: calibrated",
    "> all systems nominal",
    "> you are doing great today",
    "> rest is productive",
    "> small steps still count",
    "> be gentle with yourself",
    "> you deserve good things",
    "> penguin status: very cute",
    "> progress beats perfection",
    "> you showed up. that counts",
    "> every small effort matters",
    "> your pace is valid",
    "> proud of you for trying",
    "> good things take time",
    "> rest is not giving up",
    "> you are still growing",
    "> today was not wasted",
    "> you are enough right now",
    "> breathe. then try again",
    "> your best is always enough",
    "> celebrate small wins too",
    "> it is okay to start over",
    "> keep going. you are close",
    "> one step is still movement",
    "> you matter more than output",
    "> be as kind to you as to others",
    "> today counts. tomorrow too",
]
random.shuffle(TERM_LINES)

# ── SAVE/LOAD ─────────────────────────────────────────────────────────────────
_SAVE_FILE = os.path.join(_IMG_DIR, "waddle_save.json")

def load_save():
    try:
        with open(_SAVE_FILE, encoding='utf-8') as f: return json.load(f)
    except Exception:
        return {'points':0,'unlocked':[],'equipped':[]}

def write_save(d):
    with open(_SAVE_FILE, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False)

def _apply_location(lat, lon, city):
    """Update module-level location globals used by Weather fetch."""
    global LAT, LON, CITY
    LAT=lat; LON=lon; CITY=city
    # Patch the loc line in TERM_LINES so Chill screen shows the right city
    for i,line in enumerate(TERM_LINES):
        if line.startswith("> loc:"):
            TERM_LINES[i]=f"> loc: {CITY}"; break

# ── WADDLE STATS ──────────────────────────────────────────────────────────────
class Waddle:
    SPEECH={
        'happy'  :["hewwo!! ♥","i love you sm","yippee!!","*happy waddle*",":3"],
        'excited':["AAAAAA!!","LET'S GOOO","!!!!!!","SO HYPED RN","eeeee ♥♥"],
        'idle'   :["...","*stares*","just vibing","hmm.","hello?","*blinks*"],
        'sleepy' :["zzz...","five more mins","so sleepy","*snores*"],
        'hungry' :["feed me NOW","FISH PLEASE","so hungry","*stares at u*"],
        'sad'    :["it's fine. i'm fine.","*tiny tear*","feeling blue","..."],
    }
    def __init__(self):
        sv=load_save()
        self.points=sv.get('points',0)
        self.unlocked=sv.get('unlocked',[])
        self.equipped=sv.get('equipped',[])
        self.hunger=float(random.randint(18,52))
        self.happiness=float(random.randint(52,86))
        self.energy=float(random.randint(46,80))
    def save(self):
        sv=load_save()
        sv.update({'points':self.points,'unlocked':self.unlocked,'equipped':self.equipped})
        write_save(sv)
    @property
    def mood(self):
        if self.hunger>78:    return 'hungry'
        if self.happiness<22: return 'sad'
        if self.energy<18:    return 'sleepy'
        if self.happiness>90 and self.energy>70: return 'excited'
        if self.happiness>78: return 'happy'
        return 'idle'
    def feed(self): self.hunger=max(0,self.hunger-40); self.happiness=min(100,self.happiness+8)
    def tick(self,dt):
        r=dt/1000.0
        self.hunger=min(100,self.hunger+r*0.14)
        self.happiness=max(0,self.happiness-r*0.07)
        self.energy=max(0,self.energy-r*0.06)
    def speech(self): return random.choice(self.SPEECH.get(self.mood,["..."]))


# ── DODGE GAME ────────────────────────────────────────────────────────────────
class DodgeGame:
    PY=SH-64; SPX=3; FW=42; FH=34; LIVES=3
    # Cyber pastel file colours — properly saturated pastels, not muddy
    FCOLS=[
        (188, 100, 220),  # pastel purple
        ( 88, 188, 232),  # pastel cyan
        (220,  96, 168),  # pastel pink
        ( 96, 210, 165),  # pastel mint
        (168, 128, 255),  # pastel lavender
    ]

    def __init__(self,w):
        self.w=w; self.px=SW//2; self.debris=[]; self.fish=[]
        self.pts=0; self.alive=True; self.frame=0
        self.dt_d=0; self.dt_f=0; self.speed=2.2
        self.catch_flashes=[]   # {x,y,life,vx,vy,col} sparkle burst on catch
        self.combo=0            # consecutive fish caught without dying
        # Fish reward: 1 fish per catch normally; 2 fish when combo ≥ 5.
        # Total fish is saved to Waddle.points on death.
        self.fish_earned=0
        self.level=1            # displayed level
        self.near_miss_t=0      # flash when debris just misses
        self.levelup_t=0; self.levelup_n=1  # level-up announcement
        self.lives=3; self.invincible_t=0; self.hit_flash_t=0
        # Pre-built CRT scanline overlay — built once, blitted every frame
        self._crt = pygame.Surface((SW, SH), pygame.SRCALPHA)
        for _y in range(0, SH, 2):
            pygame.draw.line(self._crt, (0,0,0,16), (0,_y),(SW,_y))
        # Virus.exe mechanic
        self.virus_active  = False
        self.virus_ending  = False    # True while files sweep off-screen at end
        self.virus_t       = 0        # ms elapsed in current virus phase
        self.virus_trigger = 10       # score that trips the next virus
        self.virus_files   = []       # big slow virus file objects {x,y}
        self.virus_flash   = 0        # ms of red flash on trigger
        # Drifting starfield
        _rng = random.Random(7)
        self.stars = [{'x': float(_rng.randint(0,SW)), 'y': float(_rng.randint(0,SH)),
                       'spd': _rng.uniform(0.25,0.8), 'bright': _rng.randint(70,190)}
                      for _ in range(38)]

    def update(self,dt,keys):
        if not self.alive: return
        self.frame+=1
        if self.near_miss_t>0: self.near_miss_t-=dt

        # Virus.exe phase trigger & tick
        VIRUS_DUR = 8000
        if not self.virus_active and self.pts >= self.virus_trigger:
            self.virus_active = True
            self.virus_t      = 0
            self.virus_flash  = 500
            self.virus_trigger += random.randint(16, 28)
            self.virus_files  = [
                {'x': float(random.randint(70, SW-70)), 'y': -80.0},
                {'x': float(random.randint(70, SW-70)), 'y': -180.0},
            ]
            Sounds.virus_alert()
        if self.virus_active:
            if not self.virus_ending:
                self.virus_t += dt
                if self.virus_t >= VIRUS_DUR:
                    self.virus_ending = True
        if self.virus_flash > 0: self.virus_flash -= dt

        # Drift starfield
        for s in self.stars:
            s['y'] = (s['y'] + s['spd']) % SH

        # Speed ramp every 50 pts
        self.speed=2.2+min(3.0,(self.pts//10)*0.35)
        _nl=1+(self.pts//10)
        if _nl>self.level: self.levelup_t=1400; self.levelup_n=_nl
        self.level=_nl
        if self.levelup_t>0:    self.levelup_t-=dt
        if self.invincible_t>0: self.invincible_t-=dt
        if self.hit_flash_t>0:  self.hit_flash_t-=dt

        mv=5
        if keys[pygame.K_LEFT]:  self.px=max(22,self.px-mv)
        if keys[pygame.K_RIGHT]: self.px=min(SW-22,self.px+mv)
        self.dt_d+=dt
        _d_interval = max(380,1380-self.pts*40) if self.virus_active else max(560,1380-self.pts*40)
        if self.dt_d>_d_interval:
            self.dt_d=0
            self.debris.append({'x':random.randint(self.FW//2+14,SW-self.FW//2-14),
                                 'y':-self.FH,'col':random.choice(self.FCOLS)})
        self.dt_f+=dt
        if self.dt_f>3200:
            self.dt_f=0
            if random.random()<0.72:
                _gold = random.random() < 0.20
                self.fish.append({'x':random.randint(34,SW-34),'y':-24,'gold':_gold,'val':5 if _gold else 1})
        for d in self.debris: d['y']+=self.speed
        for f in self.fish:   f['y']+=self.speed*0.68
        self.debris=[d for d in self.debris if d['y']<SH+44]
        self.fish  =[f for f in self.fish   if f['y']<SH+44]

        # Update catch flashes
        self.catch_flashes=[cf for cf in self.catch_flashes if cf['life']>0]
        for cf in self.catch_flashes: cf['life']-=dt/400.0

        # Head-only hitbox: sprite top = PY - 28*SPX + 8*SPX = PY - 20*SPX
        # Head occupies grid rows 0-9 → 9*SPX pixels tall, narrower than body
        head_top    = int(self.PY - 20*self.SPX)
        head_bottom = head_top + 9*self.SPX
        head_hw     = 5*self.SPX          # head half-width (narrower than body)
        body_hw     = 9*self.SPX          # keep for fish collection below

        foot_bottom = int(self.PY)   # full sprite vertical extent
        for d in self.debris:
            db_top = d['y'] - self.FH//2
            db_bot = d['y'] + self.FH//2
            if (db_bot > head_top and db_top < foot_bottom
                    and abs(d['x']-self.px) < body_hw + self.FW//2):
                if self.invincible_t <= 0:
                    self.combo=0; self.lives-=1; self.hit_flash_t=400
                    if self.lives<=0:
                        self.alive=False
                        self.w.happiness=max(0,  self.w.happiness-15)
                        self.w.energy   =max(0,  self.w.energy   -8)
                        self.w.points+=self.fish_earned; self.w.save(); return
                    else:
                        self.invincible_t=2000
                        self.w.happiness=max(0,self.w.happiness-5)
                        self.debris=[dd for dd in self.debris if dd['y']<head_top-40]
                        break
            elif (db_bot > head_top and db_top < foot_bottom
                    and abs(d['x']-self.px) < body_hw + self.FW//2 + 18):
                self.near_miss_t=max(self.near_miss_t,380)

        for f in self.fish[:]:
            if (f['y'] > head_top and abs(f['x']-self.px) < body_hw + 16):
                self.fish.remove(f)
                self.combo+=1
                fish=f['val']*(2 if self.combo>=5 else 1)
                self.fish_earned+=fish
                self.pts+=f['val']
                Sounds.catch_fish()
                # Spawn catch flash particles
                for _ in range(8):
                    ang=random.uniform(0,math.pi*2)
                    spd=random.uniform(1.2,3.0)
                    self.catch_flashes.append({
                        'x':float(f['x']),'y':float(f['y']),
                        'vx':math.cos(ang)*spd,'vy':math.sin(ang)*spd,
                        'life':1.0,'col':random.choice([(255,180,220),(180,140,255),(255,160,220)])
                    })
                self.w.hunger   =max(0,   self.w.hunger   -10)
                self.w.happiness=min(100, self.w.happiness+5)

        # Virus file movement + collision
        VFW, VFH = 72, 58
        exit_spd = 9.0 if self.virus_ending else max(1.0, self.speed * 0.55)
        for vf in self.virus_files:
            vf['y'] += exit_spd
        self.virus_files = [vf for vf in self.virus_files if vf['y'] < SH+90]
        if self.virus_ending and not self.virus_files:
            self.virus_active = False
            self.virus_ending = False
            self.virus_t      = 0
        for vf in self.virus_files:
            if self.virus_ending: break  # no collision during exit sweep
            vfb_top = vf['y'] - VFH//2
            vfb_bot = vf['y'] + VFH//2
            if (vfb_bot > head_top and vfb_top < foot_bottom
                    and abs(vf['x']-self.px) < head_hw + VFW//2):
                if self.invincible_t <= 0:
                    # Virus = instant death
                    self.combo=0; self.hit_flash_t=400
                    self.alive=False
                    self.w.happiness=max(0,  self.w.happiness-15)
                    self.w.energy   =max(0,  self.w.energy   -8)
                    self.w.points  +=self.fish_earned; self.w.save(); return

        # Move catch flash particles
        for cf in self.catch_flashes:
            cf['x']+=cf['vx']; cf['y']+=cf['vy']; cf['vy']+=0.08

        self.w.energy  =max(0,   self.w.energy  -0.055)
        self.w.hunger  =min(100, self.w.hunger  +0.030)
        if self.frame%40==0:
            self.w.happiness=min(100,self.w.happiness+0.8)

    def _file(self,surf,x,y,col):
        """
        Cyber pastel corrupted file icon.
        Looks like a glossy folder with glitch corruption lines,
        a frowny face, and a frosted glass sheen.
        """
        x,y=int(x),int(y)
        FW,FH=self.FW,self.FH
        bx=x-FW//2; by=y-FH//2

        # ── Colour variants ──
        dark  = clamp_color(col[0]-45, col[1]-45, col[2]-45)
        light = clamp_color(col[0]+55, col[1]+55, col[2]+55)
        pale  = clamp_color(col[0]+80, col[1]+80, col[2]+80)

        # ── Drop shadow ──
        sh=pygame.Surface((FW+4,FH+4),pygame.SRCALPHA)
        pygame.draw.rect(sh,(0,0,0,55),(0,0,FW+4,FH+4),border_radius=6)
        surf.blit(sh,(bx+2,by+3))

        # ── Main folder body ──
        pygame.draw.rect(surf,col,(bx,by,FW,FH),border_radius=5)

        # ── Inner gradient (top lighter, bottom darker) ──
        for i in range(FH//2):
            al=int(55*(1-i/(FH//2)))
            pygame.draw.line(surf,(*light,al),(bx+3,by+i),(bx+FW-4,by+i))

        # ── Bottom shadow inside ──
        for i in range(6):
            al=int(40*i/6)
            pygame.draw.line(surf,(*dark,al),(bx+3,by+FH-1-i),(bx+FW-4,by+FH-1-i))

        # ── Tab on top-left ──
        tw=FW//3+4; th=10
        pygame.draw.rect(surf,col,(bx,by-th,tw,th+4),border_radius=3)
        pygame.draw.rect(surf,(*light,80),(bx+1,by-th+1,tw-2,4))  # tab shine

        # ── Glitch scan lines across body ──
        for gi in range(3):
            gy=by+8+gi*9
            gl_col=clamp_color(col[0]+30,col[1]+30,col[2]+30)
            pygame.draw.line(surf,(*gl_col,90),(bx+4,gy),(bx+FW-5,gy))
            # Glitch break — missing segment
            pygame.draw.line(surf,col,(bx+8+gi*5,gy),(bx+14+gi*5,gy))

        # ── Glass sheen overlay ──
        sheen=pygame.Surface((FW-4,FH//3),pygame.SRCALPHA)
        pygame.draw.rect(sheen,(255,255,255,30),(0,0,FW-4,FH//3),border_radius=4)
        surf.blit(sheen,(bx+2,by+2))

        # ── Border ──
        pygame.draw.rect(surf,light,(bx,by,FW,FH),2,border_radius=5)
        pygame.draw.rect(surf,pale, (bx+1,by+1,FW-2,2))  # top highlight line

        # ── X eyes + frown — classic "dead" folder face ──
        ey=by+FH*2//5
        for xc in (x-8, x+8):
            pygame.draw.line(surf,(245,235,255),(xc-3,ey-3),(xc+3,ey+3),2)
            pygame.draw.line(surf,(245,235,255),(xc+3,ey-3),(xc-3,ey+3),2)
        # Frown arc
        for i in range(-6,7):
            fm_y=int(ey+10-int(3.5*(1.0-(i/6.0)**2)))
            pygame.draw.circle(surf,(225,215,255),(x+i,fm_y),1)

        # ── Corner glitch pixel scatter ──
        for gx2,gy2 in [(bx+1,by+1),(bx+FW-3,by+1),(bx+1,by+FH-3)]:
            pygame.draw.rect(surf,pale,(gx2,gy2,2,2))

    def _fish(self,surf,x,y,gold=False):
        """Cute kawaii fish with proper shading. Gold variant worth 5pts."""
        x,y=int(x),int(y)
        if gold:
            FBODY=(255,215,60); FBODY2=(235,185,30); FSHINE=(255,245,180)
            FTAIL=(210,165,20); FEYE=(60,30,5); FOUT=(180,130,10)
        else:
            # Body — aqua-cyan gradient feel
            FBODY=(88,210,252); FBODY2=(62,185,235); FSHINE=(185,242,255)
            FTAIL=(58,178,228); FEYE=(18,5,48); FOUT=(42,155,210)

        # Tail fin
        pygame.draw.polygon(surf,FTAIL,[(x-13,y),(x-24,y-8),(x-24,y+8)])
        pygame.draw.polygon(surf,FOUT, [(x-13,y),(x-24,y-8),(x-24,y+8)],1)

        # Dorsal fin
        pygame.draw.polygon(surf,FTAIL,[(x-4,y-8),(x+4,y-15),(x+10,y-8)])
        pygame.draw.polygon(surf,FOUT, [(x-4,y-8),(x+4,y-15),(x+10,y-8)],1)

        # Body ellipse
        pygame.draw.ellipse(surf,FBODY2,(x-14,y-9,30,18))
        pygame.draw.ellipse(surf,FBODY, (x-13,y-8,28,16))

        # Body shading — lighter top half
        for i in range(6):
            al=int(65*(1-i/6))
            pygame.draw.line(surf,(*FSHINE,al),(x-10,y-7+i),(x+11,y-7+i))

        # Outline
        pygame.draw.ellipse(surf,FOUT,(x-13,y-8,28,16),1)

        # Scales (subtle arcs)
        for sx2,sy2 in [(x-2,y-2),(x+5,y-2),(x-4,y+2)]:
            pygame.draw.arc(surf,(*FOUT,80),
                pygame.Rect(sx2-4,sy2-3,8,6),0,math.pi,1)

        # Eye
        pygame.draw.circle(surf,(240,235,255),(x+7,y-1),4)
        pygame.draw.circle(surf,FEYE,(x+7,y-1),3)
        pygame.draw.circle(surf,WHI, (x+8,y-2),1)

        # +5 label — only on gold fish
        if gold:
            lbl=F11.render("+5",False,(255,240,100))
            surf.blit(lbl,(x-lbl.get_width()//2,y-30))

    def _virus_file(self,surf,x,y):
        """Big corrupted VIRUS.EXE obstacle — 72×58, red palette, skull face."""
        x,y=int(x),int(y)
        FW,FH=72,58
        col=(200,30,55)
        bx=x-FW//2; by=y-FH//2
        light=clamp_color(col[0]+55,col[1]+55,col[2]+55)
        pale =clamp_color(col[0]+85,col[1]+85,col[2]+85)
        # Drop shadow
        sh=pygame.Surface((FW+6,FH+6),pygame.SRCALPHA)
        pygame.draw.rect(sh,(0,0,0,75),(0,0,FW+6,FH+6),border_radius=8)
        surf.blit(sh,(bx+3,by+4))
        # Body
        pygame.draw.rect(surf,col,(bx,by,FW,FH),border_radius=6)
        # Inner gradient
        for i in range(FH//2):
            al=int(50*(1-i/(FH//2)))
            pygame.draw.line(surf,(*light,al),(bx+3,by+i),(bx+FW-4,by+i))
        # Tab
        tw=FW//3+4; th=12
        pygame.draw.rect(surf,col,(bx,by-th,tw,th+4),border_radius=3)
        pygame.draw.rect(surf,(*light,80),(bx+1,by-th+1,tw-2,5))
        # Glitch lines
        for gi in range(4):
            gy=by+8+gi*11
            gl_col=clamp_color(col[0]+40,col[1]+40,col[2]+40)
            pygame.draw.line(surf,(*gl_col,100),(bx+4,gy),(bx+FW-5,gy))
            pygame.draw.line(surf,col,(bx+8+gi*6,gy),(bx+16+gi*6,gy))
        # Glass sheen
        sheen=pygame.Surface((FW-4,FH//3),pygame.SRCALPHA)
        pygame.draw.rect(sheen,(255,255,255,22),(0,0,FW-4,FH//3),border_radius=4)
        surf.blit(sheen,(bx+2,by+2))
        # Border
        pygame.draw.rect(surf,light,(bx,by,FW,FH),2,border_radius=6)
        # Skull: X eyes
        ey=by+FH*2//5
        for xc in (x-12,x+12):
            pygame.draw.line(surf,(255,170,190),(xc-5,ey-5),(xc+5,ey+5),2)
            pygame.draw.line(surf,(255,170,190),(xc+5,ey-5),(xc-5,ey+5),2)
        # Skull: teeth row
        for tx in range(x-11,x+13,6):
            pygame.draw.rect(surf,(255,170,190),(tx,ey+9,4,7))
        pygame.draw.line(surf,col,(x-10,ey+12),(x+12,ey+12),1)
        # Label
        lbl=F8.render("VIRUS.EXE",False,pale)
        surf.blit(lbl,(x-lbl.get_width()//2,by+4))
        # Pulsing glow ring
        pulse_a=int(abs(math.sin(pygame.time.get_ticks()/300))*55)+15
        glow=pygame.Surface((FW+22,FH+22),pygame.SRCALPHA)
        pygame.draw.rect(glow,(*col,pulse_a),(0,0,FW+22,FH+22),5,border_radius=11)
        surf.blit(glow,(bx-11,by-11))

    def draw(self,surf):
        # Deep purple-pink gradient
        for y in range(SH):
            t = y/SH
            r = clamp_color(int(52+t*20), int(10+t*8), int(88+t*22))
            pygame.draw.line(surf, r, (0,y), (SW,y))
        grid_bg(surf,(200,80,255),20,40)
        # Floor glow strip
        fl=pygame.Surface((SW,3),pygame.SRCALPHA)
        pygame.draw.rect(fl,(255,80,200,60),(0,0,SW,3))
        surf.blit(fl,(0,self.PY))

        # Drifting starfield
        for s in self.stars:
            _sc=pygame.Surface((5,5),pygame.SRCALPHA)
            pygame.draw.circle(_sc,(235,220,255,s['bright']),(2,2),1)
            if s['bright']>150:
                pygame.draw.circle(_sc,(255,245,255,s['bright']//4),(2,2),2)
            surf.blit(_sc,(int(s['x'])-2,int(s['y'])-2))

        # Near-miss edge flash
        if self.near_miss_t>0:
            na=int((self.near_miss_t/380)*80)
            ef=pygame.Surface((SW,SH),pygame.SRCALPHA)
            pygame.draw.rect(ef,(255,80,150,na),(0,0,SW,SH),8)
            surf.blit(ef,(0,0))

        for d in self.debris:
            self._file(surf,d['x'],d['y'],d['col'])
            # Motion trail sparkle above debris tile
            _draw_cross_star(surf,d['col'],d['x'],int(d['y']-self.FH//2),2,38)
        for f in self.fish:   self._fish(surf,f['x'],f['y'],gold=f.get('gold',False))

        # Virus files
        for vf in self.virus_files:
            self._virus_file(surf,vf['x'],vf['y'])

        # Virus vignette + start flash
        if self.virus_active:
            _pa=int(abs(math.sin(self.virus_t/350))*35)+10
            _vv=pygame.Surface((SW,SH),pygame.SRCALPHA)
            pygame.draw.rect(_vv,(220,20,50,_pa),(0,0,SW,SH),14)
            surf.blit(_vv,(0,0))
        if self.virus_flash>0:
            _fa=int((self.virus_flash/500)*100)
            _fl=pygame.Surface((SW,SH),pygame.SRCALPHA)
            _fl.fill((220,20,50,_fa))
            surf.blit(_fl,(0,0))

        # CRT scanline overlay
        surf.blit(self._crt,(0,0))

        # Catch flash particles
        for cf in self.catch_flashes:
            a=int(cf['life']*255)
            sz=max(2,int(cf['life']*6))
            _draw_cross_star(surf,cf['col'],int(cf['x']),int(cf['y']),sz,a)

        # Hit flash
        if self.hit_flash_t>0:
            _hfa=int((self.hit_flash_t/400)*160)
            _hf=pygame.Surface((SW,SH),pygame.SRCALPHA)
            _hf.fill((255,255,255,_hfa))
            surf.blit(_hf,(0,0))

        # Waddle sprite + accessories (flicker during invincibility)
        _draw_spr = not (self.invincible_t>0 and (self.frame//4)%2==0)
        ws=get_spr('happy' if self.alive else 'sad',self.SPX)
        wx=int(self.px-ws.get_width()//2)
        wy=int(self.PY-22*self.SPX)
        if _draw_spr:
            surf.blit(ws,(wx,wy))
            for eid in self.w.equipped:
                it=next((x for x in ITEMS if x['id']==eid),None)
                if it: draw_accessory(surf,eid,it['col'],wx,wy,self.SPX)

        # Level-up announcement
        if self.levelup_t>0:
            la=min(255,int(self.levelup_t/5.5))
            _lv=pygame.Surface((SW,56))
            _lv.fill((0,0,0)); _lv.set_colorkey((0,0,0)); _lv.set_alpha(la)
            blit_c(_lv,F24,f"LEVEL {self.levelup_n}",(255,80,180),SW//2,4)
            blit_c(_lv,F8,"♡  keep going  ♡",(220,160,255),SW//2,34)
            surf.blit(_lv,(0,SH//2-28))

        # ── HUD: LVL / fish / lives ──
        hud_w=128; hx=SW//2-hud_w//2
        cy=draw_win(surf,hx,6,hud_w,96,"DODGE.EXE")
        blit_c(surf,F11,f"LVL {self.level}",(80,45,155),SW//2,cy+7)
        blit_c(surf,F11,f"{self.fish_earned}",(80,45,155),SW//2,cy+22)
        _hgap=5; _hw=21
        _htotal=self.LIVES*_hw+(self.LIVES-1)*_hgap
        _hx0=SW//2-_htotal//2
        for _li in range(self.LIVES):
            _hc=(255,80,155) if _li<self.lives else (80,40,100)
            _draw_pixel_heart(surf,_hc,_hx0+_li*(_hw+_hgap)+_hw//2,cy+43,px=3,alpha=220)
        # Virus bar — floats just below window when active
        if self.virus_active:
            prog=min(1.0,self.virus_t/8000)
            _bw=hud_w-16; _bx2=hx+8; _vy=6+96+3
            _vc=(255,80,110) if (self.frame//8)%2==0 else (190,40,75)
            _vl=F8.render("virus cleaning",True,_vc)
            surf.blit(_vl,(SW//2-_vl.get_width()//2,_vy))
            pygame.draw.rect(surf,(55,18,75),(_bx2,_vy+10,_bw,5),border_radius=2)
            _fw=int(_bw*prog)
            if _fw>0:
                pygame.draw.rect(surf,(255,50,100),(_bx2,_vy+10,_fw,5),border_radius=2)

        if not self.alive:
            ov=pygame.Surface((SW,SH),pygame.SRCALPHA)
            ov.fill((6,2,16,210)); surf.blit(ov,(0,0))
            # Glitch lines
            for _gl in range(5):
                _gy=random.randint(0,SH)
                _gs=pygame.Surface((SW,2),pygame.SRCALPHA)
                _gs.fill((200,40,100,38))
                surf.blit(_gs,(random.randint(-8,8),_gy))
            cy3=draw_win(surf,SW//2-130,SH//2-70,260,140,"GAME OVER")
            blit_c(surf,F32,"GAME OVER",(255,75,155),SW//2,cy3+4)
            blit_c(surf,F8,"fish earned",(160,110,220),SW//2,cy3+48)
            blit_c(surf,F32,f"{self.fish_earned}",(255,75,155),SW//2,cy3+64)
            if (self.frame//14)%2==0:
                blit_c(surf,F8,"press ESC to exit",(120,60,160),SW//2,cy3+100)


def _draw_cross_star(surf, col, x, y, size, alpha=255):
    """Draw a 4-point cross/sparkle star with optional alpha."""
    if alpha < 10: return
    s = pygame.Surface((size*6+2, size*6+2), pygame.SRCALPHA)
    cx2, cy2 = size*3+1, size*3+1
    # Long cross arms
    pygame.draw.rect(s, (*col, alpha), (cx2-1, cy2-size*3, 2, size*6))
    pygame.draw.rect(s, (*col, alpha), (cx2-size*3, cy2-1, size*6, 2))
    # Diagonal shorter arms (45°)
    d = max(1, size)
    for dd in range(d):
        a2 = int(alpha*(1-dd/d)*0.5)
        pygame.draw.rect(s, (*col, a2), (cx2-dd-1, cy2-dd-1, 2, 2))
        pygame.draw.rect(s, (*col, a2), (cx2+dd-1, cy2-dd-1, 2, 2))
        pygame.draw.rect(s, (*col, a2), (cx2-dd-1, cy2+dd-1, 2, 2))
        pygame.draw.rect(s, (*col, a2), (cx2+dd-1, cy2+dd-1, 2, 2))
    surf.blit(s, (x-size*3-1, y-size*3-1))


def _draw_pixel_heart(surf, col, cx, cy, px=2, alpha=255):
    """7×6 pixel heart. cx/cy = centre. px = pixel size."""
    grid = ["0110110","1111111","1111111","0111110","0011100","0001000"]
    if alpha<10: return
    r,g,b = col[0],col[1],col[2]
    for gy,row in enumerate(grid):
        for gx,c in enumerate(row):
            if c=='1':
                s=pygame.Surface((px,px),pygame.SRCALPHA)
                s.fill((r,g,b,alpha))
                surf.blit(s,(cx-3*px+gx*px, cy-3*px+gy*px))


def _draw_cloud_puff(surf, cx, cy, w=52, col=(255,255,255), alpha=200):
    """Fluffy pixel cloud via overlapping circles — top puff never clips."""
    cw=w+30
    top_cr=w//4             # radius of tallest centre puff
    top_cy=top_cr+2         # centre y — 2px padding so top never clips surface
    ch=max(w//2+20, top_cy+top_cr+6)   # surface tall enough for all puffs
    mid_y=ch//2+4           # y-centre for the flanking lower puffs
    cs=pygame.Surface((cw,ch),pygame.SRCALPHA)
    r,g,b=col
    for ox2,oy2,cr in [(w//4,mid_y,w//5),(w//2,top_cy,top_cr),
                       (3*w//4,mid_y,w//5),(w//2,mid_y,w//6)]:
        pygame.draw.circle(cs,(r,g,b,alpha),(ox2,oy2),cr)
    surf.blit(cs,(cx-w//2-15, cy-top_cy))


def _draw_hud_fish(surf, cx, cy):
    """Tiny kawaii fish icon for the score HUD — ~18×12px."""
    fc=(88,210,252); fdk=(42,155,210); feye=(18,5,48)
    # Tail
    pygame.draw.polygon(surf,fc,[(cx-8,cy),(cx-14,cy-5),(cx-14,cy+5)])
    # Body
    pygame.draw.ellipse(surf,fc,(cx-7,cy-5,18,10))
    # Belly shine
    pygame.draw.ellipse(surf,clamp_color(fc[0]+40,fc[1]+40,fc[2]+40),(cx-4,cy-3,10,5))
    # Top fin
    pygame.draw.polygon(surf,fdk,[(cx-1,cy-5),(cx+4,cy-9),(cx+7,cy-5)])
    # Eye
    pygame.draw.circle(surf,(240,230,255),(cx+6,cy-1),3)
    pygame.draw.circle(surf,feye,(cx+6,cy-1),2)
    pygame.draw.circle(surf,(255,255,255),(cx+7,cy-2),1)


def _draw_ddr_arrow(surf, direction, col, cx, cy, sz=13, alpha=255):
    """Draw a thick DDR-style filled arrow. direction: 'up'|'down'|'left'|'right'."""
    r,g,b = col
    s = pygame.Surface((sz*4+2, sz*4+2), pygame.SRCALPHA)
    sc = sz*2+1  # surface centre
    hw = max(3, sz//3)  # half stem width
    # Arrow shape: arrowhead (triangle) + stem (rectangle), pointing in direction
    if direction == 'up':
        pts = [(sc, sc-sz), (sc-sz, sc+hw//2), (sc-hw, sc+hw//2),
               (sc-hw, sc+sz), (sc+hw, sc+sz), (sc+hw, sc+hw//2), (sc+sz, sc+hw//2)]
    elif direction == 'down':
        pts = [(sc, sc+sz), (sc-sz, sc-hw//2), (sc-hw, sc-hw//2),
               (sc-hw, sc-sz), (sc+hw, sc-sz), (sc+hw, sc-hw//2), (sc+sz, sc-hw//2)]
    elif direction == 'left':
        pts = [(sc-sz, sc), (sc+hw//2, sc-sz), (sc+hw//2, sc-hw),
               (sc+sz, sc-hw), (sc+sz, sc+hw), (sc+hw//2, sc+hw), (sc+hw//2, sc+sz)]
    else:  # right
        pts = [(sc+sz, sc), (sc-hw//2, sc-sz), (sc-hw//2, sc-hw),
               (sc-sz, sc-hw), (sc-sz, sc+hw), (sc-hw//2, sc+hw), (sc-hw//2, sc+sz)]
    pygame.draw.polygon(s, (r,g,b,alpha), pts)
    # Dark outline for pop
    oc = (max(0,r-60), max(0,g-60), max(0,b-60), min(255,alpha))
    pygame.draw.polygon(s, oc, pts, 2)
    surf.blit(s, (cx - sz*2 - 1, cy - sz*2 - 1))


# ── CODE GAME ─────────────────────────────────────────────────────────────────
HACK=[
    "def dream_run():",
    "  # loading modules",
    "  if (x): fish.exe OK",
    "  func() → patch node",
    "  while{}: loop active",
    "  return kawaii_mode",
    ">> compile: OK",
    "  if (x): checksum pass",
    "  func() inject: done",
    "  while{}: buffer live",
    "  return ACCESS_GRANTED",
    ">> all tests passing",
    "  func() dreams: ON",
    ">> dream.sync: LIVE",
]

class DreamGame:
    DIRS  = ['func()','return','if (x):','while{}']
    DKEYS = {pygame.K_UP:'func()',pygame.K_DOWN:'return',
             pygame.K_LEFT:'if (x):',pygame.K_RIGHT:'while{}'}
    ARFULL= {'func()':'↑','return':'↓','if (x):':'←','while{}':'→'}
    ALABEL= {'func()':'UP','return':'DOWN','if (x):':'LEFT','while{}':'RIGHT'}
    ARDIR = {'func()':'up','return':'down','if (x):':'left','while{}':'right'}
    KCOLS = {'func()': (255,120,210),   # hot pink
             'return': (180,120,255),   # lavender
             'if (x):':(255, 60,185),   # magenta
             'while{}':(220,130,255)}   # purple
    LIVES = 3   # starting lives; max lives = 5

    def __init__(self,w):
        self.w=w; self.state='start'
        self.seq=[]; self.si=0; self.ii=0; self.rnd=1
        self.show_t=0; self.show_phase='on'; self.res_t=0; self.flash=None
        self.frame=0; self.hlines=[]; self.hi=0
        self.cd_t=0; self.cd=3
        self.lives     = self.LIVES      # hearts remaining; run ends at 0
        # Streak: counts consecutive correct rounds.
        # At streak 5 → earn 2 fish AND gain +1 life (up to 5), then streak resets.
        self.streak    = 0
        self.fish_earned = 0             # cumulative fish earned this session
        self.last_earn   = 0             # fish earned on the most recent win
        self.shake_t   = 0               # ms remaining for shake
        self.err_flash = 0               # ms remaining for red flash
        self.sparkles  = []              # ambient floating hearts/stars
        self.particles = []              # burst particles on correct key
        # Pre-built CRT scanline overlay (built once, blit every frame)
        self._crt=pygame.Surface((SW,SH),pygame.SRCALPHA)
        for _cy in range(0,SH,2):
            pygame.draw.line(self._crt,(0,0,0,18),(0,_cy),(SW,_cy))

    def _pick_next(self):
        """Pick next item: no 3 consecutive same; no immediate repeat on short seqs."""
        choices=list(self.DIRS)
        if len(self.seq)>=2 and self.seq[-1]==self.seq[-2]:
            choices=[d for d in choices if d!=self.seq[-1]]
        elif len(self.seq)>=1 and len(self.seq)<5:
            choices=[d for d in choices if d!=self.seq[-1]]
        return random.choice(choices)

    def _show_timing(self):
        """ON/OFF display ms — speeds up from round 5 (original Simon mechanic)."""
        if   self.rnd>=13: return 420,110
        elif self.rnd>=9:  return 540,135
        elif self.rnd>=5:  return 670,155
        else:               return 820,180

    def _retry(self):
        """Immediately re-show the same sequence after a mistake (life lost)."""
        self.si=0; self.ii=0; self.show_t=0; self.show_phase='on'
        self.flash=None
        self.state='showing'

    def _begin(self):
        n=min(2+(self.rnd-1)//3,9)
        while len(self.seq)<n: self.seq.append(self._pick_next())
        self.si=0; self.ii=0; self.show_t=0; self.show_phase='on'
        self.state='showing'; self.flash=None
        self.hlines=[]; self.hi=0

    def handle_event(self,ev):
        if ev.type==pygame.KEYDOWN:
            if self.state=='start' and ev.key in(pygame.K_RETURN,pygame.K_SPACE):
                self.lives=self.LIVES; self.streak=0; self.fish_earned=0
                self.rnd=1; self.seq=[]
                self.state='countdown'; self.cd_t=0; self.cd=3; return
            if self.state=='fail':
                return 'back'
            if self.state!='waiting': return
            d=self.DKEYS.get(ev.key)
            if not d: return
            self.flash=d
            # Terminal types a line per input
            if self.hi<len(HACK): self.hlines.append(HACK[self.hi]); self.hi+=1
            if len(self.hlines)>5: self.hlines.pop(0)

            if d==self.seq[self.ii]:
                # Particle burst from tile centre
                ti=self.DIRS.index(d)
                _tw,_th=96,70; _gap=8; _ax=(SW-(4*(_tw+_gap)-_gap))//2
                _tcx=_ax+ti*(_tw+_gap)+_tw//2; _tcy=10+_th//2
                for _ in range(10):
                    _ang=random.uniform(0,math.pi*2); _spd=random.uniform(1.8,4.8)
                    self.particles.append({
                        'x':float(_tcx),'y':float(_tcy),
                        'vx':math.cos(_ang)*_spd,'vy':math.sin(_ang)*_spd,
                        'col':self.KCOLS[d],'life':1.0,'sz':random.uniform(1.5,3.5)
                    })
                self.ii+=1
                if self.ii>=len(self.seq):
                    # 1 fish per correct key; x2 on 5th streak (+life)
                    self.streak+=1
                    base=len(self.seq)
                    if self.streak>=5:
                        earn=base*2
                        self.lives=min(5,self.lives+1)
                        self.streak=0
                        self.hlines.append(f">> +{earn} fish  BUILD OK  [+LIFE!]")
                    else:
                        earn=base
                        self.hlines.append(f">> +{earn} fish  BUILD OK")
                    self.last_earn=earn
                    self.fish_earned+=earn
                    self.w.points+=earn
                    self.w.save()
                    self.state='win'; self.res_t=0; self.rnd+=1
                    Sounds.dream_win()
                    self.w.happiness=min(100,self.w.happiness+15)
            else:
                self.lives=max(0,self.lives-1)
                self.streak=0
                self.shake_t=500; self.err_flash=420
                self.hlines.append(f">> ERROR: bad input  [{self.lives} lives left]")
                Sounds.dream_lose()
                self.w.happiness=min(100,self.w.happiness+3)
                if self.lives<=0:
                    self.state='fail'; self.res_t=0
                else:
                    self._retry()

    def update(self,dt):
        self.frame+=1; self.show_t+=dt
        if self.shake_t>0:   self.shake_t  =max(0,self.shake_t-dt)
        if self.err_flash>0: self.err_flash=max(0,self.err_flash-dt)

        # Ambient sparkles in wall area (above tile zone)
        self.sparkles=[s for s in self.sparkles if s['life']>0]
        for s in self.sparkles: s['life']-=dt/1200.0; s['y']-=0.3
        if self.frame%18==0 and random.random()<0.7:
            col=random.choice(list(self.KCOLS.values()))
            self.sparkles.append({
                'x':random.randint(12,SW-110),'y':random.randint(100,135),
                'col':col,'life':1.0,'heart':random.random()<0.45})

        # Particle physics
        self.particles=[p for p in self.particles if p['life']>0]
        for p in self.particles:
            p['x']+=p['vx']; p['y']+=p['vy']
            p['vy']+=0.12; p['life']-=dt/550.0

        if self.state=='countdown':
            self.cd_t+=dt
            if self.cd_t>1000: self.cd_t=0; self.cd-=1
            if self.cd<=0: self._begin()
        elif self.state=='showing':
            _on_t,_off_t=self._show_timing()
            if self.show_phase=='on':
                if self.show_t>_on_t:
                    self.show_t=0; self.show_phase='off'
            else:  # dark gap between items
                if self.show_t>_off_t:
                    self.show_t=0; self.show_phase='on'; self.si+=1
                    if self.si>=len(self.seq):
                        self.state='waiting'; self.flash=None; self.show_phase='on'
        elif self.state in('win','lose'):
            self.res_t+=dt
            if self.res_t>1800:
                if self.state=='win': self._begin()
                else: self._retry()   # replay same sequence with fresh countdown
        elif self.state=='fail':
            self.res_t+=dt  # just for animation timing on fail screen

    def draw(self,surf):
        # ── DARK PURPLE GAMING ROOM ── (ref: deep indigo setup, cherry blossoms, neon) ──

        # Wall: deep indigo-purple; floor: very dark
        wline=int(SH*0.62)
        for y in range(SH):
            t=y/SH
            if t<0.62:
                r=int(22+t*16); g=int(8+t*8); b=int(55+t*22)
                c=clamp_color(r,g,b)
            else:
                tf=(t-0.62)/0.38
                c=clamp_color(int(14+tf*6),int(5+tf*3),int(30+tf*12))
            pygame.draw.line(surf,c,(0,y),(SW,y))

        # Neon pink floor strip + underglow
        pygame.draw.rect(surf,(255,25,130),(0,wline,SW,2))
        for gi in range(48,0,-3):
            ga=int(36*(gi/48))
            gs0=pygame.Surface((SW,gi*2),pygame.SRCALPHA)
            pygame.draw.ellipse(gs0,(255,20,120,ga),(0,0,SW,gi*2))
            surf.blit(gs0,(0,wline+2-gi))

        # ── FAIRY LIGHTS — more droop, more glow on dark bg ──
        n_lights=22; rope_pts=[]
        for li in range(n_lights+1):
            lx=int(li*(SW/n_lights)); droop=int(10*math.sin(li/n_lights*math.pi))
            rope_pts.append((lx,4+droop))
        for i in range(len(rope_pts)-1):
            pygame.draw.line(surf,(65,40,95),rope_pts[i],rope_pts[i+1],1)
        for li in range(n_lights):
            lx,ly=rope_pts[li]
            wire_len=7+int(math.sin(li*0.9)*3)
            pygame.draw.line(surf,(60,38,88),(lx,ly),(lx,ly+wire_len),1)
            lc=[(255,140,220),(195,120,255),(120,185,255),(255,215,90),(170,255,195),(255,95,195)][li%6]
            fv=max(0.0,0.48+0.52*math.sin(self.frame*0.07+li*0.65))
            for gr in range(13,0,-2):
                ga=max(0,int(58*fv*(gr/13)))
                gs2=pygame.Surface((gr*2,gr*2),pygame.SRCALPHA)
                pygame.draw.circle(gs2,(*lc,ga),(gr,gr),gr)
                surf.blit(gs2,(lx-gr,ly+wire_len-gr))
            pygame.draw.circle(surf,lc,(lx,ly+wire_len),4)
            pygame.draw.circle(surf,clamp_color(lc[0]+35,lc[1]+35,lc[2]+35),(lx,ly+wire_len),2)

        # ── CHERRY BLOSSOMS — arch in from both sides ──
        _brng=random.Random(77)
        def _blossom_branch(sx,sy,angle,length,depth):
            if depth==0 or length<5: return
            ex=int(sx+math.cos(angle)*length); ey=int(sy+math.sin(angle)*length)
            bc=clamp_color(50+depth*8,22+depth*3,60+depth*6)
            pygame.draw.line(surf,bc,(sx,sy),(ex,ey),max(1,depth))
            if depth<=2:
                for _ in range(5):
                    bx=ex+_brng.randint(-10,10); by=ey+_brng.randint(-10,10)
                    br=_brng.randint(4,7)
                    bs=pygame.Surface((br*2+2,br*2+2),pygame.SRCALPHA)
                    ba=_brng.randint(155,210)
                    bc2=_brng.choice([(255,148,200,ba),(255,172,215,ba),(240,128,185,ba),(255,198,225,ba)])
                    pygame.draw.circle(bs,bc2,(br+1,br+1),br); surf.blit(bs,(bx-br,by-br))
            _blossom_branch(ex,ey,angle-0.40,length*0.68,depth-1)
            _blossom_branch(ex,ey,angle+0.35,length*0.62,depth-1)
            if depth>2: _blossom_branch(ex,ey,angle-0.05,length*0.76,depth-1)
        _blossom_branch(-10,-2,-math.pi*0.10,68,5)   # left arch
        _blossom_branch(SW+10,-2,-math.pi*0.90,68,5) # right arch (mirror)
        # Falling petals across whole width
        for i in range(26):
            px2=int((i*73+self.frame*0.55)%SW)
            py2=int((i*51+self.frame*(0.26+i*0.016))%wline)
            pa=int(115+75*math.sin(self.frame*0.05+i))
            ps2=pygame.Surface((6,6),pygame.SRCALPHA)
            pygame.draw.ellipse(ps2,(255,162,205,pa),(0,1,6,4))
            surf.blit(ps2,(px2-3,py2-2))

        # ── WINDOW — right-of-centre, deep starry night ──
        wx2=SW//2+12; wy2=18; ww2=128; wh2=100
        pygame.draw.rect(surf,(42,18,78),(wx2-5,wy2-5,ww2+10,wh2+10),border_radius=8)
        pygame.draw.rect(surf,(128,55,200),(wx2-5,wy2-5,ww2+10,wh2+10),2,border_radius=8)
        for wy3 in range(wh2):
            t2=wy3/wh2
            wc=clamp_color(int(8+t2*18),int(4+t2*10),int(32+t2*28))
            pygame.draw.line(surf,wc,(wx2,wy2+wy3),(wx2+ww2,wy2+wy3))
        pygame.draw.line(surf,(75,42,125),(wx2+ww2//2,wy2),(wx2+ww2//2,wy2+wh2),1)
        pygame.draw.line(surf,(75,42,125),(wx2,wy2+wh2//2),(wx2+ww2,wy2+wh2//2),1)
        for i in range(22):
            stx=wx2+4+int((i*37)%(ww2-8)); sty=wy2+4+int((i*23)%(int(wh2*0.6)-4))
            fv2=0.32+0.68*math.sin(self.frame*0.07+i*0.8)
            if i%4==0: _draw_cross_star(surf,(195,165,255),stx,sty,1,int(fv2*220))
            else: pygame.draw.rect(surf,(175,155,255),(stx,sty,2,2))
        pygame.draw.circle(surf,(255,248,195),(wx2+ww2-16,wy2+14),9)
        pygame.draw.circle(surf,(10,4,30),(wx2+ww2-11,wy2+10),8)
        for ci in range(7):
            cbx=wx2+6+ci*17; cbh=random.Random(ci+10).randint(6,15)
            pygame.draw.rect(surf,clamp_color(28+ci*7,10+ci*4,55+ci*12),(cbx,wy2+wh2-cbh,13,cbh))
        wg=pygame.Surface((ww2,wh2),pygame.SRCALPHA)
        pygame.draw.rect(wg,(110,72,210,18),(0,0,ww2,wh2),border_radius=5); surf.blit(wg,(wx2,wy2))
        pygame.draw.rect(surf,(50,26,88),(wx2-7,wy2+wh2,ww2+14,8),border_radius=3)

        # ── GAMING CHAIR — far left, partially visible ──
        ch_x=6; ch_y=wline-90
        pygame.draw.rect(surf,(28,12,58),(ch_x,ch_y,44,74),border_radius=9)
        pygame.draw.rect(surf,(115,55,195),(ch_x,ch_y,44,74),2,border_radius=9)
        pygame.draw.rect(surf,(38,18,72),(ch_x+5,ch_y-11,34,19),border_radius=5)
        pygame.draw.rect(surf,(115,55,195),(ch_x+5,ch_y-11,34,19),1,border_radius=5)
        # Cat paw cushion — white, fluffy
        for pxi,pxo,pyo in [(0,-3,0),(1,12,0),(2,5,-9),(3,-7,-4)]:
            pygame.draw.circle(surf,(238,228,255),(ch_x+19+pxo,ch_y+22+pyo),7)
        pygame.draw.ellipse(surf,(238,228,255),(ch_x+6,ch_y+14,30,22))
        pygame.draw.ellipse(surf,(198,182,230),(ch_x+8,ch_y+16,26,18))
        # Chair seat
        pygame.draw.ellipse(surf,(32,15,68),(ch_x-6,ch_y+70,58,18))
        pygame.draw.ellipse(surf,(52,26,92),(ch_x-6,ch_y+70,58,18),1)

        # ── BOOKSHELF — right side, dark purple ──
        bsx=SW-104; bsy=18; bsw=100; bsh=110
        pygame.draw.rect(surf,(32,14,62),(bsx,bsy,bsw,bsh),border_radius=5)
        pygame.draw.rect(surf,(88,42,138),(bsx,bsy,bsw,bsh),2,border_radius=5)
        rng3=random.Random(42)
        shelf_items=[
            [(185,80,255),(255,95,185),(75,180,255),(155,225,140),(210,95,255),(155,195,255)],
            [(255,165,75),(115,185,255),(178,95,255),(255,155,195),(95,230,195)],
            [(138,75,220),(195,138,75),(75,155,220),(218,155,115),(155,95,238)],
        ]
        for shelf in range(3):
            shy=bsy+10+shelf*(bsh//3); shelf_y=shy+bsh//3-6
            pygame.draw.rect(surf,(52,25,92),(bsx+4,shelf_y,bsw-8,5),border_radius=2)
            pygame.draw.rect(surf,(78,42,128),(bsx+4,shelf_y,bsw-8,2),border_radius=2)
            bx3=bsx+6
            for bc3 in shelf_items[shelf]:
                bkw=rng3.randint(8,14); bkh=rng3.randint(16,30); bky=shelf_y-bkh
                if bx3+bkw<bsx+bsw-4:
                    pygame.draw.rect(surf,bc3,(bx3,bky,bkw,bkh),border_radius=1)
                    pygame.draw.rect(surf,clamp_color(bc3[0]+42,bc3[1]+42,bc3[2]+42),(bx3,bky,bkw,3))
                    pygame.draw.rect(surf,clamp_color(bc3[0]-32,bc3[1]-32,bc3[2]-32),(bx3,bky,bkw,bkh),1,border_radius=1)
                bx3+=bkw+rng3.randint(1,3)
        fig_x=bsx+bsw-20; fig_y=bsy+10
        if IMG_PIX_PENGUIN:
            surf.blit(pygame.transform.scale(IMG_PIX_PENGUIN,(20,20)),(fig_x-10,fig_y-10))
        else:
            pygame.draw.circle(surf,(195,155,255),(fig_x,fig_y),5)
        # Dream catcher on shelf side
        dc_x=bsx-10; dc_y=bsy+28
        pygame.draw.circle(surf,(175,115,255),(dc_x,dc_y),10,2)
        pygame.draw.circle(surf,(195,135,255),(dc_x,dc_y),6,1)
        for ang3 in range(0,360,45):
            r3=math.radians(ang3)
            pygame.draw.line(surf,(155,95,220),(dc_x,dc_y),(int(dc_x+8*math.cos(r3)),int(dc_y+8*math.sin(r3))),1)
        for fi,fao in enumerate([-4,0,4]):
            pygame.draw.line(surf,(175,135,240),(dc_x+fao,dc_y+10),(dc_x+fao+fi-1,dc_y+22),1)

        # ── NEON PLANT left of desk — coral/purple glow ──
        pl_x=18; pl_y=wline-8
        pygame.draw.rect(surf,(48,22,88),(pl_x+6,pl_y-8,14,18),border_radius=3)
        pygame.draw.rect(surf,(105,50,175),(pl_x+6,pl_y-8,14,18),1,border_radius=3)
        for leaf_ang,leaf_len,leaf_col in [
            (-1.3,30,(255,45,200)),(-0.7,36,(215,28,255)),(-1.85,24,(255,75,215)),
            (-0.2,32,(195,45,255)),(0.25,20,(255,55,175))
        ]:
            lx2=int(pl_x+13+math.cos(leaf_ang)*leaf_len); ly2=int(pl_y-3+math.sin(leaf_ang)*leaf_len)
            pygame.draw.line(surf,leaf_col,(pl_x+13,pl_y-3),(lx2,ly2),2)
            lgl=pygame.Surface((12,8),pygame.SRCALPHA)
            pygame.draw.ellipse(lgl,(*leaf_col,75),(0,0,12,8)); surf.blit(lgl,(lx2-6,ly2-4))

        # Right neon plant (bookshelf side)
        pl2_x=bsx-18; pl2_y=wline-6
        pygame.draw.rect(surf,(48,22,88),(pl2_x+5,pl2_y-8,12,16),border_radius=3)
        for leaf_ang2,leaf_len2,leaf_c2 in [
            (-1.8,22,(215,55,255)),(-1.4,30,(195,75,255)),(-2.2,16,(175,45,240)),(-0.9,24,(235,65,255))
        ]:
            lx3=int(pl2_x+11+math.cos(leaf_ang2)*leaf_len2); ly3=int(pl2_y-2+math.sin(leaf_ang2)*leaf_len2)
            pygame.draw.line(surf,leaf_c2,(pl2_x+11,pl2_y-2),(lx3,ly3),2)
            gls=pygame.Surface((10,6),pygame.SRCALPHA)
            pygame.draw.ellipse(gls,(*leaf_c2,80),(0,0,10,6)); surf.blit(gls,(lx3-5,ly3-3))

        # ── Wall stickers — glowing hearts on dark wall ──
        _wall_stickers = [
            (160, 150, self.KCOLS['func()']),
            (208, 158, self.KCOLS['if (x):']),
            (255, 145, self.KCOLS['return']),
        ]
        for wx3,wy3,wc in _wall_stickers:
            _draw_pixel_heart(surf, wc, wx3, wy3, px=2, alpha=200)
        _draw_cross_star(surf, self.KCOLS['while{}'], 183, 164, 2, 160)
        _draw_cross_star(surf, self.KCOLS['func()'],  238, 152, 2, 145)

        # ── Ambient sparkles (update in self.sparkles) ──
        for sp in self.sparkles:
            a=max(0,int(sp['life']*200))
            if sp['heart']:
                _draw_pixel_heart(surf, sp['col'], int(sp['x']), int(sp['y']), px=2, alpha=a)
            else:
                _draw_cross_star(surf, sp['col'], int(sp['x']), int(sp['y']), 2, a)

        # ── Desk ── (Waddle is drawn inside draw_desk, on top of everything)
        draw_desk(surf, SW//2-20, wline-2, self.frame, self.state)

        # ── START SCREEN ──
        if self.state=='start':
            cy=draw_win(surf,SW//2-116,32,232,120,"code.exe")
            blit_c(surf,F18,"repeat the pattern",(55,18,88),SW//2,cy+4)
            blit_c(surf,F18,"to win!",(55,18,88),SW//2,cy+26)
            pulse=0.65+0.30*math.sin(self.frame*0.12)
            bc2=clamp_color(int(80+55*pulse),int(52+40*pulse),int(160+88*pulse))
            bx3=SW//2-112; by3=cy+62
            pygame.draw.rect(surf,bc2,(bx3,by3,224,28),border_radius=8)
            pygame.draw.rect(surf,(198,168,255),(bx3,by3,224,28),2,border_radius=8)
            blit_c(surf,F14,"PRESS ENTER TO START",(255,240,255),SW//2,by3+7)
            blit_shadow_l(surf,F8,"ESC = close IDE",(255,220,245),12,10)
            return

        if self.state=='countdown':
            cy=draw_win(surf,SW//2-72,22,144,74,"compiling...")
            _num_s=F32.render(str(self.cd),False,(245,205,255))
            _nx=SW//2-_num_s.get_width()//2; _ny=cy+10
            # Glow copies behind digit
            # Glow via smoothscale down→up
            _gc=pygame.Surface((_num_s.get_width()+24,_num_s.get_height()+24),pygame.SRCALPHA)
            _gc.blit(_num_s,(12,12))
            _gsm=pygame.transform.smoothscale(_gc,(max(1,_gc.get_width()//3),max(1,_gc.get_height()//3)))
            _gb=pygame.transform.smoothscale(_gsm,(_gc.get_size()))
            pulse2=0.6+0.4*math.sin(self.frame*0.15)
            _gb.set_alpha(int(170*pulse2))
            surf.blit(_gb,(_nx-12,_ny-12))
            surf.blit(_num_s,(_nx,_ny))
            return

        # ── Shake offset ──
        if self.shake_t>0:
            ox=random.randint(-5,5); oy=random.randint(-3,3)
        else:
            ox=oy=0

        # ── Red error flash border ──
        if self.err_flash>0:
            fa=int((self.err_flash/420)*140)
            ef=pygame.Surface((SW,SH),pygame.SRCALPHA)
            pygame.draw.rect(ef,(255,30,60,fa),(0,0,SW,SH),14)
            for gi in range(0,SH,8):
                if random.random()<0.25:
                    pygame.draw.rect(ef,(255,60,80,int(fa*0.4)),(0,gi,SW,2))
            surf.blit(ef,(0,0))

        # ── FAIL SCREEN ──
        if self.state=='fail':
            ov=pygame.Surface((SW,SH),pygame.SRCALPHA)
            ov.fill((20,5,10,210)); surf.blit(ov,(0,0))
            cy=draw_win(surf,SW//2-130,SH//2-70,260,140,"BUILD FAILED")
            blit_c(surf,F32,"BUILD FAILED",(255,60,100),SW//2,cy+4)
            blit_c(surf,F8,"fish earned",(160,110,220),SW//2,cy+48)
            blit_c(surf,F32,f"{self.fish_earned}",(255,75,155),SW//2,cy+64)
            return

        # ── CODE TILES — large centered DDR arrows only ──
        tw,th=96,70; gap=8
        total=4*(tw+gap)-gap; ax=(SW-total)//2; ay=10+oy
        for i,d in enumerate(self.DIRS):
            tx=ax+i*(tw+gap)+ox
            show_on=(self.state=='showing' and self.show_phase=='on'
                     and self.si<len(self.seq) and self.seq[self.si]==d)
            inp_on=(self.flash==d)
            col=self.KCOLS[d]

            if show_on:
                # Simon Says: pulsing glow — single surface allocation for all layers
                pulse=0.55+0.45*math.sin(self.show_t*0.009)
                glow_r=max(10,int(28*pulse))
                _gls=pygame.Surface((tw+glow_r*2,th+glow_r*2),pygame.SRCALPHA)
                for g in range(glow_r,0,-2):
                    ha=int(44*(g/glow_r))
                    pygame.draw.rect(_gls,(*col,ha),(glow_r-g,glow_r-g,tw+g*2,th+g*2),border_radius=14+g)
                surf.blit(_gls,(tx-glow_r,ay-glow_r))
                # Soft bloom via smoothscale down→up (cheap, always works)
                _bsrc=pygame.Surface((tw,th),pygame.SRCALPHA)
                pygame.draw.rect(_bsrc,(*col,int(85*pulse)),(0,0,tw,th),border_radius=14)
                _bsm=pygame.transform.smoothscale(_bsrc,(max(1,tw//4),max(1,th//4)))
                _blm=pygame.transform.smoothscale(_bsm,(tw+20,th+20))
                _blm.set_alpha(int(130*pulse))
                surf.blit(_blm,(tx-10,ay-10))
                # Base fill
                fill_a=int(190+55*pulse)
                gs=pygame.Surface((tw,th),pygame.SRCALPHA)
                pygame.draw.rect(gs,(*col,fill_a),(0,0,tw,th),border_radius=14)
                surf.blit(gs,(tx,ay))
                # Entry flash
                if self.show_t<130:
                    fl=pygame.Surface((tw,th),pygame.SRCALPHA)
                    fl.fill((255,255,255,int((1-self.show_t/130)*160)))
                    surf.blit(fl,(tx,ay))
                pygame.draw.rect(surf,clamp_color(col[0]+45,col[1]+45,col[2]+45),(tx,ay,tw,th),3,border_radius=14)
                arr_col=(255,255,255)
            elif inp_on:
                gs=pygame.Surface((tw,th),pygame.SRCALPHA)
                pygame.draw.rect(gs,(*col,210),(0,0,tw,th),border_radius=14)
                surf.blit(gs,(tx,ay))
                pygame.draw.rect(surf,col,(tx,ay,tw,th),3,border_radius=14)
                arr_col=(255,255,255)
            else:
                # Subtle ambient glow behind inactive tile
                for _g in range(6,0,-2):
                    _hs=pygame.Surface((tw+_g*2,th+_g*2),pygame.SRCALPHA)
                    pygame.draw.rect(_hs,(*col,7),(0,0,tw+_g*2,th+_g*2),border_radius=14+_g)
                    surf.blit(_hs,(tx-_g,ay-_g))
                ds=pygame.Surface((tw,th),pygame.SRCALPHA)
                pygame.draw.rect(ds,(20,8,46,215),(0,0,tw,th),border_radius=14)
                surf.blit(ds,(tx,ay))
                pygame.draw.rect(surf,col,(tx,ay,tw,th),2,border_radius=14)
                arr_col=clamp_color(col[0]-40,col[1]-40,col[2]-40)

            # Large DDR arrow centered in tile
            _draw_ddr_arrow(surf,self.ARDIR[d],arr_col,tx+tw//2,ay+th//2,sz=16)

        # ── HUD row: lives | progress dots | fish ──
        dot_y=ay+th+10+oy
        # Pill background spanning full width
        hud_pill=pygame.Surface((SW-12,22),pygame.SRCALPHA)
        pygame.draw.rect(hud_pill,(18,7,44,190),(0,0,SW-12,22),border_radius=7)
        surf.blit(hud_pill,(6+ox,dot_y-11+oy))
        pygame.draw.rect(surf,(72,36,128),(6+ox,dot_y-11+oy,SW-12,22),1,border_radius=7)

        # Lives hearts — left inside pill (draw up to max(LIVES, lives))
        max_hearts=max(self.LIVES,self.lives)
        for i in range(max_hearts):
            hcol=(245,75,130) if i<self.lives else (45,28,80)
            _draw_pixel_heart(surf,hcol,22+i*19+ox,dot_y+oy,px=2,alpha=235)

        # Progress dots — centred
        n_seq=max(1,len(self.seq))
        dot_spacing=min(22, (SW-200)//(n_seq+1))
        for i in range(len(self.seq)):
            dx=int(SW//2-(n_seq-1)*dot_spacing//2+i*dot_spacing)
            if i<self.ii:
                pygame.draw.circle(surf,(255,140,220),(dx,dot_y),5)
                pygame.draw.circle(surf,(200,80,200),(dx,dot_y),5,1)
            else:
                pygame.draw.circle(surf,(80,50,130),(dx,dot_y),4)
                pygame.draw.circle(surf,(130,80,190),(dx,dot_y),4,1)

        # Fish pill — right inside pill
        blit_l(surf,F11,f"✦{self.fish_earned:03d}",(220,140,255),SW-68+ox,dot_y-7+oy)

        # Particle burst draw
        for p in self.particles:
            a=max(0,min(255,int(p['life']*245)))
            sz=max(1,int(p['sz']*p['life']))
            _draw_cross_star(surf,p['col'],int(p['x']),int(p['y']),sz,a)

        # ── TERMINAL at bottom — dark readable text (3 lines max) ──
        term_h=68; term_y=SH-term_h-4+oy; term_x=4+ox; term_w=SW-8
        max_tw2=term_w-18
        cy2=draw_win(surf,term_x,term_y,term_w,term_h,"code.exe — output")
        shown=self.hlines[-3:] if self.hlines else []
        for i,line in enumerate(shown):
            tl=line
            while F_SM.size(tl)[0]>max_tw2 and len(tl)>4: tl=tl[:-1]
            if F_SM.size(tl)[0]>max_tw2: tl=tl[:-1]+'…'
            if "ERROR" in tl:    lc=(170,45,65)
            elif "GRANTED" in tl or "OK" in tl: lc=(38,125,55)
            else:                lc=(82,52,138)
            blit_l(surf,F_SM,tl,lc,term_x+8,cy2+i*14,aa=True)
        if self.frame%20<10:
            if shown:
                cw2=F_SM.size(shown[-1])[0]
                pygame.draw.rect(surf,(100,62,155),(term_x+8+min(cw2,max_tw2),cy2+(len(shown)-1)*14+2,6,9))
            else:
                pygame.draw.rect(surf,(100,62,155),(term_x+8,cy2+2,6,9))

        # ── Status bar (above terminal) ──
        if self.state in('showing','waiting','win','lose'):
            msgs={'showing':f"watch carefully...  {self.si+1} / {len(self.seq)}",
                  'waiting':f"your turn!  {self.ii} / {len(self.seq)} done",
                  'win':    f"✦ round {self.rnd-1} compiled!  +{self.last_earn} fish",
                  'lose':   f"✕ wrong!  {self.lives} {'life' if self.lives==1 else 'lives'} left  — retrying..."}
            mcols={'showing':(55,18,95),'waiting':(38,18,90),
                   'win':(80,18,160),'lose':(155,28,48)}
            sy2=term_y-26+oy
            if self.state=='win':
                sy2-=int(abs(math.sin(self.res_t*0.007))*6)
            sb=pygame.Surface((SW-20,22),pygame.SRCALPHA)
            _bg_col=(238,220,255,230) if self.state=='win' else \
                    (255,235,235,230) if self.state=='lose' else (255,245,255,220)
            pygame.draw.rect(sb,_bg_col,(0,0,SW-20,22),border_radius=6)
            surf.blit(sb,(10+ox,sy2))
            _bdr=(160,80,220) if self.state=='win' else (200,60,60) if self.state=='lose' else (210,100,195)
            pygame.draw.rect(surf,_bdr,(10+ox,sy2,SW-20,22),1,border_radius=6)
            blit_c(surf,F11,msgs[self.state],mcols[self.state],SW//2+ox,sy2+4)

        # Round badge (top-left pill)
        rnd_s=pygame.Surface((68,18),pygame.SRCALPHA)
        pygame.draw.rect(rnd_s,(20,8,48,200),(0,0,68,18),border_radius=6)
        surf.blit(rnd_s,(6+ox,4+oy))
        pygame.draw.rect(surf,(100,55,180),(6+ox,4+oy,68,18),1,border_radius=6)
        blit_l(surf,F11,f"RND {self.rnd}",(220,185,255),10+ox,5+oy)

        blit_shadow_l(surf,F8,"ESC = close IDE",(200,170,240),SW-116,5)

        # CRT scanline overlay — subtle, runs over everything
        surf.blit(self._crt,(0,0))


# ── WARDROBE CATALOG ──────────────────────────────────────────────────────────
ITEMS = [
    {'id':'bow',    'name':'Pink Bow',        'cost':50,  'type':'hat',    'col':(255,140,195)},
    {'id':'tophat', 'name':'Star Band',        'cost':100, 'type':'hat',    'col':(200,120,255)},
    {'id':'crown',  'name':'Star Crown',      'cost':200, 'type':'hat',    'col':(235,150,210)},
    {'id':'beret',  'name':'Lilac Beret',     'cost':80,  'type':'hat',    'col':(168,110,228)},
    {'id':'halo',   'name':'Flip Phone',      'cost':150, 'type':'hat',    'col':(180,120,255)},
    {'id':'horns',  'name':'Angel Halo',      'cost':120, 'type':'hat',    'col':(200,155,255)},
    {'id':'shades', 'name':'Cool Shades',     'cost':80,  'type':'glasses','col':(28, 18, 48)},
    {'id':'hrtgls', 'name':'Cherry Charm',    'cost':110, 'type':'scarf',  'col':(220,50,90)},
    {'id':'scarf',  'name':'Pink Scarf',      'cost':60,  'type':'scarf',  'col':(255,150,195)},
    {'id':'necktie','name':'Heart Necklace',  'cost':70,  'type':'scarf',  'col':(180,100,255)},
]

def draw_accessory(surf, item_id, col, ox, oy, px=7):
    """
    Draw a wearable accessory on top of Waddle.
    All pixel offsets scale with px so wardrobe cards (px=2) look proportional.
    """
    sc = px / 7.0          # scale factor: 1.0 at default px=7, ~0.29 at px=2
    def S(v):              # scaled signed offset
        if v == 0: return 0
        return max(1, int(round(abs(v)*sc))) * (1 if v > 0 else -1)
    def Sz(v):             # scaled dimension — always >= 1
        return max(1, int(round(v * sc)))

    hcx   = ox + int(13*px)
    htop  = oy
    heye  = oy + (9*px)//2   # eye block rows 3-6, centre at row 4.5
    hneck = oy + int(10*px)
    dk    = clamp_color(col[0]-40, col[1]-40, col[2]-40)
    lt    = clamp_color(col[0]+40, col[1]+40, col[2]+40)

    if item_id == 'bow':
        bx, by2 = hcx, htop - S(2)
        lw = Sz(20); lh = Sz(14)
        # Ribbon tails (behind lobes)
        pygame.draw.polygon(surf, dk, [
            (bx-S(3), by2+S(2)), (bx-S(14), by2+S(16)), (bx-S(9), by2+S(16))])
        pygame.draw.polygon(surf, dk, [
            (bx+S(3), by2+S(2)), (bx+S(14), by2+S(16)), (bx+S(9), by2+S(16))])
        # Left lobe
        pygame.draw.ellipse(surf, col, (bx-S(22), by2-S(9), lw, lh))
        pygame.draw.ellipse(surf, dk,  (bx-S(22), by2-S(9), lw, lh), max(1,S(2)))
        # Right lobe
        pygame.draw.ellipse(surf, col, (bx+S(2),  by2-S(9), lw, lh))
        pygame.draw.ellipse(surf, dk,  (bx+S(2),  by2-S(9), lw, lh), max(1,S(2)))
        # Center knot
        kw = Sz(12); kh = Sz(10)
        pygame.draw.ellipse(surf, lt, (bx-S(6), by2-S(5), kw, kh))
        pygame.draw.ellipse(surf, dk, (bx-S(6), by2-S(5), kw, kh), 1)
        # Shine
        sw = Sz(8); sh2 = Sz(4)
        shs = pygame.Surface((sw, sh2), pygame.SRCALPHA)
        pygame.draw.ellipse(shs, (255,255,255,80), (0,0,sw,sh2))
        surf.blit(shs, (bx-S(20), by2-S(8)))

    elif item_id == 'tophat':
        # Y2K Star Headband — stretchy band with sparkle stars on top
        bw = Sz(38); bh = Sz(8)
        # Band across forehead
        pygame.draw.rect(surf, col, (hcx-bw//2, htop-S(5), bw, bh), border_radius=Sz(4))
        pygame.draw.rect(surf, dk,  (hcx-bw//2, htop-S(5), bw, bh), 1, border_radius=Sz(4))
        # Shimmer stripe
        pygame.draw.rect(surf, lt,  (hcx-bw//2+S(4), htop-S(4), Sz(14), Sz(2)))
        # Three sparkle stars above the band
        for sxo, ssz in [(-S(13), Sz(5)), (0, Sz(7)), (S(13), Sz(5))]:
            _draw_cross_star(surf, lt, hcx+sxo, htop-S(8)-ssz, ssz, 220)

    elif item_id == 'crown':
        bw = Sz(28); bh = Sz(8)
        pygame.draw.rect(surf, col, (hcx-bw//2, htop-bh, bw, bh), border_radius=2)
        for xo, ch2 in [(-S(10),S(12)), (0,S(16)), (S(10),S(12))]:
            pygame.draw.polygon(surf, col, [
                (hcx+xo-S(5), htop-bh),
                (hcx+xo+S(5), htop-bh),
                (hcx+xo,      htop-bh-ch2)])
        for xo, gc in [(-S(10),(255,140,200)), (0,(190,140,255)), (S(10),(255,180,225))]:
            pygame.draw.circle(surf, gc, (hcx+xo, htop-S(4)), Sz(3))

    elif item_id == 'beret':
        bw = Sz(32); bh = Sz(18)
        pygame.draw.ellipse(surf, col, (hcx-bw//2, htop-S(12), bw, bh))
        pygame.draw.ellipse(surf, clamp_color(col[0]+30,col[1]+30,col[2]+30),
                            (hcx-bw//2, htop-S(12), bw, bh), 2)
        pygame.draw.circle(surf, clamp_color(col[0]-20,col[1]-20,col[2]-20),
                           (hcx+S(8), htop-S(10)), Sz(3))
        sw = Sz(14); sh2 = Sz(6)
        s2 = pygame.Surface((sw, sh2), pygame.SRCALPHA)
        pygame.draw.ellipse(s2, (255,255,255,60), (0,0,sw,sh2))
        surf.blit(s2, (hcx-S(12), htop-S(11)))

    elif item_id == 'halo':
        # Flip Phone — held at right wing tip (col 22-25, row 12-13)
        fpx2 = hcx + S(63); fpy2 = hneck + S(14)
        pw   = Sz(9); half = Sz(7)
        dkp  = clamp_color(col[0]-50, col[1]-50, col[2]-50)
        ltp  = clamp_color(col[0]+40, col[1]+40, col[2]+40)
        pygame.draw.rect(surf, dkp,          (fpx2, fpy2,         pw, half), border_radius=2)
        pygame.draw.rect(surf, (220,140,255),(fpx2+S(1), fpy2+S(1), max(1,pw-S(2)), max(1,half-S(3))))
        pygame.draw.rect(surf, ltp,          (fpx2+pw//2-S(1), fpy2-S(3), Sz(3), Sz(4)))
        pygame.draw.rect(surf, ltp,          (fpx2, fpy2+half, pw, Sz(2)))
        pygame.draw.rect(surf, col,          (fpx2, fpy2+half+S(2), pw, max(1,half+S(1))), border_radius=2)
        for ki in range(2):
            for kj in range(3):
                pygame.draw.rect(surf, dkp, (fpx2+S(2)+kj*S(3), fpy2+half+S(4)+ki*S(3), Sz(2), Sz(2)))
        pygame.draw.rect(surf, dkp, (fpx2, fpy2, pw, half*2+S(3)), 1, border_radius=2)

    elif item_id == 'horns':
        # Angel Halo — flat glowing ring, properly scaled
        hy   = htop - S(10)
        rw   = Sz(34); rh = Sz(14); thick = max(2,S(5))
        gw   = rw+Sz(18); gh = rh+Sz(14)
        glow = pygame.Surface((gw, gh), pygame.SRCALPHA)
        for gi in range(min(S(9),gw//2), 0, max(1,S(3))):
            pygame.draw.ellipse(glow, (*col, int(10*gi//max(1,S(9)))),
                (gw//2-rw//2-gi, gh//2-rh//2-gi//2, rw+gi*2, rh+gi), max(1, thick-2))
        surf.blit(glow, (hcx-gw//2, hy-gh//2))
        pygame.draw.ellipse(surf, col,
            (hcx-rw//2, hy-rh//2, rw, rh), thick)
        pygame.draw.ellipse(surf, clamp_color(col[0]+50,col[1]+50,col[2]+30),
            (hcx-S(11), hy-S(4), Sz(22), Sz(8)), max(1,S(2)))

    elif item_id == 'shades':
        lo = Sz(42)       # eyes are 6 grid cols from centre → ±42px at px=7
        lw2 = Sz(22); lh2 = Sz(12)
        for side in [-1, 1]:
            lx2 = hcx + side*lo - lw2//2
            pygame.draw.rect(surf, col, (lx2, heye-lh2//2, lw2, lh2), border_radius=max(1,S(3)))
            pygame.draw.rect(surf, clamp_color(col[0]+40,col[1]+40,col[2]+40),
                             (lx2, heye-lh2//2, lw2, lh2), 1, border_radius=max(1,S(3)))
            sw2 = Sz(8); sh3 = Sz(4)
            shs2 = pygame.Surface((sw2, sh3), pygame.SRCALPHA)
            shs2.fill((255,255,255,70))
            surf.blit(shs2, (lx2+S(2), heye-lh2//2+S(1)))
        # Short nose bridge between lenses
        pygame.draw.line(surf, col, (hcx-S(6), heye), (hcx+S(6), heye), max(1,S(2)))

    elif item_id == 'hrtgls':
        # Cherry Charm necklace — Y2K kawaii
        chain_y = hneck - S(2)
        cr_col = (210, 35, 70)       # cherry red
        cr_lt  = (245, 100, 130)     # highlight
        stem_col = (55, 130, 55)     # stem green
        ltn2 = clamp_color(col[0]+50, col[1]+50, col[2]+50)
        # Chain links across neckline
        for cx3 in range(hcx-S(16), hcx+S(17), max(1,S(4))):
            pygame.draw.circle(surf, ltn2, (cx3, chain_y), Sz(2))
        # Y-shaped stems
        mid_x = hcx - S(2)
        pygame.draw.line(surf, stem_col, (mid_x, chain_y+S(2)), (hcx-S(8), chain_y+S(11)), max(1,Sz(2)))
        pygame.draw.line(surf, stem_col, (mid_x, chain_y+S(2)), (hcx+S(4), chain_y+S(11)), max(1,Sz(2)))
        pygame.draw.line(surf, stem_col, (mid_x, chain_y), (mid_x, chain_y+S(3)), max(1,Sz(2)))
        # Two cherries
        cr = max(3, Sz(5))
        pygame.draw.circle(surf, cr_col, (hcx-S(8), chain_y+S(11)), cr)
        pygame.draw.circle(surf, cr_col, (hcx+S(4), chain_y+S(11)), cr)
        # Highlights
        pygame.draw.circle(surf, cr_lt, (hcx-S(10), chain_y+S(9)), max(1,cr//2))
        pygame.draw.circle(surf, cr_lt, (hcx+S(2),  chain_y+S(9)), max(1,cr//2))

    elif item_id == 'scarf':
        sc1 = col
        sc2 = clamp_color(col[0]-30, col[1]-30, col[2]-30)
        lts = clamp_color(col[0]+40, col[1]+40, col[2]+40)
        bw2 = Sz(56); fw = Sz(48); fh = Sz(9)
        pygame.draw.rect(surf, sc2, (hcx-S(28), hneck-S(2), bw2, Sz(11)), border_radius=Sz(6))
        pygame.draw.rect(surf, sc1, (hcx-S(24), hneck,      fw,  fh),     border_radius=Sz(5))
        step = max(1, S(6))
        for i in range(0, fw, step):
            pygame.draw.line(surf, lts, (hcx-S(24)+i, hneck+S(1)), (hcx-S(24)+i, hneck+fh-S(1)), 1)
        # Knot ball on right side
        kw2 = Sz(12); kh2 = Sz(14)
        pygame.draw.ellipse(surf, sc1, (hcx+S(22), hneck-S(5), kw2, kh2))
        pygame.draw.ellipse(surf, sc2, (hcx+S(22), hneck-S(5), kw2, kh2), 1)
        tw = Sz(8); th2 = Sz(16)
        pygame.draw.rect(surf, sc1, (hcx+S(24), hneck+S(8), tw, th2), border_radius=Sz(3))
        fstep = max(1, S(3))
        for fi in range(0, tw, fstep):
            pygame.draw.line(surf, sc2, (hcx+S(24)+fi, hneck+S(8)+th2), (hcx+S(23)+fi, hneck+S(8)+th2+S(4)), max(1,S(2)))

    elif item_id == 'necktie':
        ltn = clamp_color(col[0]+50, col[1]+50, col[2]+50)
        chain_y = hneck - S(3)
        cr2 = Sz(2)
        cstep = max(1, S(4))
        for cx3 in range(hcx-S(18), hcx+S(19), cstep):
            pygame.draw.circle(surf, ltn, (cx3, chain_y), cr2)
        for cy3 in range(chain_y+S(4), chain_y+S(15), cstep):
            pygame.draw.circle(surf, ltn, (hcx, cy3), cr2)
        hs = max(2, int(round(3*sc)))
        _heart(surf, (*col, 240), hcx-S(6), chain_y+S(14), hs)
        _heart(surf, (*clamp_color(col[0]-40, col[1]-40, col[2]-40), 180),
               hcx-S(6), chain_y+S(14), hs)


# ── WARDROBE ──────────────────────────────────────────────────────────────────
class Wardrobe:
    COLS = 5   # 10 items → 2 rows of 5

    def __init__(self, w):
        self.w          = w
        self.frame      = 0
        self.sel        = 0
        self.msg        = ''
        self.msg_t      = 0
        self.settings   = False   # settings overlay open
        self.settings_sel = 0    # selected option in settings overlay (0-3)
        # Pre-build background shimmer pattern (done once, not every frame)
        self._bg = pygame.Surface((SW, SH), pygame.SRCALPHA)
        for ci in range(0, SW, 18):
            for cj in range(0, SH, 18):
                if (ci//18 + cj//18) % 2 == 0:
                    pygame.draw.rect(self._bg, (255,200,240,10), (ci, cj, 18, 18))

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if self.settings:
                if ev.key == pygame.K_ESCAPE:
                    self.settings = False; return None
                elif ev.key == pygame.K_UP:
                    self.settings_sel = (self.settings_sel - 1) % 4
                elif ev.key == pygame.K_DOWN:
                    self.settings_sel = (self.settings_sel + 1) % 4
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.settings_sel == 0:
                        self.w.points+=100; self.w.save()
                        self._flash("✦ +100 fish! motherload ✦"); Sounds.happy_chime()
                    elif self.settings_sel == 1:
                        self.settings = False
                        return 'change_city'
                    elif self.settings_sel == 2:
                        write_save({})   # wipe everything including city
                        self.settings = False
                        return 'restart'
                    self.settings = False
                return None
            n = len(ITEMS)
            total_slots = n + 1   # 0-9 items, 10 = settings gear
            if ev.key == pygame.K_ESCAPE:   return 'back'
            if ev.key == pygame.K_LEFT:
                if self.sel == 10:   self.sel = n - 1
                else:                self.sel = (self.sel - 1) % n
                Sounds.menu_beep()
            elif ev.key == pygame.K_RIGHT:
                if self.sel == n - 1:  self.sel = 10
                elif self.sel == 10:   self.sel = 0
                else:                  self.sel = (self.sel + 1) % n
                Sounds.menu_beep()
            elif ev.key == pygame.K_UP:
                if self.sel == 10:   self.sel = n - 1
                else:                self.sel = (self.sel - self.COLS) % n
                Sounds.menu_beep()
            elif ev.key == pygame.K_DOWN:
                if self.sel >= n - self.COLS:  self.sel = 10   # last row → settings
                elif self.sel == 10:           self.sel = 0
                else:                          self.sel = (self.sel + self.COLS) % n
                Sounds.menu_beep()
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.sel == 10:
                    self.settings = True; self.settings_sel = 0
                else:
                    self._action(); Sounds.confirm()
        return None

    def _action(self):
        it = ITEMS[self.sel]
        iid = it['id']
        # If already equipped → unequip
        if iid in self.w.equipped:
            self.w.equipped.remove(iid)
            self._flash(f"removed {it['name']}")
            self.w.save(); return
        # If unlocked → equip (one per type slot)
        if iid in self.w.unlocked:
            # Remove any existing item of same type
            same = [x['id'] for x in ITEMS
                    if x['type']==it['type'] and x['id'] in self.w.equipped]
            for s2 in same: self.w.equipped.remove(s2)
            self.w.equipped.append(iid)
            self._flash(f"equipped!")
            self.w.save(); return
        # Try to buy
        if self.w.points >= it['cost']:
            self.w.points -= it['cost']
            self.w.unlocked.append(iid)
            self.w.equipped.append(iid)
            self.w.save()
            self._flash(f"bought!")
            Sounds.happy_chime()
        else:
            need = it['cost'] - self.w.points
            self._flash(f"need {need} more pts")
            Sounds.sad_boop()

    def _flash(self, msg):
        self.msg = msg; self.msg_t = 2200

    def update(self, dt):
        self.frame += 1
        if self.msg_t > 0: self.msg_t -= dt

    def _draw_item_card(self, surf, it, ix, iy, cw, ch, state, focused=False):
        """state: 'locked'|'unlocked'|'equipped'|'selected'
        ch=110 layout (all relative to iy):
          name pill   iy+3  .. iy+17
          hat headroom iy+17 .. iy+28  (crown/halo sit here)
          sprite top  iy+28, visual bottom iy+72  (22 rows × 2px)
          stand       iy+74 .. iy+77
          badge       iy+80 .. iy+97
        """
        iid = it['id']
        col = it['col']

        # ── Card drop shadow ──
        shd_s = pygame.Surface((cw+6,ch+6),pygame.SRCALPHA)
        pygame.draw.rect(shd_s,(0,0,0,40),(0,0,cw+6,ch+6),border_radius=14)
        surf.blit(shd_s,(ix+2,iy+4))

        # ── Card background ──
        if state == 'equipped':
            card_col = clamp_color(col[0]//4+188, col[1]//4+188, col[2]//4+188)
            bdr_col  = col; bdr_w = 3
        elif state == 'selected':
            card_col = (232, 215, 255)
            p = int(180+55*math.sin(self.frame*0.15))
            bdr_col  = (p, 50, 230); bdr_w = 3
        elif state == 'unlocked':
            card_col = (228, 218, 252); bdr_col = (148,108,228); bdr_w = 2
        else:
            card_col = (210, 200, 232); bdr_col = (158,138,198); bdr_w = 1

        cs = pygame.Surface((cw, ch), pygame.SRCALPHA)
        pygame.draw.rect(cs, (*card_col, 252), (0,0,cw,ch), border_radius=12)
        surf.blit(cs, (ix, iy))
        pygame.draw.rect(surf, bdr_col, (ix,iy,cw,ch), bdr_w, border_radius=12)

        # ── Focus pulse ring for any focused (cursor-on) card ──
        if focused and state not in ('equipped','selected'):
            p = int(180+55*math.sin(self.frame*0.15))
            pygame.draw.rect(surf,(p,50,230),(ix-1,iy-1,cw+2,ch+2),2,border_radius=13)

        # ── Subtle inner shimmer for equipped/selected ──
        if state in ('equipped','selected'):
            glow_s = pygame.Surface((cw-4,ch-4),pygame.SRCALPHA)
            ga = int(30+20*math.sin(self.frame*0.15))
            pygame.draw.rect(glow_s,(*bdr_col,ga),(0,0,cw-4,ch-4),border_radius=10)
            surf.blit(glow_s,(ix+2,iy+2))

        # ── Mini Waddle (px=2) — sprite top at iy+28, accessories clipped to card ──
        # Layout: soy+spr_h+2=stand=iy+86, badge=iy+92, badge+17=iy+109 < ch=110 ✓
        spr_px = 2
        spr_w = 26*spr_px; spr_h = 28*spr_px   # 52 × 56
        sox = ix + cw//2 - spr_w//2
        soy = iy + 28
        mood = 'happy' if state in ('equipped','selected') else 'idle'
        blit_spr(surf, mood, spr_px, sox, soy)
        # Animated sparkle at wing tip for selected/equipped items
        # Right wing tip: cols 22-25 rows 10-13 → x≈sox+spr_w-3, y≈soy+10*spr_px+spr_px//2
        if state in ('equipped','selected'):
            wtx = sox + spr_w - 2
            wty = soy + 10*spr_px + spr_px//2
            wsz = max(1, int(0.8 + 0.8*abs(math.sin(self.frame*0.22))))
            wc = clamp_color(col[0]+50, col[1]+50, col[2]+50)
            _draw_cross_star(surf, wc, wtx, wty, wsz, int(160+95*abs(math.sin(self.frame*0.22))))
        if state != 'locked':
            # Clip accessories to card bounds so halo/crown stay inside
            old_clip = surf.get_clip()
            surf.set_clip((ix, iy, cw, ch))
            draw_accessory(surf, iid, col, sox, soy, spr_px)
            surf.set_clip(old_clip)
        else:
            lk = pygame.Surface((cw, ch), pygame.SRCALPHA)
            pygame.draw.rect(lk, (30,8,55,70), (0,0,cw,ch), border_radius=12)
            surf.blit(lk, (ix, iy))
            # Lock icon centred on sprite area
            lk_s = F11.render("lock", True, (200,175,240))
            surf.blit(lk_s,(ix+cw//2-lk_s.get_width()//2, iy+55))

        # ── Mannequin display stand base ──
        # Use 22*spr_px (visual content rows) not spr_h (28 rows incl. 6 empty) so
        # the stand sits right under the feet instead of 12px below them.
        stand_y = soy + 22*spr_px + 2   # = iy+74
        st_col = clamp_color(col[0]//2+90, col[1]//2+90, col[2]//2+90)
        st_dk  = clamp_color(st_col[0]-22, st_col[1]-22, st_col[2]-22)
        pygame.draw.rect(surf, st_col, (sox-2, stand_y,   spr_w+4, 4), border_radius=3)
        pygame.draw.rect(surf, st_dk,  (sox-2, stand_y,   spr_w+4, 4), 1, border_radius=3)
        pygame.draw.rect(surf, st_col, (ix+cw//2-10, stand_y+4, 20, 3), border_radius=2)

        # ── Status badge ── (iy+80)
        badge_y = stand_y + 6     # = iy+80, badge 17px tall → iy+97 < ch=110
        if state == 'equipped':
            bt = "ON \u2665"; bc2 = col; btc = (255,255,255)
        elif state == 'unlocked':
            bt = "equip"; bc2 = (108,65,195); btc = (255,255,255)
        else:
            bt = f"{it['cost']} fish"
            bc2 = (108,65,195) if state=='selected' else (140,122,182)
            btc = (255,255,255)
        bs = F11.render(bt, True, btc)
        bw2 = bs.get_width()+10; bx2 = ix+cw//2-bw2//2
        badge_s = pygame.Surface((bw2,17), pygame.SRCALPHA)
        pygame.draw.rect(badge_s, (*bc2, 228), (0,0,bw2,17), border_radius=5)
        surf.blit(badge_s, (bx2, badge_y))
        surf.blit(bs, (bx2+5, badge_y+2))

        # ── Item name — drawn LAST so it's always on top of any glow ──
        name_full = it['name']
        nc = (55,25,100) if state != 'locked' else (95,72,145)
        nm = F8.render(name_full, True, nc)
        while nm.get_width() > cw-8 and len(name_full) > 3:
            name_full = name_full[:-1]
            nm = F8.render(name_full+'…', True, nc)
        # Pill backing for legibility
        pill_w = nm.get_width()+10; pill_h = 14
        pill_s = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
        pygame.draw.rect(pill_s,(255,255,255,150),(0,0,pill_w,pill_h),border_radius=5)
        surf.blit(pill_s,(ix+cw//2-pill_w//2, iy+3))
        surf.blit(nm, (ix+cw//2-nm.get_width()//2, iy+5))

    def draw(self, surf):
        # ── Background ──
        for y in range(SH):
            t = y/SH
            r = clamp_color(int(252-t*22), int(228-t*32), int(252-t*18))
            pygame.draw.line(surf, r, (0,y), (SW,y))
        surf.blit(self._bg, (0,0))   # pre-built shimmer (no per-frame alloc)
        grid_bg(surf, (215, 75, 185), 18, 20)

        # Drifting sparkles
        for i in range(14):
            sx2 = int((i*163+self.frame//5)%SW)
            sy2 = int((i*97)%(SH-30))+15
            fv  = 0.35+0.45*math.sin(self.frame*0.05+i)
            _draw_cross_star(surf,clamp_color(int(fv*255),int(fv*90),int(fv*195)),
                             sx2,sy2,max(1,int(fv*2)),int(fv*160))

        # ── Header window — h=62: content=32px, fits F18+fish without overflow ──
        cy = draw_win(surf, 6, 6, SW-12, 62, "wardrobe.exe")
        blit_c(surf, F18, "★  BOUTIQUE  ★", (55,25,105), SW//2-45, cy+3, aa=True)
        # Fish count — icon + F14 number, right side
        _draw_hud_fish(surf, SW-76, cy+14)
        pts_s=F14.render(str(self.w.points),True,(55,22,100))
        surf.blit(pts_s,(SW-58, cy+14-pts_s.get_height()//2))
        # Gear icon — static decorative
        gear_s=F11.render("⚙",True,(100,60,180))
        surf.blit(gear_s,(SW-22, cy-1))

        # ── Item grid: 5 cols × 88 wide × 110 tall → 2 rows ──
        # Layout math: gy0=72, 2*(110+5)-5=225, grid bottom=297, +3+14btn=314 < 320 ✓
        cw=88; ch=110; gap=5
        total_w = self.COLS*(cw+gap)-gap
        gx0 = (SW-total_w)//2
        gy0 = 72

        for i, it in enumerate(ITEMS):
            row = i // self.COLS
            col2 = i %  self.COLS
            ix = gx0 + col2*(cw+gap)
            iy = gy0 + row*(ch+gap)
            iid = it['id']
            if iid in self.w.equipped:     state='equipped'
            elif iid in self.w.unlocked:   state='unlocked'
            elif i == self.sel:            state='selected'
            else:                          state='locked'
            self._draw_item_card(surf, it, ix, iy, cw, ch, state, focused=(i==self.sel))

        # ── Settings button (sel=10) — bottom strip ──
        # grid bottom = 72 + 2*(110+5)-5 = 297; btn at 300, h=16, bottom=316 ✓
        grid_bottom = gy0 + 2*(ch+gap) - gap
        btn_h = 16; btn_w = 160; btn_x = (SW-btn_w)//2
        btn_y = grid_bottom + 3
        s10 = (self.sel == 10)
        draw_glass(surf, btn_x, btn_y, btn_w, btn_h, r=8,
                   tint=(188,148,252) if s10 else (155,120,220),
                   a=88 if s10 else 55)
        if s10:
            gp3 = int(180+55*math.sin(self.frame*0.15))
            pygame.draw.rect(surf,(gp3,50,230),(btn_x,btn_y,btn_w,btn_h),2,border_radius=8)
        else:
            pygame.draw.rect(surf,(130,90,200),(btn_x,btn_y,btn_w,btn_h),1,border_radius=8)
        blit_c(surf,F8,"settings",
               (255,240,255) if s10 else (140,100,200),
               SW//2, btn_y+4, aa=True)

        # ── Flash message ──
        if self.msg_t > 0 and self.msg:
            ms = F18.render(self.msg, True, (55,25,105))
            surf.blit(ms, (SW//2-ms.get_width()//2, SH//2-12))

        # ── Settings overlay ──
        if self.settings:
            pw2=240; ph2=172; px3=(SW-pw2)//2; py3=(SH-ph2)//2
            cy3=draw_win(surf,px3,py3,pw2,ph2,"settings.exe")
            opts=[
                "motherload  +100 fish",
                "change city",
                "reset everything",
                "close",
            ]
            row_h=34
            for oi,otxt in enumerate(opts):
                row_y=cy3+4+oi*row_h
                if oi==self.settings_sel:
                    pygame.draw.rect(surf,WIN_BAR,(px3+8,row_y-3,pw2-16,26),border_radius=5)
                    blit_c(surf,F14,otxt,(255,255,255),SW//2,row_y)
                else:
                    blit_c(surf,F14,otxt,(90,35,145),SW//2,row_y)


# ── CHILL SCREEN ──────────────────────────────────────────────────────────────
class Chill:
    def __init__(self,w):
        self.w=w; self.frame=0
        self.wx=Weather()
        self.tlines=[TERM_LINES[0]]; self.ti=1; self.tt=0
        self.shooting_stars=[]

    def handle_event(self,ev):
        if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE: return 'back'

    def update(self,dt):
        self.frame+=1
        # Chill = relaxing. Slow energy + happiness restore. Very slight hunger.
        self.w.energy   =min(100,self.w.energy   +dt/1000*0.36)
        self.w.happiness=min(100,self.w.happiness+dt/1000*0.18)
        self.w.hunger   =min(100,self.w.hunger   +dt/1000*0.10)
        self.tt+=dt
        if self.tt>2400:
            self.tt=0
            self.tlines.append(TERM_LINES[self.ti%len(TERM_LINES)])
            self.ti+=1
            if len(self.tlines)>8: self.tlines.pop(0)
        # Spawn shooting stars randomly (~1 every 4-8 seconds on average)
        if random.random()<0.004:
            spd=random.uniform(8,14)
            if random.random()<0.5: spd=-spd
            vy=abs(spd)*random.uniform(0.18,0.40)
            self.shooting_stars.append({
                'x':float(random.randint(20,SW-20)),
                'y':float(random.randint(6,SH//3)),
                'vx':spd,'vy':vy,'life':float(random.randint(600,900))
            })
        new_ss=[]
        for ss in self.shooting_stars:
            ss['x']+=ss['vx']; ss['y']+=ss['vy']; ss['life']-=dt
            if ss['life']>0 and -20<=ss['x']<=SW+20:
                new_ss.append(ss)
        self.shooting_stars=new_ss

    def _sky(self,surf):
        if IMG_HOLO:
            # Holographic pastel grid photo as sky (matches reference image)
            surf.blit(IMG_HOLO, (0, 0))
            # Overall darkening overlay for mood + readability
            dark = pygame.Surface((SW, SH), pygame.SRCALPHA)
            dark.fill((12, 6, 32, 72))
            surf.blit(dark, (0, 0))
            # Stronger fade from midpoint down
            fade = pygame.Surface((SW, SH), pygame.SRCALPHA)
            for y in range(SH):
                if y > SH * 0.42:
                    a = int(160 * ((y - SH*0.42) / (SH*0.58)))
                    pygame.draw.line(fade, (12, 5, 30, a), (0, y), (SW, y))
            surf.blit(fade, (0, 0))
        else:
            for y in range(SH):
                t=y/SH
                r=int(48+t*40);  g=int(12+t*16);  b=int(78+t*50)
                pygame.draw.line(surf,clamp_color(r,g,b),(0,y),(SW,y))
        grid_bg(surf,(220,80,180),20,18)

    def _stars(self,surf):
        for i in range(30):
            sx=(i*149+12)%SW; sy=(i*103+8)%(SH*2//3)
            fv=0.42+0.44*math.sin(self.frame*0.046+i)
            a=min(255,max(0,int(fv*210)))
            if i%3==0:
                _draw_cross_star(surf,(200,175,255),sx,sy,max(1,int(1+fv)),a)
            else:
                cr=min(255,max(0,int(200+fv*55)))
                cg=min(255,max(0,int(110+fv*60)))
                cb=min(255,max(0,int(220+fv*35)))
                s2=pygame.Surface((4,4),pygame.SRCALPHA)
                pygame.draw.rect(s2,(cr,cg,cb,a),(1,0,2,4))
                pygame.draw.rect(s2,(cr,cg,cb,a),(0,1,4,2))
                surf.blit(s2,(sx-2,sy-2))

    def _shooting_stars(self,surf):
        for ss in self.shooting_stars:
            frac=max(0.0,ss['life']/900.0)
            for j in range(12):
                tj=j/12.0
                tx2=int(ss['x']-ss['vx']*tj*1.4)
                ty2=int(ss['y']-ss['vy']*tj*1.4)
                a=int(frac*(1.0-tj)*240)
                if a<8: continue
                sz=max(1,int((1.0-tj)*2.5))
                s2=pygame.Surface((sz*2+2,sz*2+2),pygame.SRCALPHA)
                pygame.draw.circle(s2,(255,min(255,int(160+tj*70)),min(255,int(200+tj*40)),a),(sz+1,sz+1),sz)
                surf.blit(s2,(tx2-sz,ty2-sz))

    def _bg_clouds(self,surf):
        # Triple-puff clouds drifting in the sky — same style as main screen
        # Positioned in the upper half to look atmospheric; avoid overlapping left panels
        for ccx_base,ccy,cw,ca,spd in [
            (320,  48,  96, 200, 0.14),
            (440,  72,  80, 185, 0.22),
            (260,  96,  68, 175, 0.10),
            (400, 130,  88, 195, 0.18),
        ]:
            ccx=int((ccx_base+self.frame*spd)%(SW+cw+60))-30
            # Three overlapping puffs — identical to the main screen cloud technique
            _draw_cloud_puff(surf, ccx,            ccy,    cw,        (255,255,255), ca)
            _draw_cloud_puff(surf, ccx-cw//3,      ccy+8,  cw*2//3,   (255,255,255), ca-22)
            _draw_cloud_puff(surf, ccx+cw//3,      ccy+8,  cw*2//3,   (255,255,255), ca-22)
        # Extra small clouds near Waddle (cx≈362, y≈200) — soft and dreamy
        bob2=math.sin(self.frame*0.018+1.2)*3
        _draw_cloud_puff(surf, 430, int(170+bob2),  52, (255,250,255), 155)
        _draw_cloud_puff(surf, 404, int(178+bob2),  34, (255,250,255), 130)
        _draw_cloud_puff(surf, 456, int(178+bob2),  34, (255,250,255), 130)
        bob3=math.sin(self.frame*0.022+2.8)*2
        _draw_cloud_puff(surf, 310, int(158+bob3),  44, (255,250,255), 140)
        _draw_cloud_puff(surf, 286, int(165+bob3),  28, (255,250,255), 115)
        _draw_cloud_puff(surf, 334, int(165+bob3),  28, (255,250,255), 115)

    def _waddle_cloud(self,surf):
        bob=math.sin(self.frame*0.024)*2.0
        spr_px=5; spr_w=26*spr_px; spr_h=28*spr_px   # 130 × 140
        cx=362
        sox=cx-spr_w//2                               # 297
        soy=int(198-spr_h+36+bob)                     # ≈ 94+bob  (10px lower)
        # Cloud platform — identical 3-puff style as pet screen
        ccx=sox+spr_w//2+15                           # ≈ 377
        ccy=soy+spr_h-12                              # ≈ 212+bob
        _draw_cloud_puff(surf,ccx,          ccy,   130,(255,252,255),224)
        _draw_cloud_puff(surf,ccx-spr_w//4, ccy+8,  82,(255,252,255),200)
        _draw_cloud_puff(surf,ccx+spr_w//4, ccy+8,  82,(255,252,255),200)
        shd=pygame.Surface((spr_w+20,7),pygame.SRCALPHA)
        pygame.draw.ellipse(shd,(180,140,210,48),(0,0,spr_w+20,7))
        surf.blit(shd,(sox-10,ccy+26))
        # Sleeping Waddle
        blit_spr(surf,'sleepy',spr_px,sox,soy)
        # ZZZ
        za=0.40+0.40*math.sin(self.frame*0.04)
        zc=clamp_color(int(za*168),int(za*128),int(za*252))
        surf.blit(F18.render("z",False,zc),(cx+56,soy-20))
        surf.blit(F14.render("z",False,zc),(cx+70,soy-38))

    def _weather(self,surf):
        """Weather card using draw_win style — top-left of chill screen."""
        wx2=8; wy=10; ww=240; wh=162
        cy=draw_win(surf,wx2,wy,ww,wh,"weather.exe")   # cy = wy+27
        # Clip all content to the window interior so nothing overflows
        old_clip=surf.get_clip()
        surf.set_clip((wx2+2, cy, ww-4, wh-(cy-wy)))

        if not self.wx.ready:
            blit_l(surf,F14,"fetching...",(160,80,180),wx2+14,cy+28)
            surf.set_clip(old_clip); return
        if self.wx.err:
            blit_l(surf,F14,"offline",(180,60,60),wx2+14,cy+28)
            surf.set_clip(old_clip); return

        w2=self.wx
        try:
            raw_code=int(getattr(w2,'_code',0))
        except Exception:
            raw_code=0

        # Icon — left side
        draw_wx_icon(surf,raw_code,wx2+34,cy+34,size=44)

        # Right side — constrained to card width
        tx=wx2+82; max_tw=(wx2+ww)-tx-8
        # Temperature
        temp_s=F32.render(f"{w2.temp}°",True,(70,20,100))
        surf.blit(temp_s,(tx, cy+2))

        # Condition — F11 (fits more comfortably), auto-truncate
        cond_text=w2.cond
        cs2=F11.render(cond_text,True,(95,38,135))
        while cs2.get_width()>max_tw and len(cond_text)>4:
            cond_text=cond_text[:-1]; cs2=F11.render(cond_text+"…",True,(95,38,135))
        surf.blit(cs2,(tx, cy+38))

        # Feels + humidity + city — F11 for legibility
        feels_s=f"feels {w2.feels}°"
        while F11.size(feels_s)[0]>max_tw: feels_s=feels_s[:-1]
        blit_l(surf,F11,feels_s,(108,52,148),tx,cy+54,aa=True)

        hum_s=f"{w2.hum}% humidity"
        while F11.size(hum_s)[0]>max_tw: hum_s=hum_s[:-1]
        blit_l(surf,F11,hum_s,(120,68,158),tx,cy+69,aa=True)

        city_s=CITY
        while F8.size(city_s)[0]>max_tw: city_s=city_s[:-1]
        blit_l(surf,F8,city_s,(148,90,185),tx,cy+85,aa=True)

        # Divider
        pygame.draw.rect(surf,(220,140,210),(wx2+10,cy+97,ww-20,1))

        # Hourly row — 4 slots at 56px spacing, fits cleanly
        if w2.hourly:
            hx=wx2+10
            for h in w2.hourly[:4]:
                time_s=h['h']; temp_hs=f"{h['t']}°"
                blit_l(surf,F8, time_s,(105,55,148),hx,cy+101,aa=True)
                blit_l(surf,F11,temp_hs,(68,22,108),hx,cy+113,aa=True)
                hx+=56

        surf.set_clip(old_clip)

    def _forecast(self,surf):
        """5-day forecast below the weather card on the left column."""
        if not self.wx.ready or self.wx.err or not self.wx.daily: return
        cards=self.wx.daily[:5]
        card_w=46; card_h=68; gap=3
        # Left-aligned block below weather card (wy=10, wh=162 → bottom=172, gap 4 → dy=176)
        dx=8; dy=176
        for i,d in enumerate(cards):
            cx2=dx+i*(card_w+gap)
            try: dcode=int(d.get('_code',0))
            except: dcode=0
            fc=pygame.Surface((card_w,card_h),pygame.SRCALPHA)
            pygame.draw.rect(fc,(255,245,255,238),(0,0,card_w,card_h),border_radius=9)
            surf.blit(fc,(cx2,dy))
            pygame.draw.rect(surf,(210,80,185),(cx2,dy,card_w,card_h),3,border_radius=9)
            pygame.draw.rect(surf,(255,80,180),(cx2+3,dy+3,card_w-6,2),border_radius=7)
            blit_c(surf,F11,d['d'],  (80,30,120),   cx2+card_w//2, dy+4,  aa=True)
            draw_wx_icon(surf,dcode,  cx2+card_w//2, dy+27,         size=18)
            blit_c(surf,F8, d['hi'], (60,20,100),   cx2+card_w//2-9, dy+47, aa=True)
            blit_c(surf,F8, d['lo'], (100,80,160),  cx2+card_w//2+9, dy+47, aa=True)

    def _terminal(self,surf):
        # Left column, below 5-day forecast (forecast dy=176, card_h=68 → bottom=244, gap 4 → ty=248)
        tx=8; ty=248; tw2=240; th=SH-ty-4
        cy=draw_win(surf,tx,ty,tw2,th,"affirmations.exe")
        max_tw=tw2-18
        # Always show exactly 3 affirmation lines
        nlines=3
        shown=self.tlines[-nlines:]
        for i,line in enumerate(shown):
            is_last=(i==len(shown)-1)
            tl=line
            while F_SM.size(tl)[0]>max_tw and len(tl)>4:
                tl=tl[:-1]
            if F_SM.size(tl)[0]>max_tw: tl=tl[:-1]+'…'
            col2=(75,40,125) if is_last else (105,65,148)
            blit_l(surf,F_SM,tl,col2,tx+8,cy+i*12,aa=True)
        if shown and self.frame%24<12:
            tw3=F_SM.size(shown[-1])[0]
            pygame.draw.rect(surf,(108,58,162),(tx+8+min(tw3,max_tw),cy+len(shown)*12-11,6,9))

    def _desktop_icons(self,surf):
        """Y2K fake desktop icon row — bottom-right, below sleeping Waddle."""
        icons=[
            ("music.exe",  "♫", (210,140,255)),
            ("camera.exe", "◎", (255,150,200)),
            ("chat.exe",   "◉", (130,195,255)),
            ("shop.exe",   "✦", (255,210,90)),
        ]
        iw=46; ih=46; gap=6
        total_w=len(icons)*iw+(len(icons)-1)*gap
        sx=254+(218-total_w)//2   # centre in right column
        sy=244
        for i,(name,sym,col) in enumerate(icons):
            ix=sx+i*(iw+gap)
            # Glass icon card
            draw_glass(surf,ix,sy,iw,ih,r=8,tint=col,a=50)
            pygame.draw.rect(surf,col,(ix,sy,iw,ih),1,border_radius=8)
            # Symbol centred in card
            sym_s=F14.render(sym,True,col)
            surf.blit(sym_s,(ix+iw//2-sym_s.get_width()//2, sy+ih//2-sym_s.get_height()//2))
            # App name
            nm_s=F8.render(name,True,(190,155,235))
            surf.blit(nm_s,(ix+iw//2-nm_s.get_width()//2, sy+ih+3))
            # "coming soon" below name
            cs_s=F8.render("coming soon",True,(170,130,215))
            surf.blit(cs_s,(ix+iw//2-cs_s.get_width()//2, sy+ih+13))

    def draw(self,surf):
        self._sky(surf)
        self._stars(surf)
        self._shooting_stars(surf)
        self._bg_clouds(surf)
        self._waddle_cloud(surf)  # right side
        self._weather(surf)       # top-left
        self._forecast(surf)      # middle-left (below weather)
        self._terminal(surf)      # bottom-left (below forecast)


def _heart(surf, col, x, y, s):
    """Draw a small pixel heart. col can include alpha for SRCALPHA surfaces."""
    s=max(1,int(s))
    hs=pygame.Surface((s*4+2,s*4+2),pygame.SRCALPHA)
    # Heart shape: two top bumps + triangle body
    for r,c,w in [(0,1,1),(0,2,1),(1,0,4),(2,0,4),(3,1,2)]:
        pygame.draw.rect(hs,col,(c*s,r*s,w*s,s))
    surf.blit(hs,(x,y))


def _draw_fluffy_cloud(surf, col, cx, cy, scale=1.0):
    """Draw a fluffy multi-circle cloud with alpha."""
    cx,cy=int(cx),int(cy)
    if len(col)==4:
        r,g,b,a=col
    else:
        r,g,b=col; a=255
    for ox2,oy2,cr2 in [(0,0,1.0),(-0.55,0.15,0.72),(0.55,0.15,0.72),
                         (-0.28,0.28,0.58),(0.28,0.28,0.58)]:
        rc=int(cr2*32*scale)
        if rc<1: continue
        cs=pygame.Surface((rc*2+2,rc*2+2),pygame.SRCALPHA)
        pygame.draw.circle(cs,(r,g,b,a),(rc+1,rc+1),rc)
        surf.blit(cs,(int(cx+ox2*32*scale)-rc,int(cy+oy2*24*scale)-rc))


# ── PET SCREEN ────────────────────────────────────────────────────────────────
class PetScreen:
    MENU=('FEED','REST','PLAY','CODE','CHILL','WARDROBE')

    def __init__(self,w):
        self.w=w; self.sel=0; self.frame=0
        self.fb=''; self.fb_t=0
        self.speech=w.speech(); self.sp_t=0
        self.sparks=[]; self.tears=[]; self.squash=1.0

    def handle_event(self,ev):
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_LEFT:
                self.sel=(self.sel-1)%len(self.MENU); return 'LEFT'
            elif ev.key==pygame.K_RIGHT:
                self.sel=(self.sel+1)%len(self.MENU); return 'RIGHT'
            elif ev.key in(pygame.K_RETURN,pygame.K_SPACE): return self.MENU[self.sel]
        return None

    def update(self,dt):
        self.frame+=1; self.w.tick(dt)
        if self.fb_t>0: self.fb_t-=dt
        self.sp_t+=dt
        mood=self.w.mood
        _sp_thresh=18000 if mood=='idle' else 7000 if mood in ('excited','happy') else 11000
        if self.sp_t>_sp_thresh: self.sp_t=0; self.speech=self.w.speech()

        ph=self.frame*(0.18 if mood in ('excited','happy') else 0.07)
        sv=math.sin(ph)
        if   mood=='excited': self.squash=1.0+sv*0.028
        elif mood=='happy':   self.squash=1.0+sv*0.030
        elif mood=='sad':     self.squash=1.0+sv*0.008
        else:                 self.squash=1.0+sv*0.016

        if mood=='happy' and self.frame%10==0:
            ox,oy=self._spr_pos()
            cx,cy=ox+26*PX//2,oy+14*PX
            cols=[(255,178,218),(198,158,255),(210,185,255),(255,175,215)]
            n = 2 if mood=='excited' else 1
            for _ in range(n):
                self.sparks.append({'x':cx+random.randint(-80,80),
                                     'y':cy+random.randint(-55,30),
                                     'life':1.0,'sz':random.uniform(2,4),
                                     'col':random.choice(cols)})
        self.sparks=[p for p in self.sparks if p['life']>0]
        for p in self.sparks: p['life']-=0.036; p['y']-=0.55

        ox,oy=self._spr_pos()
        if mood=='sad' and self.frame%52==0:
            self.tears.append({'x':ox+7*PX, 'y':oy+8*PX,'life':1.0,'vy':0.52,'vx':-0.10,'w':4.0,'h':6.0})
            self.tears.append({'x':ox+17*PX,'y':oy+8*PX,'life':1.0,'vy':0.52,'vx':0.12, 'w':4.0,'h':6.0})
        self.tears=[t for t in self.tears if t['life']>0]
        for t in self.tears:
            t['y']+=t['vy']; t['vy']+=0.09; t['x']+=t['vx']
            t['h']=min(t['h']+0.06,11); t['life']-=0.010

    def _bob(self):
        mood=self.w.mood
        if mood=='happy':   return math.sin(self.frame*0.18)*4.5
        if mood=='excited': return math.sin(self.frame*0.11)*1.5
        if mood=='sad':     return math.sin(self.frame*0.04)*1.2
        if mood=='sleepy':  return math.sin(self.frame*0.03)*1.5
        if mood=='hungry':  return math.sin(self.frame*0.22)*2.5
        return math.sin(self.frame*0.07)*3.0

    def _spr_pos(self):
        """Waddle centred slightly right of screen midpoint to balance stats on left."""
        sw2=26*PX
        cx=SW//2+14          # 14px right of true centre — gives stats 160px left space
        ox=cx-sw2//2
        # Vertical: sit on cloud — pushed down so feet land on cloud platform
        oy=int((10+268-28*PX)//2) + 26
        return ox, oy+int(self._bob())

    def do_action(self,a):
        if a=='FEED':
            self.w.feed()
            msgs=['nom nom! ♥','so yummy!!','fish time ♥','*munch munch*']
            self.fb=random.choice(msgs); self.fb_t=2000
        elif a=='REST':
            self.w.energy=min(100,self.w.energy+25)
            self.w.happiness=min(100,self.w.happiness+5)
            msgs=['nap time...','resting... zzz','*yawn* ty ♥','energy up!']
            self.fb=random.choice(msgs); self.fb_t=2000
            Sounds.confirm()

    def draw(self,surf):
        mood=self.w.mood

        # ── Clean Y2K pink gradient — mood-tinted, no busy photo ──
        bg_base={'happy':(255,215,235),'excited':(255,205,248),
                 'sad':(215,220,255),'sleepy':(228,215,255),
                 'hungry':(255,218,210),'idle':(255,215,235)}
        bg=bg_base.get(mood,(255,215,235))
        for y in range(SH):
            t=y/SH
            r=int(bg[0]-t*18); g=int(bg[1]-t*28); b=int(bg[2]-t*15)
            pygame.draw.line(surf,clamp_color(r,g,b),(0,y),(SW,y))
        grid_bg(surf,(230,80,170),22,28)

        # ── Animated drifting background hearts ──
        for i in range(16):
            # Each heart has a fixed lane but drifts upward based on frame
            hx=int((i*67+29)%SW)
            raw_y=(i*53+self.frame*(0.35+i*0.018))%(SH+30)
            hy=int(SH+10-raw_y)
            alpha=int(25+15*math.sin(self.frame*0.05+i))
            hs=max(3,4-(i%3))
            hs_surf=pygame.Surface((hs*4+4,hs*4+4),pygame.SRCALPHA)
            _heart(hs_surf,(255,180,210,alpha),0,0,hs)
            surf.blit(hs_surf,(hx,hy))

        # ── Corner hearts (static decoration) ──
        for hx,hy,hs in [(6,6,6),(SW-22,6,5),(6,SH-22,4),(SW-20,SH-24,5)]:
            _heart(surf,(255,190,220,70),hx,hy,hs)

        # ── Background drifting clouds — upper sky ──────────────────────────────
        _BG_CLOUDS=[
            (20,  30,  104, 100, 0.08, (255,252,255)),
            (210, 18,   78,  80, 0.13, (255,248,255)),
            (390, 52,   88,  88, 0.10, (255,250,252)),
            (100, 78,   64,  70, 0.17, (255,252,255)),
            (310, 68,   96,  78, 0.09, (252,248,255)),
            (460, 24,   72,  72, 0.15, (255,250,255)),
        ]
        for bx,by,cw2,ca,spd,ctint in _BG_CLOUDS:
            cx2=int((bx+self.frame*spd)%(SW+cw2+60))-30
            _draw_cloud_puff(surf,cx2,by,cw2,ctint,ca)

        # ── Dreamy bottom clouds (triple-puff clusters, like chill screen) ───────
        for _bcx_base,_bcy,_bcw,_bca,_bspd in [
            ( 40, 262, 110, 165, 0.06),
            (200, 252, 130, 180, 0.04),
            (390, 268, 100, 155, 0.07),
            (560, 256, 118, 170, 0.05),
        ]:
            _bcx=int((_bcx_base+self.frame*_bspd)%(SW+180))-60
            _draw_cloud_puff(surf,_bcx,          _bcy,   _bcw,       (255,252,255),_bca)
            _draw_cloud_puff(surf,_bcx-_bcw//3,  _bcy+10,_bcw*2//3, (255,250,255),_bca-25)
            _draw_cloud_puff(surf,_bcx+_bcw//3,  _bcy+10,_bcw*2//3, (255,250,255),_bca-25)

        # ── Sparkle particles ──
        for p in self.sparks:
            sz=max(2,int(p['sz']*2.8))
            a=max(0,min(255,int(p['life']*255)))
            _draw_cross_star(surf,p['col'],int(p['x']),int(p['y']),sz,a)

        # ── Tears ──
        for t in self.tears:
            pygame.draw.ellipse(surf,(138,192,255),
                (int(t['x']),int(t['y']),max(1,int(t['w'])),max(1,int(t['h']))))

        # ── Low energy screen vignette ──
        if self.w.energy < 20:
            pulse=0.4+0.4*math.sin(self.frame*0.12)
            a=int(pulse*50)
            vg=pygame.Surface((SW,SH),pygame.SRCALPHA)
            for band in range(30,0,-3):
                ba=max(0,int(a*(1-band/30)))
                pygame.draw.rect(vg,(120,80,200,ba),(SW//2-band*8,SH//2-band*5,band*16,band*10),3)
            surf.blit(vg,(0,0))

        wing_up=(mood in ('happy','excited')) and math.sin(self.frame*0.18)>0
        ox,oy=self._spr_pos()

        # ── Kawaii cloud platform behind the pet ──
        spr_w=26*PX; spr_h=28*PX
        ccx=ox+spr_w//2+12; ccy=oy+spr_h-28
        # Three overlapping puffs → proper fluffy cloud, no egg shapes
        _draw_cloud_puff(surf, ccx,            ccy,   140, (255,252,255), 224)
        _draw_cloud_puff(surf, ccx-spr_w//4,   ccy+8,  90, (255,252,255), 200)
        _draw_cloud_puff(surf, ccx+spr_w//4,   ccy+8,  90, (255,252,255), 200)
        # Soft shadow under cloud
        shd=pygame.Surface((spr_w+20,7),pygame.SRCALPHA)
        pygame.draw.ellipse(shd,(180,140,210,48),(0,0,spr_w+20,7))
        surf.blit(shd,(ccx-spr_w//2-10, ccy+26))

        blit_spr(surf,mood,PX,ox,oy,wing_up,sy=self.squash)

        # ── Equipped accessories ──
        for eid in self.w.equipped:
            it = next((x for x in ITEMS if x['id']==eid), None)
            if it: draw_accessory(surf, eid, it['col'], ox, oy, PX)

        # ── Sleepy zzz ──
        if mood=='sleepy':
            za=0.38+0.38*math.sin(self.frame*0.04)
            zc=clamp_color(int(za*165),int(za*125),int(za*252))
            surf.blit(F14.render("z",False,zc),(ox+26*PX,oy+4))
            surf.blit(F11.render("z",False,zc),(ox+26*PX+14,oy-10))

        # ── Speech bubble — drawn after accessories so hats never cover it ──
        self._speech(surf,ox,oy)

        self._stats(surf)
        self._points(surf)
        self._menu(surf)

        if self.fb_t>0 and self.fb:
            ox2,oy2=self._spr_pos()
            fs=F18.render(self.fb,False,PUR)
            surf.blit(fs,(SW//2-fs.get_width()//2,max(8,oy2-52)))

    def _speech(self,surf,ox,oy):
        """Mood speech bubble — drawn after accessories so hats never block it.
        Floats above the sprite head; full screen width so text is never cut off."""
        mood=self.w.mood
        bub_cols={
            'happy'  :(255,215,240), 'excited':(255,200,245),
            'sad'    :(215,225,255), 'sleepy' :(230,220,255),
            'hungry' :(255,215,210), 'idle'   :(255,215,240),
        }
        bdr_cols={
            'happy'  :(255,175,215), 'excited':(255,140,230),
            'sad'    :(175,195,255), 'sleepy' :(200,175,255),
            'hungry' :(255,165,155), 'idle'   :(255,192,225),
        }
        bc=bub_cols.get(mood,(255,215,240))
        bdc=bdr_cols.get(mood,(255,192,225))

        # Right-side bubble: starts right of sprite face centre
        spr_cx=ox+13*PX
        bx_start=spr_cx+10
        text=self.speech
        fs=F11.render(text,False,TXT_DK)
        max_tw=SW-bx_start-8-32          # text area available to the right
        while fs.get_width()>max_tw and len(text)>4:
            text=text[:-1]; fs=F11.render(text+'…',False,TXT_DK)
        tw=fs.get_width()+32; th=30

        bx=min(bx_start, SW-tw-8)        # clamp if bubble too wide
        by=max(8, oy-th-18)

        # Soft shadow
        sh=pygame.Surface((tw+2,th+2),pygame.SRCALPHA)
        pygame.draw.rect(sh,(0,0,0,14),(0,0,tw+2,th+2),border_radius=11)
        surf.blit(sh,(bx+2,by+3))

        # Bubble fill — a=115 keeps it readable when crown tips peek behind it
        draw_glass(surf,bx,by,tw,th,r=11,tint=bc,a=115)
        pygame.draw.rect(surf,bdc,(bx,by,tw,th),1,border_radius=11)

        # Text
        surf.blit(fs,(bx+16,by+th//2-fs.get_height()//2))

        # Left-pointing tail toward sprite face
        ty_mid=by+th//2
        pygame.draw.polygon(surf,bc, [(bx,ty_mid-7),(bx,ty_mid+7),(bx-12,ty_mid)])
        pygame.draw.polygon(surf,bdc,[(bx,ty_mid-7),(bx,ty_mid+7),(bx-12,ty_mid)],1)

        # Star decorations
        if mood in ('happy','excited'):
            star_c=(255,180,220)
            _draw_cross_star(surf,star_c,bx+8,by+6,1,180)
            _draw_cross_star(surf,star_c,bx+tw-9,by+7,1,150)

    def _stats(self,surf):
        """Stat bars — 3 bars evenly spaced in left column."""
        sx=8; sy=58; bw=144; bh=20; gap=30
        stats=[
            ('HUNGER',   self.w.hunger,    (255,108,108), self.w.hunger>70),
            ('HAPPINESS',self.w.happiness, (255,158,64),  self.w.happiness<25),
            ('ENERGY',   self.w.energy,    (82,210,148),  self.w.energy<20),
        ]
        for i,(label,val,col,warn) in enumerate(stats):
            y=sy+i*(bh+gap)
            dark=clamp_color(col[0]-40,col[1]-40,col[2]-40)
            lite=clamp_color(col[0]+50,col[1]+50,col[2]+50)

            # Warning pulse — glow behind bar when critical
            if warn:
                pulse=0.45+0.45*math.sin(self.frame*0.16)
                wa=int(pulse*65)
                wg=pygame.Surface((bw+16,bh+16),pygame.SRCALPHA)
                pygame.draw.rect(wg,(*col,wa),(0,0,bw+16,bh+16),border_radius=10)
                surf.blit(wg,(sx-8,y-8))

            # Label — F8 size, dark purple, AA
            blit_l(surf,F8,label,(62,28,105),sx,y-15,aa=True)

            # Outer glass container
            draw_glass(surf,sx-2,y-2,bw+4,bh+4,r=7,tint=col,a=32)

            # Track
            pygame.draw.rect(surf,(228,212,238),(sx,y,bw,bh),border_radius=5)

            # Fill
            fw=max(0,int((val/100)*bw))
            if fw>1:
                pygame.draw.rect(surf,col,(sx,y,fw,bh),border_radius=5)
                top=pygame.Surface((fw,bh//2),pygame.SRCALPHA)
                top.fill((*lite,50)); surf.blit(top,(sx,y))
                bot=pygame.Surface((fw,4),pygame.SRCALPHA)
                bot.fill((*dark,35)); surf.blit(bot,(sx,y+bh-4))

            # Shine
            shine=pygame.Surface((bw,bh//3),pygame.SRCALPHA)
            pygame.draw.rect(shine,(255,255,255,42),(0,0,bw,bh//3),border_radius=4)
            surf.blit(shine,(sx,y))

            # Border
            pygame.draw.rect(surf,lite,(sx,y,bw,bh),1,border_radius=5)

    def _points(self,surf):
        # Fish icon + number — bare, no box, top-right corner
        num_s=F18.render(f"{self.w.points:04d}",True,(55,22,100))
        py=10; rx=SW-num_s.get_width()-32
        _draw_hud_fish(surf,rx+6,py+num_s.get_height()//2)
        surf.blit(num_s,(rx+18,py))

    def _menu(self,surf):
        # Single row of 6 buttons with group dividers
        n=len(self.MENU); gap=5; bh=46
        total_usable=SW-14
        iw=(total_usable - (n-1)*gap)//n
        total=n*(iw+gap)-gap
        sx=(SW-total)//2; sy=SH-bh-5
        for i,item in enumerate(self.MENU):
            rx=sx+i*(iw+gap); is_sel=(i==self.sel)
            tint=(188,148,252) if is_sel else (240,218,255)
            draw_glass(surf,rx,sy,iw,bh,r=10,tint=tint,a=72)
            bdr=(88,30,160) if is_sel else (140,90,200)
            pygame.draw.rect(surf,bdr,(rx,sy,iw,bh),3 if is_sel else 2,border_radius=10)
            # Selected pulse glow
            if is_sel:
                gv=int(30+18*math.sin(self.frame*0.14))
                gs=pygame.Surface((iw-4,bh-4),pygame.SRCALPHA)
                pygame.draw.rect(gs,(140,80,230,gv),(0,0,iw-4,bh-4),border_radius=8)
                surf.blit(gs,(rx+2,sy+2))
            lbl=F11.render(item,True,(255,255,255) if is_sel else (62,28,105))
            surf.blit(lbl,(rx+iw//2-lbl.get_width()//2,sy+bh//2-lbl.get_height()//2))


# ── BOOT SCREEN ───────────────────────────────────────────────────────────────
BOOT_MSGS = [
    "initializing waddle.exe...",
    "loading fish.dat...  OK",
    "calibrating happiness sensors...",
    "mounting /dev/penguin...",
    "syncing code buffer...   OK",
    "patching cute module v3.2...",
    "connecting to moon...  OK",
    "loading pixel font...  OK",
    "all systems normal  ♥",
    "welcome back  ✦",
]

# ── LOCATION SETUP ────────────────────────────────────────────────────────────
class LocationSetup:
    """Shown on first launch when no location is saved.
    User types a city name → geocoded via Open-Meteo → saved to waddle_save.json.
    """
    def __init__(self):
        self.text     = ''
        self.state    = 'input'   # 'input' | 'searching' | 'confirm' | 'error'
        self.result   = None      # {'name', 'lat', 'lon'}
        self.err_msg  = ''
        self.frame    = 0
        self._done    = False
        self._res_buf = None
        self._err_buf = None

    def handle_event(self, ev):
        if ev.type != pygame.KEYDOWN: return None
        if self.state == 'input':
            if ev.key == pygame.K_RETURN and self.text.strip():
                self.state = 'searching'
                self._done = False; self._res_buf = None; self._err_buf = None
                threading.Thread(target=self._geocode, daemon=True).start()
            elif ev.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif ev.unicode and len(self.text) < 36:
                self.text += ev.unicode
        elif self.state == 'confirm':
            if ev.key == pygame.K_RETURN:   return 'done'
            if ev.key == pygame.K_ESCAPE:
                self.state='input'; self.text=''; self.result=None
        elif self.state == 'error':
            self.state='input'
        return None

    def _geocode(self):
        try:
            enc = urllib.parse.quote(self.text.strip())
            url = (f"https://geocoding-api.open-meteo.com/v1/search"
                   f"?name={enc}&count=1&language=en&format=json")
            req = urllib.request.Request(url, headers={"User-Agent":"WaddlePet/5"})
            with urllib.request.urlopen(req, timeout=10) as r:
                import json as _j; d = _j.loads(r.read())
            if d.get('results'):
                res = d['results'][0]
                admin1 = res.get('admin1','')
                country = res.get('country_code','').upper()
                display = f"{res['name']}, {admin1}" if admin1 else f"{res['name']}, {country}"
                self._res_buf = {'name':display,'lat':res['latitude'],'lon':res['longitude']}
            else:
                self._err_buf = "city not found — try again"
        except Exception:
            self._err_buf = "network error — try again"
        self._done = True

    def update(self, dt):
        self.frame += 1
        if self.state == 'searching' and self._done:
            self._done = False
            if self._res_buf:
                self.result = self._res_buf; self._res_buf = None
                self.state = 'confirm'
            else:
                self.err_msg = self._err_buf or "error"; self._err_buf = None
                self.state = 'error'

    def draw(self, surf):
        surf.fill((255, 228, 245))
        # Decorative drifting dots
        for i in range(5):
            xd = (self.frame*0.7 + i*97)%SW
            pygame.draw.circle(surf,(255,190,230),
                               (int(xd),int(40+math.sin(self.frame*0.04+i)*18)),3)
        # Title
        blit_c(surf, F24, "waddle ♡",    (210, 80, 185), SW//2, 28, aa=True)
        blit_c(surf, F14, "where do you live?", (155,62,168), SW//2, 62, aa=True)
        blit_c(surf, F8, "so we can show you live weather on the chill screen ♡", (180,110,200), SW//2, 82, aa=True)
        # Input box
        bx=SW//2-148; bw=296; by3=100; bh=34
        pygame.draw.rect(surf,(255,255,255),(bx,by3,bw,bh),border_radius=9)
        pygame.draw.rect(surf,(215,110,210),(bx,by3,bw,bh),2,border_radius=9)
        cur_char='|' if self.frame%24<12 and self.state=='input' else ''
        ts=F14.render((self.text or '')+cur_char, True, (72,28,115))
        surf.blit(ts,(bx+10,by3+8))
        # Status line
        if self.state=='input':
            blit_c(surf,F8,"type your city and press ENTER",(165,85,185),SW//2,146,aa=True)
        elif self.state=='searching':
            dots='.'*(1+(self.frame//8)%3)
            blit_c(surf,F14,f"searching{dots}",(160,80,180),SW//2,152,aa=True)
        elif self.state=='confirm' and self.result:
            name=self.result['name']
            if F14.size(name)[0]>SW-40:
                name=name[:26]+'…'
            blit_c(surf,F14,name,(72,28,115),SW//2,152,aa=True)
            blit_c(surf,F11,"ENTER to confirm  ·  ESC to retry",(145,72,175),SW//2,176,aa=True)
        elif self.state=='error':
            blit_c(surf,F14,self.err_msg,(200,50,80),SW//2,152,aa=True)
            blit_c(surf,F8,"press any key to try again",(165,85,185),SW//2,176,aa=True)
        # Hearts
        for hx2,hy2 in [(52,268),(428,268),(44,198),(436,198)]:
            _draw_pixel_heart(surf,(255,150,200),hx2,hy2,px=3,alpha=200)
        blit_c(surf,F8,"you can change this in waddle.py anytime",(190,130,200),SW//2,306,aa=True)


class BootScreen:
    DURATION = 3800   # ms total boot time

    def __init__(self):
        self.frame   = 0
        self.elapsed = 0
        self.lines   = []
        self.li      = 0          # next line to show
        self.lt      = 0          # timer for next line
        self.done    = False
        self._blip   = False
        Sounds.boot_blip()        # pre-cache

    def update(self, dt):
        self.frame   += 1
        self.elapsed += dt
        self.lt      += dt
        interval = self.DURATION // (len(BOOT_MSGS)+1)
        if self.lt > interval and self.li < len(BOOT_MSGS):
            self.lines.append(BOOT_MSGS[self.li])
            self.li  += 1
            self.lt   = 0
            Sounds.boot_blip()
        if self.elapsed >= self.DURATION:
            if not self.done:
                Sounds.boot_done()
            self.done = True

    def draw(self, surf):
        # ── Static loading screen image ──────────────────────────────────────────
        if IMG_BOOT:
            surf.blit(IMG_BOOT, (0, 0))
        else:
            surf.fill((158, 165, 210))

        # ── Animated loading bar — centred, just below the folder row ────────────
        prog = min(1.0, self.elapsed / self.DURATION)
        bpw=240; bph=12; bpx=(SW-bpw)//2; bpy=271  # centred, below folders ≈y271

        # Subtle dark track behind bar (blends with gradient bg)
        pygame.draw.rect(surf,(40,30,70,180),(bpx-4,bpy-4,bpw+8,bph+8))

        # Border
        pygame.draw.rect(surf,(38,35,72),(bpx-2,bpy-2,bpw+4,bph+4))
        # Empty (white)
        pygame.draw.rect(surf,(245,245,252),(bpx,bpy,bpw,bph))
        # Pink fill
        _fw=max(0,int(prog*bpw))
        if _fw>0:
            pygame.draw.rect(surf,(215,152,172),(bpx,bpy,_fw,bph))
            # Sheen
            _sh=pygame.Surface((_fw,bph//2),pygame.SRCALPHA)
            _sh.fill((255,255,255,55)); surf.blit(_sh,(bpx,bpy))
        # Percentage label centred below bar
        _pct=F8.render(f"{int(prog*100)}%",True,(80,70,130))
        surf.blit(_pct,(bpx+bpw//2-_pct.get_width()//2, bpy+bph+3))


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    """
    Game loop — simple string-based screen state machine.
    cur ∈ {'boot','pet','dodge','code','chill','wardrobe'}

    Persistent screens (pet, chill, wardrobe) are created once and reused.
    Mini-game screens (dodge, code) are re-instantiated fresh every time the
    player enters them — this resets score/lives without touching Waddle's stats.
    """
    # ── Location setup — run once if no location saved ────────────────────────
    sv=load_save()
    if 'lat' in sv and 'lon' in sv and 'city' in sv:
        _apply_location(sv['lat'], sv['lon'], sv['city'])
    else:
        loc_setup=LocationSetup()
        loc_done=False
        while not loc_done:
            dt2=clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
                r=loc_setup.handle_event(ev)
                if r=='done':
                    res=loc_setup.result
                    _apply_location(res['lat'], res['lon'], res['name'])
                    sv2=load_save()
                    sv2.update({'lat':res['lat'],'lon':res['lon'],'city':res['name']})
                    write_save(sv2)
                    loc_done=True
            if not loc_done:
                loc_setup.update(dt2)
                loc_setup.draw(screen)
                pygame.display.flip()

    w=Waddle(); pet=PetScreen(w); chill=Chill(w); wardrobe=Wardrobe(w)
    cur='boot'; boot=BootScreen(); dodge=None; code_game=None

    def go(name):
        """Switch to a new screen; recreate mini-game instances so they start fresh."""
        nonlocal cur,dodge,code_game
        cur=name
        if name=='dodge':    dodge=DodgeGame(w)
        if name=='code':     code_game=DreamGame(w)
        Sounds.confirm()

    while True:
        dt=clock.tick(FPS)
        keys=pygame.key.get_pressed()
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT:
                w.save(); pygame.quit(); sys.exit()
            if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE:
                if cur!='pet': cur='pet'; Sounds.menu_beep()
            if cur=='boot':
                pass  # boot screen eats all input
            elif cur=='pet':
                a=pet.handle_event(ev)
                if   a=='PLAY':          go('dodge')
                elif a=='CODE':          go('code')
                elif a=='CHILL':         cur='chill'; Sounds.confirm()
                elif a=='WARDROBE':      cur='wardrobe'; Sounds.confirm()
                elif a=='FEED':          pet.do_action('FEED'); Sounds.feed()
                elif a=='REST':          pet.do_action('REST')
                elif a in ('LEFT','RIGHT'): Sounds.menu_beep()
            elif cur=='code' and code_game:
                r3=code_game.handle_event(ev)
                if r3=='back': cur='pet'; Sounds.menu_beep()
            elif cur=='chill':
                if chill.handle_event(ev)=='back': cur='pet'; Sounds.menu_beep()
            elif cur=='wardrobe':
                r2=wardrobe.handle_event(ev)
                if r2=='back': cur='pet'; Sounds.menu_beep()
                elif r2=='restart':
                    pygame.quit()
                    os.execv(sys.executable, [sys.executable]+sys.argv)
                elif r2=='change_city':
                    loc2=LocationSetup(); ld2=False
                    while not ld2:
                        dt3=clock.tick(FPS)
                        for ev3 in pygame.event.get():
                            if ev3.type==pygame.QUIT: pygame.quit(); sys.exit()
                            r3=loc2.handle_event(ev3)
                            if r3=='done':
                                res3=loc2.result
                                _apply_location(res3['lat'],res3['lon'],res3['name'])
                                sv3=load_save()
                                sv3.update({'lat':res3['lat'],'lon':res3['lon'],'city':res3['name']})
                                write_save(sv3)
                                ld2=True
                        if not ld2:
                            loc2.update(dt3); loc2.draw(screen); pygame.display.flip()
                    chill=Chill(w)  # refresh weather data for new city

        if cur=='boot':
            boot.update(dt)
            if boot.done: cur='pet'
        elif cur=='pet':              pet.update(dt)
        elif cur=='dodge' and dodge:
            alive_before=dodge.alive
            dodge.update(dt,keys)
            if alive_before and not dodge.alive: Sounds.game_over()
        elif cur=='code' and code_game: code_game.update(dt)
        elif cur=='chill':            chill.update(dt)
        elif cur=='wardrobe':         wardrobe.update(dt)

        if   cur=='boot':                  boot.draw(screen)
        elif cur=='pet':                   pet.draw(screen)
        elif cur=='dodge' and dodge:       dodge.draw(screen)
        elif cur=='code' and code_game:    code_game.draw(screen)
        elif cur=='chill':                 chill.draw(screen)
        elif cur=='wardrobe':              wardrobe.draw(screen)

        pygame.display.flip()

if __name__=='__main__':
    main()
