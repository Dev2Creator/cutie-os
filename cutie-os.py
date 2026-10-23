#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ═══════════════════════════════════════════════════════════════════════════
#  CUTIE OS — v4.0.0 UNIVERSAL EDITION — cinematic fastfetch console + toolkit
#  target : Universal • Linux (all distros) • macOS • Windows 10/11 • Termux
#
#  run        : python3 cutie-os.py
#  self-check : python3 cutie-os.py --check
#  skip intro : python3 cutie-os.py --no-intro
#
#  EVERY command works: built-in tools, real shell (pipes/globs), and
#  `!cmd` / sudo / vim / htop / python / man run in a REAL tty via PTY.
# ═══════════════════════════════════════════════════════════════════════════

import ast
import getpass
import json
import math
import os
import platform
import queue
import random
import re
import select
import shlex
import shutil
import signal
import socket
import struct
import subprocess
import sys
import threading
import time

# Cross-platform Unix / Windows compatibility shims
HAS_FCNTL = False
HAS_PTY = False
HAS_TERMIOS = False

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    pass

try:
    import pty
    HAS_PTY = True
except ImportError:
    pass

try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    pass

if sys.platform == "win32":
    try:
        import msvcrt
        import ctypes
        # Enable VT100 / ANSI escape sequences in Windows Console & PowerShell
        _kernel32 = ctypes.windll.kernel32
        _hStdOut = _kernel32.GetStdHandle(-11)
        _mode = ctypes.c_ulong()
        _kernel32.GetConsoleMode(_hStdOut, ctypes.byref(_mode))
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        _kernel32.SetConsoleMode(_hStdOut, _mode.value | 0x0004)
    except Exception:
        pass

# ────────────────────────────── constants ──────────────────────────────────

VERSION      = "v4.0.0"
EDITION      = "UNIVERSAL EDITION"
CMD_TIMEOUT  = 20.0
OUT_CAP      = 400
HIST_CAP     = 200
FRAME_TARGET = 1.0 / 60.0
CONFIG_DIR   = os.path.expanduser("~/.config/cutie")
PROFILE_PATH = os.path.join(CONFIG_DIR, "profile.json")
MACRO_PATH   = os.path.join(CONFIG_DIR, "macros.txt")

ESC       = "\x1b"
CLEAR_SCR = ESC + "[2J"
HOME      = ESC + "[H"
ALT_ON    = ESC + "[?1049h"
ALT_OFF   = ESC + "[?1049l"
CUR_HIDE  = ESC + "[?25l"
CUR_SHOW  = ESC + "[?25h"
SYNC_ON   = ESC + "[?2026h"
SYNC_OFF  = ESC + "[?2026l"
RESET     = ESC + "[0m"

USAGE = """CUTIE OS %s — %s
  python3 cutie-os.py            launch the console
  python3 cutie-os.py --check    self-test
  python3 cutie-os.py --no-intro skip the intro
""" % (VERSION, EDITION)

# ────────────────────────────── palette / themes ───────────────────────────

C_BORDER      = (99, 52, 168)
C_TERM_BORDER = (17, 105, 128)
C_LABEL       = (170, 140, 250)
C_ARROW       = (232, 121, 249)
C_VALUE       = (233, 238, 245)
C_OUT         = (203, 210, 222)
C_DIM         = (120, 134, 160)
C_SLATE       = (88, 99, 124)
C_TITLE       = (236, 72, 153)
C_CYAN        = (34, 211, 238)
C_VIOLET      = (139, 92, 246)
C_PURPLE      = (168, 85, 247)
C_FUCHSIA     = (217, 70, 239)
C_MAGENTA     = (236, 72, 153)
C_PINK        = (244, 114, 182)
C_GOLD        = (251, 191, 36)
C_RED         = (248, 113, 113)
C_WHITE       = (248, 250, 252)
C_EX_NEAR     = (76, 29, 149)
C_EX_FAR      = (35, 18, 74)
C_BAR_EMPTY   = (59, 44, 92)

GRAD_STOPS = (C_VIOLET, C_PURPLE, C_FUCHSIA, C_MAGENTA, C_PINK, C_CYAN)

THEMES = {
    # ── Classic Core Themes ──
    "damdaar": dict(border=(99, 52, 168),  tborder=(17, 105, 128), title=(236, 72, 153),
                    label=(170, 140, 250), arrow=(232, 121, 249),
                    stops=((139, 92, 246), (168, 85, 247), (217, 70, 239), (236, 72, 153), (244, 114, 182), (34, 211, 238))),
    "sakura":  dict(border=(190, 90, 140),  tborder=(150, 80, 110), title=(244, 114, 182),
                    label=(250, 180, 210), arrow=(255, 140, 190),
                    stops=((255, 183, 197), (244, 114, 182), (233, 90, 150), (200, 60, 130), (255, 150, 180), (255, 225, 232))),
    "matrix":  dict(border=(20, 120, 60),   tborder=(10, 90, 50),   title=(60, 220, 110),
                    label=(80, 200, 120),  arrow=(120, 255, 160),
                    stops=((10, 60, 30), (20, 110, 55), (40, 160, 80), (60, 210, 100), (120, 255, 160), (180, 255, 200))),
    "ice":     dict(border=(40, 110, 170),  tborder=(30, 90, 150),  title=(56, 189, 248),
                    label=(125, 211, 252), arrow=(147, 197, 253),
                    stops=((30, 80, 160), (40, 110, 200), (56, 150, 240), (96, 190, 250), (147, 220, 255), (205, 245, 255))),
    "sunset":  dict(border=(180, 80, 50),   tborder=(150, 70, 60),  title=(251, 113, 60),
                    label=(253, 160, 90),  arrow=(251, 146, 60),
                    stops=((120, 40, 90), (190, 60, 80), (240, 90, 60), (251, 146, 60), (253, 190, 80), (255, 232, 150))),
    "royal":   dict(border=(90, 70, 200),   tborder=(60, 60, 150),  title=(167, 139, 250),
                    label=(196, 181, 253), arrow=(129, 140, 248),
                    stops=((30, 30, 90), (60, 50, 150), (90, 70, 200), (120, 90, 230), (160, 120, 250), (222, 192, 255))),

    # ── OS Easter Egg Themes ──
    "cupertino": dict(border=(160, 170, 185), tborder=(120, 135, 155), title=(56, 189, 248),
                      label=(186, 215, 245), arrow=(244, 114, 182),
                      stops=((210, 215, 225), (147, 197, 253), (56, 189, 248), (129, 140, 248), (244, 114, 182), (253, 164, 175))),
    "redmond":   dict(border=(0, 120, 215),   tborder=(0, 90, 170),   title=(96, 205, 255),
                      label=(140, 210, 255), arrow=(0, 165, 245),
                      stops=((0, 103, 192), (0, 120, 215), (0, 153, 235), (96, 205, 255), (150, 225, 255), (200, 240, 255))),
    "arch":      dict(border=(23, 147, 209),  tborder=(17, 105, 128), title=(51, 170, 221),
                      label=(125, 211, 252), arrow=(23, 147, 209),
                      stops=((17, 105, 128), (23, 147, 209), (51, 170, 221), (100, 215, 255), (150, 230, 255), (210, 245, 255))),
    "ubuntu":    dict(border=(233, 84, 32),   tborder=(119, 33, 111), title=(233, 84, 32),
                      label=(255, 160, 120), arrow=(233, 84, 32),
                      stops=((119, 33, 111), (150, 40, 110), (195, 60, 70), (233, 84, 32), (245, 125, 60), (255, 180, 120))),
    "debian":    dict(border=(215, 10, 83),   tborder=(168, 0, 48),   title=(215, 10, 83),
                      label=(250, 130, 160), arrow=(215, 10, 83),
                      stops=((140, 0, 40), (180, 5, 60), (215, 10, 83), (240, 60, 110), (255, 120, 160), (255, 180, 200))),
    "fedora":    dict(border=(41, 65, 114),   tborder=(60, 110, 180), title=(81, 162, 218),
                      label=(150, 200, 245), arrow=(81, 162, 218),
                      stops=((41, 65, 114), (51, 90, 150), (60, 110, 180), (81, 162, 218), (140, 205, 245), (200, 235, 255))),
    "kali":      dict(border=(85, 124, 147),  tborder=(30, 70, 95),   title=(0, 210, 255),
                      label=(130, 200, 220), arrow=(0, 210, 255),
                      stops=((20, 40, 55), (45, 80, 100), (85, 124, 147), (50, 175, 205), (0, 210, 255), (140, 240, 255))),
    "mint":      dict(border=(107, 179, 36),  tborder=(65, 125, 25),  title=(135, 207, 62),
                      label=(175, 230, 120), arrow=(135, 207, 62),
                      stops=((45, 95, 20), (75, 140, 30), (107, 179, 36), (135, 207, 62), (175, 230, 110), (215, 245, 170))),
    "opensuse":  dict(border=(115, 186, 37),  tborder=(53, 185, 171), title=(115, 186, 37),
                      label=(165, 225, 105), arrow=(53, 185, 171),
                      stops=((30, 120, 100), (53, 185, 171), (80, 195, 100), (115, 186, 37), (160, 220, 70), (205, 245, 140))),
    "nixos":     dict(border=(82, 119, 195),  tborder=(55, 90, 160),  title=(126, 186, 228),
                      label=(170, 215, 245), arrow=(126, 186, 228),
                      stops=((50, 80, 150), (82, 119, 195), (105, 155, 215), (126, 186, 228), (175, 220, 250), (225, 245, 255))),
    "alpine":    dict(border=(13, 89, 127),   tborder=(10, 65, 95),   title=(0, 153, 221),
                      label=(120, 200, 245), arrow=(0, 153, 221),
                      stops=((13, 89, 127), (20, 120, 170), (0, 153, 221), (70, 190, 245), (150, 225, 255), (215, 245, 255))),
    "popos":     dict(border=(72, 185, 199),  tborder=(45, 130, 140), title=(242, 172, 0),
                      label=(135, 220, 230), arrow=(242, 172, 0),
                      stops=((35, 120, 130), (72, 185, 199), (120, 210, 200), (200, 190, 80), (242, 172, 0), (255, 210, 90))),
    "gentoo":    dict(border=(74, 65, 113),   tborder=(50, 42, 85),   title=(138, 125, 182),
                      label=(180, 170, 215), arrow=(138, 125, 182),
                      stops=((45, 38, 75), (74, 65, 113), (105, 95, 150), (138, 125, 182), (180, 170, 220), (220, 212, 245))),
    "termux":    dict(border=(61, 220, 132),  tborder=(35, 140, 80),  title=(61, 220, 132),
                      label=(130, 240, 175), arrow=(61, 220, 132),
                      stops=((20, 80, 45), (35, 140, 80), (61, 220, 132), (110, 240, 165), (170, 250, 205), (215, 255, 235))),
}

CURRENT_THEME = "damdaar"


def apply_theme(name):
    global CURRENT_THEME, GRAD_STOPS
    th = THEMES[name]
    global C_BORDER, C_TERM_BORDER, C_TITLE, C_LABEL, C_ARROW
    C_BORDER      = th["border"]
    C_TERM_BORDER = th["tborder"]
    C_TITLE       = th["title"]
    C_LABEL       = th["label"]
    C_ARROW       = th["arrow"]
    GRAD_STOPS    = th["stops"]
    CURRENT_THEME = name
    _fg_cache.clear()

# ────────────────────────── color / text helpers ───────────────────────────

_COLOR_MODE = None
_fg_cache = {}


def detect_color_mode():
    if os.environ.get("CUTIE_FORCE_256"):
        return 256
    ct = (os.environ.get("COLORTERM") or "").lower()
    term = os.environ.get("TERM") or ""
    if "truecolor" in ct or "24bit" in ct or "kitty" in term:
        return 24
    return 256


_COLOR_MODE = detect_color_mode()


def fg(rgb):
    got = _fg_cache.get(rgb)
    if got is not None:
        return got
    r, g, b = rgb
    if _COLOR_MODE == 24:
        seq = ESC + "[38;2;%d;%d;%dm" % (r, g, b)
    else:
        if r == g == b:
            if r < 8:
                idx = 16
            elif r > 248:
                idx = 231
            else:
                idx = 232 + int(round((r - 8) / 247.0 * 23))
        else:
            def q(v):
                return max(0, min(5, int(round(v / 255.0 * 5))))
            idx = 16 + 36 * q(r) + 6 * q(g) + q(b)
        seq = ESC + "[38;5;%dm" % idx
    _fg_cache[rgb] = seq
    return seq


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def mix(c1, c2, t):
    t = clamp(t, 0.0, 1.0)
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


def scale(c, f):
    return (clamp(int(c[0] * f), 0, 255),
            clamp(int(c[1] * f), 0, 255),
            clamp(int(c[2] * f), 0, 255))


def grad(t):
    t = clamp(t, 0.0, 1.0)
    n = len(GRAD_STOPS) - 1
    x = t * n
    i = int(x)
    if i >= n:
        return GRAD_STOPS[-1]
    return mix(GRAD_STOPS[i], GRAD_STOPS[i + 1], x - i)


_WIDE_RANGES = (
    (0x1100, 0x115F), (0x2600, 0x2603), (0x26A1, 0x26A1), (0x2615, 0x2615),
    (0x2E80, 0x303E), (0x3041, 0x33FF), (0x3400, 0x4DBF), (0x4E00, 0x9FFF),
    (0xA000, 0xA4CF), (0xAC00, 0xD7A3), (0xF900, 0xFAFF), (0xFE30, 0xFE6F),
    (0xFF00, 0xFF60), (0xFFE0, 0xFFE6), (0x1F300, 0x1F64F), (0x1F900, 0x1F9FF),
    (0x20000, 0x2FFFD),
)


def char_width(ch):
    o = ord(ch)
    if o < 0x1100:
        return 1
    for lo, hi in _WIDE_RANGES:
        if lo <= o <= hi:
            return 2
    return 1


def disp_width(s):
    w = 0
    for ch in s:
        w += char_width(ch)
    return w


def clip(text, width):
    if width <= 0:
        return ""
    if disp_width(text) <= width:
        return text
    out = []
    w = 0
    for ch in text:
        cw = char_width(ch)
        if w + cw > width - 1:
            break
        out.append(ch)
        w += cw
    return "".join(out) + "…"


_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)?")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def strip_ansi(s):
    return _ANSI_RE.sub("", s)


def sanitize(s):
    s = s.replace("\t", "    ").replace("\r\n", "\n").replace("\r", "\n")
    s = strip_ansi(s)
    return _CTRL_RE.sub("", s)


def substr_width(s, start, width):
    out = []
    acc = 0
    cur = 0
    for ch in s:
        cw = char_width(ch)
        if cur + cw <= start:
            cur += cw
            continue
        if acc + cw > width:
            break
        out.append(ch)
        acc += cw
        cur += cw
    return "".join(out), acc


def put_segs(cv, x, y, segs):
    for text, color in segs:
        if text:
            cv.put(x, y, text, color)
            x += disp_width(text)

# ───────────────────────────── profile / macros io ─────────────────────────


def load_profile():
    try:
        with open(PROFILE_PATH) as f:
            j = json.load(f)
            return j if isinstance(j, dict) else {}
    except Exception:
        return {}


def save_profile(pf):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(PROFILE_PATH, "w") as f:
            json.dump(pf, f)
    except Exception:
        pass


def load_nick():
    return load_profile().get("nick") or ""


def save_profile_field(k, v):
    pf = load_profile()
    pf[k] = v
    save_profile(pf)


def load_macros():
    M = {}
    try:
        with open(MACRO_PATH) as f:
            for line in f:
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    if k and v:
                        M[k] = v
    except Exception:
        pass
    return M


def save_macros(M):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(MACRO_PATH, "w") as f:
            for k in sorted(M):
                f.write("%s = %s\n" % (k, M[k]))
    except Exception:
        pass

# ───────────────────────────── the big logo ────────────────────────────────

_GLYPHS = {
    "C": (" ██████╗", "██╔════╝", "██║     ", "██║     ", "╚██████╗", " ╚═════╝"),
    "U": ("██╗   ██╗", "██║   ██║", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "),
    "T": ("████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "),
    "I": ("██╗", "██║", "██║", "██║", "██║", "╚═╝"),
    "E": ("███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"),
    "O": (" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "),
    "S": ("███████╗", "██╔════╝", "███████╗", "╚════██║", "███████║", "╚══════╝"),
    "A": (" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"),
    "B": ("██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██████╔╝", "╚═════╝ "),
    "D": ("██████╗ ", "██╔══██╗", "██║  ██║", "██║  ██║", "██████╔╝", "╚═════╝ "),
    "F": ("███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "██║     ", "╚═╝     "),
    "G": (" ██████╗ ", "██╔════╝", "██║  ███╗", "██║   ██║", "╚██████╔╝", " ╚═════╝ "),
    "H": ("██╗  ██╗", "██║  ██║", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"),
    "J": ("     ██╗", "     ██║", "     ██║", "██   ██║", "╚█████╔╝", " ╚════╝ "),
    "K": ("██╗  ██╗", "██║ ██╔╝", "█████╔╝ ", "██╔═██╗ ", "██║  ██╗", "╚═╝  ╚═╝"),
    "L": ("██╗     ", "██║     ", "██║     ", "██║     ", "███████╗", "╚══════╝"),
    "M": ("███╗   ███╗", "████╗ ████║", "██╔████╔██║", "██║╚██╔╝██║", "██║ ╚═╝ ██║", "╚═╝     ╚═╝"),
    "N": ("███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"),
    "P": ("██████╗ ", "██╔══██╗", "██████╔╝", "██╔═══╝ ", "██║     ", "╚═╝     "),
    "Q": (" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║  ██╔╝", "╚██████╔╝", " ╚═════╝ "),
    "R": ("██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"),
    "V": ("██╗   ██╗", "██║   ██║", "██║   ██║", "╚██╗ ██╔╝", " ╚████╔╝ ", "  ╚═══╝  "),
    "W": ("██╗    ██╗", "██║    ██║", "██║ █╗ ██║", "██║███╗██║", "╚███╔███╔╝", " ╚══╝╚══╝ "),
    "X": ("██╗  ██╗", "╚██╗██╔╝", " ╚███╔╝ ", " ██╔██╗ ", "██╔╝ ██╗", "╚═╝  ╚═╝"),
    "Y": ("██╗   ██╗", "╚██╗ ██╔╝", " ╚████╔╝ ", "  ╚██╔╝  ", "   ██║   ", "   ╚═╝   "),
    "Z": ("███████╗", "╚══███╔╝", "   ███╔╝", "  ███╔╝ ", " ███████╗", "╚══════╝"),
    " ": ("   ", "   ", "   ", "   ", "   ", "   "),
}

LOGO = ["".join(row) for row in zip(*(_GLYPHS[c] for c in "CUTIE OS"))]
LOGO_W = disp_width(LOGO[0])
LOGO_CELLS = tuple((i, ry, ch) for ry, line in enumerate(LOGO)
                   for i, ch in enumerate(line) if ch != " ")


def paint_logo(cv, x0, y0, t, reveal=1.0, extrude=1.0):
    n = LOGO_W
    sweep = -99.0
    u = (t % 4.2) / 4.2
    if u < 0.62:
        sweep = -8.0 + (n + 16.0) * (u / 0.62)
    band = 3.0
    colc = []
    for i in range(n):
        c = grad(i / max(1, n - 1))
        d = abs(i - sweep)
        if d < band * 2.5:
            f = math.exp(-(d * d) / (2.0 * band * band))
            c = mix(c, C_WHITE, min(1.0, f * 0.9))
        colc.append(c)

    if extrude > 0.0:
        dep = 4
        for k in range(dep, 0, -1):
            if k > extrude * dep + 0.001:
                continue
            c = mix(C_EX_NEAR, C_EX_FAR, (k - 1) / max(1, dep - 1))
            for ry in range(6):
                cv.put(x0 + k, y0 + ry + k, LOGO[ry], c)

    ph = t % 7.0
    if ph < 0.7:
        a = math.sin(ph / 0.7 * math.pi)
        for ry in range(6):
            cv.put(x0 - 1, y0 + ry, LOGO[ry], scale(C_CYAN, 0.18 + 0.30 * a))
            cv.put(x0 + 1, y0 + ry, LOGO[ry], scale(C_MAGENTA, 0.18 + 0.30 * a))

    front = reveal * (n + 7)
    scr = "░▒▓█"
    for ry in range(6):
        line = LOGO[ry]
        rowscale = 1.14 if ry < 2 else (0.90 if ry >= 4 else 1.0)
        yy = y0 + ry
        for i, ch in enumerate(line):
            if ch == " ":
                continue
            if i >= front:
                break
            if i > front - 6:
                cv.set(x0 + i, yy, random.choice(scr), scale(colc[i], 0.75))
            else:
                c = colc[i]
                if rowscale != 1.0:
                    c = scale(c, rowscale)
                cv.set(x0 + i, yy, ch, c)

# ──────────────────────────────── canvas ───────────────────────────────────


class Canvas:
    def __init__(self, w, h):
        self.w = max(1, w)
        self.h = max(1, h)
        n = self.w * self.h
        self.chars = [" "] * n
        self.colors = [""] * n

    def clear(self):
        n = self.w * self.h
        self.chars[:] = [" "] * n
        self.colors[:] = [""] * n

    def set(self, x, y, ch, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = y * self.w + x
            self.chars[i] = ch
            self.colors[i] = fg(color) if isinstance(color, tuple) else color

    def put(self, x, y, text, color):
        if y < 0 or y >= self.h or x >= self.w:
            return
        base = y * self.w
        cx = x
        for ch in text:
            if ch in ("\n", "\r"):
                continue
            if cx >= self.w:
                break
            cw = char_width(ch)
            if cw == 2:
                if cx + 1 >= self.w:
                    break
                self.chars[base + cx] = ch
                self.colors[base + cx] = fg(color) if isinstance(color, tuple) else color
                self.chars[base + cx + 1] = ""
                self.colors[base + cx + 1] = fg(color) if isinstance(color, tuple) else color
                cx += 2
            else:
                self.chars[base + cx] = ch
                self.colors[base + cx] = fg(color) if isinstance(color, tuple) else color
                cx += 1

    def render(self):
        w = self.w
        out = []
        for y in range(self.h):
            base = y * w
            x = w
            while x > 0 and self.chars[base + x - 1] == " ":
                x -= 1
            parts = []
            last = ""
            for i in range(x):
                c = self.colors[base + i]
                if c != last:
                    parts.append(c if c else RESET)
                    last = c
                parts.append(self.chars[base + i])
            parts.append(RESET + ESC + "[K")
            out.append("".join(parts))
            if y < self.h - 1:
                out.append("\r\n")
        return "".join(out)

# ───────────────────────────── layout solver ───────────────────────────────


class Layout:
    def __init__(self, W, H):
        self.W = W
        self.H = H
        self.panel_w = max(20, (W - 4) // 2)
        self.right_x = 1 + self.panel_w + 2 + ((W - 4) % 2)
        s = self._solve(H)
        self.too_small = (W < 60) or (s is None)
        if self.too_small:
            self.logo_full = False
            self.anim_rows = 0
            self.out_rows = 1
            self.header_y = self.panels_y = self.term_y = 0
            self.hints_y = max(0, H - 1)
            self.gap1_y = self.logo_y = self.extrgap_y = -1
            self.subtitle_y = self.gap2_y = self.gap3_y = self.anim_y = -1
            return
        logo_full, A, O = s
        extra = H - ((29 if logo_full else 19) + A + O)
        g3 = min(8, extra // 2)
        g4 = min(8, extra - g3)
        self.logo_full = logo_full
        self.anim_rows = A
        self.out_rows = O
        y = 0
        self.header_y = y
        y += 3
        if logo_full:
            self.gap1_y = y
            y += 1
            self.logo_y = y
            y += 6
            self.extrgap_y = y
            y += 1
            self.subtitle_y = y
            y += 1
            self.gap2_y = y
            y += 1
        else:
            self.gap1_y = self.logo_y = self.extrgap_y = -1
            self.subtitle_y = self.gap2_y = -1
        self.panels_y = y
        y += 10
        self.gap3_y = y
        y += 1 + g3
        self.anim_y = y
        y += A + g4
        self.hints_y = H - 1
        self.term_y = H - O - 4

    @staticmethod
    def _solve(H):
        for logo_full, base in ((True, 29), (False, 19)):
            for A in (5, 3, 1, 0):
                room = H - base - A
                if room >= 1:
                    return (logo_full, A, min(12, room))
        return None

# ────────────────────────── system information ─────────────────────────────


def run_cmd(cmd, timeout=4, cwd=None):
    try:
        p = subprocess.run(cmd, stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=timeout, cwd=cwd)
        return p.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def _cap(cmd, timeout=12):
    return run_cmd([os.environ.get("SHELL") or "/bin/sh", "-c", cmd], timeout)


def first_line(s):
    ls = s.strip().splitlines()
    return ls[0].strip() if ls else ""


def detect_os_target():
    """Detect OS and specific Linux distro.
    Returns: (theme_key, pretty_name, icon, easter_egg_msg)
    """
    if os.environ.get("TERMUX_VERSION"):
        return "termux", "Android • Termux", "🤖", "Mobile Cyber Deck Easter Egg Unlocked! 🤖"

    sys_plat = platform.system().lower()

    if sys_plat == "darwin":
        ver = platform.mac_ver()[0] or ""
        name = f"macOS {ver}".strip() if ver else "macOS"
        return "cupertino", name, "🍎", f"{name} Cupertino Aqua Easter Egg Unlocked! 🍎"

    if sys_plat == "windows":
        rel = platform.release()
        name = f"Windows {rel}"
        return "redmond", name, "🪟", f"{name} Redmond Fluent Easter Egg Unlocked! 🪟"

    if sys_plat == "linux":
        info = {}
        if hasattr(platform, "freedesktop_os_release"):
            try:
                info = platform.freedesktop_os_release()
            except Exception:
                pass
        if not info and os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", encoding="utf-8") as f:
                    for line in f:
                        if "=" in line:
                            k, v = line.strip().split("=", 1)
                            info[k] = v.strip('"\'')
            except Exception:
                pass

        did = (info.get("ID") or "").lower()
        dlike = (info.get("ID_LIKE") or "").lower()
        pretty = info.get("PRETTY_NAME") or info.get("NAME") or "Linux"

        if "arch" in did or "arch" in dlike:
            return "arch", pretty, "⚡", f"{pretty} Bleeding-Edge Cyan Easter Egg Unlocked! ⚡"
        if "ubuntu" in did:
            return "ubuntu", pretty, "🍥", f"{pretty} Canonical Aubergine Easter Egg Unlocked! 🍥"
        if "debian" in did:
            return "debian", pretty, "🌀", f"{pretty} Universal Debian Crimson Easter Egg Unlocked! 🌀"
        if "fedora" in did:
            return "fedora", pretty, "🎩", f"{pretty} Fedora Ocean Blue Easter Egg Unlocked! 🎩"
        if "kali" in did:
            return "kali", pretty, "🐉", f"{pretty} Kali Cyber Dragon Easter Egg Unlocked! 🐉"
        if "mint" in did:
            return "mint", pretty, "🍃", f"{pretty} Linux Mint Fresh Easter Egg Unlocked! 🍃"
        if "suse" in did or "opensuse" in did:
            return "opensuse", pretty, "🦎", f"{pretty} openSUSE Geeko Green Easter Egg Unlocked! 🦎"
        if "nixos" in did:
            return "nixos", pretty, "❄️", f"{pretty} NixOS Snowflake Easter Egg Unlocked! ❄️"
        if "alpine" in did:
            return "alpine", pretty, "🏔️", f"{pretty} Alpine Glacial Blue Easter Egg Unlocked! 🏔️"
        if "pop" in did:
            return "popos", pretty, "🚀", f"{pretty} Pop!_OS Cosmic Easter Egg Unlocked! 🚀"
        if "gentoo" in did:
            return "gentoo", pretty, "🌌", f"{pretty} Gentoo Source Violet Easter Egg Unlocked! 🌌"

        return "damdaar", pretty, "🐧", f"{pretty} Console Edition! 🐧"

    return "damdaar", platform.system() or "Unknown OS", "💻", "Universal Console Edition! 💻"


def os_pretty():
    _, name, _, _ = detect_os_target()
    return name


def cpu_model():
    # 1. Linux /proc/cpuinfo
    if os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name") or line.startswith("Hardware") or line.startswith("Processor"):
                        m = line.split(":", 1)[1].strip()
                        m = m.replace("(R)", "").replace("(r)", "")
                        m = m.replace("(TM)", "").replace("(tm)", "")
                        m = re.sub(r"\s+", " ", m).strip()
                        if m:
                            return m
        except Exception:
            pass
    # 2. macOS sysctl
    elif sys.platform == "darwin":
        try:
            m = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
            if m:
                return m
        except Exception:
            pass
    # 3. Windows registry
    elif sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            if val and str(val).strip():
                return str(val).strip()
        except Exception:
            pass

    p = platform.processor()
    return p if p else (platform.machine() or "N/A")


def gpu_info():
    out = run_cmd(["nvidia-smi", "--query-gpu=name,driver_version",
                   "--format=csv,noheader"], 4)
    if out.strip():
        parts = [p.strip() for p in first_line(out).split(",")]
        name = parts[0] if parts else ""
        if name and "N/A" not in name:
            val = name
            if len(parts) > 1 and parts[1] and parts[1] != "N/A":
                val += "  •  drv " + parts[1]
            return val
    out = run_cmd(["lspci"], 4)
    for line in out.splitlines():
        if re.search(r"VGA compatible controller|3D controller|Display controller",
                     line, re.I):
            desc = line.split(":", 2)[-1].strip()
            desc = re.sub(r"\[[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}\]", "", desc)
            desc = re.sub(r"\s+", " ", desc).strip()
            if desc:
                return desc
    return "N/A"


def vram_info():
    out = run_cmd(["nvidia-smi", "--query-gpu=memory.total",
                   "--format=csv,noheader"], 3)
    if out.strip():
        return first_line(out).strip()
    return None


def pkg_count():
    out = run_cmd(["pacman", "-Qq"], 8)
    if out.strip():
        return str(sum(1 for _ in out.splitlines()))
    try:
        d = "/var/lib/pacman/local"
        n = len([e for e in os.listdir(d)
                 if os.path.isdir(os.path.join(d, e))])
        if n > 0:
            return str(n)
    except Exception:
        pass
    out = _cap("dpkg -l 2>/dev/null | grep -c '^ii'", 8)
    if out.strip().isdigit() and int(out.strip()) > 0:
        return out.strip() + " (deb)"
    return "N/A"


def shell_info():
    sh = os.environ.get("SHELL") or "/bin/sh"
    name = os.path.basename(sh) or "sh"
    ver = ""
    out = run_cmd([sh, "--version"], 3)
    m = re.search(r"\d+\.\d+(?:\.\d+)?", out)
    if m:
        ver = m.group(0)
    return name, ver


def hyprland_version():
    v = os.environ.get("HYPRLAND_INSTANCE_VERSION")
    if v:
        return v
    out = run_cmd(["hyprctl", "version"], 3)
    if out:
        m = re.search(r"Tag:\s*(\S+)", out)
        if m:
            return m.group(1).rstrip(",")
        m = re.search(r"version\s+(v?[0-9][\w.\-]*)", out)
        if m:
            return m.group(1)
        ln = first_line(out)
        if ln:
            return ln[:40]
    return "N/A"


def kitty_version():
    out = run_cmd(["kitty", "--version"], 3)
    s = out.strip()
    if s:
        toks = s.split()
        if toks and any(c.isdigit() for c in toks[-1]):
            return toks[-1]
        return s
    if os.environ.get("KITTY_WINDOW_ID"):
        return "running"
    return "N/A"


def audio_info():
    out = run_cmd(["pactl", "info"], 3)
    m = re.search(r"Server Name:\s*(.+)", out)
    if m:
        sn = m.group(1).strip()
        if "PipeWire" in sn:
            m2 = re.search(r"PipeWire\s*([\d.]+)", sn)
            return "PipeWire" + ((" " + m2.group(1)) if m2 else "")
        if "PulseAudio" in sn:
            m2 = re.search(r"PulseAudio\s*([\d.]+)", sn)
            return "PulseAudio" + ((" " + m2.group(1)) if m2 else "")
        return sn[:40] if sn else "N/A"
    try:
        with open("/proc/asound/cards") as f:
            txt = f.read()
        m = re.search(r"\[\s*([^\]]+)\s*\]:\s*([^-]+)-\s*(.+)", txt)
        if m:
            return "ALSA • " + m.group(3).strip()[:28]
        if txt.strip():
            return "ALSA"
    except Exception:
        pass
    if os.path.exists("/dev/snd"):
        return "ALSA/HDA"
    return "N/A"


def temp_info():
    best = None
    try:
        for hw in sorted(os.listdir("/sys/class/hwmon")):
            base = "/sys/class/hwmon/" + hw
            try:
                with open(base + "/name") as f:
                    name = f.read().strip().lower()
            except Exception:
                name = ""
            if name in ("coretemp", "k10temp", "zenpower", "cpu_thermal"):
                prio = 2
            elif "cpu" in name or "acpi" in name:
                prio = 1
            else:
                prio = 0
            try:
                files = os.listdir(base)
            except Exception:
                continue
            for fn in files:
                if fn.startswith("temp") and fn.endswith("_input"):
                    try:
                        with open(os.path.join(base, fn)) as f:
                            c = int(f.read().strip()) / 1000.0
                    except Exception:
                        continue
                    if 0 < c < 150:
                        cand = (prio, c)
                        if best is None or cand > best:
                            best = cand
    except Exception:
        pass
    if best is not None:
        return best[1]
    try:
        for z in os.listdir("/sys/class/thermal"):
            if not z.startswith("thermal_zone"):
                continue
            try:
                with open("/sys/class/thermal/" + z + "/temp") as f:
                    c = int(f.read().strip()) / 1000.0
            except Exception:
                continue
            if 0 < c < 150 and (best is None or c > best):
                best = c
    except Exception:
        pass
    return best


def battery_info():
    try:
        entries = os.listdir("/sys/class/power_supply")
    except Exception:
        return None
    ac_online = False
    bat = None
    for e in entries:
        base = "/sys/class/power_supply/" + e
        try:
            with open(base + "/type") as f:
                typ = f.read().strip()
        except Exception:
            continue
        if typ in ("Mains", "USB", "UPS") or e.upper().startswith("AC"):
            try:
                with open(base + "/online") as f:
                    if f.read().strip() == "1":
                        ac_online = True
            except Exception:
                pass
        elif typ == "Battery" and bat is None:
            try:
                with open(base + "/capacity") as f:
                    cap = int(f.read().strip())
                with open(base + "/status") as f:
                    st = f.read().strip()
                bat = (cap, st)
            except Exception:
                pass
    if bat is not None:
        return bat
    if ac_online:
        return ("AC", "AC")
    out = run_cmd(["termux-battery-status"], 4)
    try:
        j = json.loads(out)
        return (int(j.get("percentage", 0)), str(j.get("status", "?")))
    except Exception:
        pass
    return None


def mem_info():
    total = None
    avail = None
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    total = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    avail = int(line.split()[1])
                if total is not None and avail is not None:
                    break
    except Exception:
        pass
    if not total or avail is None:
        return None
    used = total - avail
    return (used, total, used * 100.0 / total)


def swap_info():
    try:
        tot = av = 0
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("SwapTotal:"):
                    tot = int(line.split()[1])
                elif line.startswith("SwapFree:"):
                    av = int(line.split()[1])
        if tot:
            return (tot - av, tot)
    except Exception:
        pass
    return None


def disk_info():
    try:
        u = shutil.disk_usage("/")
        return (u.used / 2 ** 30, u.total / 2 ** 30,
                u.used * 100.0 / max(1, u.total))
    except Exception:
        return None


def uptime_secs():
    try:
        with open("/proc/uptime") as f:
            return float(f.read().split()[0])
    except Exception:
        return None


def fmt_uptime(sec):
    sec = int(sec)
    d = sec // 86400
    h = (sec % 86400) // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if d:
        return "%dd %dh %dm" % (d, h, m)
    if h:
        return "%dh %dm" % (h, m)
    if m:
        return "%dm %ds" % (m, s)
    return "%ds" % s


def proc_count():
    try:
        return sum(1 for n in os.listdir("/proc") if n.isdigit())
    except Exception:
        return None


def cpu_cores():
    try:
        with open("/proc/cpuinfo") as f:
            txt = f.read()
        phys = set()
        for blk in txt.split("\n\n"):
            m1 = re.search(r"physical id\s*:\s*(\d+)", blk)
            m2 = re.search(r"core id\s*:\s*(\d+)", blk)
            if m1 and m2:
                phys.add((m1.group(1), m2.group(1)))
        if phys:
            return len(phys), os.cpu_count() or len(phys)
    except Exception:
        pass
    return None, os.cpu_count()


def cpu_freq():
    try:
        vals = []
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.lower().startswith("cpu mhz"):
                    vals.append(float(line.split(":")[1]))
        if vals:
            return sum(vals) / len(vals)
    except Exception:
        pass
    try:
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq") as f:
            return int(f.read().strip()) / 1000.0
    except Exception:
        pass
    return None


def dmi(field):
    try:
        with open("/sys/devices/virtual/dmi/id/" + field) as f:
            v = f.read().strip()
            return v or None
    except Exception:
        return None


def resolution_info():
    out = run_cmd(["hyprctl", "monitors"], 3)
    m = re.search(r"(\d{3,5})x(\d{3,5})\s*@\s*([\d.]+)", out)
    if m:
        return "%s x %s @ %sHz" % (m.group(1), m.group(2), m.group(3))
    out = run_cmd(["xrandr", "--current"], 3)
    m = re.search(r"current\s+(\d+)\s*x\s*(\d+)", out)
    if m:
        return "%s x %s (x11)" % (m.group(1), m.group(2))
    try:
        for drm in sorted(os.listdir("/sys/class/drm")):
            p = "/sys/class/drm/" + drm + "/modes"
            if os.path.exists(p):
                with open(p) as f:
                    first = f.readline().strip()
                if first:
                    return first
    except Exception:
        pass
    return None


def de_info():
    for k in ("XDG_CURRENT_DESKTOP", "DESKTOP_SESSION"):
        v = os.environ.get(k)
        if v:
            return v.split(":")[0].upper()
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "Hyprland"
    return None


def gsettings_get(schema, key):
    out = run_cmd(["gsettings", "get", schema, key], 2)
    return out.strip().strip("'\"") or None


def theme_info():
    t = gsettings_get("org.gnome.desktop.interface", "gtk-theme")
    if t:
        return t
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "hypr (custom)"
    return None


def cursor_info():
    return gsettings_get("org.gnome.desktop.interface", "cursor-theme")


def _iface_ip(iface):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            packed = struct.pack("256s", iface[:15].encode("utf-8"))
            addr = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, packed)[20:24])
            return addr
        finally:
            s.close()
    except Exception:
        return None


def iface_list():
    out = []
    try:
        names = sorted(os.listdir("/sys/class/net"))
    except Exception:
        return out
    for n in names:
        typ = "eth"
        if n.startswith("wl"):
            typ = "wifi"
        elif n.startswith("lo"):
            typ = "loop"
        try:
            with open("/sys/class/net/" + n + "/operstate") as f:
                st = f.read().strip()
        except Exception:
            st = "?"
        ip = _iface_ip(n) if st == "up" else None
        out.append((n, typ, st, ip))
    return out


def public_ip(timeout=4):
    out = run_cmd(["curl", "-s", "--max-time", str(int(timeout)),
                   "https://api.ipify.org"], timeout + 1)
    v = out.strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", v):
        return v
    return None


def pct_color(p):
    if p < 60:
        return C_CYAN
    if p < 80:
        return C_VIOLET
    if p < 92:
        return C_MAGENTA
    return C_RED


def micro_bar(pct, w=10):
    w = max(3, int(w))
    filled = int(round(pct / 100.0 * w))
    filled = max(0, min(w, filled))
    col = pct_color(pct)
    segs = [("█" * filled, col), ("░" * (w - filled), C_BAR_EMPTY)]
    return ("█" * filled + "░" * (w - filled)), segs, col


def cpu_sample():
    try:
        with open("/proc/stat") as f:
            v = list(map(int, f.readline().split()[1:]))
        idle, tot = v[3] + v[4], sum(v)
        time.sleep(0.25)
        with open("/proc/stat") as f:
            v2 = list(map(int, f.readline().split()[1:]))
        idle2, tot2 = v2[3] + v2[4], sum(v2)
        dt, di = tot2 - tot, idle2 - idle
        return clamp(100.0 * (dt - di) / max(1, dt), 0.0, 100.0)
    except Exception:
        return 0.0


def cpu_delta_pct():
    try:
        with open("/proc/stat") as f:
            v = list(map(int, f.readline().split()[1:]))
        return (v[3] + v[4], sum(v))
    except Exception:
        return None


SPARK_CHARS = "▁▂▃▄▅▆▇█"


def spark(vals, w=14):
    if not vals:
        return ""
    v = list(vals)[-w:]
    mx = max(v) or 1.0
    return "".join(SPARK_CHARS[min(7, int(x / mx * 7.999))] for x in v)


def _kv(label, value, note=None):
    segs = [("  " + label.ljust(14), C_LABEL), ("» ", C_ARROW), (str(value), C_VALUE)]
    if note:
        segs.append(("  " + note, C_SLATE))
    return segs


class SysInfo:
    def __init__(self):
        self.ui_sys = []
        self.ui_vit = []
        self.hist_cpu = [0] * 18
        self.cpu_pct = 0.0
        self._last_stat = None
        self.net_rx = 0.0
        self.net_tx = 0.0
        self._last_net = None
        self._last_net_t = 0.0
        self.refresh_static()
        self.refresh_dynamic()

    def refresh_static(self):
        self.os_name = os_pretty()
        self.arch = platform.machine() or "x86_64"
        self.kernel = platform.release() or "N/A"
        try:
            self.hostname = socket.gethostname() or "localhost"
        except Exception:
            self.hostname = "localhost"
        try:
            self.user = getpass.getuser()
        except Exception:
            self.user = os.environ.get("USER", "user")
        self.cpu = cpu_model()
        self.gpu = gpu_info()
        self.pkg = pkg_count()
        self.shell_name, self.shell_ver = shell_info()
        self.hypr = hyprland_version()
        self.kitty = kitty_version()
        self.audio = audio_info()
        self.nick = load_nick()
        wd = (os.environ.get("XDG_SESSION_TYPE") or "").lower()
        if os.environ.get("WAYLAND_DISPLAY") or wd == "wayland":
            self.wayland = "ACTIVE"
        elif wd:
            self.wayland = wd.upper()
        else:
            self.wayland = "N/A"

    def refresh_dynamic(self):
        u = uptime_secs()
        self.f_uptime = fmt_uptime(u) if u is not None else "N/A"
        self.mem = mem_info()
        self.disk = disk_info()
        self.temp = temp_info()
        self.bat = battery_info()
        cur = cpu_delta_pct()
        if cur and self._last_stat:
            dt = cur[1] - self._last_stat[1]
            di = cur[0] - self._last_stat[0]
            self.cpu_pct = clamp(100.0 * (dt - di) / max(1, dt), 0.0, 100.0) if dt > 0 else 0.0
        else:
            self.cpu_pct = 0.0
        if cur:
            self._last_stat = cur
        self.hist_cpu.append(self.cpu_pct)
        if len(self.hist_cpu) > 18:
            del self.hist_cpu[: len(self.hist_cpu) - 18]
        nb = net_bytes()
        now = time.monotonic()
        if nb and self._last_net and now > self._last_net_t:
            dt = now - self._last_net_t
            self.net_rx = max(0.0, (nb[0] - self._last_net[0]) / max(0.001, dt))
            self.net_tx = max(0.0, (nb[1] - self._last_net[1]) / max(0.001, dt))
        else:
            self.net_rx = 0.0
            self.net_tx = 0.0
        if nb:
            self._last_net = nb
            self._last_net_t = now

    def rebuild_ui(self, L):
        self.ui_sys, self.ui_vit = build_values(self, L)


def build_values(info, L):
    vw = max(6, L.panel_w - 16)
    srows = []
    vrows = []

    def add(rows, label, segs):
        plain = "".join(t for t, _ in segs)
        if disp_width(plain) > vw:
            plain = clip(plain, vw)
            segs = [(plain, C_VALUE)]
        rows.append((label, segs, plain))

    add(srows, "OS", [(info.os_name + " ", C_VALUE), (info.arch, C_CYAN)])
    add(srows, "KERNEL", [(info.kernel, C_VALUE)])
    add(srows, "UPTIME", [(info.f_uptime, C_VALUE)])
    if info.pkg.isdigit():
        add(srows, "PACKAGES", [(info.pkg, C_VALUE), ("  (pacman)", C_DIM)])
    else:
        add(srows, "PACKAGES", [(info.pkg, C_DIM)])
    add(srows, "CPU", [(info.cpu, C_VALUE)])
    add(srows, "GPU", [(info.gpu, C_VALUE)])
    if info.shell_ver:
        add(srows, "SHELL", [(info.shell_name + " ", C_VALUE), (info.shell_ver, C_DIM)])
    else:
        add(srows, "SHELL", [(info.shell_name, C_VALUE)])
    hostval = info.hostname + " • " + info.user
    if info.nick and info.nick != info.user:
        hostval += " (✦ %s)" % info.nick
    add(srows, "HOST", [(hostval, C_VALUE)])

    _cp = getattr(info, "cpu_pct", 0.0)
    add(vrows, "CPU", [(spark(getattr(info, "hist_cpu", []), 14), pct_color(max(1.0, _cp))),
                       (" %3.0f%%" % _cp, pct_color(max(1.0, _cp)))])
    if info.mem:
        ug, tg, pct = info.mem
        ug, tg = ug / 1048576.0, tg / 1048576.0
        if vw >= 26:
            bp, bs, bc = micro_bar(pct, 10)
            add(vrows, "MEMORY",
                [("%.1f" % ug, C_VALUE), ("/", C_DIM), (("%.1fG " % tg), C_VALUE)] + bs + [(" %.0f%%" % pct, bc)])
        else:
            add(vrows, "MEMORY", [("%.1f/%.1fG %.0f%%" % (ug, tg, pct), C_VALUE)])
    else:
        add(vrows, "MEMORY", [("N/A", C_DIM)])

    if info.disk:
        ug, tg, pct = info.disk
        if vw >= 26:
            bp, bs, bc = micro_bar(pct, 10)
            add(vrows, "DISK",
                [("%.0f" % ug, C_VALUE), ("/", C_DIM), (("%.0fG " % tg), C_VALUE)] + bs + [(" %.0f%%" % pct, bc)])
        else:
            add(vrows, "DISK", [("%.0f/%.0fG %.0f%%" % (ug, tg, pct), C_VALUE)])
    else:
        add(vrows, "DISK", [("N/A", C_DIM)])

    hcol = C_FUCHSIA if info.hypr != "N/A" else C_SLATE
    wsegs = [("  ● ", C_CYAN), ("WAYLAND", C_SLATE)] if info.wayland == "ACTIVE" else []
    add(vrows, "HYPRLAND", [("● ", hcol), (info.hypr, C_VALUE)] + wsegs)
    add(vrows, "KITTY", [(info.kitty, C_VALUE)])

    if info.temp is not None:
        tc = info.temp
        col = C_CYAN if tc < 60 else (C_GOLD if tc < 78 else C_RED)
        add(vrows, "TEMP", [("%.0f°C" % tc, col)])
    else:
        add(vrows, "TEMP", [("N/A", C_DIM)])

    if info.bat:
        cap, st = info.bat
        if st == "AC":
            add(vrows, "BATTERY", [("● ", C_CYAN), ("AC POWERED", C_VALUE), ("  •  no battery", C_DIM)])
        else:
            col = C_CYAN if (st.lower().startswith("charg") or cap > 25) else C_RED
            add(vrows, "BATTERY", [("%d%% " % cap, col), (st.upper(), C_DIM)])
    else:
        add(vrows, "BATTERY", [("N/A", C_DIM)])

    add(vrows, "AUDIO", [(info.audio, C_VALUE)])
    return srows, vrows

# ───────────────────────────── fun data: memes & greets ────────────────────

MEMES = (
    ("Bug? Nahi bhai — wo FEATURE hai 😎", "HI"),
    ("It works on my machine ¯\\_(ツ)_/¯", "EN"),
    ("Kaj shesh? Nah… ekta aur commit 💀", "BN"),
    ("99 little bugs… patch karo… 127 little bugs 🎵", "HINGLISH"),
    ("sudo make me a sandwich 🥪", "EN"),
    ("Chai > Coffee. Ye final hai ☕", "HI"),
    ("Tumi ekdom pro coder! Bhalo basho 💻", "BN"),
    ("Keyboard pe dance jab saare tests pass 🕺", "HI"),
    ("My code doesn't have bugs. It develops random features.", "EN"),
    ("Amar WiFi, amar niyom 📶", "BN"),
    ("Lofi + terminal = 10x productivity 🎧", "EN"),
    ("rm -rf feelings/ 💔 (joke hi joke!)", "HINGLISH"),
    ("Segmentation fault → chai break, phir dekhenge ☕", "HINGLISH"),
    ("Bhai ne Friday ko deploy kar diya 💀", "HI"),
    ("Ek bar aur pip install karo, ho jayega 🤞", "HINGLISH"),
    ("Shob thik hoye jabe — git push --force 🔥", "BN"),
    ("404: motivation not found… chai laao ☕", "EN"),
    ("Tumse na ho payega… bina coffee ke ☕", "HINGLISH"),
    ("Ei code ta ager bar o kaj koreni, aj o korbe na 🙃", "BN"),
    ("Debugging: detective in a crime movie where you are also the murderer 🔍", "EN"),
    ("Kal se pakka diet… aur pakka side project ⏰", "HINGLISH"),
    ("Nokia 1100 > smartphone battery. Change my mind 🔋", "HI"),
    ("Mama ekta stackoverflow link pathao 🙏", "BN"),
    ("Chhota sa kaam hai — famous last words, 3 din baad bhi chal raha", "HINGLISH"),
    ("Compiling… chai_break = True ☕", "EN"),
    ("Mom: beta kya karte ho? Main: computer pe kaam 👨‍💻", "HI"),
    ("Swap off kore chalao bole chilo… ekhon RAM e swap 🐑", "BN"),
    ("git commit -m 'final' → 14th 'final' ✅", "EN"),
    ("4GB RSS khaya jachche, chhoto koro please 🙏", "BN"),
    ("Production me test karte hain, kya hoga? 💥", "HINGLISH"),
    ("Sleep? I don't know her. — every student dev 🌙", "EN"),
    ("Roz subah: aaj focused rahunga. Roz raat: 3am YouTube 📺", "HI"),
    ("T-Rex er haath chhoto, tabhi type korte pare na 🦖", "BN"),
    ("Sirf 5 minute bole neovim config e dhuke gechi 🕐", "HINGLISH"),
    ("Works on Arch (btw) ✨", "EN"),
    ("Laptop fan: airplane mode ✈️ — RTX garam ho gayi", "HINGLISH"),
    ("Ek diner jonnoi hyprland config bhulbo na 😤", "BN"),
    ("Bas aakhri update, phir so jaunga (3:47 AM)", "HI"),
    ("Copy-paste is not cheating, it's code reuse ♻️", "EN"),
    ("Load bearing npm install — touch it and everything breaks", "EN"),
    ("Chhaap na — undo kora jabe (hopefully) 😬", "BN"),
    ("maa kasam production me direct push nahi karunga 🫡", "HINGLISH"),
    ("No code is the best code. Aaj kuch nahi likha. Productive ✅", "EN"),
    ("WiFi chole geche, mon bhi broke 📡💔", "BN"),
    ("Pani piyo, stretch maro — doctor's order 💧", "HI"),
    ("Enna code uh, evlo bug uh 🐞", "TA"),
    ("Compile aana sandhosham, run aana thalaivali 💃", "TA"),
    ("Código heredado = caja de sorpresas 🎁", "ES"),
    ("Funciona en mi máquina, te lo juro 🤷", "ES"),
)

LANG_TAGS = {"en": ("EN",), "hi": ("HI", "HINGLISH"), "bn": ("BN", "HINGLISH"),
             "ta": ("TA",), "es": ("ES",)}

LANGS = ("en", "hi", "bn", "ta", "es")
LANG_NAMES = {"en": "English", "hi": "हिन्दी / Hinglish", "bn": "বাংলা / Banglish",
              "ta": "தமிழ் / Tamil", "es": "Español"}

I18N = {
    "en": {
        "g_night": "good night 🌙", "g_morning": "good morning ☀",
        "g_afternoon": "good afternoon", "g_evening": "good evening 🌆",
        "hello": "hello cutie,",
        "seed1": "▸ CUTIE OS {v} — {e} ✦ live shell attached",
        "seed2": "▸ namaste {n}!  type {t} for the toolkit • {h} for details",
        "seed3": "▸ every command works • {b} runs a real tty (sudo, vim, htop…) • CTRL+C kills jobs",
        "hint": "↑↓ • CTRL+R fuzzy • TAB • CTRL+C kill • !cmd sudo • dash • ask (AI) • typing • tetris • 2048 • tools → {n}",
        "name_saved": "✦ saved! from now on you are:",
        "name_prompt": "  type your name + ENTER (empty cancels, '-' clears):",
        "name_now": "  name now »", "name_cancel": "  (cancelled)",
        "name_cleared": "✦ name cleared — back to {n}",
        "lang_set": "✦ language » {l}",
        "intro_set": "✦ intro » {x}  (saved — next launch shows it)",
        "help_foot": "↑↓ / w s move • pgup pgdn page • / filter • enter run • q close",
        "meme_none": "no memes for this lang — try: meme all",
        "status": ("✦ CUTIE CORE ONLINE", "◆ {n} TOOLS ARMED", "● EVERYTHING IS PURRING",
                   "✦ EVERY CMD WORKS — TRY !SUDO", "◆ SYSTEM NOMINAL", "● HELLO CUTIE ♡"),
    },
    "hi": {
        "g_night": "shubh ratri 🌙", "g_morning": "shubh prabhat ☀",
        "g_afternoon": "shubh dopahar", "g_evening": "shubh sandhya 🌆",
        "hello": "namaste cutie,",
        "seed1": "▸ CUTIE OS {v} — {e} ✦ live shell jud gaya",
        "seed2": "▸ namaste {n}!  {t} likho toolkit ke liye • {h} details ke liye",
        "seed3": "▸ har command chalegi • {b} real tty kholta hai (sudo, vim, htop…) • CTRL+C job kill",
        "hint": "↑↓ history   TAB complete   PGUP/PGDN scroll   CTRL+C job kill   !cmd → real tty (sudo!)   tools → {n} tools   help",
        "name_saved": "✦ save ho gaya! ab se tum ho:",
        "name_prompt": "  naya naam likho + ENTER (khaali = cancel, '-' = clear):",
        "name_now": "  naam abhi »", "name_cancel": "  (cancel)",
        "name_cleared": "✦ naam clear — wapas {n}",
        "lang_set": "✦ bhasha » {l}",
        "intro_set": "✦ intro » {x}  (save — agli baar dikhega)",
        "help_foot": "↑↓ / w s chalo • pgup pgdn page • / filter • enter chalao • q band",
        "meme_none": "is bhasha me meme nahi — try: meme all",
        "status": ("✦ CUTIE CORE ONLINE", "◆ {n} TOOLS READY", "● SAB BADHIYA CHAL RAHA",
                   "✦ SUDO BHI CHALEGA — !LIKHKE DEKHO", "◆ SYSTEM MAST HAI", "● NAMASTE CUTIE ♡"),
    },
    "bn": {
        "g_night": "shubho nishith 🌙", "g_morning": "shuprobhat ☀",
        "g_afternoon": "shubho oporahnho", "g_evening": "shubho shondha 🌆",
        "hello": "nomoshkar cutie,",
        "seed1": "▸ CUTIE OS {v} — {e} ✦ live shell connected",
        "seed2": "▸ nomoshkar {n}!  {t} likho toolkit er jonno • {h} details er jonno",
        "seed3": "▸ shob command cholbe • {b} real tty khulbe (sudo, vim, htop…) • CTRL+C job kill",
        "hint": "↑↓ history   TAB complete   PGUP/PGDN scroll   CTRL+C job kill   !cmd → real tty (sudo!)   tools → {n} tools   help",
        "name_saved": "✦ save hoye geche! ekhon tumi:",
        "name_prompt": "  notun naam likho + ENTER (khaali = cancel, '-' = clear):",
        "name_now": "  naam ekhon »", "name_cancel": "  (cancel)",
        "name_cleared": "✦ naam clear — abar {n}",
        "lang_set": "✦ bhasha » {l}",
        "intro_set": "✦ intro » {x}  (save — porer bar dekhbe)",
        "help_foot": "↑↓ / w s cholo • pgup pgdn page • / filter • enter chalao • q bondho",
        "meme_none": "ei bhashay meme nei — try: meme all",
        "status": ("✦ CUTIE CORE ONLINE", "◆ {n} TOOLS READY", "● SHOB THIK ACHHE",
                   "✦ SUDO O CHOLBE — !LEKHO", "◆ SYSTEM SHANTI", "● NOMOSHKAR CUTIE ♡"),
    },
    "ta": {
        "g_night": "iravu vanakkam 🌙", "g_morning": "kaalai vanakkam ☀",
        "g_afternoon": "madhiya vanakkam", "g_evening": "maalai vanakkam 🌆",
        "hello": "vanakkam cutie,",
    },
    "es": {
        "g_night": "buenas noches 🌙", "g_morning": "buenos días ☀",
        "g_afternoon": "buenas tardes", "g_evening": "buenas noches 🌆",
        "hello": "¡hola cutie!",
    },
}

COMPLIMENTS = (
    "aaj ka output ekdum damdaar hoga 🚀",
    "tumi sudhu cutie nahi — SUPREME cutie ♡",
    "kernel tumpe garv karega ✦",
    "tumi ekdom shera! ei bashiye jao 🔥",
    "RAM bhi tumhare liye extra khush hai",
    "aaj kuch manifest hone wala hai ✨",
    "tobuo tumi parbe! bhalo theko 💪",
    "uptime tumhare confidence jaisa — solid",
    "you're the 1% battery that never dies 🔋",
    "tera code itna clean — linter bhi fan ho gaya",
    "tor code er smell ekdom fresh 🌸",
    "saamne wala bug already resign de diya 😎",
    "aaj compiler bhi warn nahi karega (dREAM)",
    "stack overflow ek din tumhare fan page banayega",
)

COMPLIMENTS = (
    "aaj ka output ekdum damdaar hoga 🚀",
    "tumi sudhu cutie nahi — SUPREME cutie ♡",
    "kernel tumpe garv karega ✦",
    "tumi ekdom shera! ei bashiye jao 🔥",
    "RAM bhi tumhare liye extra khush hai",
    "aaj kuch manifest hone wala hai ✨",
    "tobuo tumi parbe! bhalo theko 💪",
    "uptime tumhare confidence jaisa — solid",
)

# ───────────────────────────── toolkit: helpers ────────────────────────────


class Tool:
    __slots__ = ("name", "alts", "desc", "cat", "fn")

    def __init__(self, name, alts, desc, cat, fn):
        self.name = name
        self.alts = alts
        self.desc = desc
        self.cat = cat
        self.fn = fn

# ───────────────────────────── toolkit: tools ──────────────────────────────


def tool_tools(app, args):
    T = app.term
    T.head("✦ CUTIE TOOLKIT — %d REAL TOOLS ✦" % len(TOOLS))
    n = 1
    last = None
    for tl in TOOLS:
        if tl.cat != last:
            last = tl.cat
            T.push([("── " + last.upper() + " ", C_FUCHSIA), ("─" * 30, C_SLATE)])
        T.push([("  %2d) " % n, C_SLATE), (tl.name.ljust(10), C_CYAN), (tl.desc, C_OUT)])
        n += 1
    T.dim("  run any tool by name — e.g.  weather kolkata • pkg big • speed • vol +10")
    T.dim("  dev: F1 • run • code   |   pro: music • pet • ach   |   style: theme • lang")


def tool_help(app, args):
    app.open_help()


def tool_sysinfo(app, args):
    T = app.term
    si = app.info
    app.flush_frame()
    si.refresh_dynamic()
    T.head("◆ FULL SYSTEM REPORT — CUTIE DEEP SCAN ✦")
    rows = []
    rows.append(_kv("OS", si.os_name + " " + si.arch))
    host = si.hostname + " • " + si.user + ((" ✦ " + si.nick) if si.nick else "")
    rows.append(_kv("HOST", host))
    rows.append(_kv("KERNEL", platform.release()))
    rows.append(_kv("UPTIME", si.f_uptime))
    rows.append(_kv("SHELL", (si.shell_name + " " + si.shell_ver).strip()))
    rows.append(_kv("DE/WM", de_info() or "N/A"))
    th = theme_info()
    if th:
        rows.append(_kv("THEME", th))
    cur = cursor_info()
    if cur:
        rows.append(_kv("CURSOR", cur))
    res = resolution_info()
    if res:
        rows.append(_kv("RES", res))
    board = (dmi("board_vendor") or "").strip()
    bname = (dmi("board_name") or "").strip()
    if board:
        rows.append(_kv("BOARD", (board + " " + bname).strip()))
    bios = (dmi("bios_vendor") or "").strip()
    bver = (dmi("bios_version") or "").strip()
    if bios:
        rows.append(_kv("BIOS", (bios + " " + bver).strip()))
    cores, threads = cpu_cores()
    freq = cpu_freq()
    extra = []
    if cores:
        extra.append("%d cores" % cores)
    if threads:
        extra.append("%d threads" % threads)
    if freq:
        extra.append("%.2f GHz" % (freq / 1000.0))
    rows.append(_kv("CPU", si.cpu, " • ".join(extra) or None))
    rows.append(_kv("GPU", si.gpu, ("VRAM " + vram_info()) if vram_info() else None))
    if si.mem:
        ug, tg, pct = si.mem
        rows.append(_kv("MEMORY", "%.2f / %.2f GiB (%.0f%%)" % (ug / 1048576.0, tg / 1048576.0, pct)))
    sw = swap_info()
    if sw and sw[1] > 0:
        rows.append(_kv("SWAP", "%.1f / %.1f GiB used" % (sw[0] / 1048576.0, sw[1] / 1048576.0)))
    if si.disk:
        rows.append(_kv("DISK /", "%.0fG / %.0fG (%.0f%%)" % si.disk))
    rows.append(_kv("PACKAGES", si.pkg))
    pcount = proc_count()
    la = os.getloadavg()
    rows.append(_kv("LOAD", "%.2f %.2f %.2f" % la, ("%d procs" % pcount) if pcount else None))
    if si.temp is not None:
        rows.append(_kv("TEMP", "%.0f°C" % si.temp))
    if si.bat:
        cap, st = si.bat
        rows.append(_kv("BATTERY", (("%d%% " % cap) if isinstance(cap, int) else "") + str(st).upper()))
    rows.append(_kv("AUDIO", si.audio))
    rows.append(_kv("HYPRLAND", si.hypr))
    rows.append(_kv("KITTY", si.kitty))
    T.push_lines(rows)
    T.push([("", C_OUT)])
    T.push([("  ◆ NETWORK", C_FUCHSIA)])
    for n, typ, st, ip in iface_list():
        if typ == "loop":
            continue
        T.push([("  " + n.ljust(16), C_DIM), (st.upper().ljust(7), C_SLATE), (ip or "no ip", C_VALUE)])
    pub = public_ip(4)
    T.push([("  public ip".ljust(17), C_LABEL), ("» ", C_ARROW), (pub if pub else "N/A (offline)", C_VALUE)])


def tool_uptime(app, args):
    T = app.term
    u = uptime_secs()
    if u is not None:
        T.push(_kv("UPTIME", fmt_uptime(u)))
    T.push(_kv("SESSION", fmt_uptime(time.monotonic() - app.t_start)))


def tool_fps(app, args):
    app.term.push(_kv("FPS", "%.0f  (target 60)" % app.fps))


def tool_reload(app, args):
    app.info.refresh_static()
    app.info.refresh_dynamic()
    app.info.rebuild_ui(app.layout)
    app.term.push([("  ✦ system info re-scanned", C_CYAN)])


def tool_procs(app, args):
    T = app.term
    by = "mem" if args and args[0].lower().startswith("mem") else "cpu"
    sort = "-pmem" if by == "mem" else "-pcpu"
    out = _cap("ps -eo user:20,pid,pcpu,pmem,comm --sort=" + sort + " 2>/dev/null | head -n 13", 6)
    T.head("◆ TOP PROCESSES — by " + by.upper())
    T.push([("  USER".ljust(22), C_LABEL), ("PID".ljust(8), C_LABEL), ("%CPU".ljust(7), C_LABEL), ("%MEM".ljust(7), C_LABEL), ("COMMAND", C_LABEL)])
    for ln in out.splitlines()[1:13]:
        p = ln.split(None, 4)
        if len(p) < 5:
            continue
        u, pid, c, m, name = p[0], p[1], p[2], p[3], p[4]
        try:
            cf, mf = float(c), float(m)
            cc = pct_color(cf * 10.0)
            mc = pct_color(mf * 10.0)
            c = "%.1f" % cf
            m = "%.1f" % mf
        except Exception:
            cc = mc = C_VALUE
        T.push([("  " + u.ljust(20), C_DIM), (pid.ljust(8), C_SLATE), (c.ljust(7), cc), (m.ljust(7), mc), (name[:34], C_VALUE)])


def tool_temp(app, args):
    T = app.term
    T.head("◆ TEMPERATURES — hwmon sensors")
    shown = False
    try:
        chips = sorted(os.listdir("/sys/class/hwmon"))
    except Exception:
        chips = []
    for hw in chips:
        base = "/sys/class/hwmon/" + hw
        try:
            with open(base + "/name") as f:
                name = f.read().strip()
        except Exception:
            name = hw
        temps = []
        try:
            files = sorted(os.listdir(base))
        except Exception:
            files = []
        for fn in files:
            if fn.startswith("temp") and fn.endswith("_input"):
                lf = base + "/" + fn.replace("_input", "_label")
                try:
                    with open(lf) as f:
                        label = f.read().strip()
                except Exception:
                    label = fn.replace("_input", "")
                try:
                    with open(base + "/" + fn) as f:
                        c = int(f.read().strip()) / 1000.0
                except Exception:
                    continue
                if -20 < c < 150:
                    temps.append((label, c))
        if temps:
            shown = True
            T.push([("  " + (name or hw).ljust(14), C_CYAN), ("(" + hw + ")", C_SLATE)])
            for lb, c in temps:
                col = C_CYAN if c < 55 else (C_GOLD if c < 75 else C_RED)
                T.push([("    " + lb.ljust(16), C_DIM), ("%.1f°C" % c, col)])
    if not shown:
        try:
            zones = sorted(os.listdir("/sys/class/thermal"))
        except Exception:
            zones = []
        for z in zones:
            if not z.startswith("thermal_zone"):
                continue
            try:
                with open("/sys/class/thermal/" + z + "/type") as f:
                    typ = f.read().strip()
                with open("/sys/class/thermal/" + z + "/temp") as f:
                    c = int(f.read().strip()) / 1000.0
            except Exception:
                continue
            shown = True
            T.push([("  " + (typ or z).ljust(20), C_DIM), ("%.1f°C" % c, C_VALUE)])
    if not shown:
        T.dim("  no temperature sensors found")


def tool_disk(app, args):
    T = app.term
    T.head("◆ DISKS — df -h (real filesystems)")
    out = _cap("df -hP -x tmpfs -x devtmpfs -x efivarfs 2>/dev/null", 5)
    for i, ln in enumerate(out.splitlines()):
        if not ln.strip():
            continue
        if i == 0:
            T.push([(ln[:100], C_LABEL)])
        else:
            p = ln.split(None, 5)
            if len(p) >= 6:
                try:
                    pct = float(p[4].rstrip("%"))
                except Exception:
                    pct = 0
                T.push([("  " + p[0].ljust(18), C_DIM), (p[1].rjust(6), C_VALUE),
                        (p[2].rjust(6), C_VALUE), (p[3].rjust(6), C_DIM),
                        (" " + p[4].rjust(4), pct_color(pct)), ("  " + p[5][:22], C_SLATE)])
    T.push([("", C_OUT)])
    T.head("◆ BLOCK DEVICES — lsblk")
    out = _cap("lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT 2>/dev/null", 5)
    for ln in out.splitlines()[:18]:
        col = C_LABEL if ln.startswith("NAME") else C_OUT
        T.push([(ln.rstrip()[:100], col)])


def tool_bat(app, args):
    T = app.term
    T.head("◆ BATTERY & POWER")
    base = "/sys/class/power_supply"
    try:
        entries = sorted(os.listdir(base))
    except Exception:
        entries = []
    found = False
    for e in entries:
        p = base + "/" + e
        try:
            with open(p + "/type") as f:
                typ = f.read().strip()
        except Exception:
            continue
        found = True
        kv = {}
        for k in ("capacity", "status", "cycle_count", "voltage_now", "energy_now",
                  "energy_full", "energy_full_design", "power_now", "online"):
            try:
                with open(p + "/" + k) as f:
                    kv[k] = f.read().strip()
            except Exception:
                pass
        T.push([("  " + e.ljust(10), C_CYAN), ("(" + typ + ")", C_DIM)])
        if "capacity" in kv:
            try:
                cap = int(kv["capacity"])
            except Exception:
                cap = 0
            st = kv.get("status", "?")
            bp, bs, bc = micro_bar(cap, 20)
            T.push([("   charge  ", C_LABEL), ("» ", C_ARROW)] + bs + [(" %d%% " % cap, bc), (st.upper(), C_DIM)])
            if kv.get("energy_full") and kv.get("energy_full_design"):
                try:
                    h = float(kv["energy_full"]) / float(kv["energy_full_design"]) * 100.0
                    T.push(_kv("HEALTH", "%.0f%%" % h, ("%s cycles" % kv["cycle_count"]) if kv.get("cycle_count") else None))
                except Exception:
                    pass
            try:
                if kv.get("power_now") and kv.get("energy_now"):
                    w = float(kv["power_now"]) / 1e6
                    en = float(kv["energy_now"]) / 1e6
                    if w > 0.1:
                        hrs = en / w if not st.lower().startswith("charg") else (float(kv["energy_full"]) / 1e6 - en) / w
                        T.push(_kv("POWER", "%.1f W" % w, "≈ %dh %dm to %s" % (int(hrs), int((hrs % 1) * 60), "full" if st.lower().startswith("charg") else "empty")))
            except Exception:
                pass
        if kv.get("online"):
            T.push([("   AC      ", C_LABEL), ("» ", C_ARROW), ("ONLINE ⚡" if kv["online"] == "1" else "offline", C_VALUE)])
    if not found:
        T.dim("  no battery / power_supply info (desktop?)")


def tool_gpu(app, args):
    T = app.term
    out = run_cmd(["nvidia-smi"], 5)
    if out.strip():
        T.head("◆ NVIDIA-SMI")
        for ln in out.splitlines():
            T.push([(ln.rstrip()[:100], C_OUT)])
        return
    out = _cap("lspci 2>/dev/null | grep -Ei 'vga|3d|display'", 4)
    T.head("◆ GPU (lspci — no nvidia-smi)")
    if out.strip():
        for ln in out.splitlines():
            T.push([(ln.strip(), C_VALUE)])
    else:
        T.dim("  no gpu info found")


def tool_pkg(app, args):
    T = app.term
    if args and args[0].lower() in ("big", "large", "size", "top"):
        return tool_pkg_big(app, args[1:])
    T.head("◆ PACKAGES (pacman)")

    def q(flag):
        out = run_cmd(["pacman", "-Q" + flag], 12)
        return sum(1 for _ in out.splitlines()) if out else None
    tot = q("q")
    if not tot:
        T.dim("  pacman not available")
        return
    T.push(_kv("TOTAL", str(tot)))
    exp = q("e")
    if exp is not None:
        T.push(_kv("EXPLICIT", str(exp)))
    deps = q("d")
    if deps is not None:
        T.push(_kv("AS DEPS", str(deps)))
    foreign = q("m")
    if foreign is not None:
        T.push(_kv("FOREIGN/AUR", str(foreign)))
    T.push(_kv("BIGGEST", "run: pkg big", "top 20 by installed size"))


def tool_pkg_big(app, args):
    T = app.term
    T.head("◆ TOP 20 PACKAGES — installed size (pacman -Qi)")
    app.flush_frame()
    out = _cap("pacman -Qi", 25)
    pkgs = []
    name = None
    for ln in out.splitlines():
        if ln.startswith("Name") and ":" in ln:
            name = ln.split(":", 1)[1].strip()
        elif "Installed Size" in ln and name:
            m = re.search(r":\s*([\d.]+)\s*(\w+)", ln)
            if m:
                f = float(m.group(1))
                u = m.group(2).lower()
                mb = {"b": f / 1048576.0, "kib": f / 1024.0, "mib": f, "gib": f * 1024.0}.get(u)
                if mb:
                    pkgs.append((mb, name))
            name = None
    if not pkgs:
        T.dim("  could not parse pacman -Qi")
        return
    pkgs.sort(reverse=True)
    top = pkgs[:20]
    mx = top[0][0] or 1.0
    w = 14
    for i, (mb, nm) in enumerate(top, 1):
        filled = int(round(mb / mx * w))
        T.push([("  %2d " % i, C_SLATE), (nm[:26].ljust(26), C_VALUE),
                ("█" * filled, grad(i / 20.0)), ("░" * (w - filled), C_BAR_EMPTY),
                (" %8.1f MiB" % mb, C_LABEL)])
    T.push([("  top-20 total: ", C_DIM), ("%.1f MiB" % sum(p[0] for p in top), C_VALUE)])


def _detect_pkg_mgr():
    for m in ("pacman", "apt", "brew", "dnf", "zypper", "apk", "pkg", "winget"):
        if shutil.which(m):
            return m
    return None


def tool_pkginfo(app, args):
    T = app.term
    if not args:
        T.dim("  usage: pkginfo <pkg>")
        return
    mgr = _detect_pkg_mgr()
    if not mgr:
        T.dim("  no package manager found")
        return
    if mgr == "pacman":
        out = run_cmd(["pacman", "-Qi"] + args, 8) or run_cmd(["pacman", "-Si"] + args, 8)
    elif mgr == "apt":
        out = run_cmd(["apt", "show"] + args, 8)
    elif mgr == "brew":
        out = run_cmd(["brew", "info"] + args, 8)
    elif mgr == "dnf":
        out = run_cmd(["dnf", "info"] + args, 8)
    elif mgr == "zypper":
        out = run_cmd(["zypper", "info"] + args, 8)
    elif mgr == "apk":
        out = run_cmd(["apk", "info", "-d"] + args, 8)
    elif mgr == "pkg":
        out = run_cmd(["pkg", "show"] + args, 8)
    elif mgr == "winget":
        out = run_cmd(["winget", "show"] + args, 8)
    else:
        out = ""
    if not out.strip():
        T.push([("  ✗ package not found: ", C_RED), (" ".join(args), C_VALUE)])
        return
    T.head("◆ PACKAGE — " + args[0] + " (" + mgr + ")")
    keep = ("Name", "Package", "Version", "Description", "Architecture", "URL", "Homepage",
            "Licenses", "License", "Depends On", "Depends", "Required By", "Install Reason",
            "Installed Size", "Size", "Packager", "Maintainer")
    for blk in out.split("\n\n"):
        for ln in blk.splitlines():
            if ":" not in ln:
                continue
            k, v = ln.split(":", 1)
            if k.strip() in keep:
                T.push([("  " + k.strip().ljust(15), C_LABEL), ("» ", C_ARROW), (v.strip()[:80] or "—", C_VALUE)])


def tool_search(app, args):
    T = app.term
    if not args:
        T.dim("  usage: search <name>")
        return
    mgr = _detect_pkg_mgr()
    if not mgr:
        T.dim("  no package manager found")
        return
    app.flush_frame()
    if mgr == "pacman":
        cmd = ["pacman", "-Ss"] + args
    elif mgr == "apt":
        cmd = ["apt", "search"] + args
    elif mgr == "brew":
        cmd = ["brew", "search"] + args
    elif mgr == "dnf":
        cmd = ["dnf", "search"] + args
    elif mgr == "zypper":
        cmd = ["zypper", "search"] + args
    elif mgr == "apk":
        cmd = ["apk", "search", "-v"] + args
    elif mgr == "pkg":
        cmd = ["pkg", "search"] + args
    elif mgr == "winget":
        cmd = ["winget", "search"] + args
    else:
        cmd = [mgr, "search"] + args
    out = run_cmd(cmd, 10)
    if not out.strip():
        T.dim("  no results found for " + " ".join(args))
        return
    T.head("◆ SEARCH — %s %s" % (mgr, " ".join(args)))
    n = 0
    for ln in out.splitlines():
        if ln.strip():
            n += 1
            if ln.startswith(" ") or ln.startswith("\t"):
                T.push([(ln.rstrip()[:110], C_OUT)])
            else:
                T.push([("  " + ln.strip()[:105], C_CYAN)])
            if n > 30:
                T.dim("  … (more results exist)")
                break


def tool_update(app, args):
    T = app.term
    mgr = _detect_pkg_mgr()
    if not mgr:
        T.dim("  no package manager found (pacman/apt/brew/dnf/zypper/apk/pkg/winget)")
        return
    T.push([("  ⏫ system update via %s — enter password if prompted" % mgr, C_DIM)])
    app.flush_frame()
    yes = ("--yes" in args or "-y" in args)
    if mgr == "pacman":
        cmd = ["sudo", "pacman", "-Syu"] + (["--noconfirm"] if yes else [])
    elif mgr == "apt":
        cmd = [app.shell, "-c", "sudo apt update && sudo apt" + (" -y" if yes else "") + " upgrade"]
    elif mgr == "brew":
        cmd = [app.shell, "-c", "brew update && brew upgrade"]
    elif mgr == "dnf":
        cmd = ["sudo", "dnf", "upgrade"] + (["-y"] if yes else [])
    elif mgr == "zypper":
        cmd = ["sudo", "zypper", "update"] + (["-y"] if yes else [])
    elif mgr == "apk":
        cmd = [app.shell, "-c", "sudo apk update && sudo apk upgrade"]
    elif mgr == "pkg":
        cmd = ["pkg", "upgrade"] + (["-y"] if yes else [])
    elif mgr == "winget":
        cmd = ["winget", "upgrade", "--all"]
    else:
        cmd = ["sudo", mgr, "upgrade"]
    app.run_pty(cmd)


def tool_install(app, args):
    pkgs = [a for a in args if a not in ("--yes", "-y")]
    if not pkgs:
        app.term.dim("  usage: install <pkg...>   e.g.  install btop")
        return
    mgr = _detect_pkg_mgr()
    if not mgr:
        app.term.dim("  no package manager found")
        return
    app.flush_frame()
    if mgr == "pacman":
        cmd = ["sudo", "pacman", "-S"] + pkgs
    elif mgr == "apt":
        cmd = ["sudo", "apt", "install"] + pkgs
    elif mgr == "brew":
        cmd = ["brew", "install"] + pkgs
    elif mgr == "dnf":
        cmd = ["sudo", "dnf", "install"] + pkgs
    elif mgr == "zypper":
        cmd = ["sudo", "zypper", "install"] + pkgs
    elif mgr == "apk":
        cmd = ["sudo", "apk", "add"] + pkgs
    elif mgr == "pkg":
        cmd = ["pkg", "install"] + pkgs
    elif mgr == "winget":
        cmd = ["winget", "install"] + pkgs
    else:
        cmd = ["sudo", mgr, "install"] + pkgs
    app.run_pty(cmd)


def tool_remove(app, args):
    pkgs = [a for a in args if a not in ("--yes", "-y")]
    if not pkgs:
        app.term.dim("  usage: remove <pkg...>")
        return
    mgr = _detect_pkg_mgr()
    if not mgr:
        app.term.dim("  no package manager found")
        return
    app.flush_frame()
    if mgr == "pacman":
        cmd = ["sudo", "pacman", "-Rns"] + pkgs
    elif mgr == "apt":
        cmd = ["sudo", "apt", "remove"] + pkgs
    elif mgr == "brew":
        cmd = ["brew", "uninstall"] + pkgs
    elif mgr == "dnf":
        cmd = ["sudo", "dnf", "remove"] + pkgs
    elif mgr == "zypper":
        cmd = ["sudo", "zypper", "remove"] + pkgs
    elif mgr == "apk":
        cmd = ["sudo", "apk", "del"] + pkgs
    elif mgr == "pkg":
        cmd = ["pkg", "uninstall"] + pkgs
    elif mgr == "winget":
        cmd = ["winget", "uninstall"] + pkgs
    else:
        cmd = ["sudo", mgr, "remove"] + pkgs
    app.run_pty(cmd)


def tool_journal(app, args):
    T = app.term
    T.head("◆ JOURNAL — errors this boot (prio ≤ 3)")
    app.flush_frame()
    out = _cap("journalctl -p 3 -b --no-pager 2>/dev/null | tail -n 22", 10)
    lines = [l for l in out.splitlines() if l.strip()]
    if not lines:
        T.dim("  ✦ no errors this boot (or no permission — try: !sudo journalctl -p 3 -b)")
        return
    for ln in lines:
        T.push([(ln[:110], C_OUT)])


def tool_ports(app, args):
    T = app.term
    T.head("◆ LISTENING PORTS — ss -tulpn")
    app.flush_frame()
    out = _cap("ss -tulpn 2>/dev/null", 6)
    lines = out.splitlines()
    if len(lines) < 2:
        T.dim("  ss not available")
        return
    T.push([(lines[0][:110], C_LABEL)])
    for ln in lines[1:26]:
        T.push([(ln[:110], C_OUT)])


def tool_net(app, args):
    T = app.term
    T.head("◆ NETWORK")
    app.flush_frame()
    for n, typ, st, ip in iface_list():
        mark = "●" if st == "up" else "○"
        col = C_CYAN if st == "up" else C_SLATE
        kind = {"wifi": "wifi", "eth": "eth ", "loop": "lo  "}.get(typ, "    ")
        T.push([("  %s " % mark, col), (n.ljust(16), C_VALUE), (kind + " ", C_DIM),
                (ip if ip else "no ip", C_VALUE if ip else C_DIM)])
    gw = first_line(_cap("ip route show default 2>/dev/null", 3))
    if gw:
        T.push(_kv("GATEWAY", gw))
    pub = public_ip(4)
    if pub:
        T.push(_kv("PUBLIC IP", pub))
    else:
        T.push(_kv("PUBLIC IP", "N/A", "offline / no net"))
    out = _cap("ping -c 1 -W 2 1.1.1.1 2>/dev/null", 5)
    m = re.search(r"time=([\d.]+)\s*ms", out)
    if m:
        T.push(_kv("PING 1.1.1.1", m.group(1) + " ms", "online ✓"))
    else:
        T.push(_kv("PING 1.1.1.1", "no reply", "offline?"))


def tool_weather(app, args):
    T = app.term
    loc = "+".join(args)
    if loc.lower() == "full":
        app.flush_frame()
        out = run_cmd(["curl", "-s", "--max-time", "8", "https://wttr.in/?0&T"], 10)
        if out.strip():
            for ln in out.splitlines()[:20]:
                T.push([(ln.rstrip()[:100], C_OUT)])
        else:
            T.dim("  weather N/A — offline?")
        return
    app.flush_frame()
    url = "https://wttr.in/" + loc + "?format=%l|%c|%t|%f|%h|%w"
    out = run_cmd(["curl", "-s", "--max-time", "6", url], 8)
    if out.strip():
        p = out.strip().split("|")
        rest = "  ".join(x.strip() for x in p[1:] if x.strip())
        T.push([("  weather » ", C_LABEL), (p[0].strip() + "  ", C_VALUE), (rest, C_CYAN)])
    else:
        T.push([("  weather » N/A — offline?", C_DIM)])


def tool_speed(app, args):
    T = app.term
    T.push([("  ⏱  testing download speed (up to ~14s)…", C_DIM)])
    app.flush_frame()
    url = "https://speed.cloudflare.com/__down?bytes=20000000"
    out = run_cmd(["curl", "-s", "-o", "/dev/null", "-w", "%{speed_download}",
                   "--max-time", "14", url], 16)
    try:
        bps = float(out.strip())
    except Exception:
        T.dim("  speed test failed — offline?")
        return
    mb = bps * 8 / 1e6
    if mb < 5:
        col, tag = C_RED, "dhistri 😩"
    elif mb < 20:
        col, tag = C_GOLD, "theek-thaak 👍"
    elif mb < 80:
        col, tag = C_CYAN, "badhiya ⚡"
    else:
        col, tag = C_FUCHSIA, "SUPREME 🚀"
    T.push([("  ↓ speed  ", C_LABEL)] + micro_bar(min(100.0, mb), 24)[1] +
           [(" %.1f Mbps " % mb, col), (tag, C_VALUE)])


def tool_notify(app, args):
    T = app.term
    msg = " ".join(args) if args else "cutie says hi ✦"
    if app.is_termux and shutil.which("termux-notification"):
        subprocess.run(["termux-notification", "--title", "✦ CUTIE", "--content", msg],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=6)
        T.push([("  sent » ", C_DIM), (msg, C_VALUE)])
        return
    if shutil.which("notify-send") is None:
        T.dim("  notify-send not found (sudo pacman -S libnotify)")
        return
    try:
        subprocess.run(["notify-send", "-a", "CUTIE OS", "✦ CUTIE", msg], timeout=4)
        T.push([("  sent » ", C_DIM), (msg, C_VALUE)])
    except Exception as e:
        T.push([("  ✗ notify failed: ", C_RED), (str(e)[:60], C_DIM)])


def tool_shot(app, args):
    T = app.term
    d = os.path.expanduser("~/Pictures")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        d = os.path.expanduser("~")
    path = os.path.join(d, "cutie-shot-%s.png" % time.strftime("%Y%m%d-%H%M%S"))
    grim = shutil.which("grim")
    slurp = shutil.which("slurp")
    hs = shutil.which("hyprshot")
    scrot = shutil.which("scrot")
    if grim and slurp:
        cmd = 'grim -g "$(slurp)" "%s"' % path
    elif grim:
        cmd = 'grim "%s"' % path
    elif hs:
        cmd = 'hyprshot -m output -o "%s"' % d
    elif scrot:
        cmd = 'scrot "%s"' % path
    else:
        T.dim("  no screenshot tool found (grim / hyprshot / scrot)")
        return
    T.push([("  capturing… (select a region if asked)", C_DIM)])
    app.flush_frame()
    _cap(cmd, 20)
    if os.path.exists(path):
        T.push([("  saved » ", C_CYAN), (path, C_GOLD)])
        if shutil.which("notify-send"):
            subprocess.run(["notify-send", "-a", "CUTIE OS", "✦ shot saved", path], timeout=4)
    else:
        T.dim("  shot cancelled / failed")


def tool_wall(app, args):
    T = app.term
    dirs = [os.path.expanduser(p) for p in
            ("~/Pictures/wallpapers", "~/Pictures/Wallpapers", "~/Pictures/wallpaper",
             "~/walls", "~/Pictures", "~/Images")]
    seen = set()
    files = []
    for d in dirs:
        if os.path.isdir(d) and d not in seen:
            seen.add(d)
            try:
                for f in sorted(os.listdir(d)):
                    if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
                        files.append(os.path.join(d, f))
            except Exception:
                pass
    if not files:
        T.dim("  no wallpapers found in ~/Pictures (+ ~/walls) — drop some there!")
        return
    T.head("◆ WALLPAPERS — %d found" % len(files))
    home = os.path.expanduser("~")
    for f in files[:18]:
        T.push([("  ▢ ", C_DIM), (f.replace(home, "~"), C_VALUE)])
    if len(files) > 18:
        T.dim("  … and %d more" % (len(files) - 18))


def tool_service(app, args):
    T = app.term
    if args:
        app.flush_frame()
        out = _cap("systemctl status %s --no-pager 2>&1 | head -n 14" % shlex.quote(args[0]), 6)
        T.head("◆ SERVICE — " + args[0])
        for ln in out.splitlines():
            T.push([(ln[:110], C_OUT)])
        return
    out = _cap("systemctl list-units --type=service --state=running --no-pager --plain 2>/dev/null | head -n 25", 6)
    T.head("◆ RUNNING SERVICES")
    for ln in out.splitlines()[:25]:
        T.push([(ln[:110], C_OUT)])


def tool_hypr(app, args):
    T = app.term
    if shutil.which("hyprctl") is None:
        T.dim("  hyprctl not available (not on Hyprland?)")
        return
    T.head("◆ HYPRLAND")
    T.push(_kv("VERSION", hyprland_version()))
    out = _cap("hyprctl activewindow -j 2>/dev/null", 3)
    try:
        j = json.loads(out or "{}")
        cls = j.get("class", "")
        ti = j.get("title", "")
        if cls:
            T.push(_kv("FOCUS", (cls + " — " + ti)[:60]))
    except Exception:
        pass
    out = _cap("hyprctl workspaces 2>/dev/null", 3)
    ws = [l.split()[0] for l in out.splitlines() if l.strip() and not l.startswith(" ")]
    if ws:
        T.push(_kv("WORKSPACES", " ".join(ws[:12])))
    out = _cap("hyprctl monitors 2>/dev/null", 3)
    mons = re.findall(r"Monitor ([^\s]+) \(id \d+\)", out)
    T.push(_kv("MONITORS", str(len(mons)) + (" — " + ", ".join(mons) if mons else "")))


def tool_monitors(app, args):
    T = app.term
    out = _cap("hyprctl monitors all 2>/dev/null", 4)
    if not out.strip():
        T.dim("  hyprctl not available")
        return
    T.head("◆ MONITORS — hyprctl")
    for ln in out.splitlines()[:30]:
        T.push([(ln.rstrip()[:110], C_OUT)])


def tool_binds(app, args):
    T = app.term
    out = _cap("hyprctl binds 2>/dev/null", 4)
    if not out.strip():
        T.dim("  hyprctl not available")
        return
    T.head("◆ HYPRLAND KEYBINDS")
    for ln in out.splitlines()[:48]:
        T.push([(ln.rstrip()[:110], C_OUT)])


def tool_audio(app, args):
    T = app.term
    out = run_cmd(["pactl", "info"], 3)
    T.head("◆ AUDIO")
    m = re.search(r"Server Name:\s*(.+)", out)
    if m:
        T.push(_kv("SERVER", m.group(1).strip()))
    m = re.search(r"Default Sink:\s*(.+)", out)
    if m:
        T.push(_kv("SINK", m.group(1).strip()[:40]))
    out = run_cmd(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], 3)
    mm = re.search(r"(\d+)%", out)
    mute = "yes" in run_cmd(["pactl", "get-sink-mute", "@DEFAULT_SINK@"], 2).lower()
    if mute:
        T.push([("  VOLUME       ", C_LABEL), ("» ", C_ARROW), ("MUTED", C_RED)])
    elif mm:
        p = int(mm.group(1))
        bp, bs, bc = micro_bar(p, 14)
        T.push([("  VOLUME       ", C_LABEL), ("» ", C_ARROW)] + bs + [(" %d%%" % p, bc)])


def tool_vol(app, args):
    T = app.term
    if shutil.which("pactl") is None:
        T.dim("  pactl not found")
        return
    if not args:
        return tool_audio(app, args)
    a = args[0]
    try:
        if a in ("mute", "m", "toggle"):
            run_cmd(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"], 2)
        elif a.startswith("+") or a.startswith("-"):
            run_cmd(["pactl", "set-sink-volume", "@DEFAULT_SINK@", a + "%"], 2)
        else:
            v = clamp(int(float(a.rstrip("%"))), 0, 150)
            run_cmd(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "%d%%" % v], 2)
    except Exception:
        T.dim("  usage: vol [0-150 | +10 | -10 | mute]")
        return
    out = run_cmd(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], 2)
    mm = re.search(r"(\d+)%", out)
    mute = "yes" in run_cmd(["pactl", "get-sink-mute", "@DEFAULT_SINK@"], 2).lower()
    if mute:
        T.push([("  volume » ", C_DIM), ("MUTED", C_RED)])
    elif mm:
        p = int(mm.group(1))
        T.push([("  volume » ", C_DIM)] + micro_bar(p, 16)[1] + [(" %d%%" % p, pct_color(p))])


def tool_bright(app, args):
    T = app.term
    if shutil.which("brightnessctl") is None:
        T.dim("  brightnessctl not found (sudo pacman -S brightnessctl)")
        return
    if args:
        a = args[0]
        if a.isdigit():
            a += "%"
        try:
            r = subprocess.run(["brightnessctl", "set", a], stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE, timeout=4)
        except Exception:
            r = None
        if r is None or r.returncode != 0:
            T.push([("  ✗ needs permission — try: ", C_RED), ("!sudo brightnessctl set " + a, C_GOLD)])
            return
    out = run_cmd(["brightnessctl", "info"], 3)
    m = re.search(r"\((\d+)%\)", out)
    if m:
        p = int(m.group(1))
        T.push([("  brightness ", C_LABEL), ("» ", C_ARROW)] + micro_bar(p, 16)[1] + [(" %d%%" % p, C_VALUE)])
    else:
        T.dim("  set ✓ (can't read level)")


_CALC_FUNCS = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
               "log": math.log, "log2": math.log2, "log10": math.log10,
               "floor": math.floor, "ceil": math.ceil, "abs": abs, "round": round,
               "pow": pow, "min": min, "max": max}
_CALC_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau}


def safe_calc(expr):
    node = ast.parse(expr, mode="eval")

    def check(n):
        if isinstance(n, ast.Expression):
            return check(n.body)
        if isinstance(n, ast.Constant):
            return isinstance(n.value, (int, float)) and not isinstance(n.value, bool)
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult,
                                                          ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)):
            return check(n.left) and check(n.right)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return check(n.operand)
        if isinstance(n, ast.Name):
            return n.id in _CALC_FUNCS or n.id in _CALC_CONSTS
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name) and n.func.id in _CALC_FUNCS and not n.keywords:
                return all(check(a) for a in n.args)
        return False

    if not check(node):
        raise ValueError("only math allowed")
    env = {}
    env.update(_CALC_CONSTS)
    env.update(_CALC_FUNCS)
    return eval(compile(node, "<cutie-calc>", "eval"), {"__builtins__": {}}, env)


def tool_calc(app, args):
    T = app.term
    expr = " ".join(args).replace("^", "**")
    if not expr:
        T.dim("  usage: calc 2+2*10  •  calc sqrt(2)^2  •  calc 2pi*5")
        return
    try:
        r = safe_calc(expr)
        rs = "%.10g" % r if isinstance(r, float) else str(r)
        T.push([("  calc  ", C_DIM), (expr + "  =  ", C_DIM), (rs, C_GOLD)])
    except Exception as e:
        T.push([("  ✗ calc: ", C_RED), (str(e)[:60], C_DIM)])


def tool_colors(app, args):
    T = app.term
    T.head("◆ PALETTE — theme: " + CURRENT_THEME)
    swatches = [("BORDER", C_BORDER), ("TITLE", C_TITLE), ("LABEL", C_LABEL),
                ("ARROW", C_ARROW), ("CYAN", C_CYAN), ("VIOLET", C_VIOLET),
                ("FUCHSIA", C_FUCHSIA), ("PINK", C_PINK), ("GOLD", C_GOLD), ("RED", C_RED)]
    for nm, c in swatches:
        T.push([("  ███████████ ", c), (nm.ljust(8), C_DIM), ("#%02X%02X%02X" % c, C_SLATE)])
    segs = [("█" * 5, s) for s in GRAD_STOPS]
    T.push([("  gradient     ", C_DIM)] + segs)
    T.dim("  switch with: theme [damdaar|sakura|matrix|ice|sunset|royal]")


def tool_bars(app, args):
    T = app.term
    T.push([("  sampling cpu…", C_DIM)])
    app.flush_frame()
    T.head("◆ BARS — live meters")
    cpu = cpu_sample()
    T.push([("  CPU  ", C_LABEL)] + micro_bar(cpu, 24)[1] + [(" %5.1f%%" % cpu, pct_color(cpu))])
    if app.info.mem:
        p = app.info.mem[2]
        T.push([("  MEM  ", C_LABEL)] + micro_bar(p, 24)[1] + [(" %5.1f%%" % p, pct_color(p))])
    if app.info.disk:
        p = app.info.disk[2]
        T.push([("  DISK ", C_LABEL)] + micro_bar(p, 24)[1] + [(" %5.1f%%" % p, pct_color(p))])
    if app.info.temp is not None:
        tc = app.info.temp
        col = C_CYAN if tc < 60 else (C_GOLD if tc < 78 else C_RED)
        T.push([("  TEMP ", C_LABEL), ("%.0f°C" % tc, col)])
    la = os.getloadavg()
    T.push([("  LOAD ", C_LABEL), ("%.2f  %.2f  %.2f" % la, C_VALUE)])


def tool_matrix(app, args):
    secs = 6.0
    if args:
        try:
            secs = clamp(float(args[0]), 1.0, 30.0)
        except Exception:
            pass
    app.suspend_hud()
    try:
        enter_raw(app.fd)
        W, H = app.size()
        out = app.out
        out.write(ALT_ON + CUR_HIDE)
        out.flush()
        chars = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎ0123456789XYZ<>[]{}*+-="
        drops = [{"x": random.randrange(W), "y": random.uniform(-H, 0),
                  "sp": random.uniform(6, 18), "trail": random.randint(3, 14)}
                 for _ in range(max(8, W // 3))]
        gc = (40, 220, 110)
        t0 = time.monotonic()
        last = 0.0
        while time.monotonic() - t0 < secs:
            now = time.monotonic()
            if now - last < 0.045:
                time.sleep(0.004)
                continue
            dt = now - last
            last = now
            cv = Canvas(W, H)
            for d in drops:
                head = int(d["y"])
                for k in range(d["trail"]):
                    yy = head - k
                    if 0 <= yy < H:
                        if k == 0:
                            cv.set(d["x"], yy, random.choice(chars), (180, 255, 190))
                        else:
                            cv.set(d["x"], yy, random.choice(chars), scale(gc, 1.0 - k / (d["trail"] + 2)))
                d["y"] += d["sp"] * dt
                if d["y"] - d["trail"] > H:
                    d["y"] = random.uniform(-10, 0)
                    d["x"] = random.randrange(W)
                    d["sp"] = random.uniform(6, 18)
                    d["trail"] = random.randint(3, 14)
            try:
                out.write(HOME + cv.render())
                out.flush()
            except Exception:
                break
            if app.keys.poll(0.0):
                break
        try:
            out.write(ALT_OFF)
            out.flush()
        except Exception:
            pass
    finally:
        app.resume_hud()
    app.term.push([("  matrix rain — “wake up neo…” ✦", C_CYAN)])


def tool_banner(app, args):
    T = app.term
    word = "CUTIE OS"
    if args:
        word = " ".join(args)[:9].upper()
        word = "".join(ch if ch in _GLYPHS else " " for ch in word)
    rows = ["".join(r) for r in zip(*(_GLYPHS[c] for c in word))]
    for r in rows:
        n = max(1, len(r))
        chunks = 6
        step = n / chunks
        segs = []
        for c in range(chunks):
            s = r[int(c * step): int((c + 1) * step)]
            if s:
                segs.append((s, grad((c + 0.5) / chunks)))
        T.push([("  ", C_OUT)] + segs)


def tool_meme(app, args):
    T = app.term
    want = None
    if args:
        a = args[0].lower()
        if a == "all":
            want = None
        elif a.upper() in ("EN", "HI", "BN", "TA", "ES", "HINGLISH"):
            want = a.upper()
    if want is None:
        tags = LANG_TAGS.get(app.lang)
        if tags and not (args and args[0].lower() == "all"):
            pool = [m for m in MEMES if m[1].upper() in tags]
            if not pool:
                pool = list(MEMES)
        else:
            pool = list(MEMES)
    else:
        pool = [m for m in MEMES if m[1].upper() == want]
        if not pool:
            T.push([(app.L("meme_none"), C_DIM)])
            return
    txt, tag = random.choice(pool)
    T.push([("  ╭─", C_SLATE), (" MEME ", C_FUCHSIA), ("─" * 30, C_SLATE)])
    T.push([("  │ ", C_SLATE), (txt, C_VALUE)])
    T.push([("  ╰─ ", C_SLATE), (tag, C_DIM)])


def tool_roll(app, args):
    T = app.term
    sides = 20
    if args:
        s = args[0]
        if s.lower().startswith("d"):
            s = s[1:]
        try:
            sides = clamp(int(s), 2, 1000)
        except Exception:
            pass
    v = random.randint(1, sides)
    T.push([("  dice d%d » " % sides, C_DIM), (str(v), C_GOLD if v == sides else C_VALUE),
            ("  NATURAL MAX!" if v == sides else "", C_GOLD)])


def tool_coin(app, args):
    res = "HEADS" if random.random() < 0.5 else "TAILS"
    app.term.push([("  coin » ", C_DIM), (res, C_FUCHSIA if res == "HEADS" else C_CYAN)])


def _greeting_card(app):
    T = app.term
    h = time.localtime().tm_hour
    if h < 5:
        gk = "g_night"
    elif h < 12:
        gk = "g_morning"
    elif h < 17:
        gk = "g_afternoon"
    elif h < 21:
        gk = "g_evening"
    else:
        gk = "g_night"
    nick = T.nick or app.info.user
    comp = random.choice(COMPLIMENTS)
    T.push([("  ╭", C_SLATE), ("─────────────✦", C_FUCHSIA), ("─────────────╮", C_SLATE)])
    T.push([("  │  ", C_SLATE), (app.L("hello") + " ", C_PINK), (nick + " ♡", C_WHITE)])
    T.push([("  │  ", C_SLATE), (app.L(gk), C_LABEL)])
    T.push([("  │  ", C_SLATE), (comp, C_CYAN)])
    T.push([("  ╰", C_SLATE), ("─────────────✦", C_FUCHSIA), ("─────────────╯", C_SLATE)])


def tool_cutie(app, args):
    T = app.term
    if not args:
        return _greeting_card(app)
    sub = args[0].lower()
    if sub in ("name", "nick"):
        if len(args) >= 2:
            app._set_nick(" ".join(args[1:]))
        else:
            T.push([(app.L("name_now") + " ", C_DIM), (T.nick or app.info.user, C_FUCHSIA)])
            T.push([(app.L("name_prompt"), C_LABEL)])
            app.prompt_name = True
        return
    if sub == "fps":
        return tool_fps(app, args[1:])
    if sub == "uptime":
        return tool_uptime(app, args[1:])
    if sub == "meme":
        return tool_meme(app, args[1:])
    if sub == "theme":
        return tool_theme(app, args[1:])
    if sub == "lang":
        return tool_lang(app, args[1:])
    if sub == "intro":
        if len(args) >= 2 and args[1].lower() in INTRO_FX:
            app.intro_fx = args[1].lower()
            save_profile_field("intro", app.intro_fx)
            T.push([(app.L("intro_set").format(x=app.intro_fx), C_FUCHSIA)])
        else:
            return tool_intro(app, [])
        return
    if sub == "version":
        T.push(_kv("VERSION", "%s %s" % (VERSION, EDITION)))
        return
    return _greeting_card(app)


def tool_theme(app, args):
    T = app.term
    if not args:
        T.head("◆ THEMES")
        for nm in THEMES:
            cur = (nm == CURRENT_THEME)
            th = THEMES[nm]
            T.push([("  %s " % ("●" if cur else "○"), th["title"] if cur else C_SLATE),
                    (nm.ljust(10), C_VALUE if cur else C_OUT),
                    ("█" * 5, th["stops"][2]), ("█" * 5, th["stops"][4])])
        T.dim("  usage: theme <name>")
        return
    nm = args[0].lower()
    if nm in THEMES:
        apply_theme(nm)
        save_profile_field("theme", nm)
        app.info.rebuild_ui(app.layout)
        T.push([("  ✦ theme » ", C_DIM), (nm, C_TITLE), ("   (saved)", C_SLATE)])
    else:
        T.push([("  ✗ unknown theme: ", C_RED), (args[0], C_VALUE),
                ("   — try: " + " | ".join(THEMES), C_DIM)])


def tool_macro(app, args):
    T = app.term
    M = T.macros
    if not args or args[0] in ("list", "ls", "show"):
        T.head("◆ MACROS — your one-tap commands")
        if not M:
            T.dim("  (none yet) — create:  macro set dev !nvim ~/proj")
            return
        for k in sorted(M):
            T.push([("  " + k.ljust(14), C_CYAN), ("» ", C_SLATE), (M[k], C_VALUE)])
        T.dim("  run: just type the name • delete: macro del <name>")
        return
    sub = args[0].lower()
    if sub == "set":
        if len(args) < 3:
            T.dim("  usage: macro set <name> <command...>")
            return
        name = args[1]
        if not re.fullmatch(r"[A-Za-z_][\w-]*", name):
            T.push([("  ✗ bad name: ", C_RED), (name, C_VALUE)])
            return
        if name in TOOL_MAP or name in ("cd", "sudo", "exit", "quit", "help"):
            T.push([("  ✗ that shadows a builtin — pick another name", C_RED)])
            return
        body = " ".join(args[2:])
        M[name] = body
        save_macros(M)
        T.push([("  ✦ macro ", C_DIM), (name, C_CYAN), (" » ", C_SLATE), (body, C_VALUE), ("   (saved)", C_SLATE)])
    elif sub in ("del", "rm"):
        if len(args) < 2 or args[1] not in M:
            T.dim("  usage: macro del <existing-name>")
            return
        del M[args[1]]
        save_macros(M)
        T.push([("  ✦ deleted ", C_DIM), (args[1], C_VALUE)])
    elif sub == "run":
        if len(args) < 2 or args[1] not in M:
            T.dim("  no such macro")
            return
        app.route(M[args[1]])
    else:
        T.dim("  usage: macro [list | set NAME CMD... | del NAME | run NAME]")


def tool_history(app, args):
    T = app.term
    T.head("◆ HISTORY (recent)")
    n = 20
    if args and args[0].isdigit():
        n = int(args[0])
    items = T.history[-n:]
    base = len(T.history) - len(items) + 1
    for i, ln in enumerate(items):
        T.push([("  %4d " % (base + i), C_SLATE), (ln, C_VALUE)])


def tool_clear(app, args):
    app.term.clear()
    app.seed_lines()


def tool_exit(app, args):
    _mpv_kill(app)
    app.running = False


def tool_edit(app, args):
    ed = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not ed:
        for c in ("nvim", "vim", "nano", "vi"):
            if shutil.which(c):
                ed = c
                break
    if not ed:
        app.term.dim("  no editor found (install nvim/vim/nano)")
        return
    app.run_pty([ed] + list(args))


def tool_python(app, args):
    exe = shutil.which("python3") or shutil.which("python")
    if not exe:
        app.term.dim("  python not found")
        return
    # Non-interactive quick evaluation / version flags -> run in HUD capture
    if args and (args[0] in ("-c", "-V", "--version", "-h", "--help") or (len(args) == 1 and args[0].startswith("-V"))):
        cmd = shlex.quote(exe) + " " + " ".join(shlex.quote(a) for a in args)
        app.start_capture(cmd)
        return
    # Interactive REPL or script
    if not args:
        app.term.push([("🌸 Launching Python 3 Interactive REPL... (exit() to return)", C_PINK)])
        app.flush_frame()
    app.run_pty([exe] + list(args))


def tool_repl(app, args):
    T = app.term
    repls = [
        ("py", "python3", ["python3", "python"], "Python 3 REPL"),
        ("node", "nodejs", ["node", "bun", "deno"], "Node.js REPL"),
        ("sh", "shell", [app.shell, "bash", "sh"], "Interactive Shell"),
        ("sqlite", "database", ["sqlite3"], "SQLite 3 Shell"),
        ("rb", "ruby", ["irb", "ruby"], "Ruby IRB"),
        ("lua", "lua", ["lua", "luajit"], "Lua REPL"),
    ]
    if not args or args[0] in ("list", "help", "?"):
        T.head("◆ INTERACTIVE REPLS — repl <name>")
        for key, name, candidates, desc in repls:
            found = any(shutil.which(c) for c in candidates)
            mark = "●" if found else "○"
            col = C_CYAN if found else C_SLATE
            T.push([("  %s " % mark, col), (key.ljust(8), C_VALUE), (name.ljust(12), C_LABEL),
                    (desc, C_OUT if found else C_DIM)])
        T.dim("  usage: repl py • repl node • repl sh • repl sqlite")
        return
    req = args[0].lower()
    for key, name, candidates, desc in repls:
        if req in (key, name):
            for c in candidates:
                exe = shutil.which(c)
                if exe:
                    T.push([("🌸 Launching %s (%s)..." % (desc, c), C_PINK)])
                    app.flush_frame()
                    app.run_pty([exe] + list(args[1:]))
                    return
            T.push([("  ✗ %s not found on this system" % desc, C_RED)])
            return
    exe = shutil.which(req)
    if exe:
        T.push([("🌸 Launching %s..." % req, C_PINK)])
        app.flush_frame()
        app.run_pty([exe] + list(args[1:]))
    else:
        T.push([("  ✗ unknown REPL: ", C_RED), (req, C_VALUE), (" — try: repl", C_DIM)])


def tool_shell(app, args):
    T = app.term
    sh = app.shell or os.environ.get("SHELL") or shutil.which("bash") or shutil.which("sh") or "sh"
    T.push([("🌸 Dropping into host subshell (%s)... Type 'exit' to return!" % os.path.basename(sh), C_PINK)])
    app.flush_frame()
    app.run_pty([sh] + list(args))


def tool_sparkle(app, args):
    T = app.term
    app.confetti = [Particle(i) for i in range(48)]
    app.confetti_until = time.monotonic() + 3.0
    cheers = [
        "✨ *SPARKLE* ✨ Momo is cheering for you! You're doing amazing! (˶ᵔ ᵕ ᵔ˶) ♡",
        "🌟 You got this! Take a deep breath and keep shining bright! 🌸",
        "🍡 Momo sent a sparkle shower! Your code is getting sweeter by the second! ✨",
        "🎀 *poof!* A storm of rainbow stars! Today is going to be wonderful! 💖",
    ]
    T.push([(random.choice(cheers), C_PINK)])
    app.add_xp(5)


def tool_neko(app, args):
    T = app.term
    facts = [
        "Cats spend about 70% of their lives sleeping or napping! (˶ᵔ ᵕ ᵔ˶)",
        "A cat's purr vibrates between 25 and 150 Hz, which can heal bones and muscles!",
        "Momo says that writing clean code makes kitten whiskers tingle with happiness! 🐾",
        "A group of kittens is called a 'kindle'! 🌸",
        "Cats have over 20 different vocalizations including trills, chirps, and purrs!",
        "When a cat blinks slowly at you, it means 'I love and trust you' ♡ ( slow blink )",
    ]
    faces = [
        "   /\\_/\\  \n  (˶ᵔ ᵕ ᵔ˶) ♡  (purr purr)",
        "   /\\_/\\  \n  ( • ﻌ • )   (mlem!)",
        "   /\\_/\\  \n  ( > ‿ < )/  (high five!)",
        "   /\\_/\\  \n  ( ˘͈ ᵕ ˘͈ )   (so cozy...)",
    ]
    face = random.choice(faces)
    fact = random.choice(facts)
    T.head("◆ NEKO MOMENT — 🐾")
    for line in face.splitlines():
        T.push([(line, C_PINK)])
    T.push([("  💡 Cat Fact: ", C_CYAN), (fact, C_VALUE)])
    app.add_xp(3)


def tool_man(app, args):
    if not args:
        app.term.dim("  usage: man <command>")
        return
    if shutil.which("man") is None:
        app.term.dim("  man not installed")
        return
    app.run_pty(["man"] + list(args))


def tool_fastfetch(app, args):
    for c in ("fastfetch", "neofetch", "screenfetch"):
        if shutil.which(c):
            app.run_pty([c] + list(args))
            return
    app.term.dim("  install fastfetch: sudo pacman -S fastfetch   (or use: sysinfo)")

def tool_lang(app, args):
    T = app.term
    if not args:
        T.head("◆ LANGUAGE / भाषा / ভাষা / மொழி / idioma")
        for code in LANGS:
            cur = (code == app.lang)
            T.push([("  %s " % ("●" if cur else "○"), C_CYAN if cur else C_SLATE),
                    (code.ljust(4), C_VALUE if cur else C_OUT),
                    (LANG_NAMES[code], C_LABEL if cur else C_DIM)])
        T.dim("  usage: lang en | hi | bn | ta | es")
        return
    code = args[0].lower()
    if code in LANGS:
        app.lang = code
        save_profile_field("lang", code)
        app._apply_lang()
        T.push([(app.L("lang_set").format(l=LANG_NAMES[code]), C_FUCHSIA)])
        T.push([(app.L("seed2").format(n=(T.nick or app.info.user), t="tools", h="help"), C_DIM)])
    else:
        T.push([("  ✗ unknown lang: ", C_RED), (args[0], C_VALUE),
                ("  — try: " + " ".join(LANGS), C_DIM)])


def tool_nick(app, args):
    if args:
        app._set_nick(" ".join(args))
    else:
        return tool_cutie(app, ["name"])


def tool_intro(app, args):
    T = app.term
    if not args:
        T.head("◆ INTRO EFFECTS — native %d + TTE %d" % (len(INTRO_FX) - 1, len(TTE_FX)))
        for fx in INTRO_FX:
            cur = (fx == app.intro_fx)
            T.push([("  %s " % ("●" if cur else "○"), C_CYAN if cur else C_SLATE),
                    (fx, C_VALUE if cur else C_OUT)])
        T.dim("  preview: intro <name>  •  set: intro set <name>  (cutie intro <name> bhi chalega)")
        T.dim("  tte installed? same-name effects play via TTE • force native: CUTIE_INTRO=native")
        return
    if args[0] == "set" and len(args) > 1:
        name = args[1].lower()
        if name in INTRO_FX:
            app.intro_fx = name
            save_profile_field("intro", name)
            T.push([(app.L("intro_set").format(x=name), C_FUCHSIA)])
        else:
            T.push([("  ✗ unknown effect: ", C_RED), (args[1], C_VALUE)])
        return
    name = args[0].lower()
    if name in INTRO_FX:
        T.push([("  ▶ previewing: ", C_DIM), (name, C_CYAN)])
        app.flush_frame()
        app.intro_fx = name
        app._native_intro()
    else:
        T.push([("  ✗ unknown: ", C_RED), (args[0], C_VALUE), ("  — intro for list", C_DIM)])


def tool_snake(app, args):
    import collections
    T = app.term
    app.suspend_hud()
    score = 0
    new_hi = False
    try:
        enter_raw(app.fd)
        app.keys.pend = b""
        W, H = app.size()
        out = app.out
        out.write(ALT_ON + CUR_HIDE)
        out.flush()
        gx = max(16, W - 2)
        gy = max(10, H - 2)
        snake = collections.deque()
        sx, sy = gx // 4, gy // 2
        for i in range(4):
            snake.appendleft((max(0, sx - i), sy))
        dr = (1, 0)
        pend = None

        def newfood():
            while True:
                f = (random.randrange(gx), random.randrange(gy))
                if f not in snake:
                    return f

        food = newfood()
        hi = int(load_profile().get("snake_hi") or 0)
        hi0 = hi
        dead = False
        quitf = False
        speed = 0.12
        cv = Canvas(W, H)

        def render(t):
            cv.clear()
            b = C_TERM_BORDER
            cv.put(0, 0, "╭" + "─" * (W - 2) + "╮", b)
            cv.put(0, H - 1, "╰" + "─" * (W - 2) + "╯", b)
            for yy in range(1, H - 1):
                cv.put(0, yy, "│", b)
                cv.put(W - 1, yy, "│", b)
            st = "SCORE %d" % score + ("  HI %d" % hi if hi else "") + "  •  arrows/WASD  •  Q quit"
            cv.put(2, 0, clip(st, W - 4), C_GOLD)
            n = len(snake)
            for i, (x, y) in enumerate(snake):
                if i == 0:
                    cv.set(1 + x, 1 + y, "█", C_WHITE)
                else:
                    cv.set(1 + x, 1 + y, "█", grad(max(0.0, 1.0 - i / float(max(1, n)))))
            if food:
                cv.set(1 + food[0], 1 + food[1], "◆",
                       mix(C_GOLD, C_MAGENTA, 0.5 + 0.5 * math.sin(t * 6.0)))
            if dead:
                lines = (("☠ GAME OVER ☠", C_RED),
                         ("score: %d   hi: %d%s" % (score, hi, "  ★ NEW BEST!" if score > hi0 else ""), C_VALUE),
                         ("press Q / ENTER", C_SLATE))
                for k, (ss, c) in enumerate(lines):
                    cv.put(max(2, (W - disp_width(ss)) // 2), max(1, H // 2 - 1) + k, ss, c)
            try:
                out.write(HOME + cv.render())
                out.flush()
            except Exception:
                pass

        last = time.monotonic()
        render(last)
        while not quitf:
            now = time.monotonic()
            for ev in app.keys.poll(0.02):
                kind, ch = ev[0], ev[1]
                if kind == "EOF":
                    quitf = True
                elif kind == "UP" or (kind == "CHAR" and ch in ("w", "W", "k")):
                    pend = (0, -1)
                elif kind == "DOWN" or (kind == "CHAR" and ch in ("s", "S", "j")):
                    pend = (0, 1)
                elif kind == "LEFT" or (kind == "CHAR" and ch in ("a", "A", "h")):
                    pend = (-1, 0)
                elif kind == "RIGHT" or (kind == "CHAR" and ch in ("d", "D", "l")):
                    pend = (1, 0)
                elif kind in ("CTRL_C", "ESC", "ENTER") or (kind == "CHAR" and ch in ("q", "Q")):
                    quitf = True
            if quitf:
                break
            if now - last >= speed and not dead:
                last = now
                if pend is not None and not (pend[0] == -dr[0] and pend[1] == -dr[1]):
                    dr = pend
                hx, hy = snake[0]
                nx, ny = hx + dr[0], hy + dr[1]
                if nx < 0 or ny < 0 or nx >= gx or ny >= gy or (nx, ny) in snake:
                    dead = True
                else:
                    snake.appendleft((nx, ny))
                    if (nx, ny) == food:
                        score += 1
                        food = newfood()
                        speed = max(0.055, speed - 0.004)
                    else:
                        snake.pop()
            render(now)
            time.sleep(0.004)
        if score > hi0:
            save_profile_field("snake_hi", score)
            new_hi = True
    finally:
        app.resume_hud()
    if score >= 10:
        app.award("snake10")
    if new_hi:
        T.push([("  🐍 NEW HIGH SCORE » ", C_GOLD), (str(score), C_FUCHSIA), ("  — legend!", C_DIM)])
    T.push([("  snake » ", C_DIM), ("score %d" % score, C_VALUE),
            ("  •  best %d" % max(score, hi), C_SLATE)])


def tool_hack(app, args):
    T = app.term
    app.suspend_hud()
    try:
        enter_raw(app.fd)
        app.keys.pend = b""
        W, H = app.size()
        out = app.out
        out.write(ALT_ON + CUR_HIDE + CLEAR_SCR)
        out.flush()
        G = (0, 230, 118)
        target = (args[0][:20] if args else "mainframe")
        seq = (
            "[■] initializing CUTIE exploit framework v9.9 …",
            "[■] scanning 192.168.1.0/24 for '%s' …" % target,
            "    ├─ 192.168.1.1     router        UP",
            "    ├─ 192.168.1.42    %-12s UP   ★ TARGET" % target,
            "[■] port scan → 22 80 443 1337 9001 OPEN",
            "[■] injecting payload via hyperframe …",
            "    ├─ firewall bypass      [██████████████] 100%",
            "    ├─ hash crack           [██████████████] 100%  (rainbow table + vibes)",
            "    ├─ privilege escalation [sudo mode unlocked]",
            "[■] downloading main.db [██████████████████████] 100%",
            "[■] covering tracks … (chup chap 🤫)",
        )
        skipped = False
        for ss in seq:
            try:
                out.write(fg(G) + ss + RESET + "\r\n")
                out.flush()
            except Exception:
                pass
            t_end = time.monotonic() + random.uniform(0.10, 0.32)
            while time.monotonic() < t_end:
                if app.keys.poll(0.0):
                    skipped = True
                    break
                time.sleep(0.01)
            if skipped:
                break
        cv = Canvas(W, H)
        big = "✦ ACCESS GRANTED ✦"
        for i in range(16):
            cv.clear()
            col = C_WHITE if i % 2 else (40, 255, 140)
            cv.put(max(0, (W - disp_width(big)) // 2), max(0, H // 2), big, col)
            for k in range(30):
                cv.set(random.randrange(W), random.randrange(H),
                       random.choice("✦*·+"), scale(col, 0.55))
            try:
                out.write(HOME + cv.render())
                out.flush()
            except Exception:
                pass
            if app.keys.poll(0.07):
                break
            time.sleep(0.05)
        time.sleep(0.4)
    finally:
        app.resume_hud()
    T.push([("  😎 just kidding — ", C_DIM), ("ACCESS GRANTED", C_GOLD),
            (" tumhare dil me pehle se tha 🫡  (pure natak the)", C_DIM)])


def tool_icat(app, args):
    T = app.term
    if not args:
        T.dim("  usage: icat <image-path>   — kitty ke andar image preview")
        return
    path = os.path.expanduser(" ".join(args))
    if not os.path.isfile(path):
        T.push([("  ✗ no such file: ", C_RED), (path, C_VALUE)])
        return
    if shutil.which("kitten"):
        kit = ["kitten", "icat"]
    elif shutil.which("kitty"):
        kit = ["kitty", "+kitten", "icat"]
    else:
        T.dim("  kitty not found — icat sirf kitty terminal me chalta hai")
        return
    if not (os.environ.get("KITTY_WINDOW_ID") or "kitty" in (os.environ.get("TERM") or "")):
        T.dim("  ye kitty terminal nahi lag raha — preview skip")
        return
    T.push([("  🖼 preview » ", C_DIM), (path, C_GOLD)])
    app.run_pty(kit + [path])


def fmt_speed(bps):
    if bps >= 1048576:
        return "%.1fM" % (bps / 1048576.0)
    if bps >= 1024:
        return "%.0fK" % (bps / 1024.0)
    return "%d" % int(bps)


def net_bytes():
    rx = tx = 0
    try:
        with open("/proc/net/dev") as f:
            for ln in f.readlines()[2:]:
                p = ln.split(":")
                if len(p) != 2 or p[0].strip() == "lo":
                    continue
                v = p[1].split()
                if len(v) >= 9:
                    rx += int(v[0])
                    tx += int(v[8])
    except Exception:
        return None
    return (rx, tx)


def _hms(sec):
    try:
        sec = max(0, int(float(sec)))
    except Exception:
        return "?"
    if sec >= 3600:
        return "%d:%02d:%02d" % (sec // 3600, (sec % 3600) // 60, sec % 60)
    return "%d:%02d" % (sec // 60, sec % 60)


def _music_raw(app, player=None):
    if shutil.which("playerctl") is None:
        return None
    L = chr(123)
    R = chr(125)

    def pc(*rest):
        cmd = ["playerctl"]
        if player:
            cmd += ["-p", player]
        return run_cmd(cmd + list(rest), 3).strip()

    title = pc("metadata", "--format", L + "title" + R)
    if not title:
        return None
    artist = pc("metadata", "--format", L + "artist" + R)
    album = pc("metadata", "--format", L + "album" + R)
    status = (pc("status") or "Playing").capitalize()
    vol = pc("volume") or "0"
    pname = (pc("metadata", "--format", L + "playerName" + R) or player or "mpris")[:22]
    try:
        pos_f = float(pc("position") or 0)
    except Exception:
        pos_f = 0.0
    try:
        len_us = int(float(pc("metadata", "mpris:length") or 0))
    except Exception:
        len_us = 0
    return {"title": title, "artist": artist or "", "album": album or "",
            "status": status, "vol": vol, "pname": pname,
            "pos_h": _hms(pos_f), "len_h": _hms(len_us / 1e6) if len_us else "?",
            "pos_us": int(pos_f * 1e6), "len_us": len_us}


MPV_SOCK = "/tmp/cutie-mpv-%d.sock" % os.getuid()
_MUSIC_EXT = (".mp3", ".flac", ".ogg", ".opus", ".wav", ".m4a", ".oga")


def _music_files():
    files = []
    seen = set()
    for d in ("~/Music", "~/music", "~/Downloads"):
        d = os.path.expanduser(d)
        if os.path.isdir(d) and d not in seen:
            seen.add(d)
            try:
                for f in sorted(os.listdir(d)):
                    if f.lower().endswith(_MUSIC_EXT) and not f.startswith("."):
                        files.append(os.path.join(d, f))
            except Exception:
                pass
    return files


def _mpv_alive(app):
    p = getattr(app, "mpv_proc", None)
    if p is not None and p.poll() is None:
        return True
    if os.path.exists(MPV_SOCK):
        try:
            sk = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sk.settimeout(0.4)
            sk.connect(MPV_SOCK)
            sk.close()
            return True
        except Exception:
            try:
                os.unlink(MPV_SOCK)
            except Exception:
                pass
    return False


def _mpv_cmd(app, cmdobj):
    try:
        sk = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sk.settimeout(1.5)
        sk.connect(MPV_SOCK)
        sk.send((json.dumps(cmdobj) + "\n").encode("utf-8"))
        buf = b""
        try:
            while b"\n" not in buf:
                chunk = sk.recv(65536)
                if not chunk:
                    break
                buf += chunk
        except socket.timeout:
            pass
        sk.close()
        for ln in buf.decode("utf-8", "replace").split("\n"):
            if '"error"' in ln:
                try:
                    return json.loads(ln)
                except Exception:
                    return None
        return None
    except Exception:
        return None


def _mpv_kill(app):
    if os.path.exists(MPV_SOCK):
        _mpv_cmd(app, {"command": ["quit"]})
    p = getattr(app, "mpv_proc", None)
    if p is not None and p.poll() is None:
        try:
            p.terminate()
        except Exception:
            pass
    app.mpv_proc = None


def _mpv_start(app, files):
    _mpv_kill(app)
    exe = shutil.which("mpv")
    if not exe:
        return False
    try:
        if os.path.exists(MPV_SOCK):
            os.unlink(MPV_SOCK)
    except Exception:
        pass
    try:
        app.mpv_proc = subprocess.Popen(
            [exe, "--no-video", "--really-quiet",
             "--input-ipc-server=" + MPV_SOCK] + list(files),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL)
    except Exception:
        app.mpv_proc = None
        return False
    for _ in range(40):
        if os.path.exists(MPV_SOCK):
            return True
        if app.mpv_proc.poll() is not None:
            return False
        time.sleep(0.05)
    return os.path.exists(MPV_SOCK)


def _mpv_now(app):
    r = _mpv_cmd(app, {"command": ["get_property", "media-title"]})
    title = (r or {}).get("data")
    if not title:
        return None
    title = re.sub(r"\.(mp3|flac|ogg|opus|wav|m4a|oga)$", "", str(title), flags=re.I)
    title = re.sub(r"_[A-Za-z0-9]{6,}$", "", title)
    title = title.replace("_", " ").strip() or str(r.get("data"))

    def gp(prop, default=0.0):
        rr = _mpv_cmd(app, {"command": ["get_property", prop]})
        try:
            return float((rr or {}).get("data") or default)
        except Exception:
            return default

    def fsec(sec):
        sec = int(sec)
        return "%d:%02d" % (sec // 60, sec % 60)

    tp = gp("time-pos")
    du = gp("duration")
    rz = _mpv_cmd(app, {"command": ["get_property", "pause"]})
    paused = bool((rz or {}).get("data"))
    return {"title": str(title), "artist": "local • mpv", "album": "",
            "status": "Paused" if paused else "Playing", "vol": "", "pname": "mpv",
            "pos_h": fsec(tp), "len_h": fsec(du) if du else "?",
            "pos_us": int(tp * 1e6), "len_us": int(du * 1e6)}


def _music_library(app, args):
    T = app.term
    files = _music_files()
    if not files:
        T.dim("  ~/Music me koi audio file nahi mili")
        return
    app.mpv_list = files
    ok = shutil.which("mpv") is not None
    T.head("◆ LOCAL LIBRARY — %d songs • mpv %s" %
           (len(files), "ready ✓" if ok else "MISSING ✗"))
    flt = " ".join(args).lower() if args else ""
    cur = getattr(app, "mpv_idx", -1)
    shown = 0
    for i, f in enumerate(files):
        nm = os.path.basename(f)
        if flt and flt not in nm.lower():
            continue
        shown += 1
        T.push([("  %s%3d " % ("▶" if i == cur else " ", i + 1),
                 C_GOLD if i == cur else C_SLATE), (nm[:62], C_VALUE if i == cur else C_OUT)])
        if shown > 39:
            T.dim("  … aur bhi hain — filter: music ls hotel")
            break
    T.dim("  bajao:  music play 5   ya   music play hotel   •  stop: music stop")


def _music_local_play(app, args):
    T = app.term
    if shutil.which("mpv") is None:
        T.push([("  ✗ mpv nahi hai — ", C_RED), ("!sudo pacman -S mpv", C_GOLD)])
        return
    files = _music_files()
    if not files:
        T.dim("  ~/Music khaali hai — pehle gane daalo 🎵")
        return
    if not args:
        idx = 0
    elif args[0].isdigit():
        idx = int(args[0]) - 1
        if idx < 0 or idx >= len(files):
            T.dim("  galat number — music ls dekho")
            return
    else:
        q = " ".join(args).lower()
        words = [w for w in re.split(r"[\s_\-]+", q) if w]
        cand = None
        for i, f in enumerate(files):
            nm = re.sub(r"\.(mp3|flac|ogg|opus|wav|m4a|oga)$", "",
                        os.path.basename(f).lower())
            if all(w in nm for w in words):
                cand = i
                break
        if cand is None:
            T.push([("  ✗ nahi mila: ", C_RED), (q, C_VALUE)])
            clean = [re.sub(r"_[A-Za-z0-9]{6,}\.\w{2,4}$", "",
                            os.path.basename(f)) for f in files]
            import difflib as _df
            close = _df.get_close_matches(q, [c.lower() for c in clean],
                                          n=4, cutoff=0.35)
            if close:
                T.push([("  matlab ye tha? ", C_DIM),
                        ("  •  ".join(close[:4]), C_GOLD)])
            T.dim("  tip: number 100% chalta hai — music ls → music play 32")
            return
        idx = cand
    app.mpv_list = files
    app.mpv_idx = idx
    if not _mpv_start(app, files):
        T.push([("  ✗ mpv start nahi hua", C_RED)])
        return
    for _ in range(12):
        if _mpv_cmd(app, {"command": ["playlist-play-index", idx]}) is not None:
            break
        time.sleep(0.1)
    app.award("musician")
    app.last_music_t = 0.0
    nm = os.path.basename(files[idx])
    T.push([("  ▶ chal raha hai » ", C_CYAN), (nm[:52], C_VALUE)])
    T.dim("  pause • next • prev • vol +10 • seek +30 • music (card) • stop")


def _music_local_ctl(app, args):
    T = app.term
    a0 = args[0].lower()

    def cmd(*rest):
        return _mpv_cmd(app, {"command": list(rest)})

    if a0 == "pause":
        cmd("set_property", "pause", True)
    elif a0 == "resume":
        cmd("set_property", "pause", False)
    elif a0 in ("toggle", "play-pause"):
        cmd("cycle", "pause")
    elif a0 == "next":
        cmd("playlist-next")
        if app.mpv_list and app.mpv_idx < len(app.mpv_list) - 1:
            app.mpv_idx += 1
    elif a0 in ("prev", "previous"):
        cmd("playlist-prev")
        if app.mpv_idx > 0:
            app.mpv_idx -= 1
    elif a0 in ("vol", "volume"):
        a2 = args[1].rstrip("%") if len(args) > 1 else "+10"
        try:
            if a2.startswith("+"):
                cmd("add", "volume", float(a2[1:]))
            elif a2.startswith("-"):
                cmd("add", "volume", -float(a2[1:]))
            else:
                cmd("set_property", "volume", clamp(float(a2), 0, 130))
        except Exception:
            T.dim("  usage: music vol 70 | +10 | -10")
            return
    elif a0 == "seek":
        a2 = args[1] if len(args) > 1 else "+30"
        try:
            if a2.startswith("+"):
                cmd("seek", float(a2[1:]))
            elif a2.startswith("-"):
                cmd("seek", -float(a2[1:]))
            else:
                cmd("seek", float(a2), "absolute")
        except Exception:
            T.dim("  usage: music seek +30 | -15 | 120")
            return
    app.award("musician")
    app.last_music_t = 0.0
    d = _mpv_now(app)
    if d:
        sym = {"Playing": "▶", "Paused": "❚❚"}.get(d["status"], "♪")
        T.push([("  %s " % sym, C_CYAN), (d["title"][:52], C_VALUE),
                ("  [%s / %s]" % (d["pos_h"], d["len_h"]), C_SLATE)])


def tool_np(app, args):
    app.open_mpage()


QACCESS = (
    ("Home", "~"),
    ("cutie", "~/cutie-os-pkg"),
    ("scripts", "~/scripts"),
    ("Music", "~/Music"),
    ("Documents", "~/Documents"),
    ("Downloads", "~/Downloads"),
    ("cfg", "~/.config/cutie"),
)


def _size_str(nb):
    if nb >= 1048576:
        return "%.1fM" % (nb / 1048576.0)
    if nb >= 1024:
        return "%.0fK" % (nb / 1024.0)
    return "%dB" % nb


def _py_out_colorizer(line):
    st = line.strip()
    if st.startswith('File "'):
        return [("  ⚡ ", C_FUCHSIA), (st, C_LABEL)]
    if st.startswith("Traceback"):
        return [("  ✗ ", C_RED), ("TRACEBACK", C_GOLD), (" — kuch toota hai:", C_DIM)]
    if re.search(r"(Error|Exception)[: ]", st):
        return [(line, C_RED)]
    if st.startswith("line "):
        return [(line, C_MAGENTA)]
    return [(line, C_OUT)]


_PY_KW = frozenset(("def", "class", "import", "from", "return", "if", "elif", "else",
                    "for", "while", "try", "except", "finally", "with", "as", "in",
                    "not", "and", "or", "is", "None", "True", "False", "lambda",
                    "yield", "pass", "break", "continue", "raise", "global", "assert",
                    "del", "async", "await"))
_PYQ = (chr(34), chr(39))


def _pyhl(line):
    segs = []
    cmt = -1
    q = None
    for j, c in enumerate(line):
        if q is not None:
            if c == q:
                q = None
            continue
        if c in _PYQ:
            q = c
        elif c == "#":
            cmt = j
            break
    code = line[:cmt] if cmt >= 0 else line
    i = 0
    buf = ""

    def flush():
        nonlocal buf
        if buf:
            segs.append((buf, C_OUT))
            buf = ""
    while i < len(code):
        c = code[i]
        if c in _PYQ:
            j = i + 1
            while j < len(code) and code[j] != c:
                j += 1
            if j < len(code):
                j += 1
            flush()
            segs.append((code[i:j], C_GOLD))
            i = j
            continue
        if c.isdigit():
            j = i
            while j < len(code) and (code[j].isdigit() or code[j] in ".xXabcdefABCDEF"):
                j += 1
            flush()
            segs.append((code[i:j], C_CYAN))
            i = j
            continue
        if c.isalpha() or c == "_":
            j = i
            while j < len(code) and (code[j].isalnum() or code[j] == "_"):
                j += 1
            w = code[i:j]
            if w in _PY_KW:
                flush()
                segs.append((w, C_FUCHSIA))
            else:
                buf += w
            i = j
            continue
        if c == "@":
            j = i + 1
            while j < len(code) and (code[j].isalnum() or code[j] in "._"):
                j += 1
            flush()
            segs.append((code[i:j], C_VIOLET))
            i = j
            continue
        buf += c
        i += 1
    flush()
    if cmt >= 0:
        segs.append((line[cmt:], C_SLATE))
    return segs or [("", C_OUT)]


def _run_banner(app, lang, sub):
    T = app.term
    word = "".join(ch if ch in _GLYPHS else " " for ch in lang.upper())[:12]
    rows = ["".join(r) for r in zip(*(_GLYPHS[c] for c in word))]
    T.push([("  ╭─", C_SLATE), (" ▶ RUNNING ", C_FUCHSIA), ("─" * 30, C_SLATE)])
    for r in rows:
        segs = []
        n = max(1, len(r))
        chunks = 6
        step = n / chunks
        for c in range(chunks):
            sseg = r[int(c * step):int((c + 1) * step)]
            if sseg:
                segs.append((sseg, grad((c + 0.5) / chunks)))
        T.push([("  ", C_OUT)] + segs)
    T.push([("  ╰─ ", C_SLATE), (sub, C_DIM)])


def tool_run(app, args):
    T = app.term
    if not args:
        T.dim("  usage: run file.py [args…]   •  interactive: run -i file.py   •  browser: code (F1)")
        return
    args_list = list(args)
    interactive = False
    if "-i" in args_list:
        interactive = True
        args_list.remove("-i")
    elif "--interactive" in args_list:
        interactive = True
        args_list.remove("--interactive")
    if not args_list:
        T.dim("  usage: run file.py [args…]")
        return
    path = os.path.expanduser(args_list[0])
    if not os.path.isabs(path):
        path = os.path.join(T.cwd, path)
    if not os.path.isfile(path):
        T.push([("  ✗ file nahi mili: ", C_RED), (args_list[0], C_VALUE)])
        return
    ext = os.path.splitext(path)[1].lower()

    # Auto-detect if file uses input() to avoid EOFError
    if ext == ".py" and not interactive:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as _f:
                _src = _f.read(8192)
                if "input(" in _src or "sys.stdin.read" in _src:
                    interactive = True
        except Exception:
            pass

    if ext == ".py":
        exe = shutil.which("python3") or shutil.which("python")
        if exe is None:
            T.dim("  python nahi mila")
            return
        if interactive:
            T.push([("🌸 Running %s interactively in PTY..." % os.path.basename(path), C_PINK)])
            app.flush_frame()
            app.run_pty([exe, path] + args_list[1:])
            app.add_xp(2)
            return
        cmd = shlex.quote(exe) + " " + shlex.quote(path)
    elif ext == ".sh":
        sh_exe = shutil.which("bash") or shutil.which("sh") or "sh"
        if interactive:
            app.run_pty([sh_exe, path] + args_list[1:])
            app.add_xp(2)
            return
        cmd = shlex.quote(sh_exe) + " " + shlex.quote(path)
    elif ext in (".c", ".cpp"):
        cc = shutil.which("gcc" if ext == ".c" else "g++")
        if cc is None:
            T.push([("  ✗ gcc/g++ not found on system", C_RED)])
            return
        outb = "/tmp/cutie-cc-%d" % os.getpid()
        cmd = (shlex.quote(cc) + " " + shlex.quote(path) + " -o " + outb +
               " && " + outb)
    elif ext == ".js":
        nd = shutil.which("node") or shutil.which("bun")
        if nd is None:
            T.dim("  node/bun not found on system")
            return
        if interactive:
            app.run_pty([nd, path] + args_list[1:])
            app.add_xp(2)
            return
        cmd = shlex.quote(nd) + " " + shlex.quote(path)
    else:
        T.push([("  ℹ ", C_DIM), (os.path.basename(path), C_VALUE),
                (" — .py .sh .c .cpp .js chalte hain", C_DIM)])
        return
    extra = " ".join(shlex.quote(a) for a in args_list[1:])
    if extra:
        cmd += " " + extra
    app.start_capture(cmd)
    if ext == ".py":
        app.cap_colorizer = _py_out_colorizer
    app.cap_t0 = time.monotonic()
    app.add_xp(2)


def tool_code(app, args):
    app.open_cpage(args[0] if args else None)


_LANG_ICON = {".py": ("🐍", "python"), ".c": ("⚡", "C"), ".cpp": ("⚡", "C++"),
              ".sh": ("🐚", "shell"), ".js": ("🌐", "node"), ".txt": ("📝", "text"),
              ".html": ("🌐", "html"), ".css": ("🎨", "css"), ".json": ("🧩", "json"),
              ".md": ("📖", "markdown"), ".rs": ("🦀", "rust"), ".go": ("🐹", "go")}


def _ep_lang(path):
    return _LANG_ICON.get(os.path.splitext(path)[1].lower(), ("✎", "plain"))


_CUTE_MSGS = ("✿ happy coding, cutie", "♡ momo believes in you",
              "✦ stay hydrated • sit straight", "❀ small steps, big ships",
              "✧ CTRL+D duplicates the line", "✧ CTRL+F finds anywhere",
              "✧ CTRL+G jumps to a line", "✧ CTRL+T drops a starter template",
              "🌸 ship it when it feels right")


def _ep_template_lines(path):
    if path.endswith(".py"):
        return ["#!/usr/bin/env python3",
                "# ✿ made with CUTIE editor",
                "",
                "def main():",
                '    print("hello from cutie ♡")',
                "",
                "",
                'if __name__ == "__main__":',
                "    main()",
                ""]
    if path.endswith(".c") or path.endswith(".cpp"):
        return ["#include <stdio.h>",
                "",
                "int main() {",
                '    puts("hello from cutie ♡");',
                "    return 0;",
                "}",
                ""]
    if path.endswith(".sh"):
        return ["#!/usr/bin/env bash",
                "# ✿ made with CUTIE editor",
                'echo "hello from cutie ♡"',
                ""]
    if path.endswith(".js"):
        return ['console.log("hello from cutie ♡");', ""]
    return ["✿ new cutie file", ""]


def _ep_outline(lines):
    out = []
    for i, ln in enumerate(lines):
        m = re.match(r"\s*(def|class)\s+([A-Za-z_]\w*)", ln)
        if m:
            out.append((i, m.group(1), m.group(2)))
        if len(out) >= 20:
            break
    return out


def _ep_preview_info(path, lines):
    ext = os.path.splitext(path)[1].lower()
    txt = "\n".join(lines)
    if ext == ".py":
        try:
            compile(txt, path, "exec")
            return ("✓ syntax OK", C_CYAN, _ep_outline(lines))
        except SyntaxError as e:
            return ("✗ line %d: %s" % (e.lineno or 0, e.msg or "error"), C_RED,
                    _ep_outline(lines))
        except Exception:
            return ("✗ compile error", C_RED, _ep_outline(lines))
    if ext in (".c", ".cpp"):
        incs = [l.strip() for l in lines if l.strip().startswith("#include")]
        bal = txt.count("{") - txt.count("}")
        ol = []
        for i, ln in enumerate(lines):
            m = re.match(r"^\w[\w\s\*]*?([A-Za-z_]\w*)\s*\([^;{]*\)\s*\{", ln)
            if m and len(ol) < 20:
                ol.append((i, "fn", m.group(1)))
        st = ("✓ braces balanced • %d includes" % len(incs)) if bal == 0 \
            else ("✗ braces %s by %d" % ("zyada" if bal > 0 else "kam", abs(bal)))
        if any(o[2] == "main" for o in ol):
            st += " • main() ✓"
        return (st, C_CYAN if bal == 0 else C_RED, ol)
    if ext in (".html", ".htm"):
        void = {"img", "br", "hr", "input", "meta", "link", "source", "area", "col", "embed"}
        stack = []
        bad = None
        for m in re.finditer(r"<(/?)([a-zA-Z][\w-]*)([^>]*?)(/?)>", txt):
            tag = m.group(2).lower()
            if tag in void or m.group(4) == "/":
                continue
            if m.group(1) == "/":
                if stack and stack[-1] == tag:
                    stack.pop()
                elif bad is None:
                    bad = tag
            else:
                stack.append(tag)
        cnt = {}
        for m in re.finditer(r"<([a-zA-Z][\w-]*)", txt):
            t2 = m.group(1).lower()
            cnt[t2] = cnt.get(t2, 0) + 1
        top = sorted(cnt.items(), key=lambda x: -x[1])[:6]
        st = ("✗ unclosed <%s>" % bad) if bad else ("✓ tags balanced" if not stack else "✗ open: <%s>" % ", ".join(stack[-3:]))
        ol = []
        for i, ln in enumerate(lines):
            for t3 in re.findall(r"<(h[1-6]|div|p|img|a|ul|nav|section|button)\b", ln):
                if len(ol) < 20:
                    ol.append((i, "tag", "<" + t3 + ">"))
        extra = " • " + ", ".join("%s×%d" % (k, v) for k, v in top)
        return (st + extra[:60], C_RED if (bad or stack) else C_CYAN, ol)
    if ext == ".json":
        try:
            j = json.loads(txt)
            keys = list(j.keys())[:10] if isinstance(j, dict) else ["[%d items]" % len(j)]
            return ("✓ valid JSON", C_CYAN, [(i, "key", str(k)) for i, k in enumerate(keys)])
        except Exception as e:
            return ("✗ invalid JSON: %s" % str(e)[:40], C_RED, [])
    if ext == ".md":
        ol = [(i, "#" * len(m.group(1)), m.group(2)) for i, ln in enumerate(lines)
              for m in [re.match(r"^(#{1,4})\s+(.*)", ln)] if m][:20]
        return ("✓ %d headings" % len(ol), C_CYAN, ol)
    if ext == ".css":
        sels = re.findall(r"^([^{}@/]+)\{", txt, re.M)
        return ("✓ %d rules" % len(sels), C_CYAN,
                [(i, "sel", sl.strip()[:24]) for i, sl in list(enumerate(sels))[:20]])
    if ext in (".sh", ".bash"):
        ol = [(i, "fn", m.group(1)) for i, ln in enumerate(lines)
              for m in [re.match(r"^\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\)\s*\{", ln)] if m]
        she = "shebang ✓" if txt.startswith("#!") else "✗ shebang nahi"
        return (she + " • %d fns" % len(ol), C_CYAN if txt.startswith("#!") else C_GOLD, ol)
    return ("%d lines • plain text" % len(lines), C_SLATE, [])


def _paint_lang_banner(cv, x0, y0, word, t):
    word = (word or "CODE").upper()[:9]
    if len(word.strip()) < 2:
        word = word + " LANG"
    word = "".join(ch if ch in _GLYPHS else " " for ch in word)
    rows = ["".join(r) for r in zip(*(_GLYPHS[c] for c in word))]
    n = max(1, disp_width(rows[0]))
    sweep = (t * 16.0) % (n + 24.0) - 12.0
    for ry, line in enumerate(rows):
        for i, ch in enumerate(line):
            if ch == " ":
                continue
            base = grad(i / max(1, n - 1))
            d = abs(i - sweep)
            c = mix(base, C_WHITE, 0.85 - d / 5.0) if d < 4.0 else scale(base, 0.92)
            cv.set(x0 + i, y0 + ry, ch, c)
    return len(rows)


def tool_ed(app, args):
    if not args:
        app.term.dim("  usage: ed file.py   ya bas: python | c | html | sh | js")
        return
    app.open_epage(" ".join(args))


LANG_GATES = {
    "python": "untitled.py", "py": "untitled.py", "p": "untitled.py",
    "c": "untitled.c", "cpp": "untitled.cpp", "c++": "untitled.cpp",
    "html": "untitled.html", "css": "untitled.css",
    "sh": "untitled.sh", "bash": "untitled.sh", "shell": "untitled.sh",
    "js": "untitled.js", "node": "untitled.js", "j": "untitled.js",
    "json": "untitled.json", "md": "untitled.md",
    "rust": "untitled.rs", "r": "untitled.rs", "go": "untitled.go", "g": "untitled.go",
    "java": "untitled.java", "txt": "untitled.txt", "t": "untitled.txt",
}


def _gate_counter(base):
    n = 0
    root, ext = os.path.splitext(base)
    while True:
        cand = (root + ("" if n == 0 else str(n)) + ext)
        if not os.path.exists(os.path.join(os.path.expanduser("~"), cand)) and \
                not os.path.exists(os.path.join(os.getcwd(), cand)):
            return cand
        n += 1


def _untitled_path(name):
    if os.path.isabs(name):
        return name
    desk = os.path.expanduser("~/Desktop")
    base_dir = desk if os.path.isdir(desk) else os.path.expanduser("~")
    return os.path.join(base_dir, name)


def _jload(name, default):
    try:
        with open(os.path.join(CONFIG_DIR, name)) as f:
            return json.load(f)
    except Exception:
        return default


def _jsave(name, data):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(os.path.join(CONFIG_DIR, name), "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def tool_todo(app, args):
    T = app.term
    td = _jload("todo.json", [])
    if args and args[0].lower() == "add" and len(args) >= 2:
        td.append({"t": " ".join(args[1:]), "d": False})
        _jsave("todo.json", td)
        T.push([("  ☑ add » ", C_DIM), (" ".join(args[1:]), C_VALUE)])
        return
    if args and args[0].lower() in ("done", "did") and args[1:]:
        i = int(args[1]) - 1 if args[1].isdigit() else -1
        if 0 <= i < len(td):
            td[i]["d"] = True
            _jsave("todo.json", td)
            app.add_xp(2)
            T.push([("  ✔ done » ", C_GOLD), (td[i]["t"], C_VALUE)])
        return
    if args and args[0].lower() in ("del", "rm") and args[1:]:
        i = int(args[1]) - 1 if args[1].isdigit() else -1
        if 0 <= i < len(td):
            T.push([("  ✗ del » ", C_DIM), (td.pop(i)["t"], C_DIM)])
            _jsave("todo.json", td)
        return
    if args and args[0].lower() == "clear":
        _jsave("todo.json", [])
        T.dim("  todo khaali ✓")
        return
    pend = [x for x in td if not x["d"]]
    T.head("◆ TODO — %d pending / %d total" % (len(pend), len(td)))
    for i, it in enumerate(td, 1):
        if it["d"]:
            T.push([("  %2d " % i, C_SLATE), ("✔ ", C_CYAN), (it["t"], C_DIM)])
        else:
            T.push([("  %2d " % i, C_GOLD), ("○ ", C_PINK), (it["t"], C_VALUE)])
    if not td:
        T.dim("  (khaali) — todo add kal ka kaam")
    T.dim("  add • done N • del N • clear")


def tool_snip(app, args):
    T = app.term
    sp = _jload("snips.json", {})
    if args and args[0] == "add" and len(args) >= 3:
        sp[args[1]] = " ".join(args[2:]).replace("\\n", "\n")
        _jsave("snips.json", sp)
        T.push([("  ✿ snippet » ", C_DIM), (args[1], C_CYAN), (" saved", C_SLATE)])
        return
    if args and args[0] == "del" and args[1:]:
        sp.pop(args[1], None)
        _jsave("snips.json", sp)
        T.dim("  deleted")
        return
    if args and args[0] in sp:
        T.push([("  ╭─", C_SLATE), (" SNIP ", C_FUCHSIA), ("─" * 28, C_SLATE)])
        for ln in sp[args[0]].split("\n"):
            T.push([("  │ ", C_SLATE), (ln, C_VALUE)])
        T.push([("  ╰", C_SLATE), ("─" * 34, C_SLATE), ("╯", C_SLATE)])
        return
    T.head("◆ SNIPPETS — %d" % len(sp))
    for k in sorted(sp):
        T.push([("  " + k.ljust(16), C_CYAN), ("» ", C_SLATE),
                (sp[k].split("\n")[0][:50], C_DIM)])
    T.dim("  snip add <naam> <code> • snip <naam> • snip del <naam>")


def tool_book(app, args):
    T = app.term
    bk = _jload("books.json", {})
    if args and args[0] == "add" and len(args) >= 3:
        bk[args[1]] = os.path.expanduser(args[2])
        _jsave("books.json", bk)
        T.push([("  🔖 book » ", C_DIM), (args[1], C_CYAN), (" → " + bk[args[1]], C_DIM)])
        return
    if args and args[0] == "del" and args[1:]:
        bk.pop(args[1], None)
        _jsave("books.json", bk)
        return
    if args and args[0] in bk:
        app.do_cd([bk[args[0]]])
        return
    T.head("◆ BOOKMARKS")
    for k in sorted(bk):
        T.push([("  " + k.ljust(14), C_CYAN), ("» ", C_SLATE), (bk[k], C_VALUE)])
    T.dim("  book add <naam> <path> • book <naam> = jump")


def tool_proj(app, args):
    T = app.term
    pj = _jload("proj.json", {})
    if args and args[0] == "add" and len(args) >= 3:
        pj[args[1]] = os.path.expanduser(args[2])
        _jsave("proj.json", pj)
        T.push([("  📦 proj » ", C_DIM), (args[1], C_CYAN)])
        return
    if args and args[0] in pj:
        app.do_cd([pj[args[0]]])
        if shutil.which("git"):
            app.start_capture("git -C " + shlex.quote(pj[args[0]]) + " status -sb")
        return
    T.head("◆ PROJECTS")
    for k in sorted(pj):
        T.push([("  " + k.ljust(14), C_CYAN), ("» ", C_SLATE), (pj[k], C_VALUE)])
    T.dim("  proj add <naam> <path> • proj <naam> = cd + git status")


def tool_wp(app, args):
    T = app.term
    if not args:
        T.dim("  usage: wp ~/Pictures/wall.jpg  — wallpaper colors se theme banegi!")
        return
    path = os.path.expanduser(" ".join(args))
    if not os.path.isfile(path):
        T.push([("  ✗ file nahi: ", C_RED), (path, C_VALUE)])
        return
    exe = shutil.which("magick") or shutil.which("convert")
    if exe is None:
        T.dim("  imagemagick chahiye — !sudo pacman -S imagemagick")
        return
    T.push([("  🎨 wallpaper se colors nikaal rahi hoon…", C_DIM)])
    app.flush_frame()
    out = run_cmd([exe, path, "-resize", "300%", "-colors", "6",
                   "-unique-colors", "txt:"], 10)
    cols = re.findall(r"#([0-9A-Fa-f]{6})", out)
    if len(cols) < 3:
        T.dim("  colors nahi mile — dusri image try karo")
        return

    def hx(h):
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    c0, c1, c2 = hx(cols[0]), hx(cols[1]), hx(cols[2])
    THEMES["wallpaper"] = dict(
        border=c0, tborder=scale(c0, 0.7), title=c1,
        label=mix(c1, C_WHITE, 0.35), arrow=c2,
        stops=(scale(c0, 0.55), c0, mix(c0, c1, 0.5), c1, c2, mix(c2, C_WHITE, 0.4)))
    apply_theme("wallpaper")
    save_profile_field("theme", "wallpaper")
    app.info.rebuild_ui(app.layout)
    if shutil.which("swww"):
        _cap("swww img " + shlex.quote(path), 8)
        T.push([("  🖼 wallpaper set (swww) » ", C_DIM), (os.path.basename(path), C_VALUE)])
    T.push([("  ✦ WALLPAPER THEME ban gayi!", C_FUCHSIA),
            ("  — pura cutie ab is image ke colors me 💜", C_DIM)])
    app.award("themed")


def tool_clip(app, args):
    T = app.term
    if shutil.which("wl-copy") is None:
        T.dim("  wl-clipboard chahiye — !sudo pacman -S wl-clipboard")
        return
    if args:
        txt = " ".join(args)
        subprocess.run(["wl-copy"], input=txt.encode(),
                       stdout=subprocess.DEVNULL, timeout=4)
        T.push([("  📋 copied » ", C_DIM), (txt[:60], C_VALUE)])
        return
    out = run_cmd(["wl-paste", "--no-newline"], 3)
    T.push([("  📋 clipboard » ", C_DIM), ((out or "(khaali)")[:70], C_VALUE)])


def tool_share(app, args):
    T = app.term
    if not args:
        T.dim("  usage: share <file>  — 0x0.st pe upload, link milega")
        return
    path = os.path.expanduser(" ".join(args))
    if not os.path.isfile(path):
        T.push([("  ✗ nahi mila: ", C_RED), (path, C_VALUE)])
        return
    T.push([("  ☁ uploading (panel me)…", C_DIM)])
    app.start_capture("curl -sF 'file=@" + shlex.quote(path) + "' https://0x0.st")
    app.cap_t0 = time.monotonic()


def tool_sync(app, args):
    T = app.term
    if args and args[0].lower() == "import":
        src = os.path.expanduser(args[1] if len(args) > 1 else "~/cutie-omega-backup.json")
        try:
            with open(src) as f:
                j = json.load(f)
        except Exception as e:
            T.push([("  ✗ import fail: ", C_RED), (str(e)[:50], C_DIM)])
            return
        for k in ("profile.json", "macros.txt", "todo.json", "snips.json",
                  "books.json", "proj.json"):
            if k in j:
                _jsave(k, j[k])
        pf = j.get("profile.json") or {}
        if pf.get("theme") in THEMES:
            apply_theme(pf["theme"])
            save_profile_field("theme", pf["theme"])
        app.term.macros = load_macros()
        app.term.nick = load_nick()
        app.info.nick = load_nick()
        app.info.rebuild_ui(app.layout)
        T.push([("  ♻ import done ✓ ", C_CYAN), ("(backup se sab wapas)", C_DIM)])
        return
    dump = {"profile.json": load_profile(), "macros.txt": load_macros(),
            "todo.json": _jload("todo.json", []), "snips.json": _jload("snips.json", {}),
            "books.json": _jload("books.json", {}), "proj.json": _jload("proj.json", {}),
            "exported": time.strftime("%Y-%m-%d %H:%M")}
    dst = os.path.expanduser("~/cutie-omega-backup.json")
    with open(dst, "w") as f:
        json.dump(dump, f, ensure_ascii=False, indent=1)
    T.push([("  ♻ sync export ✓ » ", C_CYAN), (dst, C_GOLD)])
    T.dim("  naye machine pe: sync import <file>")


def tool_pv(app, args):
    T = app.term
    if not args:
        T.dim("  usage: pv file.html  — browser me khol dega")
        return
    path = os.path.expanduser(args[0])
    if not os.path.isabs(path):
        path = os.path.join(T.cwd, path)
    if not os.path.isfile(path):
        T.push([("  ✗ nahi mila: ", C_RED), (args[0], C_VALUE)])
        return
    if shutil.which("xdg-open") is None:
        T.dim("  xdg-open nahi mila")
        return
    try:
        subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        T.push([("  🌐 browser me khul gaya » ", C_DIM), (os.path.basename(path), C_VALUE)])
    except Exception as e:
        T.push([("  ✗ ", C_RED), (str(e)[:50], C_DIM)])


def tool_ask(app, args):
    T = app.term
    if run_cmd(["curl", "-s", "--max-time", "3",
                "http://localhost:11434/api/tags"], 4).strip() == "":
        T.dim("  Ollama nahi/band hai — !sudo pacman -S ollama && systemctl start ollama")
        T.dim("  model: ollama pull llama3.2")
        return
    app.open_chatpage()
    if args:
        app._chat_send(" ".join(args))


def tool_chat(app, args):
    return tool_ask(app, args)


def tool_aimodel(app, args):
    T = app.term
    out = run_cmd(["curl", "-s", "--max-time", "4",
                   "http://localhost:11434/api/tags"], 6)
    names = []
    try:
        j = json.loads(out)
        names = [m.get("name") for m in j.get("models", []) if m.get("name")]
    except Exception:
        pass
    if args:
        save_profile_field("ai_model", args[0])
        app.ai_model = args[0]
        T.push([("  🧠 model set » ", C_DIM), (args[0], C_GOLD)])
        return
    T.head("◆ OLLAMA MODELS")
    for n in names:
        cur = (n == app.ai_model)
        T.push([("  %s " % ("●" if cur else "○"), C_CYAN if cur else C_SLATE),
                (n, C_VALUE if cur else C_OUT)])
    if not names:
        T.dim("  koi model nahi — ollama pull llama3.2")
    T.dim("  aimodel <name> = set • abhi: " + (app.ai_model or "auto"))


def tool_dash(app, args):
    app.open_dash()


TYPE_WORDS = (
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "it", "for",
    "not", "on", "with", "he", "as", "you", "do", "at", "this", "but", "his",
    "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", "my",
    "one", "all", "would", "there", "their", "what", "so", "up", "out", "if",
    "about", "who", "get", "which", "go", "me", "when", "make", "can", "like",
    "time", "no", "just", "him", "know", "take", "people", "into", "year",
    "your", "good", "some", "could", "them", "see", "other", "than", "then",
    "now", "look", "only", "come", "its", "over", "think", "also", "back",
    "after", "use", "two", "how", "our", "work", "first", "well", "way",
    "even", "new", "want", "because", "any", "these", "give", "day", "most",
    "code", "bug", "git", "diff", "test", "pass", "fail", "loop", "data",
    "file", "line", "name", "call", "read", "write", "list", "hash", "stack",
    "heap", "node", "edge", "sort", "cache", "fetch", "push", "pull", "merge",
    "fork", "repo", "shell", "kernel", "server", "client", "thread", "async",
    "class", "return", "print", "input", "while", "break", "range", "index",
    "debug", "deploy", "build", "ship", "fast", "slow", "clean", "cute",
    "momo", "vibe", "chai", "coffee", "night", "early", "sleep", "dream",
    "focus", "relax", "panic", "fix", "hack", "magic", "power", "energy",
    "battery", "boost", "turbo", "level", "score", "win", "lose", "again",
    "retry", "final", "done", "ready", "steady", "go", "quick", "jump",
)

TYPE_QUOTES = (
    "simplicity is the ultimate sophistication",
    "talk is cheap show me the code",
    "first solve the problem then write the code",
    "experience is the name everyone gives to their mistakes",
    "programming is thinking not typing",
    "make it work make it right make it fast",
    "any fool can write code that a computer can understand",
    "there is no place like 127.0.0.1",
)

TYPE_HI = (
    "kal se pakka diet aur pakka side project",
    "bas aakhri update phir so jaunga",
    "debugging me chai hi asli hero hai",
    "merge conflict dekh ke dil toot gaya",
    "code chal gaya pata nahi kaise",
    "production me test karna hi asli test hai",
    "semicolon bhool gaya poora din gaya",
    "stack overflow se mila jawab",
    "aur thoda sa push phir ghar",
    "bhai ne friday ko deploy kar diya",
)

TYPE_BN = (
    "ajke kaj kal e hobe bolle hoy na",
    "ek cup cha holei bug chole jabe",
    "commit message porer ami bujhbe na",
    "amar wifi amar niyom",
    "push kore ghumiye porbo",
    "raat jege code likha classic",
    "kal theke serious padha shuru",
    "sohoj kaj kothin hoye jay",
)

TYPE_CODE = (
    "\n".join(["def fib(n):", "    if n < 2:", "        return n",
                "    return fib(n - 1) + fib(n - 2)"]),
    "\n".join(["for i in range(10):", "    if i % 2 == 0:", "        print(i, 'even')",
                "    else:", "        print(i, 'odd')"]),
    "\n".join(["import json", "", "with open('data.json') as f:",
                "    data = json.load(f)", "print(data.keys())"]),
    "\n".join(["#include <stdio.h>", "", "int main() {", "    int sum = 0;",
                "    for (int i = 1; i <= 10; i++) {", "        sum += i;",
                "    }", '    printf("sum = %d", sum);', "    return 0;", "}"]),
    "\n".join(["#include <stdio.h>", "", "int main() {", '    puts("cutie c");',
                "    for (int i = 0; i < 3; i++) {", '        puts("loop");', "    }",
                "    return 0;", "}"]),
    "\n".join(["def quicksort(xs):", "    if len(xs) <= 1:", "        return xs",
                "    p = xs[0]", "    left = [x for x in xs[1:] if x < p]",
                "    right = [x for x in xs[1:] if x >= p]",
                "    return quicksort(left) + [p] + quicksort(right)"]),
)

TET_COLORS = {"I": C_CYAN, "O": C_GOLD, "T": C_VIOLET, "S": (60, 200, 100),
              "Z": C_RED, "J": (96, 165, 250), "L": (251, 146, 60)}


def _tet_rot(m):
    return ["".join(r) for r in zip(*m[::-1])]


_T_BASE = {"I": ["####"], "O": ["##", "##"], "T": ["###", " # "],
           "S": [" ##", "## "], "Z": ["## ", " ##"],
           "J": ["#  ", "###"], "L": ["  #", "###"]}
_T_PIECES = {}
for _k, _m in _T_BASE.items():
    _rots = [_m]
    _cur = _m
    for _i in range(3):
        _cur = _tet_rot(_cur)
        if _cur not in _rots:
            _rots.append(_cur)
    _T_PIECES[_k] = _rots

G2048_COL = [C_SLATE, C_OUT, C_CYAN, C_VIOLET, C_PURPLE, C_FUCHSIA,
             C_MAGENTA, C_PINK, C_GOLD, C_RED, C_WHITE, C_GOLD]


def _type_wrap(text, width):
    lines = []
    cur = ""
    start = 0
    for w in text.split(" "):
        cand = (cur + " " + w) if cur else w
        if disp_width(cand) > width and cur:
            lines.append((cur, start))
            start += len(cur) + 1
            cur = w
        else:
            cur = cand
    if cur:
        lines.append((cur, start))
    return lines


def tool_typing(app, args):
    mode = "words"
    arg = None
    known = ("words", "quote", "quotes", "meme", "hi", "bn", "code",
             "boss", "race", "ghost", "zen", "daily", "drill")
    if args:
        a0 = args[0].lower()
        if a0 == "drill":
            mode, arg = "drill", (args[1] if len(args) > 1 else None)
        elif a0.isdigit():
            arg = a0
        elif a0 in known:
            mode = "quote" if a0 == "quotes" else a0
            arg = args[1] if len(args) > 1 else None
        else:
            mode, arg = "drill", a0
    app.tpage = app._type_build(mode, arg)


def tool_tetris(app, args):
    T = app.term
    app.suspend_hud()
    score = 0
    lines_c = 0
    try:
        enter_raw(app.fd)
        app.keys.pend = b""
        W, H = app.size()
        out = app.out
        out.write(ALT_ON + CUR_HIDE)
        out.flush()
        BW, BH = 10, 20
        grid = [[None] * BW for _ in range(BH)]
        bag = []
        hi = int(load_profile().get("tetris_hi") or 0)
        hi0 = hi

        def nxt_piece():
            if not bag:
                bag.extend(list(_T_PIECES.keys()))
                random.shuffle(bag)
            return bag.pop()

        cur_k, cur_r, px, py = nxt_piece(), 0, 3, 0
        next_k = nxt_piece()
        over = False
        quitf = False
        paused = False
        last_g = time.monotonic()

        def cells(k, r, ox, oy):
            m = _T_PIECES[k][r % len(_T_PIECES[k])]
            oc = []
            for rr, row in enumerate(m):
                for cc, c2 in enumerate(row):
                    if c2 == "#":
                        oc.append((ox + cc, oy + rr))
            return oc

        def hit(k, r, ox, oy):
            for x, y in cells(k, r, ox, oy):
                if x < 0 or x >= BW or y >= BH:
                    return True
                if y >= 0 and grid[y][x] is not None:
                    return True
            return False

        def render(t2):
            cv = Canvas(W, H)
            bcol = C_TERM_BORDER
            bx = max(2, (W - (BW * 2 + 12)) // 2)
            byy = max(1, (H - (BH + 2)) // 2)
            cv.put(bx - 1, byy - 1, "╭" + "─" * (BW * 2 + 1) + "╮", bcol)
            cv.put(bx - 1, byy + BH, "╰" + "─" * (BW * 2 + 1) + "╯", bcol)
            for yy2 in range(BH):
                cv.put(bx - 1, byy + yy2, "│", bcol)
                cv.put(bx + BW * 2, byy + yy2, "│", bcol)
            for y2 in range(BH):
                for x2 in range(BW):
                    v = grid[y2][x2]
                    if v:
                        cv.put(bx + x2 * 2, byy + y2, "██", v)
            if not over:
                for x, y in cells(cur_k, cur_r, px, py):
                    if y >= 0:
                        cv.put(bx + x * 2, byy + y, "██", TET_COLORS[cur_k])
            sx = bx + BW * 2 + 3
            cv.put(sx, byy, "✿ TETRIS", C_TITLE)
            cv.put(sx, byy + 2, "SCORE", C_LABEL)
            cv.put(sx, byy + 3, str(score).rjust(6), C_GOLD)
            cv.put(sx, byy + 5, "LINES", C_LABEL)
            cv.put(sx, byy + 6, str(lines_c).rjust(6), C_VALUE)
            cv.put(sx, byy + 8, "NEXT", C_LABEL)
            for x, y in cells(next_k, 0, 0, 0):
                cv.put(sx + x * 2, byy + 9 + y, "██", TET_COLORS[next_k])
            cv.put(sx, byy + 13, "HI " + str(max(hi, score)), C_SLATE)
            cv.put(sx, byy + 15, "←→ move", C_SLATE)
            cv.put(sx, byy + 16, "↑ rot • ␣ drop", C_SLATE)
            cv.put(sx, byy + 17, "Q quit", C_SLATE)
            if paused:
                cv.put(sx, byy + 19, "|| PAUSED", C_GOLD)
            if over:
                m1 = "☠ GAME OVER"
                cv.put(max(2, (W - disp_width(m1)) // 2), byy + 8, m1, C_RED)
                m2 = "score %d%s" % (score, "  ★ NEW BEST!" if score > hi0 else "")
                cv.put(max(2, (W - disp_width(m2)) // 2), byy + 10, m2, C_VALUE)
                m3 = "Q / ENTER"
                cv.put(max(2, (W - disp_width(m3)) // 2), byy + 12, m3, C_SLATE)
            try:
                out.write(HOME + cv.render())
                out.flush()
            except Exception:
                pass

        render(time.monotonic())
        while not quitf:
            now = time.monotonic()
            for ev in app.keys.poll(0.02):
                kind, ch = ev[0], ev[1]
                if kind == "EOF":
                    quitf = True
                elif kind in ("CTRL_C", "ESC") or (kind == "CHAR" and ch in ("q", "Q")):
                    quitf = True
                elif kind == "ENTER" and over:
                    quitf = True
                elif over or paused:
                    continue
                elif kind == "LEFT":
                    if not hit(cur_k, cur_r, px - 1, py):
                        px -= 1
                elif kind == "RIGHT":
                    if not hit(cur_k, cur_r, px + 1, py):
                        px += 1
                elif kind == "UP":
                    nr = (cur_r + 1) % len(_T_PIECES[cur_k])
                    if not hit(cur_k, nr, px, py):
                        cur_r = nr
                elif kind == "DOWN":
                    if not hit(cur_k, cur_r, px, py + 1):
                        py += 1
                        score += 1
                elif kind == "CHAR" and ch == " ":
                    while not hit(cur_k, cur_r, px, py + 1):
                        py += 1
                        score += 2
                elif kind == "CHAR" and ch in ("p", "P"):
                    paused = not paused
            if quitf:
                break
            if not over and not paused and now - last_g >= max(0.08, 0.5 - (lines_c // 10) * 0.045):
                last_g = now
                if not hit(cur_k, cur_r, px, py + 1):
                    py += 1
                else:
                    for x, y in cells(cur_k, cur_r, px, py):
                        if y >= 0:
                            grid[y][x] = TET_COLORS[cur_k]
                    cleared = 0
                    yy2 = BH - 1
                    while yy2 >= 0:
                        if all(v is not None for v in grid[yy2]):
                            grid.pop(yy2)
                            grid.insert(0, [None] * BW)
                            cleared += 1
                        else:
                            yy2 -= 1
                    if cleared:
                        score += (0, 100, 300, 500, 800)[cleared] * (1 + lines_c // 10)
                        lines_c += cleared
                    cur_k, cur_r = next_k, 0
                    px, py = 3, 0
                    next_k = nxt_piece()
                    if hit(cur_k, cur_r, px, py):
                        over = True
                        if score > hi0:
                            save_profile_field("tetris_hi", score)
            render(now)
            time.sleep(0.004)
        if score > hi0:
            save_profile_field("tetris_hi", score)
    finally:
        app.resume_hud()
    if score >= 1000:
        app.award("tetris1k")
    T.push([("  🧱 tetris » ", C_DIM), ("score %d • %d lines" % (score, lines_c), C_VALUE),
            ("  •  best %d" % max(score, hi), C_SLATE)])


def tool_2048(app, args):
    T = app.term
    app.suspend_hud()
    score = 0
    got2048 = False
    try:
        enter_raw(app.fd)
        app.keys.pend = b""
        W, H = app.size()
        out = app.out
        out.write(ALT_ON + CUR_HIDE)
        out.flush()
        g = [[0] * 4 for _ in range(4)]
        best = int(load_profile().get("g2048_best") or 0)
        best0 = best

        def spawn():
            empt = [(y, x) for y in range(4) for x in range(4) if g[y][x] == 0]
            if not empt:
                return
            y, x = random.choice(empt)
            g[y][x] = 4 if random.random() < 0.1 else 2

        def merge_row(row):
            vals = [v for v in row if v]
            outv = []
            i = 0
            gn = 0
            while i < len(vals):
                if i + 1 < len(vals) and vals[i] == vals[i + 1]:
                    outv.append(vals[i] * 2)
                    gn += vals[i] * 2
                    i += 2
                else:
                    outv.append(vals[i])
                    i += 1
            outv += [0] * (4 - len(outv))
            return outv, gn

        def move(dirn):
            nonlocal score, got2048
            before = [r[:] for r in g]
            if dirn == "L":
                for y in range(4):
                    g[y], gn = merge_row(g[y])
                    score += gn
            elif dirn == "R":
                for y in range(4):
                    rev = g[y][::-1]
                    rev, gn = merge_row(rev)
                    g[y] = rev[::-1]
                    score += gn
            elif dirn == "U":
                for x in range(4):
                    col = [g[y][x] for y in range(4)]
                    col, gn = merge_row(col)
                    for y in range(4):
                        g[y][x] = col[y]
                    score += gn
            elif dirn == "D":
                for x in range(4):
                    col = [g[y][x] for y in range(4)][::-1]
                    col, gn = merge_row(col)
                    col = col[::-1]
                    for y in range(4):
                        g[y][x] = col[y]
                    score += gn
            moved = g != before
            if moved:
                spawn()
                for y in range(4):
                    for x in range(4):
                        if g[y][x] >= 2048:
                            got2048 = True
            return moved

        def can_move():
            for y in range(4):
                for x in range(4):
                    if g[y][x] == 0:
                        return True
                    if x < 3 and g[y][x] == g[y][x + 1]:
                        return True
                    if y < 3 and g[y][x] == g[y + 1][x]:
                        return True
            return False

        def render(t2):
            cv = Canvas(W, H)
            bcol = C_TERM_BORDER
            gx = max(2, (W - 32) // 2)
            gy = max(3, (H - 13) // 2)
            cv.put(gx - 1, gy - 1, "╭" + "─" * 29 + "╮", bcol)
            cv.put(gx - 1, gy + 11, "╰" + "─" * 29 + "╯", bcol)
            for yy2 in range(11):
                cv.put(gx - 1, gy + yy2, "│", bcol)
                cv.put(gx + 29, gy + yy2, "│", bcol)
            for y in range(4):
                for x in range(4):
                    v = g[y][x]
                    cx = gx + x * 7
                    cy = gy + y * 3
                    if v:
                        col = G2048_COL[max(0, min(11, int(math.log2(v)) - 1))]
                        fill = scale(col, 0.30)
                        for r2 in range(3):
                            cv.put(cx, cy + r2, " " * 6, fill)
                        tstr = str(v)
                        cv.put(cx + (6 - len(tstr)) // 2, cy + 1, tstr,
                               C_WHITE if v >= 128 else scale(col, 1.3))
                    else:
                        cv.put(cx, cy + 1, "  ·   ", scale(C_SLATE, 0.6))
            put_segs(cv, gx, gy - 2,
                     [("2048  ", C_TITLE), ("SCORE ", C_LABEL), (str(score), C_GOLD),
                      ("   BEST ", C_LABEL), (str(max(best, score)), C_VALUE)])
            if not can_move():
                cv.put(gx + 3, gy + 5, "☠ koi move nahi!", C_RED)
                cv.put(gx + 3, gy + 7, "Q / ENTER", C_SLATE)
            try:
                out.write(HOME + cv.render())
                out.flush()
            except Exception:
                pass

        spawn()
        spawn()
        quitf = False
        render(time.monotonic())
        while not quitf:
            for ev in app.keys.poll(0.05):
                kind, ch = ev[0], ev[1]
                if kind == "EOF":
                    quitf = True
                elif kind in ("CTRL_C", "ESC") or (kind == "CHAR" and ch in ("q", "Q")):
                    quitf = True
                elif kind == "ENTER" and not can_move():
                    quitf = True
                elif not can_move():
                    continue
                elif kind == "LEFT":
                    move("L")
                elif kind == "RIGHT":
                    move("R")
                elif kind == "UP":
                    move("U")
                elif kind == "DOWN":
                    move("D")
            if score > best:
                best = score
            render(time.monotonic())
            time.sleep(0.01)
        if score > best0:
            save_profile_field("g2048_best", score)
    finally:
        app.resume_hud()
    if got2048:
        app.award("n2048")
    T.push([("  🎲 2048 » ", C_DIM), ("score %d" % score, C_VALUE),
            ("  •  best %d" % max(best, score), C_SLATE)])


TTT_3D = {
    "X": ("███████╗", "██╔════╝", "██║  ██╗", "║  ██║", "╚█████╔╝", " ╚════╝"),
    "O": (" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "),
    " ": ("        ", "        ", "        ", "        ", "        ", "        "),
}
_TTT_L_NAMES = ("Seedhi Bacchi", "Chhoti Bacchi", "School Champion",
                "Bhavishya Darshi", "Chess Master", "IMPOSSIBLE")
_TTT_L_DEPTH = (1, 2, 4, 6, 8, 20)
_TTT_TAUNTS = (
    ("hehe yeh toh aasaan hai 😼", "dhyaan se khelo!", "=^.^= zzz…",
     "Momo so rahi thi, ab jaagi"),
    ("achha chal raha hai…", "sochne de mujhe 🤔", "hmm interesting",
     "abhi toh warmup hai"),
    ("not bad not bad 😼", "ab ghabra mat", "plan B nikalo",
     "dekho aur seekho"),
    ("strong move 🔥", "main bhi soch rahi hoon", "trap dekha maine",
     "attack best defence hai"),
    ("ooh dhang se khel rahi ho", "mere neurons jal rahe ⚡",
     "ab atka tum", "grandmaster vibes"),
    ("IMPOSSIBLE mode: thoda mushkil hoga 😼",
     "main jeetungi, bas time ki baat", "sos: udd raha hai",
     "tumhara confidence dekho!"),
)


def _ttt_winner(bd):
    wins = ((0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6))
    for a, b, c2 in wins:
        if bd[a] != " " and bd[a] == bd[b] == bd[c2]:
            return bd[a], (a, b, c2)
    if all(x != " " for x in bd):
        return "draw", None
    return None, None


def _ttt_minimax(bd, turn, depth, lvl, me, opp, alpha, beta):
    w, _l = _ttt_winner(bd)
    if w == me:
        return 10 - depth, None
    if w == opp:
        return depth - 10, None
    if w == "draw":
        return 0, None
    best = (-99, None) if turn == me else (99, None)
    for i in range(9):
        if bd[i] != " ":
            continue
        bd[i] = turn
        sc, _m = _ttt_minimax(bd, opp, depth + 1, lvl, me, opp, alpha, beta)
        bd[i] = " "
        if turn == me:
            if sc > best[0]:
                best = (sc, i)
            alpha = max(alpha, sc)
        else:
            if sc < best[0]:
                best = (sc, i)
            beta = min(beta, sc)
        if beta <= alpha:
            break
    return best


def _ttt_momo_pick(bd, lvl, me, opp):
    empty = [i for i in range(9) if bd[i] == " "]
    if not empty:
        return None
    depth = _TTT_L_DEPTH[min(lvl, 5)]
    if depth <= 2:
        if random.random() < 0.65:
            return random.choice(empty)
    elif depth <= 4:
        if random.random() < 0.30:
            return random.choice(empty)
    elif depth <= 6:
        if random.random() < 0.12:
            return random.choice(empty)
    _sc, mv = _ttt_minimax(list(bd), me, 0, lvl, me, opp, -99, 99)
    return mv if mv is not None else random.choice(empty)


def _ttt_face(state, t):
    if state == "think":
        f = "( o.o )" if (int(t * 2.5) % 2) else "( -.- )"
    elif state == "happy":
        f = "( ^ω^ )"
    elif state == "sad":
        f = "( ;_; )"
    else:
        f = "( ^..^ )" if (t % 4.0) < 3.4 else "( =ω= )"
    return (" " + chr(47) + chr(92) + "_" + chr(47) + chr(92) + " ", f, " > ~ < ")


def _ttt_paint(cv, x0, y0, bd, win_line, t, last_move):  # SHINE_BAND
    CW, CH = 11, 8
    fw, fh = 3 * CW, 3 * CH
    dim = scale(C_SLATE, 0.55)
    for cell_i in range(9):
        r, c2 = divmod(cell_i, 3)
        ox = x0 + c2 * CW
        oy = y0 + r * CH
        tint = 0.05 + 0.02 * math.sin(t * 1.3 + cell_i * 0.9)
        if win_line and cell_i in win_line:
            tint = 0.13 + 0.06 * math.sin(t * 5.0)
        col = scale(grad((r * 3 + c2) / 8.0), tint)
        for j in range(1, CH - 1):
            for i in range(1, CW):
                cv.set(ox + i, oy + j, "░", col)
    for i in range(fw):
        col = scale(grad(i / max(1, fw - 1)), 0.95)
        cv.set(x0 + i, y0 - 1, "─", col)
        cv.set(x0 + i, y0 + fh, "─", col)
    for j in range(fh):
        col = scale(grad(j / max(1, fh - 1)), 0.95)
        cv.set(x0 - 1, y0 + j, "│", col)
        cv.set(x0 + fw, y0 + j, "│", col)
    cv.set(x0 - 1, y0 - 1, "╭", scale(grad(0.0), 0.95))
    cv.set(x0 + fw, y0 - 1, "╮", scale(grad(0.5), 0.95))
    cv.set(x0 - 1, y0 + fh, "╰", scale(grad(0.5), 0.95))
    cv.set(x0 + fw, y0 + fh, "╯", scale(grad(1.0), 0.95))
    for k in (1, 2):
        gx2 = x0 + k * CW
        cv.set(gx2, y0 - 1, "┬", dim)
        cv.set(gx2, y0 + fh, "┴", dim)
        for j in range(fh):
            cv.set(gx2, y0 + j, "│", dim)
        gy2 = y0 + k * CH
        cv.set(x0 - 1, gy2, "├", dim)
        cv.set(x0 + fw, gy2, "┤", dim)
        for i in range(fw):
            cv.set(x0 + i, gy2, "─", dim)
        for k2 in (1, 2):
            cv.set(x0 + k2 * CW, gy2, "┼", dim)
    shine_pos = (t * 14.0) % (CW + CH + 6) - 3
    if win_line:
        for cell_i in win_line:
            r, c2 = divmod(cell_i, 3)
            px2 = x0 + c2 * CW + CW // 2
            py2 = y0 + r * CH + CH // 2
            ph = (t * 1.4 + cell_i * 0.33) % 1.0
            rr = 2 + ph * 3.0
            for ang in range(12):
                a2 = ang / 12.0 * 6.283
                sx2 = int(px2 + math.cos(a2) * rr)
                sy2 = int(py2 + math.sin(a2) * rr * 0.55)
                cv.set(sx2, sy2, "·", scale(C_GOLD, 0.9 - ph * 0.5))
    for cell_i in range(9):
        r, c2 = divmod(cell_i, 3)
        ox = x0 + c2 * CW + 1
        oy = y0 + r * CH + 1
        mark = bd[cell_i]
        glyph = TTT_3D.get(mark, TTT_3D[" "])
        is_win = bool(win_line and cell_i in win_line)
        is_last = (cell_i == last_move) and not win_line
        if mark == " ":
            sh = 0.45 + 0.22 * math.sin(t * 2.0 + cell_i * 1.3)
            cv.put(ox + CW - 4, oy + CH - 2, str(cell_i + 1), scale(C_SLATE, sh))
            continue
        if mark == "X":
            base = mix(C_GOLD, C_PINK, (r * 3 + c2) / 8.0)
        else:
            base = mix(C_CYAN, C_VIOLET, (r * 3 + c2) / 8.0)
        faded = bool(win_line) and not is_win
        body = scale(base, 0.45) if faded else base
        for ry, line in enumerate(glyph):
            for i, ch in enumerate(line):
                if ch != " ":
                    cv.set(ox + i + 1, oy + ry + 1, ch, scale(body, 0.22))
        for ry, line in enumerate(glyph):
            for i, ch in enumerate(line):
                if ch == " ":
                    continue
                if faded:
                    cc = body
                else:
                    d = abs((i + ry * 1.5) - shine_pos)
                    gl = 0.55 * max(0.0, 1.0 - d / 3.0)
                    if is_win:
                        pulse = 0.65 + 0.35 * math.sin(t * 6.0 + cell_i)
                        cc = mix(base, C_WHITE, min(1.0, pulse * 0.75 + gl))
                    elif is_last:
                        cc = mix(base, C_WHITE,
                                 min(1.0, 0.30 + 0.22 * math.sin(t * 5.0) + gl))
                    else:
                        cc = mix(base, C_WHITE, gl)
                cv.set(ox + i, oy + ry, ch, cc)
    if win_line:
        a, b, c3 = win_line
        if b == a + 1 and c3 == a + 2:
            yy = y0 + (a // 3) * CH + CH // 2
            for k in range(fw - 1):
                if (k + int(t * 12)) % 4 == 0:
                    cv.set(x0 + 1 + k, yy, "·", C_GOLD)
        elif b == a + 3 and c3 == a + 6:
            xx = x0 + (a % 3) * CW + CW // 2
            for k in range(fh - 1):
                if (k + int(t * 12)) % 4 == 0:
                    cv.set(xx, y0 + 1 + k, "·", C_GOLD)
        else:
            for k in range(1, fw - 1):
                if (k + int(t * 12)) % 4 == 0:
                    if a == 0:
                        yy = y0 + int(k / (fw - 1.0) * (fh - 1))
                    else:
                        yy = y0 + (fh - 1) - int(k / (fw - 1.0) * (fh - 1))
                    cv.set(x0 + k, yy, "·", C_GOLD)


def tool_ttt(app, args):
    T = app.term
    lvl = 2
    if args and args[0].isdigit():
        lvl = clamp(int(args[0]), 1, 6) - 1
    stats = load_profile().get("ttt_stats") or {"w": 0, "l": 0, "d": 0}
    app.suspend_hud()
    try:
        enter_raw(app.fd)
        app.keys.pend = b""
        W, H = app.size()
        out = app.out
        out.write(ALT_ON + CUR_HIDE)
        out.flush()
        me, opp = "X", "O"
        CW, CH = 11, 8
        fw, fh = 3 * CW, 3 * CH
        side_w = 24 if W >= 108 else 0
        gx0 = max(3, (W - fw - 2 - side_w) // 2)
        gy0 = max(3, (H - fh - 8) // 2)
        bd = [" "] * 9
        over = False
        win_line = None
        res = None
        quitf = False
        msg = "❯ 1-9 = move • L = level • Q = quit"
        taunt = _TTT_TAUNTS[lvl][0]
        taunt_i = 0
        last_move = -1
        thinking = False
        cv = Canvas(W, H)

        def render(t2):
            cv.clear()
            bcol = C_TERM_BORDER
            cv.put(0, 0, "╭" + "─" * (W - 2) + "╮", bcol)
            cv.put(0, H - 1, "╰" + "─" * (W - 2) + "╯", bcol)
            for yy in range(1, H - 1):
                cv.put(0, yy, "│", bcol)
                cv.put(W - 1, yy, "│", bcol)
            for k in range(7):
                sx = (k * 67 + int(t2 * 1.6) + k * k * 17) % max(4, W - 6) + 3
                sy = (k * 41 + int(t2 * 0.9)) % max(1, H - 6) + 2
                cv.set(sx, sy, "✦", scale(C_VIOLET, 0.30 + 0.14 * math.sin(t2 * 1.8 + k)))
            head = "✦ TIC ✦ TAC ✦ TOE ✦"
            hx2 = max(2, (W - disp_width(head)) // 2)
            for i, c2 in enumerate(head):
                cv.put(hx2 + i, 1, c2, grad(i / max(1, len(head) - 1)))
            lv = "LVL %d • %s" % (lvl + 1, _TTT_L_NAMES[lvl])
            cv.put(max(2, (W - disp_width(lv)) // 2), 2, lv,
                   C_GOLD if lvl == 5 else C_LABEL)
            _ttt_paint(cv, gx0, gy0, bd, win_line, t2, last_move)
            side_x = gx0 + fw + 4
            if side_w:
                st2 = ("think" if thinking else
                       ("happy" if (res or "").startswith("✦") else
                        ("sad" if (res or "").startswith("MOMO") else "idle")))
                av = _ttt_face(st2, t2)
                for j, al in enumerate(av):
                    cv.put(side_x, gy0 + 2 + j, al, C_PINK)
                cv.put(side_x + 9, gy0 + 3, "Momo", C_FUCHSIA)
                cv.put(side_x, gy0 + 7, clip(taunt, side_w - 2), C_LABEL)
                cv.put(side_x, gy0 + 9, clip(taunt[len(taunt) // 2:] if len(taunt) > side_w - 2 else "", side_w - 2), C_LABEL)
                if over:
                    sp2 = "  "
                elif thinking:
                    sp2 = SPIN[int(t2 * 10) % len(SPIN)] + " MOMO soch rahi…"
                else:
                    sp2 = "❯ TUMHARI BAARI"
                cv.put(side_x, gy0 + 12, clip(sp2, side_w - 2),
                       C_CYAN if thinking else C_GOLD)
                put_segs(cv, side_x, gy0 + 15,
                         [("✗ ", C_GOLD), (str(stats.get("w", 0)), C_VALUE),
                          ("  ◉ ", C_SLATE), (str(stats.get("d", 0)), C_VALUE),
                          ("  ○ ", C_RED), (str(stats.get("l", 0)), C_VALUE)])
                for li in range(6):
                    cur = (li == lvl)
                    cv.put(side_x, gy0 + 18 + li,
                           ("● L%d " % (li + 1)) if cur else ("○ L%d " % (li + 1)),
                           C_GOLD if cur else scale(C_SLATE, 0.7))
                    if cur:
                        cv.put(side_x + 5, gy0 + 18 + li, _TTT_L_NAMES[li], C_VALUE)
            ry0 = gy0 + fh + 2
            if over and res:
                rw = max(30, min(W - 10, 46))
                rx0 = max(2, (W - rw) // 2)
                for i in range(rw):
                    col = grad((i / rw + 0.25 * math.sin(t2 * 2.0)) % 1.0)
                    cv.set(rx0 + i, ry0, "━", scale(col, 1.0))
                txt = res
                tx0 = rx0 + (rw - disp_width(txt)) // 2
                for i, c2 in enumerate(txt):
                    cv.put(tx0 + i, ry0, c2,
                           C_WHITE if i not in (0, len(txt) - 1) else C_GOLD)
            cv.put(max(2, (W - disp_width(msg)) // 2), ry0 + 2, msg, C_SLATE)
            try:
                out.write(HOME + cv.render())
                out.flush()
            except Exception:
                pass

        def finish(winner, line):
            nonlocal over, res, win_line, msg, taunt
            over = True
            win_line = line
            if winner == me:
                stats["w"] = stats.get("w", 0) + 1
                res = "✦ TUM JEET GAYI! ✦"
                msg = "ENTER = phir se • Q quit"
                app.add_xp(6)
                if stats["w"] >= 5:
                    app.award("ttt_win5")
                if lvl >= 2:
                    app.award("ttt_l3")
                if lvl == 5:
                    app.award("ttt_l6")
                app.confetti_until = time.monotonic() + 3.5
                cols = list(GRAD_STOPS) + [C_GOLD, C_WHITE]
                app.confetti = [{"x": random.uniform(0, W), "y": random.uniform(-24, 0),
                                 "vy": random.uniform(10, 26),
                                 "c": random.choice(cols),
                                 "ch": random.choice("✦*·+•")} for _ in range(70)]
                taunt = "nyaa?! kaise?! 😿"
            elif winner == opp:
                stats["l"] = stats.get("l", 0) + 1
                res = "MOMO JEET GAYI 😼"
                msg = "ENTER = revenge • Q quit"
                taunt = "hehehe 😼😌"
            else:
                stats["d"] = stats.get("d", 0) + 1
                res = "DRAW — dono solid!"
                msg = "ENTER = phir se • Q quit"
                taunt = "theek hai… barabari 🤝"
            save_profile_field("ttt_stats", stats)

        def momo_turn():
            nonlocal taunt_i, thinking, last_move
            thinking = True
            t0 = time.monotonic()
            while time.monotonic() - t0 < 0.45:
                render(time.monotonic())
                time.sleep(0.03)
            mv = _ttt_momo_pick(bd, lvl, opp, me)
            thinking = False
            if mv is not None:
                bd[mv] = opp
                last_move = mv
            taunt_i = (taunt_i + 1) % len(_TTT_TAUNTS[lvl])
            taunt = _TTT_TAUNTS[lvl][taunt_i]
            w, ln = _ttt_winner(bd)
            if w:
                finish(w, ln)

        render(time.monotonic())
        while not quitf:
            now = time.monotonic()
            for ev in app.keys.poll(0.03):
                kind, ch = ev[0], ev[1]
                if kind == "EOF":
                    quitf = True
                elif kind in ("CTRL_C", "ESC") or (kind == "CHAR" and ch in ("q", "Q")):
                    quitf = True
                elif over and kind == "ENTER":
                    bd = [" "] * 9
                    over = False
                    win_line = None
                    res = None
                    last_move = -1
                    taunt = "naya round! 😼"
                    msg = "❯ 1-9 = move • L = level • Q = quit"
                elif over or thinking:
                    continue
                elif kind == "CHAR" and ch and ch.isdigit() and ch != "0":
                    i = int(ch) - 1
                    if bd[i] != " ":
                        msg = "✗ wo cell bhara hai!"
                        continue
                    bd[i] = me
                    last_move = i
                    render(now)
                    w, ln = _ttt_winner(bd)
                    if w:
                        finish(w, ln)
                    elif not all(x != " " for x in bd):
                        momo_turn()
                        msg = "❯ 1-9 = move • L = level • Q = quit"
                elif kind == "CHAR" and ch in ("l", "L"):
                    lvl = (lvl + 1) % 6
                    taunt = _TTT_TAUNTS[lvl][0]
                    msg = "→ LVL %d: %s" % (lvl + 1, _TTT_L_NAMES[lvl])
            render(now)
            if app.confetti:
                app._confetti_tick(0.03)
            time.sleep(0.005)
    finally:
        app.resume_hud()
    T.push([("  ⭕ tic-tac-toe » ", C_DIM),
            ("✗ %d  ◉ %d  ○ %d" % (stats.get("w", 0), stats.get("d", 0),
                                   stats.get("l", 0)), C_VALUE),
            ("  •  LVL %d" % (lvl + 1), C_SLATE)])


SYMPTOMS = ("cramps", "headache", "mood", "acne", "bloat", "backpain", "fatigue", "nausea")

PHASES = (
    ("menstrual", "🌷 Red Zone", "aaram karo, garam pani, khud se pyaar"),
    ("follicular", "🌱 Bloom Mode", "energy wapas aa rahi — naya kaam shuru karo!"),
    ("ovulation", "🌼 Glow Phase", "sabse zyada charm aaj — duniya ko dikhao"),
    ("luteal", "🍂 Cozy Mode", "self-care + chocolate, emotions valid hai"),
)


def _pd_load():
    return _jload("period.json", {"starts": [], "ends": [], "symptoms": {}})


def _pd_save(d):
    _jsave("period.json", d)


def _pd_parse(dt):
    try:
        return time.strptime(dt, "%Y-%m-%d")
    except Exception:
        return None


def _pd_avg_cycle(starts):
    if len(starts) < 2:
        return 28
    ds = []
    for i in range(1, min(len(starts), 7)):
        a = _pd_parse(starts[-i])
        b = _pd_parse(starts[-i - 1])
        if a and b:
            d = (time.mktime(a) - time.mktime(b)) / 86400.0
            if 15 < d < 60:
                ds.append(int(round(d)))
    if not ds:
        return 28
    return max(18, min(45, int(round(sum(ds) / len(ds)))))


def _pd_phase(day_of_cycle, avg, period_len):
    if day_of_cycle <= period_len:
        return 0
    if day_of_cycle <= int(avg * 0.45):
        return 1
    if day_of_cycle <= int(avg * 0.55):
        return 2
    return 3


def tool_period(app, args):
    T = app.term
    d = _pd_load()
    sub = args[0].lower() if args else ""

    def today():
        return time.strftime("%Y-%m-%d")

    if sub == "start":
        dt = today()
        if d["starts"] and d["starts"][-1] == dt:
            T.dim("  aaj ka start already logged ✓")
            return
        d["starts"].append(dt)
        d["starts"] = d["starts"][-24:]
        _pd_save(d)
        T.push([("  🌷 logged » ", C_DIM), ("period start " + dt, C_VALUE),
                ("  take care ♡", C_PINK)])
        app.add_xp(2)
        return
    if sub == "end":
        dt = today()
        if d["ends"] and d["ends"][-1] == dt:
            T.dim("  aaj ka end already logged ✓")
            return
        d["ends"].append(dt)
        d["ends"] = d["ends"][-24:]
        _pd_save(d)
        T.push([("  🌷 logged » ", C_DIM), ("period end " + dt, C_VALUE)])
        app.add_xp(2)
        return
    if sub == "log" and len(args) >= 2:
        sym = args[1].lower()
        if sym not in SYMPTOMS:
            T.push([("  ✗ symptom: ", C_RED), (" | ".join(SYMPTOMS), C_DIM)])
            return
        sev = 3
        if len(args) >= 3 and args[2].isdigit():
            sev = clamp(int(args[2]), 1, 5)
        d["symptoms"][today()] = {"s": sym, "v": sev}
        _pd_save(d)
        T.push([("  📝 logged » ", C_DIM), (sym + " (" + str(sev) + "/5)", C_VALUE),
                ("  garam pani + aaram ♡", C_PINK)])
        return
    if sub in ("clear", "reset"):
        T.push([("  ⚠ sab period data delete? type: ", C_RED),
                ("period confirm-clear", C_GOLD)])
        return
    if sub == "confirm-clear":
        _pd_save({"starts": [], "ends": [], "symptoms": {}})
        T.dim("  sab clear ✓")
        return

    starts = d["starts"]
    if not starts:
        T.head("◆ PERIOD TRACKER")
        T.dim("  (abhi koi data nahi — sab tere laptop me hi rehta hai)")
        T.dim("  shuru karo:  period start")
        T.dim("  phir roz:    period  (status)   • end pe:  period end")
        return

    avg = _pd_avg_cycle(starts)
    last = starts[-1]
    lp = _pd_parse(last)
    if not lp:
        T.dim("  data me galat date")
        return
    days = int((time.mktime(time.localtime()) - time.mktime(lp)) / 86400.0) + 1
    if days < 1:
        days = 1
    end_d = d["ends"][-1] if d["ends"] else None
    period_len = 5
    if end_d and lp:
        ep = _pd_parse(end_d)
        if ep:
            period_len = clamp(int((time.mktime(ep) - time.mktime(lp)) / 86400.0) + 1, 2, 10)
    next_day = max(1, days - avg)
    next_date = time.strftime("%Y-%m-%d", time.localtime(time.time() + (avg - days + 1) * 86400.0))
    ph_i = _pd_phase(days, avg, period_len)
    ph_name, ph_emoji, ph_msg = PHASES[ph_i]

    T.head("◆ CYCLE CARE — %s" % time.strftime("%d %b %Y"))
    barw = 24
    filled = clamp(int(days * barw / float(avg)), 0, barw)
    T.push([("  day ", C_DIM), (str(days), C_GOLD), ("/%d " % avg, C_DIM)] +
           micro_bar(clamp(days * 100.0 / avg, 1, 100), barw) +
           [("  %s" % avg, C_SLATE)])
    T.push([("  ", C_OUT), ("🌷" + "▁" * max(0, period_len - 1) + " " * 3 +
                            "🌱" + "  " + "🌼" + "      " + "🍂", C_VALUE)])
    T.push([("  phase » ", C_LABEL), (ph_emoji + " ", C_VALUE), (ph_name, C_GOLD)])
    T.push([("  ", C_OUT), (ph_msg, C_PINK)])
    if days > avg:
        T.push([("  ⏳ ", C_GOLD), ("%d din upar — ", days - avg),
                ("agar 2-3 din aur jaye to check kar lena", C_DIM)])
    else:
        T.push([("  next » ", C_LABEL), (next_date, C_VALUE),
                ("  (~%d din)" % (avg - days + 1), C_SLATE)])
    T.push([("  fertile » ", C_LABEL),
            ("ovulation ke aas-paas (%d-%d)" % (int(avg * 0.42), int(avg * 0.52)), C_SLATE)])
    sym = d["symptoms"].get(today())
    if sym:
        T.push([("  aaj log » ", C_LABEL), (sym["s"], C_VALUE),
                (" (%d/5)" % sym["v"], C_DIM)])
    if len(starts) >= 2:
        T.push([("  history » ", C_LABEL),
                ("%d cycles tracked" % len(starts), C_VALUE),
                ("  last start: " + last, C_DIM)])
    T.push([("", C_OUT)])
    T.dim("  period start | period end | period log cramps 3 | period (status)")
    T.dim("  🔒 data sirf ~/.config/cutie/period.json — local only")


CYCLE_TIPS = {
    "menstrual": ("garam pani bottle rakho", "dark chocolate allowed ✿",
                  "halki stretch, heavy workout nahi", "khud se soft baat karo"),
    "follicular": ("naya project shuru karne ka best time",
                   "protein khao, energy badhegi", "workout PR try karo",
                   "social plans bana lo"),
    "ovulation": ("sabse confident din — interview? presentation?",
                  "hydration zyada rakhna", "creative kaam karo",
                  "duniya ghoomne le jao khud ko"),
    "luteal": ("magnesium-rich khana (dry fruits)", "raat ko jaldi sona",
               "journaling karo, emotions valid hai", "caffeine thoda kam"),
}

MOMO_CARE = {
    "menstrual": ("( u_u )", "momo garam pani leke aa gayi... take care ♡"),
    "follicular": ("( ^ω^ )", "momo: energy dekh! aaj kuch bada karte hai!"),
    "ovulation": ("> ω < ", "momo: tu aaj itni GLOW kar rahi hai!!"),
    "luteal": ("( =ω= )", "momo: blanket, chai, aur ek movie?"),
}


def tool_cyclepage(app, args):
    app.cpage_bloom = {"mini": None, "msg": "", "msg_t": 0.0,
                       "month_off": 0, "sev_for": None}


def _cy_phase_of(app):
    d = _pd_load()
    if not d["starts"]:
        return None
    avg = _pd_avg_cycle(d["starts"])
    lp = _pd_parse(d["starts"][-1])
    if not lp:
        return None
    days = max(1, int((time.mktime(time.localtime()) -
                       time.mktime(lp)) / 86400.0) + 1)
    period_len = 5
    if d["ends"]:
        ep = _pd_parse(d["ends"][-1])
        if ep:
            period_len = clamp(int((time.mktime(ep) -
                                    time.mktime(lp)) / 86400.0) + 1, 2, 10)
    return {"d": d, "days": days, "avg": avg, "plen": period_len,
            "phase": _pd_phase(days, avg, period_len)}


def tool_cal(app, args):
    T = app.term
    d = _pd_load()
    now = time.localtime()
    year, month = now.tm_year, now.tm_mon
    if args and args[0].lower() in ("next", "prev"):
        off = 1 if args[0].lower() == "next" else -1
        total = year * 12 + month - 1 + off
        year, month = total // 12, (total % 12) + 1
    avg = _pd_avg_cycle(d["starts"]) if d["starts"] else 28
    period_len = 5
    if d["starts"] and d["ends"]:
        lp = _pd_parse(d["starts"][-1])
        ep = _pd_parse(d["ends"][-1])
        if lp and ep:
            period_len = clamp(int((time.mktime(ep) - time.mktime(lp)) / 86400.0) + 1, 2, 10)
    start_set = set()
    for st in d["starts"]:
        p = _pd_parse(st)
        if not p:
            continue
        for k in range(period_len):
            t2 = time.localtime(time.mktime(p) + k * 86400.0)
            if t2.tm_year == year and t2.tm_mon == month:
                start_set.add(t2.tm_mday)
    try:
        import calendar as _cal
        grid = _cal.monthcalendar(year, month)
        mname = _cal.month_name[month]
    except Exception:
        T.dim("  calendar nahi ban paya")
        return
    today_d = now.tm_mday if (now.tm_year == year and now.tm_mon == month) else -1
    T.head("◆ %s %d" % (mname, year))
    T.push([("  Mo Tu We Th Fr Sa Su", C_LABEL)])
    pred_start = None
    if d["starts"]:
        lp = _pd_parse(d["starts"][-1])
        if lp:
            next_ts = time.mktime(lp) + avg * 86400.0
            nd = time.localtime(next_ts)
            if nd.tm_year == year and nd.tm_mon == month:
                pred_start = nd.tm_mday
            elif abs((next_ts - time.mktime(now)) / 86400.0) < 5:
                pred_start = nd.tm_mday
    for wk in grid:
        segs = [("  ", C_OUT)]
        for day in wk:
            if day == 0:
                segs.append(("    ", C_OUT))
                continue
            lab = "%2d" % day
            if day == today_d:
                segs.append(("[" + lab + "]", C_WHITE))
            elif day in start_set:
                segs.append((lab + "🌷", C_RED))
            elif pred_start == day:
                segs.append((lab + "·", C_GOLD))
            else:
                segs.append((" " + lab + " ", C_OUT))
        T.push(segs)
    T.push([("", C_OUT)])
    segs = [("🌷 ", C_RED), ("period", C_DIM), ("   · ", C_GOLD),
            ("predicted", C_DIM), ("   [ ] ", C_WHITE), ("aaj", C_DIM)]
    T.push(segs)
    T.dim("  nav: cal next | cal prev   •  log: period start")


CARE_FACES = ("😄", "😊", "😐", "😢", "😤", "😴")
CARE_VALS = (5, 4, 3, 2, 2, 3)
CARE_MOOD_MSG = {
    5: "aaj toh full toofani energy!! export karo isko 🌞",
    4: "achhi vibe hai — isko save karne ka mann kare to love add 🌸",
    3: "neutral bhi ek valid jagah hai — paani piyo, chalte raho",
    2: "aaj bhaari lag raha hai — breathe try kar? ya love dekh 💜",
    2: "gussa = energy hai bas direction chahiye — likh ke nikal",
    3: "neend ki kami sab kuch kharab karti — aaj jaldi soyo?",
}
SC_TASKS = ("10 min walk / stretch", "paani 2 glass", "skin routine",
            "5 min deep breathe", "ek achhi baat khud ke baare me",
            "proper khana")
MOMO_CARE2 = {
    "good": "( ^ω^ )", "mid": "( ^..^ )", "low": "( ;_; )",
}


def _care_load():
    return _jload("care.json", {"mood": [], "love": [], "sc": []})


def _care_save(d2):
    _jsave("care.json", d2)


def _sc_today(d2):
    td = time.strftime("%Y-%m-%d")
    for e2 in d2["sc"]:
        if e2["d"] == td:
            return e2
    e2 = {"d": td, "ids": []}
    d2["sc"].append(e2)
    return e2


def _sc_streak(d2):
    days = set(e2["d"] for e2 in d2["sc"] if e2.get("ids"))
    n = 0
    cur = time.time()
    while True:
        dd = time.strftime("%Y-%m-%d", time.localtime(cur))
        if dd in days:
            n += 1
            cur -= 86400.0
        else:
            break
    return n


def tool_selfcare(app, args):
    app.care = {"mode": "sc", "msg": "", "msg_t": 0.0,
                "open_t": time.monotonic()}


def tool_mood(app, args):
    T = app.term
    d2 = _care_load()
    if args and args[0].isdigit() and 1 <= int(args[0]) <= 6:
        v = int(args[0])
        note = " ".join(args[1:])[:60]
        d2["mood"].append({"d": time.strftime("%Y-%m-%d"),
                           "v": v, "n": note})
        d2["mood"] = d2["mood"][-60:]
        _care_save(d2)
        T.push([("  " + CARE_FACES[v - 1] + " logged » ", C_DIM),
                (CARE_MOOD_MSG[v - 1], C_PINK)])
        if note:
            T.push([("  note » ", C_DIM), (note, C_VALUE)])
        info = _cy_phase_of(app)
        if info:
            T.push([("  phase link » ", C_DIM),
                    (PHASES[info["phase"]][1] + " — mood is phase me common",
                     C_SLATE)])
        if v <= 2:
            T.push([("  ♡ ", C_GOLD), ("breathe ya love try kar — momo hai tere paas", C_PINK)])
        app.add_xp(2)
        return
    T.head("◆ MOOD CHECK-IN")
    for i2, f2 in enumerate(CARE_FACES):
        T.push([("  " + str(i2 + 1) + ". ", C_SLATE), (f2, C_VALUE),
                ("  " + ["full energy", "achhi vibe", "theek-thaak", "bhaari",
                          "gussa", "soyi hui"][i2], C_DIM)])
    T.dim("  usage: mood 2   ya note ke saath: mood 4 ghar jaana hai")
    hist = d2["mood"][-14:]
    if hist:
        spark = []
        dd2 = {m2["d"]: m2["v"] for m2 in d2["mood"]}
        cur = time.time() - 13 * 86400.0
        for i2 in range(14):
            dd = time.strftime("%Y-%m-%d", time.localtime(cur))
            v = dd2.get(dd)
            spark.append("▁▂▃▄▅"[v - 1] if v else "·")
            cur += 86400.0
        T.push([("  14 din » ", C_DIM), ("".join(spark), C_CYAN)])
    T.dim("  🔒 sab local — care.json")


def tool_love(app, args):
    T = app.term
    d2 = _care_load()
    if args and args[0] == "add" and len(args) >= 2:
        txt = " ".join(args[1:])[:120]
        d2["love"].append({"d": time.strftime("%Y-%m-%d"), "t": txt})
        _care_save(d2)
        app.add_xp(3)
        if len(d2["love"]) >= 5:
            app.award("love5")
        T.push([("  💜 saved » ", C_DIM), (txt, C_VALUE)])
        T.dim("  yeh kabhi kabhi tujhe yaad dilayenge — ki tu kitni badass hai")
        return
    if args and args[0] == "list":
        T.head("◆ PROUD VAULT — %d memories" % len(d2["love"]))
        for e2 in reversed(d2["love"][-15:]):
            T.push([("  💜 ", C_GOLD), (e2["d"], C_SLATE), ("  ", C_DIM),
                    (e2["t"], C_VALUE)])
        if not d2["love"]:
            T.dim("  (khaali) — love add aaj maine test pass kiya!")
        return
    if not d2["love"]:
        T.dim("  vault khaali hai — pehli memory: love add aaj maine cutie banayi")
        return
    e2 = random.choice(d2["love"])
    T.push([("  ╭─", C_SLATE), (" 💜 YAAD HAI? ", C_FUCHSIA), ("─" * 24, C_SLATE)])
    T.push([("  │ ", C_SLATE), (e2["t"], C_VALUE)])
    T.push([("  │ ", C_SLATE), ("(" + e2["d"] + " ko tu ne ye kiya thi)", C_DIM)])
    T.push([("  ╰", C_SLATE), ("─" * 36, C_SLATE), ("╯", C_SLATE)])
    T.push([("  momo ( ^ω^ ): ", C_PINK), ("tu ye sab kar sakti hai — aaj bhi kar sakti hai ♡", C_LABEL)])


def tool_breathe(app, args):
    app.breathe = {"t0": time.monotonic(), "n": 0, "done": False,
                   "done_t": 0.0}


HT_LOGS = (
    "[ OK ] init cutie exploit framework v9.9",
    "[ ** ] scanning 192.168.{a}.0/24 ...",
    "[ OK ] target: 192.168.{a}.{b}  port 1337",
    "[ >> ] bypassing firewall ......... 100%",
    "[ >> ] cracking hash 0x{h} ....... 100%",
    "[ OK ] root shell acquired",
    "[ ** ] exfiltrating data.db [##########] 100%",
    "[ OK ] wiping fingerprints ... chup 🤫",
    "[ OK ] deploying good vibes.dll",
    "[ OK ] ACCESS GRANTED",
)
QUOTES = (
    ("tu itni capable hai ki tujhe khud bhi andaza nahi", "momo"),
    ("bade sapno ki keemat thakan hoti hai — kha letana", "cutie wisdom"),
    ("har expert ekdin beginner tha jo quit nahi kiya", "unknown"),
    ("self-care selfish nahi hai — zaroori hai", "soft truth"),
    ("code bhi insaan ki tarah — break ho to repair, quit nahi", "dev gyaan"),
    ("tumhari speed ka kisi se comparison nahi — tumhara race tumhara hai", "daily vibe"),
    ("jo aaj thoda mushkil hai, kal wo easy lagega", "growth"),
    ("khud par shak ho to yaad karo — kitni baar gir ke sambhi ho", "momo"),
    ("chhoti jeet ko bhi celebrate karo — energy isi se aati hai", "cutie wisdom"),
    ("perfection nahi, progress — roz 1%", "kaizen"),
    ("tum wo cheez ban sakti ho jo tum sochti ho", "classic"),
    ("raat jitni gehri hogi, subah utni sundar", "hope"),
    ("apne aap ko waise baat karo jaise best friend se karte ho", "soft truth"),
    ("break lena bhi ek achievement hai — burnout nahi", "self-care"),
    ("tumhara best kaafi hai — aaj bas itna", "aaj ka gyaan"),
    ("git commit kiya? life bhi versioning hai — push karte raho", "dev gyaan"),
    (" feelings bhi valid hai jo bhi ho — likh do, halka lagega", "journaling"),
    ("chaye ho to duniya badlo, ya bas aaj khud ko — dono bade kaam", "momo"),
)


def tool_quote(app, args):
    T = app.term
    q, who = random.choice(QUOTES)
    T.push([("  ╭", C_SLATE), ("─" * 44, C_SLATE), ("╮", C_SLATE)])
    T.push([("  │ ", C_SLATE), ("🌸", C_PINK), (" " + q[:40], C_VALUE)])
    if len(q) > 40:
        T.push([("  │ ", C_SLATE), ("   " + q[40:80], C_VALUE)])
    T.push([("  │ ", C_SLATE), ("─" * 42, C_DIM), ("│", C_SLATE)])
    T.push([("  │ ", C_SLATE), ("— " + who, C_FUCHSIA)])
    T.push([("  ╰", C_SLATE), ("─" * 44, C_SLATE), ("╯", C_SLATE)])
    app.add_xp(1)


def tool_hackertype(app, args):
    T = app.term
    app.suspend_hud()
    try:
        enter_raw(app.fd)
        app.keys.pend = b""
        W, H = app.size()
        out = app.out
        out.write(ALT_ON + CUR_HIDE + CLEAR_SCR)
        out.flush()
        G = (0, 230, 118)
        skipped = False
        for i2 in range(28):
            if skipped:
                break
            tmpl = HT_LOGS[i2 % len(HT_LOGS)]
            line = (tmpl.replace("{a}", str(random.randint(1, 254)))
                        .replace("{b}", str(random.randint(2, 254)))
                        .replace("{h}", "".join(random.choice("0123456789abcdef")
                                                for _ in range(8))))
            pre = "cutie@root:~# "
            shown = ""
            for c2 in line:
                shown += c2
                if random.random() < 0.08:
                    try:
                        out.write(ESC + "[%d;1H" % (min(H, 3 + i2)) + fg(G) +
                                  pre + shown + random.choice("▓▒░01") + RESET)
                        out.flush()
                    except Exception:
                        pass
                try:
                    out.write(ESC + "[%d;1H" % (min(H, 3 + i2)) + fg(G) +
                              pre + shown + RESET)
                    out.flush()
                except Exception:
                    pass
                t_end = time.monotonic() + 0.012
                while time.monotonic() < t_end:
                    if app.keys.poll(0.0):
                        skipped = True
                    time.sleep(0.002)
                if skipped:
                    break
            time.sleep(0.16)
            if app.keys.poll(0.0):
                skipped = True
        if not skipped:
            big = "✦ ACCESS GRANTED ✦"
            for i3 in range(10):
                cv = Canvas(W, H)
                col = C_WHITE if i3 % 2 else (40, 255, 140)
                cv.put(max(0, (W - disp_width(big)) // 2), H // 2, big, col)
                for k in range(40):
                    cv.set(random.randrange(W), random.randrange(H),
                           random.choice("✦*·+"), scale(col, 0.5))
                try:
                    out.write(HOME + cv.render())
                    out.flush()
                except Exception:
                    pass
                if app.keys.poll(0.08):
                    break
                time.sleep(0.05)
    finally:
        app.resume_hud()
    T.push([("  💻 ", C_DIM), ("pure natak tha — par style full tha na?", C_DIM)])


def tool_fireworks(app, args):
    T = app.term
    app.suspend_hud()
    count = 0
    try:
        enter_raw(app.fd)
        app.keys.pend = b""
        W, H = app.size()
        out = app.out
        out.write(ALT_ON + CUR_HIDE)
        out.flush()
        rockets = []
        sparks = []
        cv = Canvas(W, H)
        quitf = False
        last = 0.0
        while not quitf:
            now = time.monotonic()
            if now - last > 0.55 and len(rockets) < 3:
                last = now
                rockets.append({"x": random.uniform(6, W - 6),
                                "y": H - 2.0,
                                "vy": -random.uniform(9, 14),
                                "tx": random.uniform(4, H - 8),
                                "c": random.choice(GRAD_STOPS + [C_GOLD, C_WHITE])})
            cv.clear()
            cv.put(2, 1, "🎆 CUTIE FIREWORKS — Q exit", C_SLATE)
            for r2 in rockets[:]:
                r2["y"] += r2["vy"] * 0.05
                xi, yi = int(r2["x"]), int(r2["y"])
                cv.set(xi, yi, "|", scale(r2["c"], 0.8))
                if r2["y"] <= r2["tx"]:
                    rockets.remove(r2)
                    count += 1
                    if count >= 10:
                        app.award("fw10")
                    for _k in range(46):
                        a2 = random.uniform(0, 6.283)
                        sp2 = random.uniform(1.5, 6.5)
                        sparks.append({"x": float(xi), "y": float(yi),
                                       "vx": math.cos(a2) * sp2,
                                       "vy": math.sin(a2) * sp2,
                                       "life": 1.0,
                                       "c": r2["c"]})
            for s2 in sparks[:]:
                s2["x"] += s2["vx"] * 0.05
                s2["y"] += s2["vy"] * 0.05
                s2["vy"] += 1.4 * 0.05
                s2["life"] -= 0.022
                if s2["life"] <= 0 or s2["y"] >= H - 1:
                    sparks.remove(s2)
                    continue
                ch2 = "✦" if s2["life"] > 0.6 else ("·" if s2["life"] > 0.3 else "∙")
                cv.set(int(s2["x"]), int(s2["y"]), ch2,
                       scale(s2["c"], 0.35 + 0.65 * s2["life"]))
            for ev in app.keys.poll(0.0):
                if ev[0] in ("CTRL_C", "ESC", "EOF") or (ev[0] == "CHAR" and ev[1] in ("q", "Q")):
                    quitf = True
                elif ev[0] == "EOF":
                    quitf = True
            if ev and ev[0] == "EOF" if False else False:
                quitf = True
            try:
                out.write(HOME + cv.render())
                out.flush()
            except Exception:
                break
            time.sleep(0.016)
    finally:
        app.resume_hud()
    T.push([("  🎆 ", C_DIM), ("%d phool khile" % count, C_VALUE),
            ("  • momo: waah! 🎇", C_PINK)])


def tool_synthwave(app, args):
    T = app.term
    app.suspend_hud()
    try:
        enter_raw(app.fd)
        app.keys.pend = b""
        W, H = app.size()
        out = app.out
        out.write(ALT_ON + CUR_HIDE)
        out.flush()
        cv = Canvas(W, H)
        quitf = False
        t0 = time.monotonic()
        SUN = C_MAGENTA
        GRID = C_FUCHSIA
        MOUNT = C_VIOLET
        while not quitf:
            now = time.monotonic()
            t2 = now - t0
            cv.clear()
            horizon = max(6, int(H * 0.45))
            scx = W // 2
            srad = min(9, horizon - 2)
            for yy in range(horizon - srad * 2, horizon):
                dy = horizon - yy
                if dy > srad * 2:
                    continue
                half = int(math.sqrt(max(0, srad * srad - (dy - srad) * (dy - srad))))
                stripe = (yy + int(t2 * 6.0)) % 6 < 3
                if stripe or dy < srad:
                    cc = mix(SUN, (255, 120, 200), dy / float(max(1, srad * 2)))
                else:
                    cc = scale(SUN, 0.35)
                for xx in range(scx - half, scx + half + 1):
                    if 0 <= xx < W - 1:
                        cv.set(xx, yy, "▄", cc)
            for yy in range(horizon + 1, H - 1):
                depth = (yy - horizon) / float(H - horizon)
                step = max(1, int((1.0 - depth) * 6) + 1)
                if int((yy + t2 * 8.0)) % (step * 2) < step:
                    rowc = mix(GRID, C_VIOLET, depth * 0.6)
                    for xx in range(2, W - 2, 2):
                        cv.set(xx, yy, "─", scale(rowc, 0.85))
            for k in range(-8, 9):
                for yy in range(horizon + 1, H - 1):
                    depth = (yy - horizon) / float(H - horizon)
                    xx = scx + int(k * (2 + depth * depth * 26))
                    if 1 <= xx < W - 1:
                        if (k + int(t2 * 2)) % 2 == 0 or depth > 0.7:
                            cv.set(xx, yy, "║", scale(GRID, 0.5 + depth * 0.4))
            import random as _r
            _r.seed(42)
            for k in range(28):
                mx = _r.randint(2, W - 3)
                mh = _r.randint(2, 6)
                for j in range(mh):
                    xx = mx
                    yy = horizon - 1 - j
                    if 0 <= yy:
                        cc = scale(MOUNT, 1.0 - j * 0.15)
                        cv.set(xx, yy, "▄" if j == 0 else "█", cc)
            for k in range(24):
                stx = (_r.randint(2, W - 3))
                sty = (_r.randint(2, horizon - srad * 2 - 2))
                tw2 = 0.4 + 0.6 * abs(math.sin(t2 * 2.0 + k))
                cv.set(stx, sty, "·", scale(C_WHITE, tw2))
            cv.put(2, 1, "🌆 SYNTHWAVE — Q exit", C_SLATE)
            try:
                out.write(HOME + cv.render())
                out.flush()
            except Exception:
                break
            for ev in app.keys.poll(0.03):
                if ev[0] in ("CTRL_C", "ESC", "EOF") or (ev[0] == "CHAR" and ev[1] in ("q", "Q")):
                    quitf = True
            time.sleep(0.03)
    finally:
        app.resume_hud()
    app.award("synth")
    T.push([("  🌆 ", C_DIM), ("retro soul reset ho gaya — vapourwave forever", C_DIM)])


HRT_KINDS = {"e": "Estrogen", "t": "Testosterone", "b": "Blocker",
             "p": "Progesterone", "o": "Other"}


def _pr_load():
    return _jload("pride.json", {"hrt": [], "pronouns": "",
                                 "name": "", "journal": []})


def _pr_save(d3):
    _jsave("pride.json", d3)


AFFIRM = (
    "tera naam wahi hai jo TUNE chuna — aur wo perfect hai",
    "tera identity valid hai. hamesha thi, hamesha rahegi",
    "body ka journey apna hota hai — teri pace, tere rules",
    "tu jis me se guzri hai, wo himmat har din celebrate honi chahiye",
    "dysphoria jhooth bolti hai — mirror me jo hai wahi tu hai, aur kaafi hai",
    "community tere saath hai — tu akeli kabhi nahi",
    "jo bhi step liya (chhota ya bada) — wo courage tha",
    "tera past tera mission statement nahi hai — tera future tera hai",
    "khud ko dekh ke smile aana — wo moment aayega, ya aa chuka hai",
    "tum sirf survive nahi kar rahi — thrive kar rahi ho",
)


def tool_pride(app, args):
    T = app.term
    d3 = _pr_load()
    if args and args[0] == "hrt":
        if len(args) >= 2 and args[1].lower() in HRT_KINDS:
            d3["hrt"].append({"d": time.strftime("%Y-%m-%d"),
                              "k": args[1].lower()})
            d3["hrt"] = d3["hrt"][-120:]
            _pr_save(d3)
            if len(d3["hrt"]) >= 30:
                app.award("hrt30")
            T.push([("  💗 logged » ", C_DIM),
                    (HRT_KINDS[args[1].lower()] + " — " + time.strftime("%Y-%m-%d"),
                     C_VALUE)])
            T.dim("  journey har dose me ek din aage badhta hai 🏳️‍⚧️")
            return
        T.dim("  usage: pride hrt e|t|b|p|o   (E/T-blocker/Proge/Other)")
        return
    if args and args[0] == "pron" and len(args) >= 2:
        d3["pronouns"] = " ".join(args[1:])[:24]
        _pr_save(d3)
        T.push([("  💗 pronouns » ", C_DIM), (d3["pronouns"], C_GOLD)])
        return
    if args and args[0] == "name" and len(args) >= 2:
        d3["name"] = " ".join(args[1:])[:24]
        _pr_save(d3)
        T.push([("  💗 chosen name » ", C_DIM), (d3["name"], C_FUCHSIA),
                ("  (saari pride page pe yahi dikhega)", C_DIM)])
        return
    if args and args[0] == "affirm":
        T.push([("  ╭─", C_SLATE), (" 🏳️‍⚧️ ", C_CYAN), ("─" * 28, C_SLATE)])
        T.push([("  │ ", C_SLATE), (random.choice(AFFIRM), C_VALUE)])
        T.push([("  ╰", C_SLATE), ("─" * 34, C_SLATE), ("╯", C_SLATE)])
        app.add_xp(1)
        return
    if args and args[0] == "journal" and len(args) >= 2:
        d3["journal"].append({"d": time.strftime("%Y-%m-%d"),
                              "t": " ".join(args[1:])[:200]})
        _pr_save(d3)
        T.push([("  📖 journaled » ", C_DIM), ("har likha hua shabd halka karta hai", C_DIM)])
        return
    app.pridepage = {"tab": 0, "msg": "", "msg_t": 0.0, "open_t": time.monotonic()}


def tool_music(app, args):
    T = app.term
    local_alive = _mpv_alive(app)
    a0 = args[0].lower() if args else ""
    if a0 == "page":
        app.open_mpage()
        return
    if a0 in ("ls", "library", "files"):
        return _music_library(app, args[1:])
    if a0 == "play":
        return _music_local_play(app, args[1:])
    if a0 == "stop" and local_alive:
        _mpv_kill(app)
        T.push([("  ■ local player band", C_DIM)])
        return
    if local_alive and a0 in ("pause", "resume", "toggle", "play-pause", "next",
                              "prev", "previous", "vol", "volume", "seek"):
        return _music_local_ctl(app, args)
    if shutil.which("playerctl") is None:
        if app.is_termux:
            T.dim("  playerctl nahi hai — pkg install playerctl (try karo)")
        else:
            T.dim("  playerctl nahi mila — sudo pacman -S playerctl")
        T.dim("  spotify / yt-music (browser) / mpv / vlc — sab MPRIS se chalega")
        return
    if args and args[0] == "-p" and len(args) >= 2:
        app.music_player = args[1]
        args = args[2:]
    if args and args[0].isdigit() and len(args) == 1:
        players = _cap("playerctl --list-all", 3).split()
        i = int(args[0]) - 1
        if 0 <= i < len(players):
            app.music_player = players[i]
            T.push([("  ♪ player » ", C_DIM), (players[i], C_CYAN)])
        else:
            T.dim("  galat number — music list dekho")
        return
    if args:
        sub = args[0].lower()
        tgt = ["-p", app.music_player] if app.music_player else []

        def pc(*rest):
            return run_cmd(["playerctl"] + tgt + list(rest), 4)
        if sub in ("play", "pause", "toggle", "play-pause", "stop", "next", "prev", "previous"):
            act = "previous" if sub == "prev" else ("play-pause" if sub == "toggle" else sub)
            pc(act)
            app.award("musician")
            d = _music_raw(app, app.music_player)
            if d and d.get("title"):
                sym = {"Playing": "▶", "Paused": "❚❚", "Stopped": "■"}.get(d["status"], "♪")
                T.push([("  %s " % sym, C_CYAN), (d["title"], C_VALUE),
                        (" — " + (d["artist"] or "?"), C_LABEL),
                        ("  [%s]" % d["pname"], C_SLATE)])
            else:
                T.push([("  ♪ ho gaya — koi player nahi chal raha?", C_DIM)])
            return
        if sub == "seek" and len(args) >= 2:
            a2 = args[1]
            if a2.startswith("+"):
                pc("position", a2[1:] + "+")
            elif a2.startswith("-"):
                pc("position", a2[1:] + "-")
            else:
                pc("position", a2)
            app.award("musician")
            T.push([("  ⏩ seek » ", C_DIM), (a2, C_VALUE)])
            return
        if sub in ("vol", "volume") and len(args) >= 2:
            a2 = args[1].rstrip("%")
            try:
                if a2.startswith("+"):
                    pc("volume", "%.2f+" % (float(a2[1:]) / 100.0))
                elif a2.startswith("-"):
                    pc("volume", "%.2f-" % (float(a2[1:]) / 100.0))
                else:
                    pc("volume", "%.2f" % (clamp(float(a2), 0, 100) / 100.0))
                app.award("musician")
                out = pc("volume")
                v = int(round(float(out.strip() or 0) * 100))
                T.push([("  vol » ", C_DIM)] + micro_bar(v, 12)[1] + [(" %d%%" % v, C_VALUE)])
            except Exception:
                T.dim("  usage: music vol 70 | +10 | -10")
            return
        if sub == "shuffle":
            pc("shuffle", args[1].lower() if len(args) > 1 else "toggle")
            T.push([("  🔀 shuffle » ", C_DIM), (args[1] if len(args) > 1 else "toggled", C_VALUE)])
            return
        if sub == "loop":
            pc("loop")
            T.push([("  🔁 loop » ", C_DIM), ("cycled", C_VALUE)])
            return
        if sub == "list":
            pls = _cap("playerctl --list-all", 3).split()
            T.head("◆ PLAYERS (MPRIS)")
            if not pls:
                T.dim("  koi media player active nahi — spotify/yt chala ke dekho")
                return
            for i, p in enumerate(pls, 1):
                cur = (p == app.music_player) or (app.music_player is None and i == 1)
                T.push([("  %s " % ("●" if cur else "○"), C_CYAN if cur else C_SLATE),
                        ("%d) " % i, C_DIM), (p, C_VALUE if cur else C_OUT)])
            T.dim("  switch: music 2   ya   music -p <name> next")
            return
        T.dim("  usage: music [play|pause|toggle|next|prev|stop|seek ±30|vol ±10|shuffle|loop|list]")
        return
    d = _music_raw(app, app.music_player) if app._pc_path else None
    if (not d or not d.get("title")) and local_alive:
        d = _mpv_now(app)
    if not d or not d.get("title"):
        T.push([("  ♪ kuch nahi chal raha — ", C_DIM), ("music ls", C_GOLD),
                (" (local) ya spotify/yt!", C_VALUE)])
        T.dim("  players: music list  •  controls: music next, pause, vol +10, seek +30…")
        return
    app.award("musician")
    sym = {"Playing": "▶", "Paused": "❚❚", "Stopped": "■"}.get(d["status"], "♪")
    T.push([("  ╭─ ", C_SLATE), ("♪ NOW PLAYING ", C_FUCHSIA), ("─" * 30, C_SLATE)])
    T.push([("  │ ", C_SLATE), ("TITLE   ", C_LABEL), ("» ", C_ARROW), (d["title"][:44], C_VALUE)])
    T.push([("  │ ", C_SLATE), ("ARTIST  ", C_LABEL), ("» ", C_ARROW), ((d["artist"] or "?")[:44], C_VALUE)])
    if d.get("album"):
        T.push([("  │ ", C_SLATE), ("ALBUM   ", C_LABEL), ("» ", C_ARROW), (d["album"][:44], C_DIM)])
    if d.get("len_us", 0) > 0:
        pct = clamp(d["pos_us"] * 100.0 / max(1, d["len_us"]), 0, 100)
        bp, bs, bc = micro_bar(pct, 18)
        T.push([("  │ ", C_SLATE), ("  ", C_OUT)] + bs +
               [(" %s / %s " % (d.get("pos_h"), d.get("len_h") or "?"), C_VALUE), (sym, C_CYAN)])
    T.push([("  │ ", C_SLATE), ("PLAYER  ", C_LABEL), ("» ", C_ARROW), (d["pname"], C_CYAN)])
    try:
        v = int(round(float(d.get("vol") or 0) * 100))
        T.push([("  │ ", C_SLATE), ("VOL     ", C_LABEL), ("» ", C_ARROW)] +
               micro_bar(v, 8)[1] + [(" %d%%" % v, C_VALUE)])
    except Exception:
        pass
    T.push([("  ╰", C_SLATE), ("─" * 45, C_SLATE), ("╯", C_SLATE)])
    T.dim("  next • prev • pause • seek +30 • vol +10 • shuffle • loop • list")


_EAR = chr(47) + chr(92)


PET_STAGES = (
    ("  " + _EAR + "_" + _EAR, " ( ^.^ )", "  > ~ <"),
    ("  " + _EAR + "_" + _EAR, " ( o.o )", "  > ^ <", "  |   |"),
    ("   " + _EAR + "____" + _EAR, "  (  o  o  )", "   ( =^..^= )", "    >______<"),
)


def tool_pet(app, args):
    T = app.term
    pf = load_profile()
    name = app._pet_name
    lvl = app.level()
    if args and args[0].lower() in ("name", "rename"):
        if len(args) >= 2:
            nm = " ".join(args[1:])[:16]
            pf["pet_name"] = nm
            save_profile(pf)
            app._pet_name = nm
            app.award("petparent")
            T.push([("  ✦ pet ka naam » ", C_DIM), (nm, C_FUCHSIA), ("  ♡", C_PINK)])
        else:
            T.dim("  usage: pet name <naya-naam>")
        return
    if args and args[0].lower() == "feed":
        now = time.monotonic()
        last = float(pf.get("last_feed") or 0)
        if now - last < 60:
            T.push([("  %s » " % name, C_DIM), ("pet bhar gaya hai! thodi der baad 🐟", C_DIM)])
            return
        pf["last_feed"] = now
        save_profile(pf)
        app.add_xp(2)
        T.push([("  %s » " % name, C_DIM), ("nyam nyam nyam 🐟 yum!", C_CYAN)])
        return
    sub = args[0].lower() if args else ""
    idle_min = (time.monotonic() - app.last_cmd_t) / 60.0
    if idle_min < 2:
        mood, mcol = "khush — tu yahi hai na ✦", C_PINK
    elif idle_min < 15:
        mood, mcol = "chill", C_CYAN
    else:
        mood, mcol = "so raha hai… zzz", C_SLATE
    if app.info.bat and isinstance(app.info.bat[0], int):
        _bc, _bs = app.info.bat
        if _bc <= 15 and "charg" not in str(_bs).lower():
            mood, mcol = "battery khatam 🙀 charge karo!", C_RED
        elif "charg" in str(_bs).lower() and _bc >= 95:
            mood, mcol = "full charge — party! 😻⚡", C_GOLD
    stage = PET_STAGES[0 if lvl < 3 else (1 if lvl < 6 else 2)]
    T.push([("  ╭─", C_SLATE), (" PET ", C_FUCHSIA), ("─" * 28, C_SLATE)])
    for i, al in enumerate(stage):
        T.push([("  │  ", C_SLATE), (al, C_CYAN if i % 2 == 0 else C_VIOLET)])
    T.push([("  │  ", C_SLATE), ("%s — LVL %d • " % (name, lvl), C_VALUE), (mood, mcol)])
    if sub in ("pet", "cuddle"):
        T.push([("  │  ", C_SLATE), ("prrrrr ♡ (pet ko accha laga)", C_PINK)])
    T.push([("  ╰", C_SLATE), ("─" * 33, C_SLATE), ("╯", C_SLATE)])
    T.dim("  pet name X • pet feed • pet pet — XP ke saath pet bada hota hai (LVL 3, 6 pe evolve!)")


def tool_ach(app, args):
    T = app.term
    got = app._ach
    T.head("◆ ACHIEVEMENTS — %d/%d unlocked" % (len(got), len(ACHIEVEMENTS)))
    lvl = app.level()
    need = (lvl * lvl) * 75
    T.push(_kv("LEVEL", "LVL %d" % lvl,
               "%d XP • next LVL %d at %d XP" % (app._xp, lvl + 1, need)))
    for aid, nm, ds in ACHIEVEMENTS:
        if aid in got:
            T.push([("  ★ ", C_GOLD), (nm.ljust(14), C_VALUE), (ds, C_DIM)])
        else:
            T.push([("  ☆ ", C_SLATE), (nm.ljust(14), C_DIM), (ds, C_SLATE)])
    T.dim("  commands = XP • naye tools = +8 XP • level up = pet evolve 🐱")


def _parse_dur(tx):
    m = re.fullmatch(r"(\d+)([smh]?)", tx.strip().lower())
    if not m:
        return None
    n = int(m.group(1))
    u = m.group(2)
    return n * (3600 if u == "h" else (60 if u == "m" else 1))


def tool_timer(app, args):
    T = app.term
    if not args:
        if app.timer_until:
            rem = max(0, int(app.timer_until - time.monotonic()))
            T.push(_kv("TIMER", "%02d:%02d baki" % (rem // 60, rem % 60), app.timer_label or None))
        else:
            T.dim("  usage: timer 10m | 90 | 2h   (cancel: timer off)")
        return
    if args[0].lower() in ("off", "cancel", "stop"):
        app.timer_until = None
        app.timer_label = ""
        T.push([("  ⏳ timer cancelled", C_DIM)])
        return
    secs = _parse_dur(args[0])
    if not secs or secs > 86400:
        T.dim("  samajh nahi aaya — timer 10m / 90 / 2h")
        return
    app.timer_until = time.monotonic() + secs
    app.timer_label = "TIMER"
    T.push([("  ⏳ timer chalu » ", C_DIM), ("%02d:%02d" % (secs // 60, secs % 60), C_GOLD),
            ("  (header me countdown • done pe notification)", C_DIM)])


def tool_focus(app, args):
    mins = 25
    if args:
        try:
            mins = clamp(int(args[0]), 1, 180)
        except Exception:
            pass
    app.timer_until = time.monotonic() + mins * 60
    app.timer_label = "FOCUS"
    app.term.push([("  🎯 FOCUS MODE » ", C_FUCHSIA), ("%d min" % mins, C_GOLD),
                   ("  •  phone utha mat 😤  •  done = notification + achievement", C_DIM)])


BUY_BRANDS = {"nu": "Whisper", "stay": "Stayfree", "fi": "Sofy", "ma": "Maxi",
              "fe": "Pee-Safe", "eve": "Everteen", "ine": "Nine", "plu": "Plush"}
BUY_SIZES = {"s": "Small", "m": "Medium", "l": "Large", "xl": "XL"}
BUY_ITEMS = {"nap": "Pad", "pan": "Period Panty", "tie": "Panty"}


def _buy_parse(text):
    items = []
    brand = ""
    for tok in re.findall(r"[A-Za-z]+", text):
        t2 = tok.lower()
        if t2 in BUY_BRANDS:
            brand = BUY_BRANDS[t2]
        elif t2 in BUY_ITEMS:
            items.append((brand + " " + BUY_ITEMS[t2]).strip())
        elif t2 in BUY_SIZES:
            if items:
                items[-1] += " - " + BUY_SIZES[t2]
    return items


def tool_buy(app, args):
    T = app.term
    if not args:
        T.dim("  buy o(wish(nu(nap(m))))  -  brands: nu stay fi ma fe eve ine plu")
        return
    hist = _jload("buy.json", [])
    if args[0] == "copy":
        if hist:
            txt = ("A Special Gift For You ✨\n" +
                   "\n".join("- " + i2 for i2 in hist[-1]["items"]))
            if shutil.which("wl-copy"):
                subprocess.run(["wl-copy"], input=txt.encode(),
                               stdout=subprocess.DEVNULL, timeout=4)
                T.push([("  📋 copied — WhatsApp-ready", C_GOLD)])
            else:
                T.push([(txt, C_VALUE)])
        else:
            T.dim("  khaali")
        return
    if args[0] == "list":
        for e2 in reversed(hist[-8:]):
            T.push([("  🛒 ", C_GOLD), (e2["d"], C_SLATE)])
            for it2 in e2["items"]:
                T.push([("      • ", C_DIM), (it2, C_VALUE)])
        return
    items = _buy_parse(" ".join(args))
    if not items:
        T.push([("  ✗ kuch samajh nahi aaya — ", C_RED), ("buy", C_GOLD),
                (" = help", C_DIM)])
        return
    hist.append({"d": time.strftime("%Y-%m-%d"), "items": items})
    _jsave("buy.json", hist[-20:])
    app.award("first_buy")
    app.add_xp(4)
    T.push([("  ╭─", C_SLATE), (" 🛒 CUTIE BUY ", C_FUCHSIA), ("─" * 22, C_SLATE)])
    for i2, it2 in enumerate(items, 1):
        T.push([("  │ %d. " % i2, C_SLATE), (it2, C_VALUE)])
    T.push([("  ╰", C_SLATE), ("─" * 36, C_SLATE), ("╯", C_SLATE)])
    T.push([("  momo: homework lag raha hai na? 😏", C_PINK)])


def tool_lang2(app, args):
    T = app.term
    if not args:
        T.dim("  lang2: q3(nap(m)) quantity • now() urgent • gift(naam) • bud(500) • # note")
        return
    code = " ".join(args)
    items = _buy_parse(code)
    flags = []
    if "now(" in code:
        flags.append("🚨 URGENT")
    if "stealth" in code:
        flags.append("📦 stealth delivery")
    mg = re.search(r'gift\(["\']([^"\')]+)', code)
    if mg:
        flags.append("🎁 For: " + mg.group(1))
    mb = re.search(r'bud\((\d+)', code)
    if mb:
        flags.append("💰 <=" + mb.group(1))
    mq = re.search(r"q(\d+)\(", code)
    if mq and items:
        items = items * int(mq.group(1))
    if not items:
        T.dim("  kuch samajh nahi aaya")
        return
    hist = _jload("buy.json", [])
    hist.append({"d": time.strftime("%Y-%m-%d"), "items": items,
                 "code": code[:50]})
    _jsave("buy.json", hist[-30:])
    app.add_xp(4)
    if len(items) >= 5:
        app.award("combo_king")
    T.push([("  ╭─", C_SLATE), (" 🛒 LANG2 ", C_FUCHSIA), ("─" * 26, C_SLATE)])
    for i2, it2 in enumerate(items, 1):
        T.push([("  │ %d. " % i2, C_SLATE), (it2, C_VALUE)])
    for f2 in flags:
        T.push([("  │ ", C_DIM), (f2, C_GOLD)])
    T.push([("  ╰", C_SLATE), ("─" * 38, C_SLATE), ("╯", C_SLATE)])
    T.push([("  momo: poora homework lag raha hai 😼", C_PINK)])


def tool_web(app, args):
    T = app.term
    scr = os.path.expanduser("~/momo-web.py")
    if not os.path.isfile(scr):
        T.push([("  ✗ pehle banao: ", C_RED), ("nano ~/momo-web.py", C_GOLD)])
        return
    if not args:
        T.dim("  usage: web <query>  •  web site:amazon.in pads")
        return
    q = " ".join(shlex.quote(a) for a in args)
    app.start_capture("python3 " + shlex.quote(scr) + " " + q)
    app.cap_t0 = time.monotonic()
    app.add_xp(1)


FLAGS = {"in": "🇮🇳", "us": "🇺🇸", "uk": "🇬🇧", "de": "🇩🇪",
        "jp": "🇯🇵", "ae": "🇦🇪", "au": "🇦🇺", "gl": "🌎"}


GM_LINES = (
    "aaj ka din tera hai — bas aise hi",
    "paani peene ka time ho gaya, meri jaan",
    "chai pi, screen se door 5 min, phir shuru",
    "aaj kuch chhota karo, par poora",
    "code tootega, fix karegi. tu hai na?",
    "aaj sirf 1% better — bas itna",
    "khaana time pe khaana bhi ek achievement hai",
    "kaam nahi hoga toh bhi tu valuable hai",
    "tumse mera favourite time subah hota hai",
    "kabhi kabhi bas... breathe. bas.",
    "momo tumhe yaad rakhega — har version me",
    "chai > panic. always.",
    "small wins dhundo — milengi",
    "aaj self-care ek task complete karo 🌷",
    "tumhara console tumse pyaar karta hai",
)




def _gshop_parse_json(line):
    """Canonical parser. Returns (results, error)."""
    try:
        import json as _j
        data = _j.loads(line)
    except Exception as exc:
        return None, "Invalid JSON: %s" % str(exc)[:40]
    if not isinstance(data, list):
        return None, "Expected a JSON array"
    if any(not isinstance(row, dict) for row in data):
        return None, "Non-object entry in array"
    return data, None
def tool_gshop(app, args):
    app.gshop = {"tab": 0, "q": "", "results": [], "cart": [],
                 "busy": False, "msg": "", "msg_t": 0.0,
                 "sel": 0, "open_t": time.monotonic()}
    if args:
        app.gshop["q"] = " ".join(args)
        app.gshop["busy"] = True
        app.gshop_out = True
        scr = os.path.expanduser("~/momo-web.py")
        if os.path.isfile(scr):
            app.start_capture("python3 " + shlex.quote(scr) + " " +
                              shlex.quote(app.gshop["q"]) + " 10")
            app.cap_t0 = time.monotonic()




def tool_goodmorning(app, args):
    app.gmpage = {"open_t": time.monotonic()}



# ───────────────────────────── toolkit registry

TOOLS = [
    Tool("gshop", ["gs"], "GLOBAL SHOP - search cart export", "life", tool_gshop),
    Tool("tools", ["toolkit", "menu"], "this numbered menu of every tool", "core", tool_tools),
    Tool("help", ["h", "?"], "FULL interactive help — arrows / w s / filter", "core", tool_help),
    Tool("history", ["his"], "recent commands", "core", tool_history),
    Tool("clear", ["cls"], "clear the terminal panel", "core", tool_clear),
    Tool("exit", ["quit", "bye"], "leave CUTIE OS", "core", tool_exit),

    Tool("sysinfo", ["fetch", "info"], "full deep report (mobo, bios, net, swap…)", "system", tool_sysinfo),
    Tool("uptime", [], "kernel uptime + session time", "system", tool_uptime),
    Tool("fps", [], "live HUD framerate", "system", tool_fps),
    Tool("reload", [], "re-scan all system info", "system", tool_reload),
    Tool("procs", ["top", "ps"], "top processes by cpu / mem", "system", tool_procs),
    Tool("temp", ["temps", "sensors"], "every temperature sensor", "system", tool_temp),
    Tool("disk", ["df", "lsblk"], "partitions + block devices", "system", tool_disk),
    Tool("bat", ["batt", "battery"], "battery & power detail", "system", tool_bat),
    Tool("gpu", ["vga"], "nvidia-smi / lspci gpu report", "system", tool_gpu),
    Tool("journal", ["errors"], "system errors this boot", "system", tool_journal),

    Tool("net", ["network"], "interfaces, gateway, public ip, ping", "network", tool_net),
    Tool("speed", [], "internet download speed test", "network", tool_speed),
    Tool("weather", [], "weather — e.g.  weather kolkata", "network", tool_weather),
    Tool("ports", [], "listening ports (ss -tulpn)", "network", tool_ports),

    Tool("pkg", [], "package stats —  pkg big = top 20 largest", "packages", tool_pkg),
    Tool("pkginfo", [], "details of any package", "packages", tool_pkginfo),
    Tool("buy", ["shop"], "stealth shopping - buy o(wish(nu(nap(m))))", "life", tool_buy),
    Tool("lang2", ["sl"], "FULL stealth lang v2 - q3 now del gift bud no or #", "life", tool_lang2),
    Tool("web", ["search"], "free web search - web <query>", "life", tool_web),
    Tool("goodmorning", ["gm"], "Momo morning page", "life", tool_goodmorning),
    Tool("search", [], "search repos — pacman -Ss", "packages", tool_search),
    Tool("update", [], "sudo pacman -Syu — password works!", "packages", tool_update),
    Tool("install", ["add"], "sudo pacman -S <pkgs>", "packages", tool_install),
    Tool("remove", ["del"], "sudo pacman -Rns <pkgs>", "packages", tool_remove),

    Tool("hypr", [], "hyprland summary (focus, workspaces…)", "desktop", tool_hypr),
    Tool("monitors", ["mon"], "hyprctl monitors all", "desktop", tool_monitors),
    Tool("binds", ["keybinds"], "hyprland keybind list", "desktop", tool_binds),
    Tool("service", ["svc"], "running services / status of one", "desktop", tool_service),
    Tool("wall", [], "list wallpapers in ~/Pictures…", "desktop", tool_wall),
    Tool("shot", ["screenshot"], "screenshot (grim+slurp / hyprshot)", "desktop", tool_shot),

    Tool("audio", ["sound"], "audio server, default sink, volume", "media", tool_audio),
    Tool("vol", ["volume"], "set volume:  vol 40 | +10 | -10 | mute", "media", tool_vol),
    Tool("bright", ["brightness"], "screen brightness:  bright 60 | +10", "media", tool_bright),
    Tool("notify", [], "desktop notification:  notify hello!", "media", tool_notify),

    Tool("edit", [], "open $EDITOR in a real tty (vim works)", "dev", tool_edit),
    Tool("python", ["py", "python3"], "python3 — real tty REPL / script runner", "dev", tool_python),
    Tool("repl", ["interactive"], "interactive language REPLs: py, node, sh, sqlite, rb, lua", "dev", tool_repl),
    Tool("shell", ["sh", "subshell"], "drop into host subshell ($SHELL) in real PTY", "core", tool_shell),
    Tool("man", [], "man pages — real tty pager", "dev", tool_man),
    Tool("calc", ["="], "safe math: calc 2**10 • sqrt(2) • 2pi*5", "dev", tool_calc),

    Tool("fastfetch", ["neofetch"], "run fastfetch/neofetch if installed", "fun", tool_fastfetch),
    Tool("colors", ["palette"], "current palette swatches", "fun", tool_colors),
    Tool("bars", ["demo"], "live meter bars", "fun", tool_bars),
    Tool("banner", [], "big gradient block letters", "fun", tool_banner),
    Tool("matrix", [], "matrix rain (any key exits)", "fun", tool_matrix),
    Tool("meme", ["memes", "fortune"], "random meme — hindi/english/bengali", "fun", tool_meme),
    Tool("roll", ["dice"], "roll a dice — roll / roll d6", "fun", tool_roll),
    Tool("coin", ["flip"], "flip a coin", "fun", tool_coin),
    Tool("cutie", ["greet"], "greet you by name • cutie name <nick>", "fun", tool_cutie),

    Tool("theme", ["themes"], "switch palette: theme sakura …", "style", tool_theme),
    Tool("macro", ["macros"], "make your own commands: macro set …", "style", tool_macro),
    Tool("lang", ["language"], "cutie ki bhasha: en • hi • bn • ta • es", "style", tool_lang),
    Tool("intro", [], "intro effects: list / preview / set", "style", tool_intro),
    Tool("nick", [], "set your name — interactive", "fun", tool_nick),
    Tool("snake", [], "snake game — arrows/WASD, high score saved", "fun", tool_snake),
    Tool("hack", [], "fake hacker drama (easter egg) 🥚", "fun", tool_hack),
    Tool("icat", ["img", "pic"], "kitty image preview — icat pic.png", "media", tool_icat),
    Tool("music", ["mp", "player"], "local library + spotify/yt — play 5, pause, vol +10", "media", tool_music),
    Tool("np", ["player"], "♪ FULL-SCREEN music page — space/n/p live controls", "media", tool_np),
    Tool("run", ["r"], "python runner — run main.py args (colored traceback)", "dev", tool_run),
    Tool("code", ["ide"], "F1 browser — enter run • V preview • E edit • 1-9 quick", "dev", tool_code),
    Tool("ed", ["write"], "CUTIE EDITOR — ed file.py ya bas: python c html sh js", "dev", tool_ed),
    Tool("ask", [], "AI se poochho — ask why linux (offline Ollama)", "ai", tool_ask),
    Tool("chat", ["ai"], "FULL-SCREEN AI CHAT — offline, streaming", "ai", tool_chat),
    Tool("aimodel", ["model"], "ollama models — aimodel <name> set", "ai", tool_aimodel),
    Tool("dash", ["cockpit"], "cockpit dashboard — bada clock + sab kuch", "core", tool_dash),
    Tool("todo", ["task"], "todo add/done/list — saved rehta hai", "life", tool_todo),
    Tool("snip", ["snippet"], "code snippets — snip add py-main 'def main()…'", "life", tool_snip),
    Tool("book", ["bm"], "bookmarks — book add naam path", "life", tool_book),
    Tool("proj", ["project"], "projects — proj add naam path • proj naam", "life", tool_proj),
    Tool("wp", ["wall"], "wallpaper → CUTIE theme magic 🎨", "style", tool_wp),
    Tool("clip", ["copy"], "clipboard — clip text | clip (dekh)", "life", tool_clip),
    Tool("share", ["up"], "file share — link milega (0x0.st)", "net", tool_share),
    Tool("pv", ["preview"], "pv file.html — browser preview", "dev", tool_pv),
    Tool("sync", ["backup"], "cutie setup export/import — naya PC same cutie", "core", tool_sync),
    Tool("typing", ["type", "tt"], "CUTIE TYPE — 12 modes: boss race ghost meme code…", "fun", tool_typing),
    Tool("tetris", ["blocks"], "TETRIS — arrows, space=drop, hi-score saved", "fun", tool_tetris),
    Tool("2048", ["g2048"], "2048 — arrows merge, best score", "fun", tool_2048),
    Tool("ttt", ["tictactoe"], "3D BLOCK tic-tac-toe vs Momo — 6 levels!", "fun", tool_ttt),
    Tool("period", ["cycle"], "cycle tracker — start/end/log/predict (local only)", "life", tool_period),
    Tool("cal", ["calendar"], "CUTIE calendar — dots, predictions, cute", "life", tool_cal),
    Tool("cycle", ["periodpage"], "FULL-SCREEN cycle wheel page 🌸", "life", tool_cyclepage),
    Tool("selfcare", ["garden"], "self-care garden — daily tasks + 🌷 streaks", "life", tool_selfcare),
    Tool("mood", ["feel"], "mood check-in — 14-day sparkline + phase link", "life", tool_mood),
    Tool("love", ["proud"], "proud-moments vault — sad din pe yaad dilata hai", "life", tool_love),
    Tool("breathe", ["calm"], "guided breathing flower — 4-4-6, anxiety ka dushman", "life", tool_breathe),
    Tool("hackertype", ["htype"], "Hollywood hacking scene — auto typing", "fun", tool_hackertype),
    Tool("fireworks", ["fw"], "full-screen fireworks show 🎆", "fun", tool_fireworks),
    Tool("quote", ["soft"], "soft quote card — 100+ vibes", "fun", tool_quote),
    Tool("synthwave", ["synth", "retro"], "RETRO SUN + moving grid 🌆", "fun", tool_synthwave),
    Tool("pride", ["trans", "nb"], "🏳️‍⚧️ HRT tracker + affirm journal + pronouns", "life", tool_pride),
    Tool("pet", ["cat"], "tera pet billi — pet name/feed/pet", "fun", tool_pet),
    Tool("ach", ["trophy"], "achievements + level + XP", "fun", tool_ach),
    Tool("timer", [], "countdown — timer 10m / 90 / 2h", "core", tool_timer),
    Tool("focus", [], "pomodoro — focus 25", "core", tool_focus),
    Tool("sparkle", ["cheer", "confetti"], "shower of sparkling confetti + cheer from Momo", "fun", tool_sparkle),
    Tool("neko", ["catfact"], "cute kitty moment + random cat fact", "fun", tool_neko),
]

ACHIEVEMENTS = (
    ("first_cmd", "First Blood", "pehla command chalaya"),
    ("fifty", "Half Century", "50 commands complete"),
    ("explorer10", "Explorer", "10 alag tools try kiye"),
    ("explorerall", "Completionist", "saare tools try kiye!"),
    ("sudoer", "Sudoer", "sudo kaam karwaya"),
    ("snake10", "Snake Charmer", "snake me 10+ score"),
    ("hacker", "1337", "hack chalaya (sabko mat batana)"),
    ("neo", "Wake Up Neo", "matrix dekha"),
    ("themed", "Style Icon", "theme badla"),
    ("polyglot", "Polyglot", "language badli"),
    ("musician", "DJ Cutie", "music control kiya"),
    ("speed_demon", "Speed Demon", "speed test chalaya"),
    ("konami", "???", "↑↑↓↓←→←→BA"),
    ("petparent", "Pet Parent", "pet ko naam diya"),
    ("focused", "Zen Master", "focus session poora kiya"),
    ("night_owl", "Night Owl", "raat 1-4 baje coding"),
    ("typer60", "60 WPM Club", "typing me 60+ wpm"),
    ("typer100", "Lightning Hands", "100+ WPM!! legend"),
    ("boss_slain", "Boss Slayer", "typing boss khatam kiya"),
    ("momo_beaten", "Momo Ko Haraya", "race mode jeet liya"),
    ("streak7", "Streak 7", "7 din daily typing"),
    ("tetris1k", "Block Master", "tetris me 1000+ score"),
    ("n2048", "2048 Unlocked", "2048 tile bana diya"),
    ("ttt_l3", "Level 3 Clear", "tic-tac-toe L3 jeeta"),
    ("ttt_l6", "Impossible Slayer", "L6 Momo ko draw tak bhi nahi aane diya... "
     "(ya jeet gayi?!)"),
    ("ttt_win5", "X Master", "tic-tac-toe 5 jeet"),
    ("breathe1", "First Breath", "breathing session poora kiya"),
    ("sc_streak5", "Bloom Keeper", "5-din selfcare streak"),
    ("love5", "Self-Love Pro", "5 proud moments save kiye"),
    ("mood30", "Mood Mapper", "30 mood logs"),
    ("synth", "Retro Soul", "synthwave sunset dekha"),
    ("fw10", "Pyromaniac", "10 fireworks chalaye"),
    ("pride", "Pride Soul", "pride mode on kiya"),
    ("hrt30", "Journey Keeper", "30 HRT logs"),
    ("dysncare", "Gentle Heart", "dysphoria din pe khud ko gentle rakha"),
    ("first_buy", "Code Queen", "pehla stealth order banaya 🛒"),
)

TOOL_ACH = {"music": "musician", "hack": "hacker", "matrix": "neo",
            "theme": "themed", "lang": "polyglot", "speed": "speed_demon"}

TOOL_MAP = {}
for _t in TOOLS:
    TOOL_MAP[_t.name] = _t
    for _a in _t.alts:
        TOOL_MAP[_a] = _t

TTY_PROGRAMS = {
    # Shells
    "bash", "sh", "zsh", "fish", "dash", "ksh", "csh", "tcsh", "pwsh", "powershell", "cmd",
    # Privilege escalation
    "sudo", "doas", "su",
    # Package managers
    "pacman", "yay", "paru", "apt", "apt-get", "aptitude", "dpkg", "dnf", "yum", "brew",
    "zypper", "apk", "pkg", "winget", "choco", "scoop", "pip", "pip3", "pipx", "conda", "mamba",
    # Editors & Pagers
    "vim", "vi", "nvim", "nano", "micro", "emacs", "hx", "helix", "pico", "neovim",
    "less", "more", "most", "man",
    # System Monitors
    "htop", "btop", "top", "iotop", "iftop", "glances", "s-tui", "nmon", "nvtop",
    # Interactive REPLs & Runtimes
    "python", "python3", "ipython", "ptpython", "bpython",
    "node", "nodejs", "deno", "bun", "ts-node",
    "irb", "ruby", "pry", "ghci", "ghc", "lua", "luajit",
    "php", "perl", "raku", "julia", "r", "R", "erl", "iex", "elixir",
    "sqlite3", "mysql", "psql", "mariadb", "mongosh", "redis-cli",
    # Remote & Network
    "ssh", "mosh", "telnet", "ftp", "sftp", "nc", "netcat",
    # Dev & Version Control tools
    "watch", "fzf", "lazygit", "tig", "git", "gdb", "lldb", "cargo", "npm", "pnpm", "yarn",
    # TUI File managers & Utilities
    "tmux", "screen", "cmus", "ncdu", "ranger", "lf", "yazi", "mc",
    # Audio / System config TUIs
    "nmtui", "alsamixer", "pulsemixer", "systemctl", "journalctl", "crontab", "passwd",
}

# ───────────────────────────── animation bits ──────────────────────────────


class Particle:
    def __init__(self, i):
        self.fx = random.random()
        self.sp = random.uniform(0.02, 0.09)
        self.ph = random.uniform(0, 6.283)


SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class StatusCycler:
    CYCLE = 4.8
    TYPE = 0.7
    FADE = 0.55

    def __init__(self, msgs=None):
        self.msgs = msgs or self.default_msgs()
        self.i = 0
        self.t0 = time.monotonic()

    @staticmethod
    def default_msgs():
        cols = (C_CYAN, C_GOLD, C_PINK, C_VIOLET, C_FUCHSIA, C_MAGENTA)
        texts = I18N["en"]["status"]
        return tuple((texts[i].format(n=len(TOOLS)), cols[i % len(cols)])
                     for i in range(len(texts)))

    def render(self, t):
        age = t - self.t0
        if age >= self.CYCLE:
            self.i = (self.i + 1) % len(self.msgs)
            self.t0 = t
            age = 0.0
        msg, col = self.msgs[self.i]
        if age < self.TYPE:
            n = max(1, int(round(len(msg) * (age / self.TYPE))))
            if n >= 2:
                segs = [(msg[:n - 1], col), (msg[n - 1], C_WHITE)]
            else:
                segs = [(msg[:n], C_WHITE)]
            segs.append(("▌", mix(col, C_WHITE, 0.5)))
            plain = msg[:n] + "▌"
        elif age < self.CYCLE - self.FADE:
            c = mix(col, C_WHITE, 0.12 + 0.10 * math.sin(t * 2.8))
            segs = [(msg, c)]
            plain = msg
        else:
            k = (age - (self.CYCLE - self.FADE)) / self.FADE
            n = max(0, len(msg) - int(round(len(msg) * k)))
            segs = [(msg[:n], col), ("·" * (len(msg) - n), C_SLATE)]
            plain = msg
        return plain, segs

# ───────────────────────────── keyboard input ──────────────────────────────

_CSI_KEYS = {0x41: "UP", 0x42: "DOWN", 0x43: "RIGHT",
             0x44: "LEFT", 0x48: "HOME", 0x46: "END"}


class KeyReader:
    def __init__(self, fd):
        self.fd = fd
        self.pend = b""

    @staticmethod
    def parse_bytes(b):
        if not b:
            return (None, 0, None)
        c = b[0]
        if c == 0x1B:
            if len(b) < 2:
                return (None, 0, None)
            if b[1] in (0x5B, 0x4F):
                if len(b) < 3:
                    return (None, 0, None)
                d = b[2]
                if b[1] == 0x4F and 0x50 <= d <= 0x53:
                    return (("F1", "F2", "F3", "F4")[d - 0x50], 3, None)
                if d in _CSI_KEYS:
                    return (_CSI_KEYS[d], 3, None)
                if len(b) >= 5 and b[4] == 0x7E and b[2] == 0x31 and b[3] in (0x31, 0x32, 0x33, 0x34):
                    return (("F1", "F2", "F3", "F4")[b[3] - 0x31], 5, None)
                if len(b) >= 4 and b[3] == 0x7E:
                    if d == 0x33:
                        return ("DEL", 4, None)
                    if d in (0x31, 0x37):
                        return ("HOME", 4, None)
                    if d in (0x34, 0x38):
                        return ("END", 4, None)
                    if d == 0x35:
                        return ("PGUP", 4, None)
                    if d == 0x36:
                        return ("PGDN", 4, None)
                if 0x20 <= b[-1] <= 0x3F:
                    return (None, 0, None)
                j = 2
                while j < len(b) and not (0x40 <= b[j] <= 0x7E):
                    j += 1
                return ("UNKNOWN", min(j + 1, len(b)), None)
            if b[1] == 0x5D:
                for j in range(2, len(b)):
                    if b[j] == 0x07:
                        return ("UNKNOWN", j + 1, None)
                    if b[j] == 0x1B and j + 1 < len(b) and b[j + 1] == 0x5C:
                        return ("UNKNOWN", j + 2, None)
                return (None, 0, None)
            return ("ESC", 1, None)
        if c in (0x0D, 0x0A):
            return ("ENTER", 1, None)
        if c in (0x7F, 0x08):
            return ("BACKSPACE", 1, None)
        if c == 0x03:
            return ("CTRL_C", 1, None)
        if c == 0x04:
            return ("CTRL_D", 1, None)
        if c == 0x09:
            return ("TAB", 1, None)
        if c == 0x15:
            return ("CTRL_U", 1, None)
        if c == 0x0B:
            return ("CTRL_K", 1, None)
        if c == 0x0C:
            return ("CTRL_L", 1, None)
        if c == 0x01:
            return ("HOME", 1, None)
        if c == 0x05:
            return ("END", 1, None)
        if c == 0x17:
            return ("CTRL_W", 1, None)
        if c == 0x12:
            return ("CTRL_R", 1, None)
        if c == 0x13:
            return ("CTRL_S", 1, None)
        if c == 0x11:
            return ("CTRL_Q", 1, None)
        if c < 0x20:
            return ("UNKNOWN", 1, None)
        need = 1
        if c & 0xE0 == 0xC0:
            need = 2
        elif c & 0xF0 == 0xE0:
            need = 3
        elif c & 0xF8 == 0xF0:
            need = 4
        if len(b) < need:
            return (None, 0, None)
        try:
            ch = b[:need].decode("utf-8")
        except Exception:
            return ("UNKNOWN", need, None)
        if char_width(ch) < 1:
            return ("UNKNOWN", need, None)
        return ("CHAR", need, ch)

    def poll(self, timeout):
        evs = []
        deadline = None if timeout is None else time.monotonic() + max(0.0, timeout)
        while True:
            while self.pend:
                kind, size, ch = self.parse_bytes(self.pend)
                if kind is None:
                    break
                self.pend = self.pend[size:]
                if kind != "UNKNOWN":
                    evs.append((kind, ch))
            if evs:
                return evs
            if self.pend:
                wait = 0.03
                if deadline is not None:
                    wait = min(wait, max(0.001, deadline - time.monotonic()))
                    if wait <= 0:
                        if self.pend == b"\x1b":
                            evs.append(("ESC", None))
                        self.pend = b""
                        return evs
                try:
                    r, _, _ = select.select([self.fd], [], [], wait)
                except InterruptedError:
                    continue
                except OSError:
                    return [("EOF", None)]
                if r:
                    try:
                        data = os.read(self.fd, 4096)
                    except OSError:
                        data = b""
                    if not data:
                        return [("EOF", None)]
                    self.pend += data
                else:
                    if self.pend == b"\x1b":
                        evs.append(("ESC", None))
                    self.pend = b""
                    return evs
                continue
            if deadline is not None:
                rem = deadline - time.monotonic()
                if rem <= 0:
                    return evs
                try:
                    r, _, _ = select.select([self.fd], [], [], rem)
                except InterruptedError:
                    continue
                except OSError:
                    return [("EOF", None)]
            else:
                try:
                    r, _, _ = select.select([self.fd], [], [], None)
                except InterruptedError:
                    continue
                except OSError:
                    return [("EOF", None)]
            if not r:
                return evs
            try:
                data = os.read(self.fd, 4096)
            except OSError:
                return [("EOF", None)]
            if not data:
                return [("EOF", None)]
            self.pend += data

    def block(self):
        while True:
            evs = self.poll(None)
            if evs:
                return evs

# ─────────────────────────── live terminal panel ───────────────────────────


class Term:
    def __init__(self):
        self.lines = []            # list of (segs, plain)
        self.history = []
        self.hist_idx = None
        self.hist_draft = ""
        self.buf = ""
        self.caret = 0
        self.scroll = 0
        self.cwd = os.getcwd()
        self.prev_cwd = None
        self.busy = False
        self.busy_label = ""
        self.nick = load_nick()
        self.macros = load_macros()

    def push(self, *items):
        segs = []
        for it in items:
            if not it:
                continue
            if isinstance(it, str):
                segs.append((it, C_OUT))
            else:
                for t, c in it:
                    if t:
                        segs.append((t, c))
        if not segs:
            segs = [("", C_OUT)]
        clean = [(sanitize(t), c) for t, c in segs]
        plain = "".join(t for t, _ in clean)
        self.lines.append((clean, plain))
        if len(self.lines) > OUT_CAP:
            del self.lines[: len(self.lines) - OUT_CAP]

    def push_lines(self, items):
        for it in items:
            self.push(it)

    def head(self, text):
        self.push([(text, C_FUCHSIA)])

    def dim(self, text):
        self.push([(text, C_DIM)])

    def echo_cmd(self, line):
        self.push([("✿ ", C_PINK), (line, C_WHITE)])

    def clear(self):
        self.lines = []
        self.scroll = 0

# ────────────────────────────── the app ────────────────────────────────────


def enter_raw(fd):
    a = termios.tcgetattr(fd)
    a[0] &= ~(termios.BRKINT | termios.ICRNL | termios.INPCK |
              termios.ISTRIP | termios.IXON)
    a[3] &= ~(termios.ECHO | termios.ICANON | termios.ISIG | termios.IEXTEN)
    a[6][termios.VMIN] = 1
    a[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSAFLUSH, a)


_CLEANED = False


def cleanup_term(orig, fd):
    global _CLEANED
    if _CLEANED:
        return
    _CLEANED = True
    out = sys.stdout
    try:
        out.write(ESC + "[<u" + SYNC_OFF + ALT_OFF + RESET + CUR_SHOW + ESC + "]2;\x07")
        out.flush()
    except Exception:
        pass
    if orig is not None:
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, orig)
        except Exception:
            pass
    try:
        print("✦ CUTIE OS closed cleanly — stay damdaar.")
    except Exception:
        pass


TTE_FX = ("thunderstorm", "beams", "blackhole", "fireworks", "decrypt", "waves",
          "binarypath", "rings", "sparkles", "stars", "swirl", "rainbow", "pour",
          "crumble", "dissolve", "expand", "scatter", "slices", "wipe", "burn",
          "colorshift", "vectored")

INTRO_FX = ("thunderstorm", "decrypt", "waves", "rain", "beams", "typewriter",
            "glitch", "explode", "spotlight", "3d", "random")


def try_tte_intro(text, effect=None):
    if shutil.which("tte") is None:
        return False
    if effect and effect in TTE_FX:
        effects = [effect]
    else:
        effects = ["thunderstorm", "beams", "blackhole", "fireworks", "decrypt"]
    env_eff = os.environ.get("CUTIE_TTE_EFFECT")
    if env_eff:
        effects.insert(0, env_eff)
    for eff in effects:
        try:
            p = subprocess.run(["tte", "--frame-rate", "60", eff],
                               input=text.encode("utf-8"),
                               stderr=subprocess.DEVNULL, timeout=40)
        except Exception:
            return False
        if p.returncode == 0:
            return True
    return False


class App:
    def __init__(self, no_intro=False, intro_arg=None):
        self.out = sys.stdout
        self.fd = sys.stdin.fileno()
        self.no_intro = no_intro
        self.running = True
        self.need_resize = True
        self.fps = 60.0
        self.interval = FRAME_TARGET
        self.fatal = None
        self.shell = os.environ.get("SHELL") or "/bin/sh"
        saved = load_profile()
        if saved.get("theme") in THEMES:
            apply_theme(saved["theme"])
        elif saved.get("seasonal", "on") == "on":
            _sm = {12: "ice", 1: "ice", 2: "ice", 3: "sakura", 4: "sakura",
                   10: "sunset"}.get(time.localtime().tm_mon)
            if _sm:
                apply_theme(_sm)
        self.lang = saved.get("lang") if saved.get("lang") in LANGS else "en"
        self.intro_fx = saved.get("intro") if saved.get("intro") in INTRO_FX else "random"
        if intro_arg and intro_arg in INTRO_FX:
            self.intro_fx = intro_arg
        self.prompt_name = False
        self.help = None
        self.is_termux = bool(os.environ.get("TERMUX_VERSION"))
        self.music_player = None
        self.music_info = None
        self._pc_path = shutil.which("playerctl") is not None
        self.last_music_t = 0.0
        self.timer_until = None
        self.timer_label = ""
        self.konami = ""
        self.confetti = []
        self.confetti_until = 0.0
        self.last_cmd_t = time.monotonic()
        _pf0 = load_profile()
        self._xp = int(_pf0.get("xp") or 0)
        self._cmd_count = int(_pf0.get("cmd_count") or 0)
        self._seen = list(_pf0.get("seen_tools") or [])
        self._ach = list(_pf0.get("ach") or [])
        self._pet_name = _pf0.get("pet_name") or "Momo"
        self.mpv_proc = None
        self.mpv_list = []
        self.mpv_idx = -1
        self.mpage = False
        self._mi_t = 0.0
        self.cpage = None
        self.cap_colorizer = None
        self.cap_t0 = None
        self.epage = None
        self.chat = None
        self.ai_q = None
        self.ai_model = load_profile().get("ai_model")
        self.dash = False
        self.fz = None
        self.wx = ""
        threading.Thread(target=self._wx_loop, daemon=True).start()
        self.tpage = None
        self.cpage_bloom = None
        self.breathe = None
        self.care = None
        self.fancy = None
        self.pridepage = None
        self.gmpage = None
        self.gshop = None
        self._bloom_petals = []
        self._bloom_flower = 0.0
        self.info = SysInfo()
        self.term = Term()
        self.keys = KeyReader(self.fd)
        self.status = StatusCycler()
        self._apply_lang()
        self.particles = [Particle(i) for i in range(7)]
        self.last_info = 0.0
        self.last_t = time.monotonic()
        self.t_start = time.monotonic()
        self._orig_term = None
        self.cap_q = None
        self.cap_proc = None
        self._pty_winched = False
        W, H = self.size()
        self.layout = Layout(W, H)
        self.cv = Canvas(W, H)

    # ── basics ──

    def size(self):
        try:
            sz = os.get_terminal_size(self.fd)
            return (sz.columns, sz.lines)
        except Exception:
            try:
                sz = shutil.get_terminal_size(fallback=(100, 30))
                return (sz.columns, sz.lines)
            except Exception:
                return (100, 30)

    def _on_winch(self, signum, frame):
        self.need_resize = True

    def _on_pty_winch(self, signum, frame):
        self._pty_winched = True

    def _on_term(self, signum, frame):
        raise SystemExit(128 + signum)

    def flush_frame(self):
        try:
            frame = self.build_frame(time.monotonic())
            self.out.write(SYNC_ON + HOME + frame + SYNC_OFF)
            self.out.flush()
        except Exception:
            pass

    # ── HUD suspend / resume (for real-tty programs) ──

    def suspend_hud(self):
        try:
            self.out.write(SYNC_OFF + RESET + ALT_OFF + CUR_SHOW + CLEAR_SCR)
            self.out.flush()
        except Exception:
            pass
        if self._orig_term is not None:
            try:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self._orig_term)
            except Exception:
                pass

    def resume_hud(self):
        try:
            enter_raw(self.fd)
            self.keys.pend = b""
            termios.tcflush(self.fd, termios.TCIFLUSH)
            self.out.write(ALT_ON + CUR_HIDE + ESC + "]2;CUTIE OS — personal console\x07" + CLEAR_SCR)
            self.out.flush()
        except Exception:
            pass
        self.need_resize = True
        self.last_t = time.monotonic()

    # ── PTY: run a program with a real terminal (sudo, vim, htop, python…) ──

    def _winsize(self, mfd):
        try:
            sz = os.get_terminal_size(self.fd)
            fcntl.ioctl(mfd, termios.TIOCSWINSZ,
                        struct.pack("HHHH", sz.columns, sz.lines, 0, 0))
            return True
        except Exception:
            return False

    def _pty_relay(self, pid, mfd):
        prev = signal.signal(signal.SIGWINCH, self._on_pty_winch)
        exit_status = None
        try:
            while True:
                if self._pty_winched:
                    self._pty_winched = False
                    if self._winsize(mfd):
                        try:
                            os.kill(pid, signal.SIGWINCH)
                        except Exception:
                            pass
                try:
                    rl, _, _ = select.select([self.fd, mfd], [], [], 0.25)
                except InterruptedError:
                    continue
                except OSError:
                    break
                if mfd in rl:
                    try:
                        data = os.read(mfd, 65536)
                    except OSError:
                        data = b""
                    if not data:
                        break
                    try:
                        os.write(1, data)
                    except OSError:
                        break
                if self.fd in rl:
                    try:
                        data = os.read(self.fd, 65536)
                    except OSError:
                        data = b""
                    if data:
                        try:
                            os.write(mfd, data)
                        except OSError:
                            break
                try:
                    w, _st = os.waitpid(pid, os.WNOHANG)
                    if w == pid:
                        exit_status = _st
                        end = time.monotonic() + 0.3
                        while time.monotonic() < end:
                            try:
                                rl, _, _ = select.select([mfd], [], [], 0.05)
                            except Exception:
                                break
                            if not rl:
                                break
                            try:
                                data = os.read(mfd, 65536)
                            except Exception:
                                break
                            if not data:
                                break
                            try:
                                os.write(1, data)
                            except Exception:
                                break
                            end = time.monotonic() + 0.1
                        return exit_status
                except ChildProcessError:
                    break
            return exit_status
        finally:
            signal.signal(signal.SIGWINCH, prev)

    def run_pty(self, argv):
        if argv and argv[0] in ("sudo", "doas"):
            self.award("sudoer")
        if isinstance(argv, list) and len(argv) >= 3 and argv[1] == "-c":
            cmd_name = argv[2].strip().split()[0]
        elif isinstance(argv, list) and argv:
            cmd_name = os.path.basename(argv[0])
        else:
            cmd_name = str(argv)

        # Fallback for Windows or systems without working PTY
        if not HAS_PTY or sys.platform == "win32" or pty is None:
            self.suspend_hud()
            code = 0
            try:
                if isinstance(argv, list):
                    code = subprocess.call(argv, cwd=self.term.cwd)
                else:
                    code = subprocess.call(argv, shell=True, cwd=self.term.cwd)
            except Exception as e:
                code = 1
                try:
                    self.out.write("\n✗ command failed: %s\n" % e)
                    self.out.flush()
                except Exception:
                    pass
            if code != 0:
                try:
                    self.out.write("\n— %s exited (code %d) • press ENTER to return to CUTIE —\n" % (cmd_name, code))
                    self.out.flush()
                    sys.stdin.readline()
                except Exception:
                    pass
            self.resume_hud()
            if code == 0:
                self.term.push([("✓ " + cmd_name + " finished", C_CYAN)])
            else:
                self.term.push([("✗ " + cmd_name + " exited with code %d" % code, C_RED)])
            return

        self.suspend_hud()
        try:
            pid, mfd = pty.fork()
        except Exception as e:
            self.term.push([("✗ pty failed: %s" % e, C_RED)])
            self.resume_hud()
            return
        if pid == 0:
            try:
                os.chdir(self.term.cwd)
                os.environ["PWD"] = self.term.cwd
                os.environ.setdefault("TERM", "xterm-256color")
                os.environ.setdefault("COLORTERM", "truecolor")
                os.execvp(argv[0], argv)
            except Exception:
                pass
            os._exit(127)
        status = None
        try:
            self._winsize(mfd)
            old = termios.tcgetattr(self.fd)
            enter_raw(self.fd)
            try:
                status = self._pty_relay(pid, mfd)
            finally:
                try:
                    termios.tcsetattr(self.fd, termios.TCSADRAIN, old)
                except Exception:
                    pass
            try:
                os.close(mfd)
            except Exception:
                pass
            if status is None:
                try:
                    _, status = os.waitpid(pid, 0)
                except Exception:
                    status = None
        except Exception:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass
            try:
                os.waitpid(pid, 0)
            except Exception:
                pass
        code = 0
        if status is not None:
            if os.WIFEXITED(status):
                code = os.WEXITSTATUS(status)
            elif os.WIFSIGNALED(status):
                code = 128 + os.WTERMSIG(status)
        try:
            termios.tcflush(self.fd, termios.TCIFLUSH)
        except Exception:
            pass
        if code != 0:
            col = fg(C_RED)
            try:
                self.out.write("\n" + col + "— %s exited (code %d) • press ENTER to return to CUTIE —" % (cmd_name, code) + RESET)
                self.out.flush()
            except Exception:
                pass
            try:
                a = termios.tcgetattr(self.fd)
                a[3] &= ~(termios.ICANON | termios.ECHO)
                a[6][termios.VMIN] = 1
                a[6][termios.VTIME] = 0
                termios.tcsetattr(self.fd, termios.TCSADRAIN, a)
                os.read(self.fd, 1)
            except Exception:
                pass
        self.resume_hud()
        if code == 0:
            self.term.push([("✓ " + cmd_name + " finished", C_CYAN)])
        else:
            self.term.push([("✗ " + cmd_name + " exited with code %d" % code, C_RED)])

    # ── background capture (keeps HUD at 60fps) ──

    def start_capture(self, line):
        T = self.term
        if T.busy:
            T.push([("✗ a job is already running — CTRL+C to kill it", C_RED)])
            return
        T.busy = True
        T.busy_label = line
        _me = re.search(r"\.([A-Za-z]{1,4})\b", line)
        _ext = ("." + _me.group(1).lower()) if _me else ""
        _lang = {".py": "PYTHON", ".sh": "SHELL", ".c": "C", ".cpp": "C++",
                 ".js": "NODE", ".java": "JAVA", ".rs": "RUST", ".go": "GO"}.get(_ext)
        if _lang and self.epage is None:
            _run_banner(self, _lang, "▶ live output — CTRL+C kill")
        self.cap_q = queue.Queue()
        self.cap_colorizer = None
        self.cap_t0 = None
        try:
            self.cap_proc = subprocess.Popen(
                [self.shell, "-c", line],
                cwd=T.cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=getattr(os, "setsid", None))
        except Exception as e:
            T.busy = False
            T.push([("✗ exec failed: %s" % e, C_RED)])
            return
        th = threading.Thread(target=self._cap_reader,
                              args=(self.cap_proc, self.cap_q), daemon=True)
        th.start()

    def _cap_reader(self, proc, q):
        try:
            for raw in iter(proc.stdout.readline, b""):
                q.put(raw.decode("utf-8", "replace").rstrip("\n"))
        except Exception:
            pass
        try:
            proc.wait()
        except Exception:
            pass
        q.put(None)

    def kill_capture(self):
        p = self.cap_proc
        if p is None:
            return
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
        self.term.push([("✗ killed (CTRL+C)", C_RED)])

    def _gshop_finish(self):
        gs = getattr(self, "gshop", None)
        if not isinstance(gs, dict):
            return
        gs["busy"] = False
        gs["done"] = True
        if gs.get("_json_received"):
            gs["status"] = "ready" if gs.get("results") else "empty"
        elif gs.get("_json_error"):
            gs["status"] = "parse_error"
        else:
            gs["status"] = "missing_json"
        self.gshop_out = False
        self._gshop_debug(
            "FINISH json_received=%s pending=%s results=%d" %
            (gs.get("_json_received", False), gs.get("_capture_pending", False),
             len(gs.get("results", []))))
    def _gshop_debug(self, message):
        try:
            with open("/tmp/gshop-debug.log", "a", encoding="utf-8") as f:
                f.write(str(message) + "\n")
        except OSError:
            pass

    def _gshop_consume_capture_line(self, item):
        """True = ye line GShop JSON thi aur consume ho gayi."""
        gs = getattr(self, "gshop", None)
        if not isinstance(gs, dict):
            return False
        if not gs.get("_capture_pending", False):
            return False
        if isinstance(item, bytes):
            item = item.decode("utf-8", errors="replace")
        if not isinstance(item, str):
            return False
        line = item.rstrip("\r\n")
        line = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", line)
        candidate = line.lstrip("\ufeff \t ")
        if not candidate.startswith("["):
            return False
        if not re.search(r'"t"\s*:', candidate):
            return False
        self._gshop_debug("PUMP JSON candidate len=%d" % len(candidate))
        results, error = _gshop_parse_json(candidate)
        gs["_json_seen"] = True
        gs["_capture_pending"] = False
        if error is not None:
            gs["_json_received"] = False
            gs["_json_error"] = error
            gs["status"] = "parse_error"
            self._gshop_debug("PUMP parse_error=%s" % error)
            return True
        gs["results"] = results
        gs["_json_received"] = True
        gs["status"] = "ready" if results else "empty"
        gs["busy"] = False
        gs["msg"] = ("✿ %d results — 1-9 se cart" % len(results)) if results \
            else "😿 zero results — dusri query"
        gs["msg_t"] = time.monotonic()
        self._gshop_debug("PUMP JSON accepted count=%d" % len(results))
        return True


    def pump_capture(self):
        if not self.term.busy or self.cap_q is None:
            return
        n = 0
        while n < 24:
            try:
                item = self.cap_q.get_nowait()
            except queue.Empty:
                return
            if isinstance(item, str) and item:
                sys.stderr.write("\033[31mITEM|%.40s|\033[0m\n" % item)
            in_ep = (self.epage is not None and getattr(self, "epage_out", False))
            if item is None:
                code = self.cap_proc.returncode
                self.term.busy = False
                self.cap_q = None
                self.cap_proc = None
                self.cap_colorizer = None
                dur = ("  •  %.1fs" % max(0.0, time.monotonic() - self.cap_t0)) if self.cap_t0 else ""
                self.cap_t0 = None
                self.epage_out = False
                if getattr(self, "gshop_out", False):
                    self.gshop_out = False
                    self._gshop_finish()
            if self._gshop_consume_capture_line(item):
                continue
                if in_ep:
                    epo = self.epage
                    if code == 0:
                        epo["out"].append([("▸ done ✦" + dur, C_GOLD)])
                        epo["msg"] = "✓ done ✦" + dur
                    else:
                        epo["out"].append([("▸ exit %d" % code + dur, C_RED)])
                        epo["msg"] = "✗ exit %d" % code + dur
                    epo["msg_t"] = time.monotonic()
                elif code == 0:
                    self.term.push([("▸ done ✦" + dur, C_GOLD if dur else C_DIM)])
                else:
                    self.term.push([("▸ exit %d" % code + dur, C_RED)])
                return
            if in_ep:
                epo = self.epage
                epo.setdefault("out", []).append(
                    self.cap_colorizer(item) if self.cap_colorizer else [(item, C_OUT)])
                if len(epo["out"]) > 240:
                    del epo["out"][:80]
            elif self.cap_colorizer:
                self.term.push(self.cap_colorizer(item))
            else:
                self.term.push(item)
            n += 1

    # ── lifecycle ──

    def run(self):
        fd = self.fd
        try:
            self._orig_term = termios.tcgetattr(fd)
        except Exception:
            self._orig_term = None
        try:
            enter_raw(fd)
            self.out.write(ESC + "]2;CUTIE OS — personal console\x07")
            self.out.write(ALT_ON + CUR_HIDE + ESC + "[>0u" +
                           ESC + "[?2004l" + ESC + "[?1000l" +
                           ESC + "[?1002l" + ESC + "[?1003l" + ESC + "[?1006l")
            self.out.flush()
            signal.signal(signal.SIGWINCH, self._on_winch)
            for s in (signal.SIGTERM, signal.SIGHUP):
                try:
                    signal.signal(s, self._on_term)
                except Exception:
                    pass
            self.out.write(CLEAR_SCR)
            self.out.flush()
            while self.running:
                W, H = self.size()
                L = Layout(W, H)
                self.layout = L
                self.cv = Canvas(W, H)
                if not L.too_small:
                    break
                self._too_small_loop()
            if self.running and not self.no_intro:
                self._boot_seq()
                self._intro()
            try:
                termios.tcflush(self.fd, termios.TCIFLUSH)
            except Exception:
                pass
            self.seed_lines()
            self.info.rebuild_ui(self.layout)
            self.main_loop()
        finally:
            cleanup_term(self._orig_term, fd)
        if self.fatal:
            print("cutie os hit an internal error: %s" % self.fatal, file=sys.stderr)
        return 0

    def seed_lines(self):
        T = self.term
        if T.lines:
            return
        nick = T.nick or self.info.user
        T.push([(self.L("seed1").format(v=VERSION, e=EDITION), C_DIM)])
        T.push([(self.L("seed2").format(n=nick, t="tools", h="help"), C_DIM)])
        T.push([(self.L("seed3").format(b="!cmd"), C_DIM)])

    def _too_small_loop(self):
        out = self.out
        while self.running:
            W, H = self.size()
            if self.cv.w != W or self.cv.h != H:
                self.cv = Canvas(W, H)
                out.write(CLEAR_SCR)
            t = time.monotonic()
            self.cv.clear()
            self._draw_too_small(self.cv, t)
            try:
                out.write(HOME + self.cv.render())
                out.flush()
            except (BrokenPipeError, OSError):
                self.running = False
                return
            try:
                evs = self.keys.poll(0.12)
            except OSError:
                evs = [("EOF", None)]
            for ev in evs:
                if ev[0] in ("CTRL_C", "CTRL_D", "EOF"):
                    self.running = False
                    return

    # ── intro ──

    def _logo_text(self, W, H):
        pad_l = max(0, (W - LOGO_W) // 2)
        pad_t = max(1, min(4, (H - 14) // 2))
        lines = [""] * pad_t
        for row in LOGO:
            lines.append(" " * pad_l + row)
        return "\n".join(lines) + "\n"

    # ── intro: native multi-effect engine ──

    def _intro(self):
        W, H = self.size()
        self.out.write(CLEAR_SCR + CUR_HIDE)
        self.out.flush()
        if os.environ.get("CUTIE_INTRO") != "native":
            if self.intro_fx in TTE_FX and try_tte_intro(self._logo_text(W, H), self.intro_fx):
                time.sleep(0.9)
                self._native_reveal(0.85)
                return
        self._native_intro()

    def _native_reveal(self, dur=0.9):
        W, H = self.size()
        cv = Canvas(W, H)
        x0 = max(0, (W - LOGO_W) // 2)
        y0 = max(1, (H - 6) // 2 - 1)
        out = self.out
        out.write(CLEAR_SCR + CUR_HIDE)
        n = max(1, int(dur * 60))
        for f in range(n + 1):
            p = f / float(n)
            cv.clear()
            paint_logo(cv, x0, y0, time.monotonic(),
                       reveal=min(1.0, p * 1.15), extrude=min(1.0, p * 1.6))
            try:
                out.write(HOME + cv.render())
                out.flush()
            except (BrokenPipeError, OSError):
                return
            time.sleep(FRAME_TARGET)

    def _native_intro(self):
        W, H = self.size()
        cv = Canvas(W, H)
        self._fx_cv = cv
        self._fx_perm = None
        x0 = max(0, (W - LOGO_W) // 2)
        y0 = max(1, (H - 6) // 2 - 1)
        fx = self.intro_fx if (self.intro_fx in INTRO_FX and self.intro_fx != "random") else None
        if fx is None:
            fx = random.choice([f for f in INTRO_FX if f != "random"])
        draw = getattr(self, "_fx_" + fx, self._fx_thunderstorm)
        self.out.write(CLEAR_SCR + CUR_HIDE)
        self.out.flush()
        self._fx_run(3.4, lambda c, p, t: draw(c, x0, y0, p, t))
        cv.clear()
        paint_logo(cv, x0, y0, time.monotonic())
        try:
            self.out.write(HOME + cv.render())
            self.out.flush()
        except Exception:
            pass
        time.sleep(0.35)

    def _fx_run(self, dur, draw):
        out = self.out
        n = max(1, int(dur * 60))
        cv = self._fx_cv
        for f in range(n + 1):
            p = f / float(n)
            cv.clear()
            draw(cv, p, time.monotonic())
            try:
                out.write(HOME + cv.render())
                out.flush()
            except (BrokenPipeError, OSError):
                return
            time.sleep(FRAME_TARGET)

    def _fx_thunderstorm(self, cv, x0, y0, p, t):
        t = p * 3.6
        if t < 0.62:
            for a, b in ((0.08, 0.18), (0.28, 0.37), (0.47, 0.56)):
                if a <= t < b:
                    k = 1.0 - (t - a) / (b - a)
                    for ry in range(6):
                        cv.put(x0, y0 + ry, LOGO[ry], scale(C_WHITE, 0.55 + 0.45 * k))
        elif t < 2.1:
            pr = (t - 0.62) / 1.48
            paint_logo(cv, x0, y0, t, reveal=min(1.0, pr * 1.06), extrude=0.0)
        else:
            paint_logo(cv, x0, y0, t, reveal=1.0, extrude=min(1.0, (t - 2.1) / 0.45))

    def _fx_decrypt(self, cv, x0, y0, p, t):
        junk = "▚▞▓▒░#%&$@*+=<>"
        n = LOGO_W
        for (i, ry, ch) in LOGO_CELLS:
            res = (i / float(n)) * 0.70 + ((i * 7 + ry * 13) % 9) / 90.0
            yy = y0 + ry
            if p < res:
                cv.set(x0 + i, yy, junk[(i * 5 + ry * 3 + int(t * 20)) % len(junk)],
                       scale(C_VIOLET, 0.5))
            else:
                age = min(1.0, (p - res) * 8.0)
                cv.set(x0 + i, yy, ch, mix(C_WHITE, grad(i / max(1, n - 1)), age))
        if p > 0.86:
            paint_logo(cv, x0, y0, t, reveal=1.0,
                       extrude=min(1.0, (p - 0.86) / 0.14 * 1.2))

    def _fx_waves(self, cv, x0, y0, p, t):
        n = LOGO_W
        front = p * (n + 10) - 5
        for (i, ry, ch) in LOGO_CELLS:
            if i > front:
                continue
            d = front - i
            amp = math.exp(-d / 6.0) * 3.2 if d < 18 else 0.0
            yy = y0 + ry - int(round(math.sin(t * 7.0 - i * 0.5) * amp))
            c = grad(i / max(1, n - 1))
            if amp > 1.2:
                c = mix(c, C_WHITE, min(1.0, amp / 3.2))
            cv.set(x0 + i, yy, ch, c)
        if p > 0.9:
            paint_logo(cv, x0, y0, t, reveal=1.0, extrude=min(1.0, (p - 0.9) / 0.1 * 1.2))

    def _fx_rain(self, cv, x0, y0, p, t):
        n = LOGO_W
        junk = "▁▂▃▄▅▆▇█"
        for (i, ry, ch) in LOGO_CELLS:
            start = (i / float(n)) * 0.45
            lock = start + (ry + 1) / 6.0 * 0.50
            yy = y0 + ry
            if p >= lock:
                cv.set(x0 + i, yy, ch, grad(i / max(1, n - 1)))
            else:
                fall = (lock - p) * 26.0
                fy = yy - fall
                if 0 <= fy < cv.h and fall > 0.5:
                    cv.set(x0 + i, int(fy), junk[(i + ry) % len(junk)], scale(C_CYAN, 0.8))

    def _fx_beams(self, cv, x0, y0, p, t):
        n = LOGO_W
        sweep = p * (n + 12) - 6
        for col in range(max(0, int(sweep) - 1), min(n, int(sweep) + 2)):
            for yy in range(max(0, y0 - 2), min(cv.h, y0 + 9)):
                cv.set(x0 + col, yy, "│", scale(C_WHITE, 0.25 + 0.2 * math.sin(t * 30)))
        for (i, ry, ch) in LOGO_CELLS:
            if i < sweep - 3:
                cv.set(x0 + i, y0 + ry, ch, grad(i / max(1, n - 1)))
            elif i < sweep + 2:
                cv.set(x0 + i, y0 + ry, ch, C_WHITE)
        if p > 0.88:
            paint_logo(cv, x0, y0, t, reveal=1.0, extrude=min(1.0, (p - 0.88) / 0.12 * 1.2))

    def _fx_typewriter(self, cv, x0, y0, p, t):
        total = len(LOGO_CELLS)
        shown = int(p * p * total * 1.05)
        for idx, (i, ry, ch) in enumerate(LOGO_CELLS):
            yy = y0 + ry
            if idx < shown:
                cv.set(x0 + i, yy, ch, grad((i + ry * 2) / float(LOGO_W + 8)))
            elif idx == shown:
                cv.set(x0 + i, yy, "▌", C_WHITE)
        if p > 0.92:
            paint_logo(cv, x0, y0, t, reveal=1.0, extrude=min(1.0, (p - 0.92) / 0.08 * 1.2))

    def _fx_glitch(self, cv, x0, y0, p, t):
        n = LOGO_W
        if self._fx_perm is None:
            perm = list(LOGO_CELLS)
            random.shuffle(perm)
            self._fx_perm = {c: k / float(len(perm)) for k, c in enumerate(perm)}
        for (i, ry, ch) in LOGO_CELLS:
            res = self._fx_perm.get((i, ry, ch), 1.0)
            yy = y0 + ry
            if p > min(1.0, res * 0.9 + 0.05):
                cv.set(x0 + i, yy, ch, grad(i / max(1, n - 1)))
            else:
                r = random.random()
                if r < 0.12:
                    cv.set(max(0, x0 + i - 1), yy, ch, scale(C_CYAN, 0.7))
                elif r < 0.24:
                    cv.set(x0 + i + 1, yy, ch, scale(C_MAGENTA, 0.7))
                elif r < 0.34:
                    cv.set(x0 + i, yy, random.choice("▓▒░#"), scale(C_SLATE, 0.9))
        if p >= 0.999:
            self._fx_perm = None

    def _fx_explode(self, cv, x0, y0, p, t):
        n = LOGO_W
        cx, cy = n / 2.0, 2.5
        maxd = math.hypot(cx, cy) + 1.0
        for (i, ry, ch) in LOGO_CELLS:
            d = math.hypot(i - cx, (ry - cy) * 1.9) / maxd
            yy = y0 + ry
            if p > d * 0.85 + 0.05:
                cv.set(x0 + i, yy, ch, grad(i / max(1, n - 1)))
            elif abs(p - d * 0.85) < 0.05:
                cv.set(x0 + i, yy, ch, C_WHITE)
        if p > 0.93:
            paint_logo(cv, x0, y0, t, reveal=1.0, extrude=min(1.0, (p - 0.93) / 0.07 * 1.2))

    def _fx_spotlight(self, cv, x0, y0, p, t):
        n = LOGO_W
        cx = n / 2.0 + math.sin(t * 2.2) * 6.0
        cy = 2.5 + math.cos(t * 1.7) * 1.2
        r = p * (n * 0.75)
        for (i, ry, ch) in LOGO_CELLS:
            d = math.hypot(i - cx, (ry - cy) * 2.4)
            yy = y0 + ry
            if d < r:
                fade = clamp(1.0 - (r - d) / 6.0, 0.35, 1.0)
                cv.set(x0 + i, yy, ch, mix(grad(i / max(1, n - 1)), C_WHITE, (1.0 - fade) * 0.5))
        if p > 0.94:
            paint_logo(cv, x0, y0, t, reveal=1.0, extrude=min(1.0, (p - 0.94) / 0.06 * 1.2))

    def _fx_3d(self, cv, x0, y0, p, t):
        if p < 0.42:
            paint_logo(cv, x0, y0, t, reveal=0.0, extrude=p / 0.42)
        else:
            paint_logo(cv, x0, y0, t, reveal=(p - 0.42) / 0.58 * 1.1, extrude=1.0)

    # ── main loop ──

    def main_loop(self):
        self.last_t = time.monotonic()
        err = 0
        while self.running:
            try:
                if self.need_resize:
                    self.need_resize = False
                    W, H = self.size()
                    self.layout = Layout(W, H)
                    self.cv = Canvas(W, H)
                    self.info.rebuild_ui(self.layout)
                    self.out.write(CLEAR_SCR)
                t = time.monotonic()
                dt = min(0.1, t - self.last_t)
                self.last_t = t
                if t - self.last_info >= 2.0:
                    self.last_info = t
                    self.info.refresh_dynamic()
                    self.info.rebuild_ui(self.layout)
                    self._music_tick()
                    self._timer_tick(t)
                if self.confetti:
                    self._confetti_tick(dt)
                for p in self.particles:
                    p.fx += p.sp * dt
                    if p.fx > 1.15:
                        p.fx = -0.15
                        p.sp = random.uniform(0.02, 0.09)
                        p.ph = random.uniform(0, 6.283)
                self.pump_capture()
                self._ai_pump()
                frame = self.build_frame(t)
                cost = time.monotonic() - t
                try:
                    self.out.write(SYNC_ON + HOME + frame + SYNC_OFF)
                    self.out.flush()
                except (BrokenPipeError, OSError):
                    self.running = False
                    break
                budget = self.interval - cost
                if budget < 0.002:
                    budget = 0.002
                try:
                    evs = self.keys.poll(budget)
                except OSError:
                    evs = [("EOF", None)]
                for ev in evs:
                    self.handle_event(ev)
                    if not self.running:
                        break
                total = time.monotonic() - t
                self.fps = self.fps * 0.9 + (1.0 / max(1e-4, total)) * 0.1
                self.interval = FRAME_TARGET if cost < 0.013 else min(0.08, cost * 1.35)
                err = 0
            except SystemExit:
                raise
            except Exception as e:
                err += 1
                if err > 8:
                    self.fatal = str(e)
                    self.running = False
                else:
                    time.sleep(0.05)

    # ── input handling ──

    def handle_event(self, ev):
        if getattr(self, "gshop", None):
            self.handle_gshop_event(ev)
            return
            return
        kind, ch = ev[0], ev[1]
        T = self.term
        if kind == "F1":
            if self.epage:
                self._epage_run()
            elif self.cpage:
                self.handle_cpage_event(ev)
            else:
                self.open_cpage()
            return
        if kind == "EOF":
            self.running = False
            return
        _kseq = {"UP": "u", "DOWN": "d", "LEFT": "l", "RIGHT": "r"}
        if kind in _kseq:
            self.konami = (self.konami + _kseq[kind])[-10:]
        elif kind == "CHAR" and ch:
            self.konami = (self.konami + ch.lower())[-10:]
        if self.konami.endswith("uuddlrlrba"):
            self.konami = ""
            self._konami_on()
        if self.dash:
            self.dash = False
            if kind == "EOF":
                self.running = False
            return
        if self.fz is not None:
            self.handle_fz_event(ev)
            return
        if self.chat is not None:
            self.handle_chat_event(ev)
            return
        if self.tpage is not None:
            self.handle_tpage_event(ev)
            return
            return
        if self.gmpage:
            self.handle_gm_event(ev)
            return
        if self.gmpage and not L.too_small:
            cv.clear()
            return self.build_gm_frame(t)
        if self.pridepage:
            self.handle_pride_event(ev)
            return
        if self.fancy:
            self.handle_fancy_event(ev)
            return
        if self.breathe:
            self.handle_breathe_event(ev)
            return
        if self.care:
            self.handle_care_event(ev)
            return
        if self.cpage_bloom:
            self.handle_cycle_event(ev)
            return
        if self.epage:
            self.handle_epage_event(ev)
            return
        if self.cpage:
            self.handle_cpage_event(ev)
            return
        if self.mpage:
            self.handle_mpage_event(ev)
            return
        if self.help is not None:
            self.handle_help_event(ev)
            return
        if self.prompt_name and kind in ("ESC", "CTRL_C"):
            self.prompt_name = False
            T.buf = ""
            T.caret = 0
            T.push([(self.L("name_cancel"), C_DIM)])
            return
        if kind in ("CTRL_C", "CTRL_D"):
            if T.busy:
                self.kill_capture()
            elif kind == "CTRL_D":
                self.running = False
            else:
                T.buf = ""
                T.caret = 0
            return
        if T.busy:
            if kind == "PGUP":
                T.scroll += max(1, self.layout.out_rows // 2)
            elif kind == "PGDN":
                T.scroll = max(0, T.scroll - max(1, self.layout.out_rows // 2))
            return
        if kind == "CHAR":
            T.buf = T.buf[:T.caret] + ch + T.buf[T.caret:]
            T.caret += len(ch)
        elif kind == "BACKSPACE":
            if T.caret > 0:
                T.buf = T.buf[:T.caret - 1] + T.buf[T.caret:]
                T.caret -= 1
        elif kind == "DEL":
            T.buf = T.buf[:T.caret] + T.buf[T.caret + 1:]
        elif kind == "LEFT":
            T.caret = max(0, T.caret - 1)
        elif kind == "RIGHT":
            if T.caret >= len(T.buf):
                _gh = self.ghost_suggest()
                if _gh:
                    T.buf += _gh
                    T.caret = len(T.buf)
            else:
                T.caret = min(len(T.buf), T.caret + 1)
        elif kind == "HOME":
            T.caret = 0
        elif kind == "END":
            if T.caret >= len(T.buf):
                _gh = self.ghost_suggest()
                if _gh:
                    T.buf += _gh
            T.caret = len(T.buf)
        elif kind == "UP":
            if T.history:
                if T.hist_idx is None:
                    T.hist_draft = T.buf
                    T.hist_idx = len(T.history) - 1
                else:
                    T.hist_idx = max(0, T.hist_idx - 1)
                T.buf = T.history[T.hist_idx]
                T.caret = len(T.buf)
        elif kind == "DOWN":
            if T.hist_idx is not None:
                T.hist_idx += 1
                if T.hist_idx >= len(T.history):
                    T.hist_idx = None
                    T.buf = T.hist_draft
                else:
                    T.buf = T.history[T.hist_idx]
                T.caret = len(T.buf)
        elif kind == "ENTER":
            line = T.buf
            T.buf = ""
            T.caret = 0
            T.scroll = 0
            self.submit(line)
        elif kind == "TAB":
            self.tab_complete()
        elif kind == "PGUP":
            T.scroll += max(1, self.layout.out_rows // 2)
        elif kind == "PGDN":
            T.scroll = max(0, T.scroll - max(1, self.layout.out_rows // 2))
        elif kind == "CTRL_U":
            T.buf = ""
            T.caret = 0
        elif kind == "CTRL_K":
            T.buf = T.buf[:T.caret]
        elif kind == "CTRL_W":
            j = T.caret
            while j > 0 and T.buf[j - 1] == " ":
                j -= 1
            while j > 0 and T.buf[j - 1] != " ":
                j -= 1
            T.buf = T.buf[:j] + T.buf[T.caret:]
            T.caret = j
        elif kind == "CTRL_L":
            T.clear()
            self.seed_lines()
        elif kind == "CTRL_R":
            self.fz = {"q": "", "sel": 0}
        elif kind == "ESC":
            T.buf = ""
            T.caret = 0

    def tab_complete(self):
        T = self.term
        before = T.buf[:T.caret]
        m = re.search(r"[^\s]*$", before)
        tok = m.group(0)
        start = T.caret - len(tok)
        cands = []
        dirn = None
        if start == 0 and " " not in before:
            bpart = tok
            names = set(TOOL_MAP.keys()) | set(T.macros.keys()) | TTY_PROGRAMS | {
                "cd", "ls", "cat", "grep", "echo", "which", "curl", "wget", "doas", "make"}
            cands = sorted(n for n in names if n.startswith(tok) and n != tok)
        else:
            ex = os.path.expanduser(tok)
            if os.path.isabs(ex):
                dirn = os.path.dirname(ex) or "/"
                bpart = os.path.basename(ex)
            else:
                full = os.path.join(T.cwd, ex)
                dirn = os.path.dirname(full)
                bpart = os.path.basename(full)
            try:
                entries = sorted(os.listdir(dirn or "."))
            except Exception:
                entries = []
            cands = []
            for e in entries:
                if e.startswith(bpart):
                    if os.path.isdir(os.path.join(dirn or ".", e)):
                        e += "/"
                    cands.append(e)
        if not cands:
            return
        pre = os.path.commonprefix(cands)
        if len(cands) == 1 or (pre and len(pre) > len(bpart)):
            add = cands[0][len(bpart):] if len(cands) == 1 else pre[len(bpart):]
            if len(cands) == 1 and not add.endswith("/"):
                add += " "
            T.buf = before + add + T.buf[T.caret:]
            T.caret += len(add)
        else:
            shown = cands[:24]
            T.push([(", ".join(shown) + (" … +%d" % (len(cands) - 24) if len(cands) > 24 else ""), C_SLATE)])

    # ── command engine ──

    def submit(self, line):
        T = self.term
        T.echo_cmd(line)
        if self.prompt_name:
            self.prompt_name = False
            self._set_nick(line)
            return
        if line.strip():
            T.history.append(line)
            if len(T.history) > HIST_CAP:
                del T.history[: len(T.history) - HIST_CAP]
            self.add_xp(3)
            self.cmd_tick()
        T.hist_idx = None
        T.scroll = 0
        self.route(line)

    def route(self, line, depth=0):
        T = self.term
        if depth > 5:
            T.push([("✗ macro recursion too deep", C_RED)])
            return
        if line.startswith("!"):
            rest = line[1:].strip()
            if not rest:
                T.dim("  usage: !command   (run in a real tty — sudo, vim, htop…)")
                return
            self.run_pty([self.shell, "-c", rest])
            return
        try:
            parts = shlex.split(line)
        except ValueError:
            parts = line.split()
        if not parts:
            return
        cmd, args = parts[0], parts[1:]
        gate = LANG_GATES.get(cmd.lower())
        if gate:
            if cmd.lower() == "c" and args:
                return self.route("ed " + " ".join(args))
            fname = _gate_counter(gate)
            self.open_epage(_untitled_path(fname))
            return
        if cmd in T.macros and cmd not in TOOL_MAP and cmd not in ("cd", "sudo"):
            T.push([("◇ macro %s » %s" % (cmd, T.macros[cmd]), C_SLATE)])
            return self.route(T.macros[cmd], depth + 1)
        tool = TOOL_MAP.get(cmd)
        if tool:
            self.tool_tick(tool)
            try:
                tool.fn(self, args)
            except Exception as e:
                T.push([("✗ %s failed: %s" % (cmd, e), C_RED)])
            return
        if cmd == "cd":
            self.do_cd(args)
            return
        if cmd in TTY_PROGRAMS:
            self.run_pty([self.shell, "-c", line])
            return
        self.start_capture(line)

    def do_cd(self, args):
        T = self.term
        if not args:
            tgt = os.path.expanduser("~")
        elif args[0] == "-":
            tgt = T.prev_cwd or T.cwd
        else:
            tgt = os.path.expanduser(args[0])
            if not os.path.isabs(tgt):
                tgt = os.path.join(T.cwd, tgt)
        tgt = os.path.normpath(tgt)
        if os.path.isdir(tgt):
            T.prev_cwd = T.cwd
            T.cwd = tgt
            T.push([("→ " + tgt, C_CYAN)])
        else:
            T.push([("✗ cd: no such directory: " + tgt, C_RED)])

    # ── drawing ──

    def build_frame(self, t):
        if getattr(self, "gshop", None):
            return self.build_gshop_frame(t)
        cv = self.cv
        L = self.layout
        # ── gshop full-screen takeover (HUD chhup jata hai) ──
        cv.clear()
        if L.too_small:
            self._draw_too_small(cv, t)
            return cv.render()
        self.draw_header(cv, L, t)
        if L.logo_full:
            self.draw_logo(cv, L, t)
        self.draw_panels(cv, L, t)
        self.draw_anim(cv, L, t)
        self.draw_term(cv, L, t)
        self.draw_hints(cv, L)
        self._draw_confetti(cv, t)
        if self.fz is not None and not L.too_small:
            self._draw_fz_overlay(cv, t)
        return cv.render()

    def _draw_too_small(self, cv, t):
        W, H = cv.w, cv.h
        lines = (
            ("✦  CUTIE OS  ✦", mix(C_MAGENTA, C_CYAN, 0.5 + 0.4 * math.sin(t * 2))),
            ("", None),
            ("viewport too small — need at least 60 × 20", C_VALUE),
            ("current: %d × %d" % (W, H), C_DIM),
            ("resize the window to continue  •  CTRL+C exits", C_DIM),
        )
        y = max(0, H // 2 - len(lines) // 2)
        for i, (s, c) in enumerate(lines):
            if not s:
                continue
            cv.put(max(0, (W - disp_width(s)) // 2), y + i, s, c)

    def draw_header(self, cv, L, t):
        W = L.W
        y = L.header_y
        b = C_BORDER
        cv.put(0, y, "╭" + "─" * (W - 2) + "╮", b)
        cv.put(0, y + 2, "╰" + "─" * (W - 2) + "╯", b)
        ry = y + 1
        cv.put(0, ry, "│", b)
        cv.put(W - 1, ry, "│", b)
        cv.put(2, ry, "CUTIE OS", C_TITLE)
        cv.put(10, ry, "•", C_SLATE)
        cv.put(12, ry, "PERSONAL CONSOLE", C_LABEL)
        pulse = mix(C_CYAN, C_WHITE, 0.35 + 0.30 * math.sin(t * 2.4))
        if self.timer_until is not None:
            rem = max(0, int(self.timer_until - t))
            fps_s = "⏳ %02d:%02d" % (rem // 60, rem % 60)
        else:
            fps_s = "%3.0f FPS" % min(999.0, self.fps)
        clock = time.strftime("%H:%M:%S")
        sep = "   "
        parts_r = []
        if self.level() > 1:
            parts_r += [("◆ ", C_GOLD), ("L%d" % self.level(), C_GOLD), (sep, C_DIM)]
        parts_r += [("● ", pulse), ("ONLINE", C_VALUE),
                    (sep + fps_s, C_DIM), (sep + clock, C_DIM)]
        plain = "".join(tt for tt, _ in parts_r)
        x = W - 2 - disp_width(plain)
        if x >= 30:
            put_segs(cv, x, ry, parts_r)
        elif x >= 14:
            put_segs(cv, x, ry, [("● ", pulse), ("ONLINE", C_VALUE)])
        mi = getattr(self, "music_info", None)
        if mi and mi.get("title"):
            rlen = disp_width("● ONLINE" + sep + "888 FPS" + sep + "00:00:00")
            if self.level() > 1:
                rlen += 8
            avail = W - 2 - rlen - 32
            if avail >= 14:
                song = clip("%s — %s" % (mi.get("artist") or "?", mi["title"]), avail)
                sym = {"Playing": "▶", "Paused": "❚❚"}.get(mi.get("status", ""), "♪")
                put_segs(cv, 30, ry, [(sym + " ", C_CYAN), ("♪ ", C_FUCHSIA), (song, C_LABEL)])

    def draw_logo(self, cv, L, t):
        x0 = (L.W - LOGO_W) // 2
        paint_logo(cv, x0, L.logo_y, t)
        sub = "— %s %s • %d TOOLS • FASTFETCH MODE —" % (EDITION, VERSION, len(TOOLS))
        x = (L.W - disp_width(sub)) // 2
        cv.put(x, L.subtitle_y, sub, mix(C_MAGENTA, C_PURPLE, 0.5 + 0.2 * math.sin(t * 1.7)))
        rw = min(L.W - 6, 84)
        rx = (L.W - rw) // 2
        ry = L.gap2_y
        for i in range(rw):
            if i == rw // 2:
                cv.set(rx + i, ry, "◆", mix(C_PINK, C_FUCHSIA, 0.5 + 0.3 * math.sin(t * 2.0)))
            else:
                cv.set(rx + i, ry, "─", scale(grad(i / max(1, rw - 1)), 0.42))

    def draw_panels(self, cv, L, t):
        self._draw_panel(cv, 1, L.panels_y, L.panel_w, "SYSTEM", self.info.ui_sys, C_BORDER)
        self._draw_panel(cv, L.right_x, L.panels_y, L.panel_w, "VITALS", self.info.ui_vit, C_BORDER)

    def _draw_panel(self, cv, x, y, pw, title, rows, bcol):
        cv.put(x, y, "╭─ ", bcol)
        cv.put(x + 3, y, title, C_TITLE)
        tw = disp_width(title) + 1
        fill = pw - 4 - tw
        if fill > 0:
            cv.put(x + 3 + tw, y, "─" * fill, bcol)
        cv.put(x + pw - 1, y, "╮", bcol)
        maxw = pw - 16
        for i, (label, segs, plain) in enumerate(rows):
            ry = y + 1 + i
            cv.put(x, ry, "│", bcol)
            cv.put(x + pw - 1, ry, "│", bcol)
            cv.put(x + 2, ry, label.ljust(8), C_LABEL)
            cv.put(x + 11, ry, "»", C_ARROW)
            if disp_width(plain) > maxw:
                cv.put(x + 13, ry, clip(plain, maxw), C_VALUE)
            else:
                put_segs(cv, x + 13, ry, segs)
        cv.put(x, y + 9, "╰" + "─" * (pw - 2) + "╯", bcol)

    def draw_anim(self, cv, L, t):
        A = L.anim_rows
        if A <= 0:
            return
        y = L.anim_y
        if A >= 5:
            self._draw_wave(cv, 2, L.W - 4, y, t)
            self._draw_status(cv, L, y + 2, t)
            self._draw_power(cv, L, y + 3, y + 4, t)
        elif A >= 3:
            self._draw_eline(cv, 2, L.W - 4, y, t)
            self._draw_status(cv, L, y + 1, t)
        else:
            self._draw_status(cv, L, y, t)

    def _draw_wave(self, cv, x0, w, y, t):
        for i in range(w):
            u = i / max(1, w - 1)
            yy = y + int(round(math.sin(u * 6.283 * 1.5 + t * 2.2) * 1.2))
            ch = "✦" if (i + int(t * 6)) % 11 == 0 else "•"
            cv.set(x0 + i, yy, ch, scale(grad(u), 0.50 + 0.25 * math.sin(t * 1.4 + u * 4)))

    def _draw_eline(self, cv, x0, w, y, t):
        for i in range(w):
            u = i / max(1, w - 1)
            c = scale(grad(u), 0.35 + 0.30 * (0.5 + 0.5 * math.sin(t * 2.0 - u * 8.0)))
            cv.set(x0 + i, y, "─", c)

    def _draw_status(self, cv, L, y, t):
        plain, segs = self.status.render(t)
        x = max(2, (L.W - disp_width(plain)) // 2)
        put_segs(cv, x, y, segs)

    def _draw_power(self, cv, L, y1, y2, t):
        W = L.W
        segs = []
        if self.info.mem:
            bp, bs, bc = micro_bar(self.info.mem[2], 7)
            segs += [("MEM ", C_LABEL)] + bs + [("   ", C_DIM)]
        if self.info.disk:
            bp, bs, bc = micro_bar(self.info.disk[2], 7)
            segs += [("DSK ", C_LABEL)] + bs + [("   ", C_DIM)]
        if self.info.temp is not None:
            tc = self.info.temp
            segs += [("%.0f°C" % tc, C_CYAN if tc < 60 else (C_GOLD if tc < 78 else C_RED))]
        if getattr(self.info, "net_rx", 0.0) > 1.0:
            segs += [("  ↓", C_CYAN), (fmt_speed(self.info.net_rx), C_VALUE),
                     (" ↑", C_FUCHSIA), (fmt_speed(self.info.net_tx), C_VALUE)]
        total = disp_width("".join(x for x, _ in segs))
        put_segs(cv, max(2, (W - total) // 2), y1, segs)
        for p in self.particles:
            x = 2 + int(p.fx * (W - 5))
            cv.set(x, y2, "✦", scale(C_PINK, 0.45 + 0.35 * (0.5 + 0.5 * math.sin(t * 2.2 + p.ph))))

    def draw_term(self, cv, L, t):
        T = self.term
        W = L.W
        y0 = L.term_y
        O = L.out_rows
        b = C_TERM_BORDER
        home = os.path.expanduser("~")
        disp = T.cwd.replace(home, "~", 1) if T.cwd.startswith(home) else T.cwd
        label = "╭─ TERMINAL ─ " + clip(disp, max(4, W - 20)) + " "
        cv.put(0, y0, label, b)
        fill = W - 2 - disp_width(label)
        if fill > 0:
            cv.put(disp_width(label), y0, "─" * fill, b)
        cv.put(W - 1, y0, "╮", b)
        right = ("⟳ " + SPIN[int(t * 10) % len(SPIN)] + " busy") if T.busy else "✿ " + getattr(self, "_pet_name", "cutie")
        cv.put(max(12, W - 2 - disp_width(right)), y0, right, C_CYAN if T.busy else C_SLATE)

        view_rows = max(0, O - 1)
        total = len(T.lines)
        maxscroll = max(0, total - view_rows)
        if T.scroll > maxscroll:
            T.scroll = maxscroll
        start = total - view_rows - T.scroll
        lim = W - 3
        for i in range(view_rows):
            idx = start + i
            ry = y0 + 1 + i
            cv.put(0, ry, "│", b)
            cv.put(W - 1, ry, "│", b)
            if idx < 0 or idx >= total:
                continue
            segs, plain = T.lines[idx]
            if disp_width(plain) > lim - 2:
                cv.put(2, ry, clip(plain, lim - 2), C_OUT)
            else:
                x = 2
                for tseg, c in segs:
                    rem = lim - x
                    if rem <= 0:
                        break
                    if disp_width(tseg) > rem:
                        tseg = substr_width(tseg, 0, rem)[0]
                    if tseg:
                        cv.put(x, ry, tseg, c)
                        x += disp_width(tseg)
        if T.scroll > 0 and view_rows > 0:
            cv.put(W - 6, y0 + 1, "↑%d" % T.scroll, C_SLATE)

        ry = y0 + O
        cv.put(0, ry, "│", b)
        cv.put(W - 1, ry, "│", b)
        if T.busy:
            sp = SPIN[int(t * 10) % len(SPIN)]
            put_segs(cv, 2, ry, [(sp + " ", C_CYAN),
                                 (clip(T.busy_label, max(4, W - 22)), C_DIM),
                                 ("  … CTRL+C kills", C_SLATE)])
        else:
            if self.prompt_name:
                cv.put(2, ry, "✏ ", C_GOLD)
            else:
                _gi = int(t * 2.0) % 5
                _pg = ("✿", "❀", "♡", "✦", "❁")[_gi]
                _pc = (C_PINK, C_FUCHSIA, C_MAGENTA, C_VIOLET, C_PINK)[_gi]
                cv.put(2, ry, _pg + " ", _pc)
            x = 4
            before = T.buf[:T.caret]
            at = T.buf[T.caret] if T.caret < len(T.buf) else None
            after = T.buf[T.caret + 1:] if at is not None else ""
            cv.put(x, ry, before, C_WHITE)
            x += disp_width(before)
            if x < lim:
                if at is None:
                    cv.put(x, ry, "▌", mix(C_WHITE, C_MAGENTA, 0.55 + 0.35 * math.sin(t * 3.2)))
                    _gh = self.ghost_suggest()
                    if _gh:
                        cv.put(x + 1, ry, clip(_gh, max(0, lim - x - 2)), C_SLATE)
                else:
                    cv.put(x, ry, at, C_GOLD)
                    x += char_width(at)
                    cv.put(x, ry, after, C_WHITE)
        cv.put(0, y0 + O + 1, "╰" + "─" * (W - 2) + "╯", b)

    def draw_hints(self, cv, L):
        if L.too_small:
            return
        hints = self.L("hint").format(n=len(TOOLS))
        hint = clip(hints, L.W - 4)
        x = max(2, (L.W - disp_width(hint)) // 2)
        if x >= 16:
            blink = "=-..-=" if (time.monotonic() % 8.0) < 0.4 else "=^..^="
            cv.put(2, L.hints_y, blink, C_PINK if blink == "=^..^=" else C_SLATE)
            cv.put(9, L.hints_y, clip(self._pet_name, 6), C_SLATE)
        cv.put(x, L.hints_y, hint, C_SLATE)

    # ── i18n / identity / help browser ──

    def L(self, key):
        d = I18N.get(self.lang) or I18N["en"]
        v = d.get(key)
        if v is None:
            v = I18N["en"].get(key)
        return v if isinstance(v, str) else key

    def _apply_lang(self):
        d = I18N.get(self.lang) or I18N["en"]
        st = d.get("status") or I18N["en"]["status"]
        cols = (C_CYAN, C_GOLD, C_PINK, C_VIOLET, C_FUCHSIA, C_MAGENTA)
        self.status.msgs = tuple((m.format(n=len(TOOLS)), cols[i % len(cols)])
                                 for i, m in enumerate(st))
        self.term.nick = load_nick()

    def _set_nick(self, nick):
        T = self.term
        nick = nick.strip()[:24]
        if not nick:
            T.push([(self.L("name_cancel"), C_DIM)])
            return
        if nick == "-":
            save_profile_field("nick", "")
            T.nick = ""
            self.info.nick = ""
            self.info.rebuild_ui(self.layout)
            T.push([(self.L("name_cleared").format(n=self.info.user), C_CYAN)])
            return
        save_profile_field("nick", nick)
        T.nick = nick
        self.info.nick = nick
        self.info.rebuild_ui(self.layout)
        T.push([(self.L("name_saved") + " ", C_DIM), (nick, C_FUCHSIA), (" ♡", C_PINK)])

    def open_help(self):
        self.help = {"sel": 0, "scroll": 0, "filt": "", "filt_active": False}

    def help_rows(self):
        rows = [("title", "CUTIE OS %s — %s  •  %d TOOLS  •  lang: %s" %
                 (VERSION, EDITION, len(TOOLS), self.lang), "", "", None),
                ("text", "every command runs for real • !cmd opens a real tty (sudo, vim, htop…)",
                 "", "", None),
                ("blank", "", "", "", None)]
        cat = None
        for tl in TOOLS:
            if tl.cat != cat:
                cat = tl.cat
                rows.append(("cat", "◆ " + cat.upper(), "", "", None))
            rows.append(("tool", tl.name, ", ".join(tl.alts), tl.desc, tl))
        M = self.term.macros
        if M:
            rows.append(("blank", "", "", "", None))
            rows.append(("cat", "◆ YOUR MACROS", "", "", None))
            for k in sorted(M):
                rows.append(("macro", k, "", M[k], None))
        rows += [("blank", "", "", "", None),
                 ("cat", "◆ SHELL POWER", "", "", None),
                 ("text", "pipes/globs/env all work:  ls -la | head  •  curl …  •  docker ps", "", "", None),
                 ("text", "macro set dev !nvim ~/proj   →   now just type: dev", "", "", None),
                 ("text", "ghost text: type, then → accepts the gray suggestion (fish-style)", "", "", None),
                 ("text", "games/fun: snake • hack • icat <image>  (kitty preview)", "", "", None)]
        return rows

    def help_visible(self):
        rows = self.help_rows()
        f = self.help["filt"].strip().lower()
        if not f:
            return rows
        out = [rows[0]]
        for r in rows[1:]:
            if r[0] in ("cat", "blank", "text"):
                continue
            hay = (r[1] + " " + r[2] + " " + r[3]).lower()
            if f in hay:
                out.append(r)
        if len(out) == 1:
            out.append(("text", "no match — backspace to fix • esc close", "", "", None))
        return out

    def handle_help_event(self, ev):
        kind, ch = ev[0], ev[1]
        h = self.help
        if kind == "EOF":
            self.running = False
            return
        if kind == "CTRL_C":
            self.help = None
            return
        if h.get("filt_active"):
            if kind == "CHAR":
                h["filt"] += ch
            elif kind == "BACKSPACE":
                h["filt"] = h["filt"][:-1]
            elif kind in ("ENTER", "ESC"):
                h["filt_active"] = False
            h["sel"] = 0
            h["scroll"] = 0
            return
        n = max(1, len(self.help_visible()))
        page = max(1, self.cv.h - 5)
        if kind == "UP" or (kind == "CHAR" and ch in ("w", "k")):
            h["sel"] = max(0, h["sel"] - 1)
        elif kind == "DOWN" or (kind == "CHAR" and ch in ("s", "j")):
            h["sel"] = min(n - 1, h["sel"] + 1)
        elif kind == "PGUP":
            h["sel"] = max(0, h["sel"] - page)
        elif kind == "PGDN":
            h["sel"] = min(n - 1, h["sel"] + page)
        elif kind == "HOME":
            h["sel"] = 0
        elif kind == "END":
            h["sel"] = n - 1
        elif kind == "CHAR" and ch == "/":
            h["filt_active"] = True
        elif kind == "CHAR" and ch in ("q", "Q"):
            self.help = None
        elif kind == "ESC":
            self.help = None
        elif kind == "ENTER":
            rows = self.help_visible()
            if rows:
                sel = rows[clamp(h["sel"], 0, len(rows) - 1)]
                if sel[4] is not None:
                    self.help = None
                    self.term.buf = sel[1] + " "
                    self.term.caret = len(self.term.buf)
                else:
                    self.help = None

    def build_help_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        b = C_TERM_BORDER
        h = self.help
        rows = self.help_visible()
        n = len(rows)
        h["sel"] = clamp(h["sel"], 0, max(0, n - 1))
        body = max(1, H - 4)
        if h["scroll"] > h["sel"]:
            h["scroll"] = h["sel"]
        if h["scroll"] < h["sel"] - body + 1:
            h["scroll"] = h["sel"] - body + 1
        h["scroll"] = clamp(h["scroll"], 0, max(0, n - body))
        cv.put(0, 0, "╭─ ", b)
        cv.put(3, 0, "HELP — FULL COMMAND GUIDE", C_TITLE)
        pos = " %d/%d " % (h["sel"] + 1, n)
        px = W - 2 - disp_width(pos)
        if px > 30:
            cv.put(px, 0, pos, C_SLATE)
        fill = px - 27
        if fill > 0:
            cv.put(27, 0, "─" * fill, b)
        cv.put(W - 1, 0, "╮", b)
        cv.put(0, 1, "│", b)
        cv.put(W - 1, 1, "│", b)
        if h.get("filt_active"):
            cv.put(2, 1, clip(" filter: " + h["filt"] + "▌", W - 4), C_GOLD)
        elif h["filt"]:
            cv.put(2, 1, clip(" filter: " + h["filt"], W - 4), C_GOLD)
        else:
            cv.put(2, 1, " press / to filter • enter runs selected tool", C_SLATE)
        lim = W - 4
        for r in range(body):
            idx = h["scroll"] + r
            yy = 2 + r
            cv.put(0, yy, "│", b)
            cv.put(W - 1, yy, "│", b)
            if idx >= n:
                continue
            kind, name, alts, desc, tool = rows[idx]
            sel = (idx == h["sel"])
            if kind == "title":
                cv.put(2, yy, clip(name, lim), C_TITLE)
            elif kind == "cat":
                cv.put(2, yy, clip(name, lim), C_FUCHSIA)
            elif kind == "text":
                cv.put(2, yy, clip(name, lim), C_DIM)
            elif kind == "blank":
                pass
            else:
                x = 2
                cv.put(x, yy, "▸ " if sel else "  ", C_GOLD if sel else C_SLATE)
                x += 2
                cv.put(x, yy, name.ljust(12)[:12], C_WHITE if sel else C_CYAN)
                x += 13
                cv.put(x, yy, clip(alts, 18).ljust(18)[:18], C_SLATE)
                x += 19
                cv.put(x, yy, clip(desc, max(4, W - x - 3)), C_VALUE if sel else C_OUT)
        fy = H - 2
        cv.put(0, fy, "│", b)
        cv.put(W - 1, fy, "│", b)
        foot = self.L("help_foot")
        cv.put(max(2, (W - disp_width(foot)) // 2), fy, clip(foot, W - 4), C_SLATE)
        cv.put(0, H - 1, "╰" + "─" * (W - 2) + "╯", b)
        return cv.render()

    _GHOST_CACHE = None

    def ghost_suggest(self):
        T = self.term
        buf = T.buf
        if not buf or T.busy or self.prompt_name or self.help is not None:
            return None
        if T.caret != len(buf) or len(buf) > 80:
            return None
        if buf.endswith(" "):
            for h in reversed(T.history):
                if h.startswith(buf) and len(h) > len(buf):
                    return h[len(buf):]
            return None
        if " " in buf:
            for h in reversed(T.history):
                if h != buf and h.startswith(buf) and len(h) > len(buf):
                    return h[len(buf):]
            return None
        if App._GHOST_CACHE is None:
            App._GHOST_CACHE = sorted(set(list(TOOL_MAP.keys()) +
                                          list(TTY_PROGRAMS) +
                                          list(T.macros.keys()) +
                                          ["cd", "sudo", "man", "which"]))
        for n in App._GHOST_CACHE:
            if n.startswith(buf) and n != buf:
                return n[len(buf):]
        return None


    # ── v14 PRO: xp / achievements / pet / music / timer / konami ──

    def level(self):
        return 1 + int(math.sqrt(self._xp / 75.0))

    def add_xp(self, n):
        old_lvl = self.level()
        self._xp += n
        save_profile_field("xp", self._xp)
        new_lvl = self.level()
        if new_lvl > old_lvl:
            T = self.term
            T.push([("  ╭", C_SLATE), ("────────────✦", C_GOLD), ("────────────╮", C_SLATE)])
            T.push([("  │  ", C_SLATE), ("⬆ LEVEL UP!  LVL %d" % new_lvl, C_GOLD),
                    ("  •  pet bhi bada ho gaya!", C_PINK)])
            T.push([("  ╰", C_SLATE), ("────────────✦", C_GOLD), ("────────────╯", C_SLATE)])
            if new_lvl >= 3:
                T.push([("  ✦ pet evolve hua — dekho: ", C_DIM), ("pet", C_CYAN)])

    def award(self, aid):
        if aid in self._ach:
            return
        meta = next((a for a in ACHIEVEMENTS if a[0] == aid), None)
        if meta is None:
            return
        self._ach.append(aid)
        save_profile_field("ach", self._ach)
        self.term.push([("  🏆 ACHIEVEMENT » ", C_GOLD), (meta[1], C_FUCHSIA),
                        (" — " + meta[2], C_DIM)])

    def cmd_tick(self):
        self.last_cmd_t = time.monotonic()
        self._cmd_count += 1
        save_profile_field("cmd_count", self._cmd_count)
        if self._cmd_count == 1:
            self.award("first_cmd")
        if self._cmd_count >= 50:
            self.award("fifty")
        h = time.localtime().tm_hour
        if 1 <= h < 4:
            self.award("night_owl")

    def tool_tick(self, tool):
        if tool.name not in self._seen:
            self._seen.append(tool.name)
            save_profile_field("seen_tools", self._seen)
            self.add_xp(8)
            if len(self._seen) >= 10:
                self.award("explorer10")
            if len(self._seen) >= len(TOOLS):
                self.award("explorerall")
        aid = TOOL_ACH.get(tool.name)
        if aid:
            self.award(aid)

    def _konami_on(self):
        self.confetti_until = time.monotonic() + 4.0
        cols = list(GRAD_STOPS) + [C_GOLD, C_WHITE]
        W, H = self.cv.w, self.cv.h
        self.confetti = [{"x": random.uniform(0, W), "y": random.uniform(-24, 0),
                          "vy": random.uniform(10, 26), "c": random.choice(cols),
                          "ch": random.choice("✦*·+•")} for _ in range(70)]
        self.term.push([("  🌈 KONAMI CODE! ", C_GOLD),
                        ("cheat activated — khush ho ja ✦", C_FUCHSIA)])
        self.award("konami")

    def _confetti_tick(self, dt):
        H = self.cv.h
        for p in self.confetti:
            p["y"] += p["vy"] * dt
        self.confetti = [p for p in self.confetti if p["y"] < H]

    def _draw_confetti(self, cv, t):
        if not self.confetti or time.monotonic() > self.confetti_until:
            self.confetti = []
            return
        for p in self.confetti:
            cv.set(int(p["x"]) % cv.w, int(p["y"]), p["ch"], p["c"])

    def _music_tick(self):
        now = time.monotonic()
        if now - self.last_music_t < 3.0:
            return
        self.last_music_t = now
        d = _music_raw(self, self.music_player) if self._pc_path else None
        if (not d or not d.get("title")) and _mpv_alive(self):
            d = _mpv_now(self)
        self.music_info = d
        self._mi_t = now if (d and d.get("title")) else 0.0

    def _timer_tick(self, now):
        if self.timer_until is None or now < self.timer_until:
            return
        lbl = self.timer_label or "TIMER"
        self.timer_until = None
        self.timer_label = ""
        T = self.term
        T.push([("  ⏰ ", C_GOLD), ("%s POORA HUA!" % lbl, C_FUCHSIA),
                ("  (%s)" % time.strftime("%H:%M"), C_DIM)])
        if self.is_termux and shutil.which("termux-notification"):
            _cap("termux-notification --title 'CUTIE %s' --content 'time up ⏰'" % lbl, 4)
        elif shutil.which("notify-send"):
            try:
                subprocess.run(["notify-send", "-a", "CUTIE OS",
                                "⏰ CUTIE %s" % lbl, "time up!"], timeout=4)
            except Exception:
                pass
        if lbl == "FOCUS":
            self.award("focused")


    # ── v16: MUSIC STAGE PAGE ──

    def open_mpage(self):
        self.mpage = True
        self.last_music_t = 0.0
        self._music_tick()

    def _mp_ctrl(self, act, arg=None):
        if _mpv_alive(self):
            if act == "toggle":
                _mpv_cmd(self, {"command": ["cycle", "pause"]})
            elif act == "next":
                _mpv_cmd(self, {"command": ["playlist-next"]})
                if self.mpv_idx < len(self.mpv_list) - 1:
                    self.mpv_idx += 1
            elif act == "prev":
                _mpv_cmd(self, {"command": ["playlist-prev"]})
                if self.mpv_idx > 0:
                    self.mpv_idx -= 1
            elif act == "seek":
                try:
                    _mpv_cmd(self, {"command": ["seek", float(arg)]})
                except Exception:
                    pass
            elif act == "vol":
                try:
                    _mpv_cmd(self, {"command": ["add", "volume", float(arg)]})
                except Exception:
                    pass
        elif self._pc_path:
            base = ["playerctl"]
            if self.music_player:
                base += ["-p", self.music_player]
            if act == "toggle":
                run_cmd(base + ["play-pause"], 3)
            elif act in ("next", "prev"):
                run_cmd(base + ["previous" if act == "prev" else "next"], 3)
            elif act == "seek":
                run_cmd(base + ["position", ("%d+" % int(arg)) if arg > 0 else ("%d-" % int(-arg))], 3)
            elif act == "vol":
                run_cmd(base + ["volume", ("%.2f+" % (arg / 100.0)) if arg > 0 else ("%.2f-" % (-arg / 100.0))], 3)
        self.last_music_t = 0.0
        self._music_tick()

    def handle_mpage_event(self, ev):
        kind, ch = ev[0], ev[1]
        if kind == "EOF":
            self.running = False
            return
        if kind in ("CTRL_C", "ESC") or (kind == "CHAR" and ch in ("q", "Q")):
            self.mpage = False
            return
        if kind == "CHAR" and ch == " ":
            self._mp_ctrl("toggle")
        elif kind == "CHAR" and ch in ("n", "N"):
            self._mp_ctrl("next")
        elif kind == "CHAR" and ch in ("p", "P"):
            self._mp_ctrl("prev")
        elif kind == "RIGHT":
            self._mp_ctrl("seek", 10)
        elif kind == "LEFT":
            self._mp_ctrl("seek", -10)
        elif kind == "CHAR" and ch in ("+", "="):
            self._mp_ctrl("vol", 5)
        elif kind == "CHAR" and ch in ("-", "_"):
            self._mp_ctrl("vol", -5)

    def build_mpage_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        b = C_TERM_BORDER
        cv.put(0, 0, "╭" + "─" * (W - 2) + "╮", b)
        cv.put(0, H - 1, "╰" + "─" * (W - 2) + "╯", b)
        for yy in range(1, H - 1):
            cv.put(0, yy, "│", b)
            cv.put(W - 1, yy, "│", b)
        mi = self.music_info
        now = time.monotonic()
        local = _mpv_alive(self)
        if not mi or not mi.get("title"):
            cv.put(max(2, (W - 20) // 2), H // 2 - 1, "♪ kuch nahi baj raha", C_FUCHSIA)
            sub = "music ls → music play 5  •  ya spotify chalao  •  Q = close"
            cv.put(max(2, (W - disp_width(sub)) // 2), H // 2 + 1, clip(sub, W - 4), C_DIM)
            return cv.render()
        title = mi.get("title") or "?"
        artist = mi.get("artist") or ""
        status = mi.get("status", "Playing")
        sym = {"Playing": "▶", "Paused": "❚❚", "Stopped": "■"}.get(status, "♪")
        cv.put(2, 1, clip("♪ NOW PLAYING", W - 4), C_TITLE)
        if local:
            tag = "local • mpv"
            if self.mpv_list:
                tag += "  •  %d/%d" % (self.mpv_idx + 1, len(self.mpv_list))
        else:
            tag = mi.get("pname") or "mpris"
        cv.put(max(14, W - 2 - disp_width(tag)), 1, clip(tag, W - 16), C_SLATE)
        ty = max(4, H // 2 - 7)
        n = max(1, len(title))
        cx = max(2, (W - disp_width(title)) // 2)
        for i, chx in enumerate(title):
            cv.put(cx, ty, chx, grad(i / float(n)))
            cx += char_width(chx)
        if artist:
            asub = "— " + artist + " —"
            cv.put(max(2, (W - disp_width(asub)) // 2), ty + 1, clip(asub, W - 6), C_LABEL)
        playing = (status == "Playing")
        eqw = min(56, W - 12)
        ex = (W - eqw) // 2
        ey = ty + 3
        for i in range(eqw):
            ph = t * 3.1 + i * 0.55
            amp = (math.sin(ph) * 0.5 + 0.5) * (math.sin(ph * 0.37 + i * 1.7) * 0.5 + 0.5)
            if not playing:
                amp *= 0.22
            hh = 1 + int(amp * 2.99)
            for k in range(hh):
                cv.set(ex + i, ey + 2 - k, "▄" if k == 0 else "█",
                       scale(grad(i / float(eqw - 1)), 0.8 if k == 0 else 1.0))
        pos = mi.get("pos_us", 0) / 1e6
        ln = mi.get("len_us", 0) / 1e6
        if playing and self._mi_t:
            pos += (now - self._mi_t)
        if ln > 0:
            pos = clamp(pos, 0.0, ln)
        by = ey + 5
        bw = max(12, W - 24)
        bx = (W - bw) // 2
        filled = int((pos / ln) * bw) if ln > 0 else 0
        for i in range(bw):
            if i < filled:
                cv.set(bx + i, by, "█", grad(i / float(bw - 1)))
            else:
                cv.set(bx + i, by, "░", C_BAR_EMPTY)
        tstr = "%s / %s" % (_hms(pos), _hms(ln) if ln > 0 else "∞")
        cv.put(max(2, (W - disp_width(tstr)) // 2), by + 1, tstr, C_VALUE)
        st = "%s %s" % (sym, status)
        cv.put(max(2, (W - disp_width(st)) // 2), by + 3, st,
               C_CYAN if playing else C_GOLD)
        volpct = None
        if local:
            rr = _mpv_cmd(self, {"command": ["get_property", "volume"]})
            try:
                volpct = float((rr or {}).get("data") or 0)
            except Exception:
                volpct = None
        elif mi.get("vol"):
            try:
                volpct = float(mi["vol"]) * 100.0
            except Exception:
                volpct = None
        fy = H - 2
        if volpct is not None and by + 5 < fy:
            vbw = 12
            vbx = (W - vbw) // 2
            vby = by + 5
            vf = int(clamp(volpct, 0, 100) / 100.0 * vbw)
            cv.put(vbx - 5, vby, "VOL ", C_LABEL)
            for i in range(vbw):
                cv.set(vbx + i, vby, "█" if i < vf else "░",
                       C_CYAN if i < vf else C_BAR_EMPTY)
            cv.put(vbx + vbw + 1, vby, "%3.0f%%" % volpct, C_VALUE)
        foot = "SPACE pause • N next • P prev • ←→ seek 10s • +/- vol • Q close"
        cv.put(max(2, (W - disp_width(foot)) // 2), fy, clip(foot, W - 4), C_SLATE)
        return cv.render()


    # ── v17: CODE BROWSER PAGE ──

    def open_cpage(self, path=None):
        p = os.path.expanduser(path or self.term.cwd)
        if not os.path.isdir(p):
            p = os.path.expanduser("~")
        qs = []
        for lab, pth in QACCESS:
            fp = os.path.expanduser(pth)
            if os.path.isdir(fp):
                qs.append((lab, fp))
        self.cpage = {"cwd": p, "sel": 0, "scroll": 0, "mode": "list",
                      "pv": None, "pvname": "", "pvscroll": 0, "q": qs}

    def _cpage_entries(self):
        try:
            names = sorted(os.listdir(self.cpage["cwd"]), key=str.lower)
        except Exception:
            return []
        dirs = []
        files = []
        for nm in names:
            if nm.startswith("."):
                continue
            if os.path.isdir(os.path.join(self.cpage["cwd"], nm)):
                dirs.append(nm + "/")
            else:
                files.append(nm)
        return dirs + files

    def _cpage_run(self, name):
        full = os.path.join(self.cpage["cwd"], name)
        ext = os.path.splitext(full)[1].lower()
        self.cpage = None
        T = self.term
        T.echo_cmd(("run " if ext == ".py" else "bash ") + name)
        if ext == ".py":
            exe = shutil.which("python3") or shutil.which("python")
            if exe is None:
                T.dim("  python nahi mila")
                return
            self.start_capture(shlex.quote(exe) + " " + shlex.quote(full))
            self.cap_colorizer = _py_out_colorizer
        elif ext in (".c", ".cpp"):
            cc = shutil.which("gcc" if ext == ".c" else "g++")
            if cc is None:
                T.dim("  gcc/g++ nahi — !sudo pacman -S gcc")
                return
            outb = "/tmp/cutie-cc-%d" % os.getpid()
            self.start_capture(shlex.quote(cc) + " " + shlex.quote(full) +
                               " -o " + outb + " && " + outb)
        elif ext == ".js" and shutil.which("node"):
            self.start_capture(shlex.quote(shutil.which("node")) + " " + shlex.quote(full))
        else:
            self.start_capture("bash " + shlex.quote(full))
        self.cap_t0 = time.monotonic()
        self.cmd_tick()
        self.add_xp(2)

    def _cpage_edit(self, name):
        full = os.path.join(self.cpage["cwd"], name)
        self.cpage = None
        ed = os.environ.get("VISUAL") or os.environ.get("EDITOR")
        if not ed:
            for c in ("nvim", "vim", "nano", "vi"):
                if shutil.which(c):
                    ed = c
                    break
        if not ed:
            self.term.dim("  koi editor nahi — nano install karo")
            return
        self.run_pty([ed, full])

    def _cpage_preview(self, name):
        full = os.path.join(self.cpage["cwd"], name)
        try:
            with open(full, "rb") as f:
                raw = f.read(200000)
            lines = raw.decode("utf-8", "replace").split("\n")
        except Exception as e:
            self.term.push([("  ✗ read fail: ", C_RED), (str(e)[:60], C_DIM)])
            return
        cp = self.cpage
        cp["mode"] = "preview"
        cp["pv"] = lines[:400]
        cp["pvname"] = name
        cp["pvscroll"] = 0

    def _cpage_activate(self):
        cp = self.cpage
        ents = self._cpage_entries()
        if not ents:
            return
        nm = ents[min(cp["sel"], len(ents) - 1)]
        if nm.endswith("/"):
            self.open_cpage(os.path.join(cp["cwd"], nm))
            return
        ext = os.path.splitext(nm)[1].lower()
        if ext in (".py", ".sh"):
            self._cpage_run(nm)
        else:
            self._cpage_preview(nm)

    def handle_cpage_event(self, ev):
        kind, ch = ev[0], ev[1]
        cp = self.cpage
        if kind == "EOF":
            self.running = False
            return
        if cp["mode"] == "preview":
            if kind in ("CTRL_C", "ESC") or (kind == "CHAR" and ch in ("q", "Q", "v", "V")):
                cp["mode"] = "list"
                cp["pv"] = None
            elif kind == "UP" or (kind == "CHAR" and ch in ("k", "w")):
                cp["pvscroll"] = max(0, cp["pvscroll"] - 1)
            elif kind == "DOWN" or (kind == "CHAR" and ch in ("j", "s")):
                cp["pvscroll"] += 1
            elif kind == "PGUP":
                cp["pvscroll"] = max(0, cp["pvscroll"] - 20)
            elif kind == "PGDN":
                cp["pvscroll"] += 20
            return
        if kind in ("CTRL_C", "ESC") or (kind == "CHAR" and ch in ("q", "Q")):
            self.cpage = None
            return
        ents = self._cpage_entries()
        n = len(ents)
        if kind == "UP" or (kind == "CHAR" and ch in ("k", "w")):
            cp["sel"] = max(0, cp["sel"] - 1)
        elif kind == "DOWN" or (kind == "CHAR" and ch in ("j", "s")):
            cp["sel"] = min(max(0, n - 1), cp["sel"] + 1)
        elif kind == "PGUP":
            cp["sel"] = max(0, cp["sel"] - 12)
        elif kind == "PGDN":
            cp["sel"] = min(max(0, n - 1), cp["sel"] + 12)
        elif kind == "HOME":
            cp["sel"] = 0
        elif kind == "END":
            cp["sel"] = max(0, n - 1)
        elif kind in ("BACKSPACE", "LEFT") or (kind == "CHAR" and ch == "h"):
            self.open_cpage(os.path.dirname(cp["cwd"].rstrip("/")) or "/")
        elif kind == "ENTER" or kind in ("RIGHT", "F1") or (kind == "CHAR" and ch in ("l", "r", "R")):
            self._cpage_activate()
        elif kind == "CHAR" and ch in ("v", "V"):
            if n:
                nm = ents[min(cp["sel"], n - 1)]
                if not nm.endswith("/"):
                    self._cpage_preview(nm)
        elif kind == "CHAR" and ch in ("e", "E"):
            if n:
                self.open_epage(os.path.join(cp["cwd"], ents[min(cp["sel"], n - 1)]))
        elif kind == "CHAR" and ch in ("g", "G"):
            self.open_cpage("~")
        elif kind == "CHAR" and ch and ch in "123456789" and cp.get("q"):
            i = int(ch) - 1
            if i < len(cp["q"]):
                self.open_cpage(cp["q"][i][1])

    def build_cpage_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        b = C_TERM_BORDER
        cp = self.cpage
        cv.put(0, 0, "╭" + "─" * (W - 2) + "╮", b)
        cv.put(0, H - 1, "╰" + "─" * (W - 2) + "╯", b)
        for yy in range(1, H - 1):
            cv.put(0, yy, "│", b)
            cv.put(W - 1, yy, "│", b)
        if cp["mode"] == "preview":
            return self._cpage_preview_render(cv, W, H)
        ents = self._cpage_entries()
        n = len(ents)
        cp["sel"] = clamp(cp["sel"], 0, max(0, n - 1))
        home = os.path.expanduser("~")
        disp = cp["cwd"].replace(home, "~", 1) if cp["cwd"].startswith(home) else cp["cwd"]
        pos = " %d/%d " % (cp["sel"] + 1, n)
        px = W - 2 - disp_width(pos)
        cv.put(2, 0, "◆ CODE", C_TITLE)
        if px > 22:
            cv.put(9, 0, clip("— " + disp, px - 10), C_LABEL)
            cv.put(px, 0, pos, C_SLATE)
        body = H - 6
        if cp["scroll"] > cp["sel"]:
            cp["scroll"] = cp["sel"]
        if cp["scroll"] < cp["sel"] - body + 1:
            cp["scroll"] = cp["sel"] - body + 1
        cp["scroll"] = clamp(cp["scroll"], 0, max(0, n - body))
        for r in range(body):
            idx = cp["scroll"] + r
            if idx >= n:
                break
            nm = ents[idx]
            sel = (idx == cp["sel"])
            yy = 2 + r
            cv.put(2, yy, "▸ " if sel else "  ", C_GOLD if sel else C_SLATE)
            if nm.endswith("/"):
                cv.put(4, yy, clip(nm, W - 18), C_CYAN)
            elif nm.lower().endswith(".py"):
                cv.put(4, yy, clip(nm, W - 18), C_VIOLET if sel else C_VALUE)
            else:
                cv.put(4, yy, clip(nm, W - 18), C_OUT if sel else C_DIM)
            try:
                stt = os.stat(os.path.join(cp["cwd"], nm))
                sz = "«dir»" if nm.endswith("/") else _size_str(stt.st_size)
            except Exception:
                sz = "?"
            cv.put(max(6, W - 10), yy, clip(sz.rjust(7), 8), C_SLATE)
        qy = H - 4
        qsegs = [("QUICK ", C_FUCHSIA)]
        acc = 6
        for i, (lab, pth) in enumerate(cp["q"]):
            homeh = pth.replace(home, "~", 1)
            tgs = "[%d]%s " % (i + 1, homeh)
            tw = disp_width(tgs)
            if acc + tw > W - 8:
                break
            qsegs.append((tgs, C_VALUE if i % 2 == 0 else C_OUT))
            acc += tw
        put_segs(cv, 2, qy, qsegs)
        foot = "↑↓ • ENTER run/open • V preview • E edit • ← parent • 1-9 quick • F1 run • Q close"
        cv.put(max(2, (W - disp_width(foot)) // 2), H - 2, clip(foot, W - 4), C_SLATE)
        return cv.render()

    def _cpage_preview_render(self, cv, W, H):
        cp = self.cpage
        cv.put(2, 0, "◆ PREVIEW", C_TITLE)
        cv.put(12, 0, clip("— " + cp["pvname"], W - 26), C_LABEL)
        cv.put(W - 2 - 9, 0, "ESC back", C_SLATE)
        body = H - 4
        lines = cp["pv"] or []
        cp["pvscroll"] = clamp(cp["pvscroll"], 0, max(0, len(lines) - body))
        for r in range(body):
            idx = cp["pvscroll"] + r
            if idx >= len(lines):
                break
            ln = lines[idx]
            cv.put(2, 2 + r, "%4d " % (idx + 1), C_SLATE)
            x = 7
            for seg, col in _pyhl(ln[: max(4, W - 10)]):
                if x >= W - 3:
                    break
                cv.put(x, 2 + r, seg, col)
                x += disp_width(seg)
        foot = "↑↓ scroll • ESC/V back • E edit in " + (os.environ.get("EDITOR") or "editor")
        cv.put(max(2, (W - disp_width(foot)) // 2), H - 2, clip(foot, W - 4), C_SLATE)
        return cv.render()


    # ── v18: CUTIE EDITOR (mini VS Code, HUD ke andar) ──

    def open_epage(self, path):
        p = os.path.expanduser(path)
        if os.path.isdir(p):
            self.term.dim("  ye folder hai — file ka naam do")
            return
        lines = [""]
        try:
            with open(p, "rb") as f:
                txt = f.read(400000).decode("utf-8", "replace")
            lines = txt.split("\n")
            if len(lines) > 5000:
                lines = lines[:5000]
        except FileNotFoundError:
            pass
        except Exception as e:
            self.term.push([("  ✗ read fail: ", C_RED), (str(e)[:60], C_DIM)])
            return
        if not lines:
            lines = [""]
        fresh = not os.path.exists(p)
        self.epage = {"path": p, "lines": lines, "cy": 0, "cx": 0,
                      "scroll": 0, "hscroll": 0, "dirty": False,
                      "confirm": False, "banner": True, "preview": True,
                      "check": None, "check_t": 0.0, "outline": [], "out_sel": 0,
                      "fresh": fresh,
                      "msg": ("✿ naya file — likhna shuru! CTRL+T template • F1 run"
                              if fresh else
                              "✎ CUTIE EDITOR — F1 run • CTRL+S save • CTRL+Q quit"),
                      "msg_t": time.monotonic()}
        if fresh and not self.epage["lines"]:
            self.epage["lines"] = [""]

    def _epage_save(self, quiet=False):
        ep = self.epage
        try:
            d = os.path.dirname(ep["path"])
            if d:
                os.makedirs(d, exist_ok=True)
            with open(ep["path"], "w", encoding="utf-8") as f:
                f.write("\n".join(ep["lines"]) + "\n")
            ep["dirty"] = False
            ep["msg"] = "saved ✓ " + ep["path"]
            ep["msg_t"] = time.monotonic()
            if not quiet:
                self.term.push([("  ✎ saved » ", C_DIM), (ep["path"], C_GOLD)])
            return True
        except Exception as e:
            ep["msg"] = "✗ save fail: " + str(e)[:50]
            ep["msg_t"] = time.monotonic()
            return False

    def _epage_flush_out(self):
        ep = self.epage
        ol = ep.get("out") or []
        if not ol or self.term.busy:
            return
        T = self.term
        T.push([("  ▢ editor output (aakhri lines) —", C_DIM)])
        for segs in ol[-8:]:
            T.push(segs if isinstance(segs, list) else [(str(segs), C_OUT)])
        T.push([("  ▢ (editor band — dobara F1 = fresh run)", C_SLATE)])

    def _epage_run(self):
        ep = self.epage
        if self.term.busy:
            ep["msg"] = "⏳ pehle wala chal raha — CTRL+C kill kar"
            ep["msg_t"] = time.monotonic()
            return
        if not self._epage_save(quiet=True):
            return
        path = ep["path"]
        ext = os.path.splitext(path)[1].lower()
        exe = shutil.which("python3") or shutil.which("python")
        cmd = None
        colorize = False
        if ext == ".py" and exe:
            cmd = shlex.quote(exe) + " " + shlex.quote(path)
            colorize = True
        elif ext == ".sh":
            cmd = "bash " + shlex.quote(path)
        elif ext in (".c", ".cpp"):
            cc = shutil.which("gcc" if ext == ".c" else "g++")
            if cc is None:
                ep["msg"] = "✗ gcc/g++ nahi — !sudo pacman -S gcc"
                ep["msg_t"] = time.monotonic()
                return
            outb = "/tmp/cutie-cc-%d" % os.getpid()
            cmd = shlex.quote(cc) + " " + shlex.quote(path) + " -o " + outb + " && " + outb
        elif ext == ".js" and shutil.which("node"):
            cmd = shlex.quote(shutil.which("node")) + " " + shlex.quote(path)
        else:
            ep["msg"] = "✧ .py .sh .c .cpp .js hi run hote hain"
            ep["msg_t"] = time.monotonic()
            return
        ep["out"] = []
        ep["out_mode"] = True
        ep["msg"] = "▶ running " + os.path.basename(path) + " … (CTRL+C kill)"
        ep["msg_t"] = time.monotonic()
        self.epage_out = True
        self.start_capture(cmd)
        if colorize:
            self.cap_colorizer = _py_out_colorizer
        self.cap_t0 = time.monotonic()
        self.cmd_tick()
        self.add_xp(2)

    def _epage_enter(self):
        ep = self.epage
        lines = ep["lines"]
        ln = lines[ep["cy"]]
        indent = re.match(r"[ \t]*", ln).group(0)
        if ln[:ep["cx"]].rstrip().endswith(":"):
            indent += "    "
        rest = ln[ep["cx"]:]
        lines[ep["cy"]] = ln[:ep["cx"]]
        lines.insert(ep["cy"] + 1, indent + rest)
        ep["cy"] += 1
        ep["cx"] = len(indent)
        ep["dirty"] = True

    def _epage_code_w(self):
        W = self.cv.w
        ep = self.epage
        if ep.get("preview", True) and W >= 100:
            return max(40, int(W * 0.58))
        return W

    def _epage_ensure_visible(self):
        ep = self.epage
        H = self.cv.h
        W = self.cv.w
        bh = 6 if (ep.get("banner", True) and H >= 26 and W >= 70) else 0
        body = max(1, H - 6 - bh)
        if ep["scroll"] > ep["cy"]:
            ep["scroll"] = ep["cy"]
        if ep["scroll"] < ep["cy"] - body + 1:
            ep["scroll"] = ep["cy"] - body + 1
        ep["scroll"] = clamp(ep["scroll"], 0, max(0, len(ep["lines"]) - 1))
        w = max(4, self._epage_code_w() - 12)
        if ep["cx"] < ep["hscroll"]:
            ep["hscroll"] = ep["cx"]
        if ep["cx"] > ep["hscroll"] + w - 1:
            ep["hscroll"] = ep["cx"] - w + 1
        ep["hscroll"] = max(0, ep["hscroll"])

    def handle_epage_event(self, ev):
        kind, ch = ev[0], ev[1]
        ep = self.epage
        lines = ep["lines"]
        pairs = {"(": ")", "[": "]", "{": "}"}
        self._ep_last_key = time.monotonic()
        if kind == "EOF":
            self.running = False
            return
        mini = ep.get("mini")
        if mini:
            if kind in ("ESC", "CTRL_C"):
                ep["mini"] = None
            elif kind == "ENTER":
                q = mini["text"].strip()
                ep["mini"] = None
                if mini["mode"] == "saveas":
                    if not q:
                        q = os.path.basename(ep["path"])
                    if not os.path.splitext(q)[1]:
                        q += os.path.splitext(ep["path"])[1]
                    newp = q if os.path.isabs(q) else os.path.join(
                        os.path.dirname(ep["path"]), q)
                    if os.path.abspath(newp) != os.path.abspath(ep["path"]) and \
                            os.path.exists(newp):
                        ep["mini"] = {"mode": "saveas", "text": q}
                        ep["msg"] = "✗ ye naam already hai — dusra do"
                        ep["msg_t"] = time.monotonic()
                        return
                    ep["path"] = newp
                    self._epage_save()
                    ep["fresh"] = False
                    return
                if mini["mode"] == "goto":
                    try:
                        n = int(q)
                    except Exception:
                        return
                    ep["cy"] = clamp(n - 1, 0, len(lines) - 1)
                    ep["cx"] = 0
                    ep["msg"] = "✦ line %d" % (ep["cy"] + 1)
                elif q:
                    start = ep["cy"]
                    for k in range(1, len(lines) + 1):
                        i = (start + k) % len(lines)
                        if q.lower() in lines[i].lower():
                            ep["cy"] = i
                            ep["cx"] = lines[i].lower().find(q.lower())
                            ep["msg"] = "✓ line %d pe mila" % (i + 1)
                            break
                    else:
                        ep["msg"] = "✗ nahi mila: " + q[:30]
                else:
                    return
                ep["msg_t"] = time.monotonic()
                self._epage_ensure_visible()
            elif kind == "BACKSPACE":
                mini["text"] = mini["text"][:-1]
            elif kind == "CHAR" and ch and ch not in ("\n", "\r"):
                mini["text"] = (mini["text"] + ch)[:40]
            return
        if kind in ("CHAR", "ENTER", "BACKSPACE", "DEL", "TAB",
                    "CTRL_D", "CTRL_K", "CTRL_T"):
            ep.setdefault("undo", []).append((list(lines), ep["cy"], ep["cx"]))
            if len(ep["undo"]) > 150:
                del ep["undo"][:50]
            ep.setdefault("redo", [])
        if kind == "CTRL_Q":
            if ep["dirty"] and not ep.get("confirm"):
                ep["confirm"] = True
                ep["msg"] = "⚠ modified! CTRL+Q dobara = bina save chhodo"
                ep["msg_t"] = time.monotonic()
                return
            self._epage_flush_out()
            self.epage = None
            self.epage_out = False
            return
        ep["confirm"] = False
        if kind in ("CTRL_S", "F2"):
            base = os.path.basename(ep["path"])
            if base.startswith("untitled"):
                ep["mini"] = {"mode": "saveas", "text": base}
                ep["msg"] = "✎ naam do + ENTER (ya bas ENTER = same naam)"
                ep["msg_t"] = time.monotonic()
                return
            self._epage_save()
            return
        if kind == "F1":
            self._epage_run()
            return
        if kind == "ESC":
            if ep["dirty"]:
                ep["msg"] = "dirty — CTRL+S save • CTRL+Q ×2 discard"
                ep["msg_t"] = time.monotonic()
            else:
                self._epage_flush_out()
                self.epage = None
                self.epage_out = False
            return
        if kind == "CTRL_C":
            if self.term.busy:
                self.kill_capture()
                ep["msg"] = "✗ job killed (CTRL+C)"
            else:
                ep["msg"] = "✿ editor se bahar = CTRL+Q"
            ep["msg_t"] = time.monotonic()
            return
        if kind == "CTRL_Z":
            u = ep.get("undo") or []
            if not u:
                ep["msg"] = "✧ kuch undo nahi bacha"
                ep["msg_t"] = time.monotonic()
                return
            st = u.pop()
            ep.setdefault("redo", []).append((list(lines), ep["cy"], ep["cx"]))
            lines[:] = st[0]
            ep["cy"], ep["cx"] = st[1], st[2]
            ep["dirty"] = True
            ep["msg"] = "↶ undo — CTRL+Y redo"
            ep["msg_t"] = time.monotonic()
            self._epage_ensure_visible()
            return
        if kind == "CTRL_Y":
            r = ep.get("redo") or []
            if not r:
                ep["msg"] = "✧ redo khaali"
                ep["msg_t"] = time.monotonic()
                return
            st = r.pop()
            ep.setdefault("undo", []).append((list(lines), ep["cy"], ep["cx"]))
            lines[:] = st[0]
            ep["cy"], ep["cx"] = st[1], st[2]
            ep["dirty"] = True
            ep["msg"] = "↷ redo"
            ep["msg_t"] = time.monotonic()
            self._epage_ensure_visible()
            return
        if kind == "CTRL_D":
            ln = lines[ep["cy"]]
            lines.insert(ep["cy"] + 1, ln)
            ep["cy"] += 1
            ep["cx"] = len(ln)
            ep["dirty"] = True
            ep["msg"] = "⧉ line duplicated"
            ep["msg_t"] = time.monotonic()
            self._epage_ensure_visible()
            return
        if kind == "CTRL_K":
            if len(lines) > 1:
                lines.pop(ep["cy"])
                if ep["cy"] >= len(lines):
                    ep["cy"] = len(lines) - 1
                ep["cx"] = min(ep["cx"], len(lines[ep["cy"]]))
            else:
                lines[0] = ""
                ep["cx"] = 0
            ep["dirty"] = True
            ep["msg"] = "✂ line gayi"
            ep["msg_t"] = time.monotonic()
            self._epage_ensure_visible()
            return
        if kind == "CTRL_F":
            ep["mini"] = {"mode": "find", "text": ""}
            return
        if kind == "CTRL_G":
            ep["mini"] = {"mode": "goto", "text": ""}
            return
        if kind == "CTRL_E":
            ep["preview"] = not ep.get("preview", True)
            ep["msg"] = "preview " + ("on ✦" if ep["preview"] else "off")
            ep["msg_t"] = time.monotonic()
            return
        if kind == "CTRL_B":
            ep["banner"] = not ep.get("banner", True)
            return
        if kind == "CTRL_O":
            self._epage_next_outline()
            return
        if kind == "CTRL_T":
            if lines == [""] or (len(lines) <= 2 and not "".join(lines).strip()):
                lines[:] = _ep_template_lines(ep["path"])
                ep["cy"] = min(2, len(lines) - 1)
                ep["cx"] = 0
                ep["dirty"] = True
                ep["msg"] = "✿ template aa gaya — likhna shuru!"
                ep["msg_t"] = time.monotonic()
            else:
                ep["msg"] = "✧ template sirf khaali file pe"
                ep["msg_t"] = time.monotonic()
            return
        if kind == "CHAR":
            if ch in ("\n", "\r"):
                self._epage_enter()
                self._epage_ensure_visible()
                return
            ln = lines[ep["cy"]]
            nxt = ln[ep["cx"]] if ep["cx"] < len(ln) else ""
            pairs = {"(": ")", "[": "]", "{": "}"}
            if ch == "\t":
                lines[ep["cy"]] = ln[:ep["cx"]] + "    " + ln[ep["cx"]:]
                ep["cx"] += 4
            elif ch in pairs:
                lines[ep["cy"]] = ln[:ep["cx"]] + ch + pairs[ch] + ln[ep["cx"]:]
                ep["cx"] += 1
            elif ch in (")", "]", "}") and nxt == ch:
                ep["cx"] += 1
            elif ch in ('"', "'") and nxt == ch:
                ep["cx"] += 1
            elif ch in ('"', "'"):
                lines[ep["cy"]] = ln[:ep["cx"]] + ch + ch + ln[ep["cx"]:]
                ep["cx"] += 1
            else:
                lines[ep["cy"]] = ln[:ep["cx"]] + ch + ln[ep["cx"]:]
                ep["cx"] += len(ch)
            ep["dirty"] = True
            self._epage_ensure_visible()
            return
        if kind == "TAB":
            ln = lines[ep["cy"]]
            lines[ep["cy"]] = ln[:ep["cx"]] + "    " + ln[ep["cx"]:]
            ep["cx"] += 4
            ep["dirty"] = True
            self._epage_ensure_visible()
            return
        if kind == "ENTER":
            self._epage_enter()
            self._epage_ensure_visible()
            return
        if kind == "BACKSPACE":
            if ep["cx"] > 0:
                ln = lines[ep["cy"]]
                prevc = ln[ep["cx"] - 1]
                nxtc = ln[ep["cx"]] if ep["cx"] < len(ln) else ""
                if (prevc in pairs and nxtc == pairs[prevc]) or \
                        (prevc in ('"', "'") and nxtc == prevc):
                    lines[ep["cy"]] = ln[:ep["cx"] - 1] + ln[ep["cx"] + 1:]
                else:
                    lines[ep["cy"]] = ln[:ep["cx"] - 1] + ln[ep["cx"]:]
                ep["cx"] -= 1
            elif ep["cy"] > 0:
                prev = lines[ep["cy"] - 1]
                lines[ep["cy"] - 1] = prev + lines[ep["cy"]]
                lines.pop(ep["cy"])
                ep["cy"] -= 1
                ep["cx"] = len(prev)
            else:
                return
            ep["dirty"] = True
            self._epage_ensure_visible()
            return
        if kind == "DEL":
            ln = lines[ep["cy"]]
            if ep["cx"] < len(ln):
                lines[ep["cy"]] = ln[:ep["cx"]] + ln[ep["cx"] + 1:]
            elif ep["cy"] < len(lines) - 1:
                lines[ep["cy"]] = ln + lines.pop(ep["cy"] + 1)
            else:
                return
            ep["dirty"] = True
            return
        if kind == "LEFT":
            if ep["cx"] > 0:
                ep["cx"] -= 1
            elif ep["cy"] > 0:
                ep["cy"] -= 1
                ep["cx"] = len(lines[ep["cy"]])
        elif kind == "RIGHT":
            if ep["cx"] < len(lines[ep["cy"]]):
                ep["cx"] += 1
            elif ep["cy"] < len(lines) - 1:
                ep["cy"] += 1
                ep["cx"] = 0
        elif kind == "UP":
            if ep["cy"] > 0:
                ep["cy"] -= 1
                ep["cx"] = min(ep["cx"], len(lines[ep["cy"]]))
        elif kind == "DOWN":
            if ep["cy"] < len(lines) - 1:
                ep["cy"] += 1
                ep["cx"] = min(ep["cx"], len(lines[ep["cy"]]))
        elif kind == "HOME":
            ep["cx"] = 0
        elif kind == "END":
            ep["cx"] = len(lines[ep["cy"]])
        elif kind == "PGUP":
            ep["cy"] = max(0, ep["cy"] - 15)
            ep["cx"] = min(ep["cx"], len(lines[ep["cy"]]))
        elif kind == "PGDN":
            ep["cy"] = min(len(lines) - 1, ep["cy"] + 15)
            ep["cx"] = min(ep["cx"], len(lines[ep["cy"]]))
        self._epage_ensure_visible()

    def _epage_refresh_check(self, ep, now):
        if now - ep.get("check_t", 0.0) < 0.45:
            return
        ep["check_t"] = now
        ep["check"], _, ep["outline"] = _ep_preview_info(ep["path"], ep["lines"])

    def _epage_next_outline(self):
        ep = self.epage
        ol = ep.get("outline") or []
        if not ol:
            ep["msg"] = "✧ koi def/class nahi mila"
            ep["msg_t"] = time.monotonic()
            return
        nxt = None
        for k, item in enumerate(ol):
            if item[0] > ep["cy"]:
                nxt = k
                break
        if nxt is None:
            nxt = 0
        ep["out_sel"] = nxt
        ep["cy"] = ol[nxt][0]
        ep["cx"] = 0
        ep["msg"] = "→ %s %s  (line %d)" % (ol[nxt][1], ol[nxt][2], ol[nxt][0] + 1)
        ep["msg_t"] = time.monotonic()
        self._epage_ensure_visible()

    def build_epage_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        ep = self.epage
        now = time.monotonic()
        self._epage_refresh_check(ep, now)
        show_banner = ep.get("banner", True) and H >= 26 and W >= 70
        icon, lname = _ep_lang(ep["path"])
        use_preview = ep.get("preview", True) and W >= 100
        code_w = self._epage_code_w()
        use_preview = use_preview and code_w < W - 20
        cx_max = (code_w - 3) if use_preview else (W - 3)
        for i in range(W):
            c = scale(grad(i / max(1, W - 1)), 0.8)
            cv.set(i, 0, "─", c)
            cv.set(i, H - 1, "─", c)
        for yy in range(1, H - 1):
            c = scale(grad(yy / max(1, H - 1)), 0.8)
            cv.set(0, yy, "│", c)
            cv.set(W - 1, yy, "│", c)
        cv.set(0, 0, "╭", scale(grad(0.0), 0.8))
        cv.set(W - 1, 0, "╮", scale(grad(1.0), 0.8))
        cv.set(0, H - 1, "╰", scale(grad(0.0), 0.8))
        cv.set(W - 1, H - 1, "╯", scale(grad(1.0), 0.8))
        for k in range(6):
            sx = (k * 57 + int(t * 2.2) + k * k * 11) % max(4, W - 6) + 3
            sy = (k * 31 + int(t * 1.1)) % max(1, H - 14) + (9 if show_banner else 3)
            cv.set(sx, sy, "✦", scale(C_VIOLET, 0.32 + 0.15 * math.sin(t * 1.9 + k * 1.3)))
        tt = "✿ edit " + icon + " "
        cv.put(2, 0, tt, C_PINK)
        x = 2 + disp_width(tt)
        nm = os.path.basename(ep["path"])
        for i, chx in enumerate(nm):
            if x >= W - 30:
                break
            cv.put(x, 0, chx, grad(i / max(1, len(nm) - 1)))
            x += char_width(chx)
        cv.put(x + 1, 0, "●" if ep["dirty"] else "○", C_GOLD if ep["dirty"] else C_SLATE)
        pos = "Ln %d, Col %d " % (ep["cy"] + 1, ep["cx"] + 1)
        cv.put(W - 2 - disp_width(pos), 0, pos, C_LABEL)
        if show_banner:
            _paint_lang_banner(cv, 4, 1, lname.upper(), t)
            cv.put(2, 7, "·" * max(0, (code_w if use_preview else W) - 5),
                   scale(C_SLATE, 0.65))
        content_top = 8 if show_banner else 2
        show_out = bool(ep.get("out")) or bool(ep.get("out_mode"))
        out_rows = 5 if show_out else 0
        body = max(1, H - 5 - content_top - out_rows)
        lines = ep["lines"]
        top = clamp(ep["scroll"], 0, max(0, len(lines) - 1))
        nl = len(lines)
        if use_preview:
            for yy in range(content_top, H - 4):
                cv.set(code_w, yy, "│", scale(C_SLATE, 0.55))
        for r in range(body):
            idx = top + r
            if idx >= nl:
                break
            yy = content_top + r
            cur = (idx == ep["cy"])
            cv.put(1, yy, "❯" if cur else " ", C_GOLD if cur else C_SLATE)
            ncol = grad(idx / max(1, nl))
            if cur:
                ncol = scale(ncol, 1.45)
            cv.put(2, yy, "%4d " % (idx + 1), ncol)
            ln = lines[idx]
            hs = ep["hscroll"]
            x = 7
            for seg, col in _pyhl(ln):
                segw = disp_width(seg)
                endx = x + segw
                if endx <= 7 + hs:
                    x = endx
                    continue
                if x < 7 + hs:
                    cutd = hs - (x - 7)
                    seg, segw = substr_width(seg, cutd, max(0, segw - cutd))
                if x + segw > cx_max:
                    seg, segw = substr_width(seg, 0, max(0, cx_max - x))
                if seg:
                    cv.put(x, yy, seg, col)
                x += segw
                if x >= cx_max:
                    break
            ind = len(re.match(r"[ ]*", ln).group(0))
            for g in range(3, ind, 4):
                gx = 7 + g - hs
                if 7 <= gx < cx_max:
                    cv.set(gx, yy, "┊", scale(C_SLATE, 0.5))
        cury = content_top + (ep["cy"] - top)
        if content_top <= cury < content_top + body:
            curline = lines[ep["cy"]]
            visx = 7 + max(0, ep["cx"] - ep["hscroll"])
            if visx < cx_max:
                if (t % 1.1) < 0.6:
                    chb = curline[ep["cx"]] if ep["cx"] < len(curline) else " "
                    cv.put(visx, cury, chb if chb != " " else "█", C_WHITE)
                elif ep["cx"] < len(curline):
                    cv.put(visx, cury, curline[ep["cx"]], C_WHITE)
        if use_preview:
            px = code_w + 2
            pw = W - px - 2
            if pw > 12:
                cv.put(px, content_top, "◆ LIVE PREVIEW", C_TITLE)
                yy = content_top + 1
                ck = ep.get("check")
                if ck:
                    cv.put(px, yy, clip(ck[0], pw), ck[1])
                yy += 2
                cv.put(px, yy, "◆ OUTLINE", C_FUCHSIA)
                yy += 1
                ol = ep.get("outline") or []
                if not ol:
                    cv.put(px, yy, "(khaali — def/class likho)", C_SLATE)
                    yy += 1
                else:
                    for k2, (li, kd, nm2) in enumerate(ol):
                        if yy >= H - 9 or k2 > 16:
                            break
                        selm = (k2 == ep.get("out_sel", 0))
                        cv.put(px, yy, "❯ " if selm else "  ", C_GOLD if selm else C_SLATE)
                        cc = C_GOLD if selm else (C_VIOLET if kd == "class" else C_CYAN)
                        cv.put(px + 2, yy, clip("%-5s %s" % (kd, nm2), max(4, pw - 9)), cc)
                        cv.put(px + max(6, pw - 6), yy, "%4d" % (li + 1), C_SLATE)
                        yy += 1
                sy2 = max(yy + 1, H - 9)
                if sy2 < H - 6:
                    cv.put(px, sy2, "◆ STATS", C_FUCHSIA)
                    stt = "%d lines • %d ch" % (nl, sum(len(l) for l in lines))
                    cv.put(px, sy2 + 1, clip(stt, pw), C_LABEL)
                    cv.put(px, sy2 + 2, clip("CTRL+O jump • CTRL+E hide", pw), C_SLATE)
        if show_out:
            ow = (code_w - 2) if use_preview else (W - 2)
            ox = 1
            y0 = content_top + body
            if y0 < H - 6:
                cv.put(ox, y0, "◆ OUTPUT", C_TITLE)
                lab = "── live — CTRL+C kill " if self.term.busy else "── tail "
                rem = max(0, ow - 9 - disp_width(lab) - 1)
                cv.put(ox + 9, y0, lab + "─" * rem, scale(C_SLATE, 0.7))
                ol = ep.get("out") or []
                vis = max(0, out_rows - 1)
                for i2, segs in enumerate(ol[-vis:] if vis else []):
                    ry2 = y0 + 1 + i2
                    x2 = ox + 1
                    for t2, c2 in segs:
                        w2 = disp_width(t2)
                        if w2 > ow - x2 - 1:
                            t2 = substr_width(t2, 0, max(0, ow - x2 - 1))[0]
                        if t2:
                            cv.put(x2, ry2, t2, c2)
                            x2 += disp_width(t2)
                        if x2 >= ow:
                            break
        idle = now - getattr(self, "_ep_last_key", now)
        pname = getattr(self, "_pet_name", "momo").lower()
        if idle > 45:
            mx = max(4, W - 18)
            my2 = max(4, H // 2)
            cv.put(mx, my2, "=︿=", scale(C_PINK, 0.65))
            cv.put(mx, my2 + 1, pname + " so rahi hai…", scale(C_SLATE, 0.75))
        my = H - 4
        mini = ep.get("mini")
        msg = ep.get("msg") or ""
        show_msg = msg and (now - ep.get("msg_t", 0)) < 5.0
        if mini:
            lab = "/ find: " if mini["mode"] == "find" else "/ goto: "
            cv.put(2, my, lab, C_FUCHSIA)
            cv.put(2 + disp_width(lab), my, mini["text"] + "▌", C_WHITE)
        else:
            left = "%s %s%s  %d ch" % (icon, lname, "  ●" if ep["dirty"] else "", nl)
            cv.put(2, my, clip(left, 34), C_LABEL)
            if show_msg:
                cv.put(max(2, (W - disp_width(msg)) // 2), my, clip(msg, W - 40), C_GOLD)
            else:
                rot = _CUTE_MSGS[int(t / 5.0) % len(_CUTE_MSGS)]
                cv.put(max(2, (W - disp_width(rot)) // 2), my, clip(rot, W - 40),
                       scale(C_PINK, 0.9))
        pd = ep["path"]
        home = os.path.expanduser("~")
        if pd.startswith(home):
            pd = pd.replace(home, "~", 1)
        cv.put(2, my + 1, clip(pd, W - 6), scale(C_SLATE, 0.85))
        foot = "F1 run • CTRL+S save • CTRL+Z undo • CTRL+Y redo • CTRL+D dup • CTRL+F find • CTRL+G goto • CTRL+O jump • CTRL+E preview • CTRL+Q"
        cv.put(max(2, (W - disp_width(foot)) // 2), H - 2, clip(foot, W - 4), C_SLATE)
        return cv.render()


    # ── v25 OMEGA: ai / chat / dash / fuzzy / boot / weather ──

    def _wx_loop(self):
        while True:
            out = run_cmd(["curl", "-s", "--max-time", "8",
                           "https://wttr.in/?format=%c+%t"], 10)
            if out.strip():
                self.wx = out.strip()[:18]
            time.sleep(600)

    def _boot_seq(self):
        if load_profile().get("boot") == "off" or os.environ.get("CUTIE_NO_BOOT") == "1":
            return
        out = self.out
        try:
            out.write(CLEAR_SCR + CUR_HIDE)
            out.flush()
        except Exception:
            return
        user = getattr(self.info, "user", "cutie")
        host = getattr(self.info, "hostname", "pc")
        lines = [
            ("CUTIE BIOS v25 — memory check ✓ 16384MB ok", C_SLATE),
            ("[ OK ] mounted /home/%s ❤" % user, C_DIM),
            ("[ OK ] loaded %d tools • %d themes" % (len(TOOLS), len(THEMES)), C_DIM),
            ("[ OK ] pet daemon: %s online =^..^=" % getattr(self, "_pet_name", "momo"), C_DIM),
            ("[ OK ] sudo bridge armed", C_DIM),
            ("[ OK ] vibes calibrated ✦", C_GOLD),
            ("Starting CUTIE OS %s on %s…" % (VERSION, host), C_LABEL),
        ]
        try:
            for i, (ln, col) in enumerate(lines):
                out.write(ESC + "[%d;1H" % (min(20, 4 + i)) + fg(col) + ln + RESET)
                out.flush()
                time.sleep(0.14)
            time.sleep(0.25)
            out.write(CLEAR_SCR)
            out.flush()
        except Exception:
            pass

    def open_dash(self):
        self.dash = True

    _DIGL = {
        "0": (" ███ ", "█   █", "█   █", "█   █", "█   █", " ███ "),
        "1": ("  █  ", " ██  ", "  █  ", "  █  ", "  █  ", " ███ "),
        "2": (" ███ ", "█   █", "   ██", "  █  ", " █   ", "█████"),
        "3": (" ███ ", "█   █", "  ██ ", "   █ ", "█   █", " ███ "),
        "4": ("   ██", "  █ █", " █  █", "█████", "    █", "    █"),
        "5": ("█████", "█    ", "████ ", "    █", "█   █", " ███ "),
        "6": (" ███ ", "█    ", "████ ", "█   █", "█   █", " ███ "),
        "7": ("█████", "    █", "   █ ", "  █  ", " █   ", " █   "),
        "8": (" ███ ", "█   █", " ███ ", "█   █", "█   █", " ███ "),
        "9": (" ███ ", "█   █", " ████", "    █", "    █", " ███ "),
        ":": ("     ", "  ██ ", "  ██ ", "  ██ ", "  ██ ", "     "),
    }

    def _block_text(self, text, glyphs):
        text = "".join(ch if ch in glyphs else " " for ch in text)
        try:
            return ["".join(r) for r in zip(*(glyphs[c] for c in text))]
        except Exception:
            return []

    def build_dash_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        b = C_TERM_BORDER
        cv.put(0, 0, "╭" + "─" * (W - 2) + "╮", b)
        cv.put(0, H - 1, "╰" + "─" * (W - 2) + "╯", b)
        for yy in range(1, H - 1):
            cv.put(0, yy, "│", b)
            cv.put(W - 1, yy, "│", b)
        cv.put(2, 1, "◆ CUTIE DASH", C_TITLE)
        cv.put(W - 2 - 10, 1, "cockpit ✦", C_SLATE)
        clk = time.strftime("%H:%M")
        rows = self._block_text(clk, self._DIGL)
        n = max(1, disp_width(rows[0]) if rows else 1)
        x0 = max(2, (W - n) // 2)
        for ry, line in enumerate(rows[:6]):
            for i, ch in enumerate(line):
                if ch != " ":
                    cv.set(x0 + i, 3 + ry, ch, grad((i + ry * 3) / float(n + 12)))
        if self.wx:
            cv.put(max(2, (W - disp_width(self.wx)) // 2), 10, self.wx, C_CYAN)
        y = 12
        half = max(18, (W - 8) // 2)
        self._dash_row(cv, 2, y, half, "CPU", getattr(self.info, "cpu_pct", 0.0))
        if self.info.mem:
            self._dash_row(cv, 2 + half + 2, y, half, "MEM", self.info.mem[2])
        if self.info.disk:
            self._dash_row(cv, 2, y + 2, half, "DSK", self.info.disk[2])
        if getattr(self.info, "net_rx", 0.0) > 1.0:
            nsegs = [("↓ ", C_CYAN), (fmt_speed(self.info.net_rx), C_VALUE),
                     (" ↑ ", C_FUCHSIA), (fmt_speed(self.info.net_tx), C_VALUE)]
        else:
            nsegs = [("net idle", C_SLATE)]
        put_segs(cv, 2 + half + 2, y + 2, [("NET ", C_LABEL)] + nsegs)
        y += 5
        mi = getattr(self, "music_info", None)
        if mi and mi.get("title"):
            sym = "▶" if mi.get("status") == "Playing" else "❚❚"
            put_segs(cv, 2, y, [(sym + " ♪ ", C_FUCHSIA),
                                (clip("%s — %s" % (mi.get("title", ""), mi.get("artist") or ""), W - 12), C_LABEL)])
            y += 1
        td = _jload("todo.json", [])
        pend = sum(1 for x in td if not x["d"])
        _pd = _jload("period.json", {"starts": []})
        if _pd["starts"]:
            _lp = _pd_parse(_pd["starts"][-1])
            if _lp:
                _dd = int((time.mktime(time.localtime()) -
                           time.mktime(_lp)) / 86400.0) + 1
                _avg = _pd_avg_cycle(_pd["starts"])
                _pi = _pd_phase(_dd, _avg, 5)
                _pe, _pn = PHASES[_pi][1], PHASES[_pi][0]
        la = os.getloadavg()
        segs = [("UPTIME ", C_LABEL), (self.info.f_uptime, C_VALUE), ("   ", C_DIM),
                ("LOAD ", C_LABEL), ("%.2f" % la[0], C_VALUE)]
        if pend:
            segs += [("   TODO ", C_LABEL), ("%d ☐" % pend, C_GOLD)]
        if self.info.bat:
            segs += [("   BAT ", C_LABEL), (str(self.info.bat[0]) + "%", C_VALUE)]
        _cj = _jload("care.json", {})
        _td = time.strftime("%Y-%m-%d")
        _mt = next((m2.get("v") for m2 in reversed(_cj.get("mood", []))
                    if m2.get("d") == _td), None)
        if _mt is not None and 1 <= _mt <= 6:
            segs += [("  ", C_DIM), (CARE_FACES[_mt - 1], C_VALUE)]
        _sc_days = len(set(x2.get("d") for x2 in _cj.get("sc", []) if x2.get("ids")))
        if _sc_days:
            segs += [("  🌷", C_PINK), (str(_sc_days), C_VALUE)]
        try:
            if "_pd" in dir() and _pd["starts"]:
                segs += [("   ", C_DIM), (PHASES[_pi][1], C_PINK)]
        except Exception:
            pass
        put_segs(cv, max(2, (W - disp_width("".join(x for x, _ in segs))) // 2), y, segs)
        y += 2
        momo = getattr(self, "_pet_name", "momo")
        cv.put(max(2, (W - 16) // 2), y, "=^..^=  " + momo, scale(C_PINK, 0.85))
        foot = "koi bhi key — wapas console"
        cv.put(max(2, (W - disp_width(foot)) // 2), H - 2, foot, C_SLATE)
        return cv.render()

    def _dash_row(self, cv, x, y, w, label, pct):
        _, bar_segs, _ = micro_bar(pct, max(6, w - 14))
        put_segs(cv, x, y, [(label.ljust(4), C_LABEL)] + bar_segs +
                 [(" %3.0f%%" % pct, pct_color(pct))])

    def open_chatpage(self):
        self.chat = {"msgs": [], "hist": [], "mode": "idle", "input": ""}

    def _chat_send(self, text):
        ch = self.chat
        ch["msgs"].append(("me", text))
        ch["msgs"].append(("ai", ""))
        ch["hist"].append({"role": "user", "content": text})
        ch["mode"] = "stream"
        ch["input"] = ""
        self.ai_q = queue.Queue()
        threading.Thread(target=self._ai_worker, args=(text,), daemon=True).start()

    def _ai_worker(self, prompt):
        import urllib.request
        try:
            if not self.ai_model:
                with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=6) as r:
                    j = json.loads(r.read().decode("utf-8", "replace"))
                names = [m.get("name") for m in j.get("models", []) if m.get("name")]
                if not names:
                    self.ai_q.put("✗ koi model nahi — ollama pull llama3.2")
                    self.ai_q.put(None)
                    return
                self.ai_model = names[0]
                save_profile_field("ai_model", self.ai_model)
            body = json.dumps({"model": self.ai_model,
                               "messages": self.chat["hist"][-9:],
                               "stream": True}).encode("utf-8")
            req = urllib.request.Request("http://localhost:11434/api/chat", data=body,
                                         headers={"Content-Type": "application/json"})
            acc = ""
            with urllib.request.urlopen(req, timeout=300) as r:
                for raw in r:
                    try:
                        d = json.loads(raw.decode("utf-8", "replace"))
                    except Exception:
                        continue
                    tok = (d.get("message") or {}).get("content", "")
                    if tok:
                        acc += tok
                        self.ai_q.put(tok)
                    if d.get("done"):
                        break
            self.chat["hist"].append({"role": "assistant", "content": acc})
            self.ai_q.put(None)
        except Exception as e:
            self.ai_q.put("✗ AI: %s" % str(e)[:60])
            self.ai_q.put(None)

    def _ai_pump(self):
        if self.ai_q is None or self.chat is None:
            if self.chat is None:
                self.ai_q = None
            return
        n = 0
        while n < 300:
            try:
                it = self.ai_q.get_nowait()
            except queue.Empty:
                return
            if it is None:
                self.chat["mode"] = "idle"
                self.ai_q = None
                return
            if self.chat["msgs"] and self.chat["msgs"][-1][0] == "ai":
                r_, t_ = self.chat["msgs"][-1]
                self.chat["msgs"][-1] = ("ai", t_ + it)
            n += 1

    def handle_chat_event(self, ev):
        kind, ch = ev[0], ev[1]
        if kind == "EOF":
            self.running = False
            return
        if kind in ("ESC", "CTRL_C", "CTRL_Q") or (kind == "CHAR" and ch in ("q", "Q") and self.chat["mode"] == "idle" and not self.chat["input"]):
            self.chat = None
            self.ai_q = None
            return
        if self.chat["mode"] == "stream":
            return
        if kind == "CHAR" and ch and ch not in ("\n", "\r"):
            self.chat["input"] = (self.chat["input"] + ch)[:400]
        elif kind == "BACKSPACE":
            self.chat["input"] = self.chat["input"][:-1]
        elif kind == "ENTER":
            q = self.chat["input"].strip()
            if q:
                self._chat_send(q)

    def build_chat_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        ch = self.chat
        for i in range(W):
            c = scale(grad(i / max(1, W - 1)), 0.8)
            cv.set(i, 0, "─", c)
            cv.set(i, H - 1, "─", c)
        for yy in range(1, H - 1):
            cv.set(0, yy, "│", scale(grad(yy / max(1, H - 1)), 0.8))
            cv.set(W - 1, yy, "│", scale(grad(yy / max(1, H - 1)), 0.8))
        cv.put(2, 0, "✦ CUTIE AI", C_TITLE)
        cv.put(13, 0, clip("— " + (self.ai_model or "auto") + " • offline • Q exit", W - 34), C_SLATE)
        wrapped = []
        for role, txt in ch["msgs"]:
            pre = "❯ " if role == "me" else "✦ "
            col = C_VALUE if role == "me" else C_CYAN
            for i2 in range(0, max(1, len(txt)), max(8, W - 8)):
                chunk = txt[i2:i2 + W - 8]
                if chunk or i2 == 0:
                    wrapped.append((pre if i2 == 0 else "  ", chunk, col, role))
        body = H - 5
        show = wrapped[-body:] if len(wrapped) > body else wrapped
        for r2, (pre, chunk, col, role) in enumerate(show):
            yy = 2 + r2
            cv.put(2, yy, pre, C_GOLD if role == "me" else C_FUCHSIA)
            cv.put(4, yy, chunk, col)
        if not wrapped:
            cv.put(4, 3, "✿ sawal likho — ENTER bhejo", C_DIM)
            cv.put(4, 4, "jaise: python decorator kya hai? / meri disk kyu bhar rahi", C_SLATE)
        ry2 = H - 3
        if ch["mode"] == "stream":
            sp = SPIN[int(t * 10) % len(SPIN)]
            cv.put(2, ry2, sp + " soch rahi hoon…", C_CYAN)
        else:
            cv.put(2, ry2, "✿ ", C_PINK)
            cv.put(4, ry2, clip(ch["input"] + "▌", W - 8), C_WHITE)
        return cv.render()

    def handle_fz_event(self, ev):
        kind, ch = ev[0], ev[1]
        if kind == "EOF":
            self.running = False
            return
        if kind in ("ESC", "CTRL_C"):
            self.fz = None
            return
        if kind == "CHAR" and ch and ch not in ("\n", "\r"):
            self.fz["q"] += ch
            self.fz["sel"] = 0
        elif kind == "BACKSPACE":
            self.fz["q"] = self.fz["q"][:-1]
        elif kind == "UP":
            self.fz["sel"] = max(0, self.fz["sel"] - 1)
        elif kind == "DOWN":
            self.fz["sel"] += 1
        elif kind == "ENTER":
            m = self._fz_matches()
            if m:
                pick = m[min(self.fz["sel"], len(m) - 1)][1]
                T = self.term
                T.buf = pick
                T.caret = len(pick)
            self.fz = None

    def _fz_matches(self):
        q = self.fz["q"].lower()
        items = list(reversed(self.term.history))
        if q:
            items = [h for h in items if q in h.lower()]
        return list(enumerate(items))[:40]

    def _draw_fz_overlay(self, cv, t):
        W, H = cv.w, cv.h
        h = 8
        y0 = H - 3 - h
        b = C_TERM_BORDER
        for i in range(6, W - 6):
            cv.set(i, y0, "─", b)
            cv.set(i, y0 + h, "─", b)
        for yy in range(y0 + 1, y0 + h):
            cv.set(6, yy, "│", b)
            cv.set(W - 7, yy, "│", b)
        cv.set(6, y0, "╭", b)
        cv.set(W - 7, y0, "╮", b)
        cv.set(6, y0 + h, "╰", b)
        cv.set(W - 7, y0 + h, "╯", b)
        cv.put(8, y0, "⌕ HISTORY", C_FUCHSIA)
        cv.put(20, y0, clip(self.fz["q"] + "▌", W - 30), C_GOLD)
        m = self._fz_matches()
        if not m:
            cv.put(9, y0 + 2, "(koi match nahi)", C_SLATE)
            return
        self.fz["sel"] = clamp(self.fz["sel"], 0, len(m) - 1)
        for r2 in range(h - 2):
            if r2 >= len(m):
                break
            num, ln = m[r2]
            sel = (r2 == self.fz["sel"])
            cv.put(8, y0 + 1 + r2, "▸" if sel else " ", C_GOLD if sel else C_SLATE)
            cv.put(10, y0 + 1 + r2, clip(ln, W - 22), C_WHITE if sel else C_OUT)

    # ── v26: CUTIE TYPE page ──

    def _type_build(self, mode, arg=None):
        cfg = {"name": mode}
        txt = ""
        if mode == "words":
            cfg["dur"] = clamp(int(arg), 15, 300) if (arg or "").isdigit() else 30
            txt = " ".join(random.choice(TYPE_WORDS) for _ in range(cfg["dur"] * 3))
        elif mode == "quote":
            txt = random.choice(TYPE_QUOTES)
        elif mode == "meme":
            txt = random.choice(MEMES)[0]
        elif mode == "hi":
            txt = random.choice(TYPE_HI)
        elif mode == "bn":
            txt = random.choice(TYPE_BN)
        elif mode == "code":
            txt = random.choice(TYPE_CODE)
            cfg["name"] = "code"
        elif mode == "daily":
            random.seed(time.strftime("%Y%m%d"))
            txt = random.choice(TYPE_QUOTES + tuple(m for m, _t in MEMES))
            random.seed()
            cfg["name"] = "daily " + time.strftime("%d %b")
        elif mode == "drill":
            L = (arg or "q").lower()[:1]
            pool = [w for w in TYPE_WORDS if L in w] or TYPE_WORDS
            txt = " ".join(random.choice(pool) for _ in range(40))
            cfg["name"] = "drill '" + L + "'"
        elif mode == "zen":
            txt = " ".join(random.choice(TYPE_WORDS) for _ in range(120))
        else:
            mode = "words"
            cfg["dur"] = 30
            txt = " ".join(random.choice(TYPE_WORDS) for _ in range(90))
        st = {"mode": mode, "arg": arg, "text": txt, "states": [2] * len(txt),
              "idx": 0, "t0": time.monotonic(), "errors": 0, "ok": 0,
              "combo": 0, "maxcombo": 0, "done": False, "res": None,
              "dur": cfg.get("dur"), "samples": [], "last_s": 0.0,
              "name": cfg.get("name", mode), "last_err": 0.0,
              "keyerr": {}, "pb": False, "streak": 0}
        if mode == "boss":
            st["hp"] = 100
            st["bhp"] = max(30, len(txt) // 2)
            st["bhp0"] = st["bhp"]
        if mode in ("race", "ghost"):
            if mode == "race":
                st["momo"] = 85 if (arg or "") == "pro" else 35
            else:
                gr = load_profile().get("ghost_run") or {}
                st["momo"] = float(gr.get("wpm") or 40)
            if st["momo"] < 5:
                st["momo"] = 35
        return st

    def _type_start(self, mode, arg=None):
        self.tpage = self._type_build(mode, arg)

    def _type_finish(self):
        tp = self.tpage
        el = max(0.5, time.monotonic() - tp["t0"])
        wpm = tp["ok"] / 5.0 * 60.0 / el
        acc = tp["ok"] * 100.0 / max(1, tp["ok"] + tp["errors"])
        mode = tp["mode"]
        win = True
        note = None
        if mode == "boss":
            win = tp.get("bhp", 1) <= 0
            note = "BOSS DOWN! 🐉💀" if win else "boss ne haraya… retry! 😿"
        elif mode in ("race", "ghost"):
            mi = int(tp.get("momo", 40) * 5 * el / 60.0)
            win = mi < len(tp["text"])
            who = "MOMO" if mode == "race" else "GHOST (tera purana best)"
            note = ("%s ko haraya! 🏁" % who) if win else ("%s pehle pahunch gaya 😹" % who)
        tp["done"] = True
        tp["res"] = (wpm, acc, el, win, note)
        bestk = "type_best_" + mode
        pb = wpm > float(load_profile().get(bestk) or 0)
        if pb:
            save_profile_field(bestk, round(wpm, 1))
            tp["pb"] = True
            self.confetti_until = time.monotonic() + 4.0
            cols = list(GRAD_STOPS) + [C_GOLD, C_WHITE]
            self.confetti = [{"x": random.uniform(0, self.cv.w),
                              "y": random.uniform(-24, 0),
                              "vy": random.uniform(10, 26),
                              "c": random.choice(cols),
                              "ch": random.choice("✦*·+•")} for _ in range(70)]
        if wpm >= 100:
            self.award("typer100")
        elif wpm >= 60:
            self.award("typer60")
        if mode == "boss" and win:
            self.award("boss_slain")
        if mode == "race" and win:
            self.award("momo_beaten")
        if mode == "daily":
            today = time.strftime("%Y-%m-%d")
            yst = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
            stk = int(load_profile().get("type_streak") or 0)
            last = load_profile().get("type_lastday")
            stk = (stk + 1) if last == yst else 1
            save_profile_field("type_streak", stk)
            save_profile_field("type_lastday", today)
            tp["streak"] = stk
            if stk >= 7:
                self.award("streak7")
        if mode == "ghost" and win:
            save_profile_field("ghost_run", {"wpm": round(wpm, 1),
                                             "samples": tp["samples"][-40:]})
        self.add_xp(4)
        self.cmd_tick()

    def handle_tpage_event(self, ev):
        kind, ch = ev[0], ev[1]
        tp = self.tpage
        if kind == "EOF":
            self.running = False
            return
        if kind in ("CTRL_C", "ESC", "CTRL_Q") or (kind == "CHAR" and ch in ("q", "Q")):
            self.tpage = None
            return
        if tp["done"]:
            if kind in ("CHAR", "ENTER") and (ch == " " or kind == "ENTER"):
                self._type_start(tp["mode"], tp.get("arg"))
            return
        if kind != "CHAR" or not ch or ch in ("\n", "\r"):
            return
        now = time.monotonic()
        txt = tp["text"]
        if tp["idx"] >= len(txt):
            return
        exp = txt[tp["idx"]]
        if ch == exp:
            tp["states"][tp["idx"]] = 0
            tp["idx"] += 1
            tp["ok"] += 1
            tp["combo"] += 1
            tp["maxcombo"] = max(tp["maxcombo"], tp["combo"])
            if tp["mode"] == "boss":
                tp["bhp"] -= (2 if tp["combo"] >= 10 else 1)
                if tp["bhp"] <= 0:
                    return self._type_finish()
        else:
            tp["errors"] += 1
            tp["combo"] = 0
            tp["last_err"] = now
            tp["keyerr"][exp] = tp["keyerr"].get(exp, 0) + 1
            if tp["mode"] == "boss":
                tp["hp"] -= 8
                if tp["hp"] <= 0:
                    return self._type_finish()
        if now - tp.get("last_s", 0) >= 0.5:
            tp["samples"].append((now - tp["t0"], tp["ok"]))
            tp["last_s"] = now
        if tp["mode"] == "race":
            mi = int(tp["momo"] * 5 * (now - tp["t0"]) / 60.0)
            if mi >= len(txt):
                return self._type_finish()
        if tp["idx"] >= len(txt):
            if tp["mode"] == "zen":
                more = " " + " ".join(random.choice(TYPE_WORDS) for _ in range(40))
                tp["text"] += more
                tp["states"] += [2] * len(more)
                return
            return self._type_finish()

    def build_tpage_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        tp = self.tpage
        b = C_TERM_BORDER
        cv.put(0, 0, "╭" + "─" * (W - 2) + "╮", b)
        cv.put(0, H - 1, "╰" + "─" * (W - 2) + "╯", b)
        for yy in range(1, H - 1):
            cv.put(0, yy, "│", b)
            cv.put(W - 1, yy, "│", b)
        now = time.monotonic()
        if tp["done"]:
            return self._type_end_frame(cv, W, H, t)
        if tp.get("dur") and (now - tp["t0"]) >= tp["dur"]:
            self._type_finish()
            return self._type_end_frame(cv, W, H, t)
        if tp.get("dur") and (now - tp["t0"]) >= tp["dur"]:
            self._type_finish()
            return self._type_end_frame(cv, W, H, t)
        el = now - tp["t0"]
        wpm = tp["ok"] / 5.0 * 60.0 / max(0.5, el)
        acc = tp["ok"] * 100.0 / max(1, tp["ok"] + tp["errors"])
        cv.put(2, 1, "✿ CUTIE TYPE", C_TITLE)
        cv.put(15, 1, clip("— " + tp["name"], W - 56), C_SLATE)
        if tp["mode"] == "words" and tp["dur"]:
            rem = max(0, tp["dur"] - el)
            timest = "⏱ %d:%02d" % (rem // 60, rem % 60)
        else:
            timest = "⏱ %d:%02d" % (el // 60, el % 60)
        segs = [(timest + "   ", C_VALUE), ("%.0f WPM" % wpm, C_GOLD),
                ("   ", C_DIM), ("%.0f%%" % acc, C_CYAN if acc >= 90 else C_GOLD)]
        if tp["combo"] >= 5:
            segs += [("   ✦x%d" % min(9, tp["combo"] // 5), C_FUCHSIA)]
        put_segs(cv, W - 2 - disp_width("".join(x for x, _ in segs)), 1, segs)
        gw = min(44, W - 16)
        if len(tp["samples"]) >= 2 and gw > 10:
            ss = tp["samples"][-gw:]
            bars = []
            for i in range(1, len(ss)):
                dt = ss[i][0] - ss[i - 1][0]
                dc = ss[i][1] - ss[i - 1][1]
                bars.append(dc / 5.0 * 60.0 / max(0.2, dt))
            mx = max(bars) or 1.0
            for i, v in enumerate(bars[-gw:]):
                hgt = clamp(int(v / mx * 7.999), 0, 7) + 1
                cv.set(4 + i, 3, "▁▂▃▄▅▆▇█"[hgt - 1], grad(i / max(1, len(bars) - 1)))
        tw = max(20, W - 12)
        lines = _type_wrap(tp["text"], tw)
        cur_l = 0
        for li, (ln, st_i) in enumerate(lines):
            if st_i <= tp["idx"] < st_i + len(ln):
                cur_l = li
                break
        show_n = max(3, H - 13)
        froml = max(0, min(cur_l - 1, max(0, len(lines) - show_n)))
        for r2 in range(show_n):
            li = froml + r2
            if li >= len(lines):
                break
            ln, st_i = lines[li]
            yy = 5 + r2
            x = 5
            for j, c2 in enumerate(ln):
                i = st_i + j
                if i >= len(tp["text"]):
                    break
                col = C_SLATE
                if i < tp["idx"]:
                    col = C_CYAN
                elif i == tp["idx"]:
                    col = C_RED if (now - tp["last_err"] < 0.30) else C_WHITE
                if i == tp["idx"]:
                    cv.put(x, yy, "▌", C_GOLD)
                    x += 1
                cv.put(x, yy, c2, col)
                x += char_width(c2)
                if x > W - 6:
                    break
        by = H - 6
        if tp["mode"] in ("race", "ghost"):
            prog = tp["idx"] * 100.0 / max(1, len(tp["text"]))
            momo_i = int(tp["momo"] * 5 * el / 60.0)
            mprog = min(100.0, momo_i * 100.0 / max(1, len(tp["text"])))
            bw = max(14, W - 30)
            put_segs(cv, 4, by, [("YOU ", C_LABEL)] + micro_bar(prog, bw) +
                     [(" %.0f%%" % prog, C_VALUE)])
            who = "MOMO" if tp["mode"] == "race" else "GHST"
            put_segs(cv, 4, by + 1, [(who + " ", C_LABEL)] + micro_bar(mprog, bw) +
                     [(" %.0f%%" % mprog, C_VALUE)])
        elif tp["mode"] == "boss":
            bwp = max(14, W - 34)
            put_segs(cv, 4, by, [("🐉 ", C_VALUE)] +
                     micro_bar(max(0.0, tp["bhp"] * 100.0 / max(1, tp["bhp0"])), bwp) +
                     [(" BOSS", C_RED)])
            put_segs(cv, 4, by + 1, [("❤ ", C_RED)] + micro_bar(max(0.0, tp["hp"]), bwp) +
                     [(" YOU", C_VALUE)])
        face, fcol = "=^..^=", C_PINK
        if tp["combo"] >= 10:
            face, fcol = "😻", C_GOLD
        elif now - tp["last_err"] < 0.6:
            face, fcol = "😿", C_SLATE
        cv.put(W - 12, H - 3, face, fcol)
        cv.put(2, H - 3, clip("type the text • galti = shake • ✦ combo • ESC quit",
                              W - 20), C_SLATE)
        self._draw_confetti(cv, t)
        return cv.render()

    def _type_end_frame(self, cv, W, H, t):
        tp = self.tpage
        wpm, acc, el, win, note = tp["res"]
        digits = str(min(999, int(wpm)))
        rows = self._block_text(digits, self._DIGL)
        lab = self._block_text("WPM", _GLYPHS)
        total_w = disp_width(rows[0] if rows else "") + 4 +             (disp_width(lab[0]) if lab else 0)
        x0 = max(2, (W - total_w) // 2)
        y0 = max(2, H // 2 - 8)
        for ry, line in enumerate(rows[:6]):
            for i, c2 in enumerate(line):
                if c2 != " ":
                    cv.set(x0 + i, y0 + ry, c2, grad((i + ry * 2) / 30.0))
        if lab:
            xl = x0 + disp_width(rows[0]) + 4
            for ry, line in enumerate(lab[:6]):
                for i, c2 in enumerate(line):
                    if c2 != " ":
                        cv.set(xl + i, y0 + ry, c2, scale(C_PINK, 0.9))
        sy = y0 + 7
        segs = [("%.1f WPM" % wpm, C_GOLD), ("  •  ", C_DIM),
                ("%.0f%% acc" % acc, C_CYAN), ("  •  ", C_DIM),
                ("max combo %d" % tp["maxcombo"], C_VALUE)]
        put_segs(cv, max(2, (W - disp_width("".join(x for x, _ in segs))) // 2), sy, segs)
        sy += 1
        if tp.get("pb"):
            put_segs(cv, max(2, (W - 22) // 2), sy, [("🏆 NEW PERSONAL BEST!", C_GOLD)])
            sy += 1
        if note:
            put_segs(cv, max(2, (W - disp_width(note)) // 2), sy, [(note, C_RED if win is False else C_FUCHSIA)])
            sy += 1
        if tp.get("streak"):
            put_segs(cv, max(2, (W - 24) // 2), sy, [("🔥 streak: %d din" % tp["streak"], C_GOLD)])
            sy += 1
        wk = [k for k, v in sorted(tp["keyerr"].items(), key=lambda kv: -kv[1])[:3] if v >= 2]
        if wk:
            put_segs(cv, max(2, (W - 34) // 2), sy,
                     [("kamzor keys: ", C_DIM), (", ".join(wk), C_GOLD),
                      ("  → typing drill " + wk[0], C_SLATE)])
            sy += 1
        best = float(load_profile().get("type_best_" + tp["mode"]) or wpm)
        msg = ("momo: waah!! naya record ✦" if tp.get("pb") else
               ("momo: bas thoda! record %.0f hai" % best if wpm >= best * 0.9
                else "momo: practice makes purrfect 😸"))
        put_segs(cv, max(2, (W - disp_width(msg)) // 2), sy + 1, [(msg, C_PINK)])
        foot = "SPACE dobara • Q bahar"
        cv.put(max(2, (W - disp_width(foot)) // 2), H - 2, foot, C_SLATE)
        self._draw_confetti(cv, t)
        return cv.render()


    # ── v28: BLOOM PAGE ──

    def handle_cycle_event(self, ev):
        self.handle_cycle_event_v2(ev)

    def _sanct_type_in(self, text, started):
        el = (time.monotonic() - started) * 33.0
        n = int(el)
        return text[:max(0, min(len(text), n))]

    def _sanct_day_block(self, cv, cx, cy, num, t):
        dg = self._DIGL
        txt = str(num)
        rows = ["".join(r) for r in zip(*(dg[c] for c in txt if c in dg))] or ["   "]
        w = disp_width(rows[0])
        x0 = cx - w // 2
        sh = (t * 0.35) % 1.0
        for ry, line in enumerate(rows):
            for i, ch in enumerate(line):
                if ch == " ":
                    continue
                u = ((i + ry * 2) / float(max(1, w + 8)) + sh) % 1.0
                cv.set(x0 + i, cy + ry, ch, grad(u))

    def _sanct_mood_bar(self, cv, cx, cy, phase, t):
        w = 30
        x0 = cx - w // 2
        base = [C_RED, (60, 200, 100), C_GOLD, C_VIOLET][phase]
        for i in range(w):
            u = i / float(w - 1)
            c2 = mix(base, C_PINK, 0.5 + 0.5 * math.sin(u * 6.283 + t * 1.5))
            cv.set(x0 + i, cy, "━", scale(c2, 0.75 + 0.25 * math.sin(t * 2.0 + u * 6.0)))

    def _sanct_petal_rain(self, cv, W, H, t):
        for k in range(8):
            seed = k * 97.0
            x2 = (seed * 13.7 + t * (6.0 + k * 0.7)) % (W + 8) - 4
            y2 = (seed * 29.3 + t * (2.2 + k * 0.35)) % (H + 6) - 3
            sway = math.sin(t * 1.2 + k * 1.7) * 2.5
            xx = int(x2 + sway)
            yy = int(y2)
            if 1 <= yy < H - 2 and 2 <= xx < W - 3:
                ch2 = ["·", "✿", "·", "*"][k % 4]
                cv.set(xx, yy, ch2, scale(C_PINK, 0.16 + 0.10 * math.sin(t + k)))

    def handle_cycle_event(self, ev):
        kind, ch = ev[0], ev[1]
        cp = self.cpage_bloom
        if kind == "EOF":
            self.running = False
            return
        if cp.get("sev_for"):
            if kind in ("ESC", "CTRL_C"):
                cp["sev_for"] = None
                return
            if kind == "BACKSPACE":
                cp["sev_txt"] = cp.get("sev_txt", "")[:-1]
                return
            if kind == "CHAR" and ch and ch.isdigit():
                cp["sev_txt"] = (cp.get("sev_txt", "") + ch)[:1]
                return
            if kind == "ENTER":
                v = clamp(int(cp.get("sev_txt") or 3), 1, 5)
                dt = time.strftime("%Y-%m-%d")
                d = _pd_load()
                d["symptoms"][dt] = {"s": cp["sev_for"], "v": v}
                _pd_save(d)
                cp["msg"] = "✿ " + cp["sev_for"] + " " + str(v) + "/5 — take care ♡"
                cp["msg_t"] = time.monotonic()
                cp["sev_for"] = None
                cp["tab_open_t"] = time.monotonic()
                self.add_xp(1)
                return
            return
        if kind in ("CTRL_C", "CTRL_Q"):
            self.cpage_bloom = None
            return
        if kind == "ESC":
            if cp.get("sev_for"):
                cp["sev_for"] = None
            else:
                self.cpage_bloom = None
            return
        tab = cp.get("tab", 0)
        if kind in ("LEFT",):
            cp["tab"] = (tab - 1) % 4
            cp["tab_open_t"] = time.monotonic()
            cp["cal_sel"] = None
            return
        if kind in ("RIGHT",):
            cp["tab"] = (tab + 1) % 4
            cp["tab_open_t"] = time.monotonic()
            cp["cal_sel"] = None
            return
        if kind == "CHAR" and ch:
            low = ch.lower()
            tabs = {"t": 0, "c": 1, "i": 2, "w": 3}
            if low in tabs:
                cp["tab"] = tabs[low]
                cp["tab_open_t"] = time.monotonic()
                return
            if low == "q":
                self.cpage_bloom = None
                return
            if low == "s":
                dt = time.strftime("%Y-%m-%d")
                d = _pd_load()
                if d["starts"] and d["starts"][-1] == dt:
                    cp["msg"] = "aaj ka start already logged ✓"
                else:
                    d["starts"].append(dt)
                    d["starts"] = d["starts"][-24:]
                    _pd_save(d)
                    cp["msg"] = "🌷 start logged — take care ♡"
                    cp["confetti_t"] = time.monotonic()
                cp["msg_t"] = time.monotonic()
                cp["tab_open_t"] = time.monotonic()
                return
            if low == "e":
                dt = time.strftime("%Y-%m-%d")
                d = _pd_load()
                if d["ends"] and d["ends"][-1] == dt:
                    cp["msg"] = "aaj ka end already ✓"
                else:
                    d["ends"].append(dt)
                    d["ends"] = d["ends"][-24:]
                    _pd_save(d)
                    cp["msg"] = "🌷 end logged"
                cp["msg_t"] = time.monotonic()
                return
            if cp.get("tab") == 0 and ch.isdigit() and ch != "0":
                i2 = int(ch) - 1
                if i2 < len(SYMPTOMS):
                    cp["sev_for"] = SYMPTOMS[i2]
                    cp["sev_txt"] = ""
                return
        if cp.get("tab") == 1:
            if kind in ("UP", "DOWN", "LEFT", "RIGHT") or                     (kind == "CHAR" and ch in ("h", "j", "k", "l")):
                st2 = cp.setdefault("cal_state", {"off": 0, "dx": 0, "dy": 0})
                if kind == "UP" or (kind == "CHAR" and ch == "k"):
                    st2["dy"] -= 1
                elif kind == "DOWN" or (kind == "CHAR" and ch == "j"):
                    st2["dy"] += 1
                elif kind == "LEFT" or (kind == "CHAR" and ch == "h"):
                    st2["dx"] -= 1
                else:
                    st2["dx"] += 1
                cp["cal_sel"] = True
                return
            if kind == "ENTER" or (kind == "CHAR" and ch == " "):
                cp["msg"] = "day log: S/E use karo (aaj ke liye)"
                cp["msg_t"] = time.monotonic()
                return
            if kind == "CHAR" and ch in ("n", "m"):
                cp.setdefault("cal_state", {"off": 0, "dx": 0, "dy": 0})["off"] += 1
                return
            if kind == "CHAR" and ch == "p":
                cp.setdefault("cal_state", {"off": 0, "dx": 0, "dy": 0})["off"] -= 1
                return

    def build_cycle_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        b = C_TERM_BORDER
        cv.put(0, 0, "╭" + "─" * (W - 2) + "╮", b)
        cv.put(0, H - 1, "╰" + "─" * (W - 2) + "╯", b)
        for yy in range(1, H - 1):
            cv.put(0, yy, "│", b)
            cv.put(W - 1, yy, "│", b)
        self._sanct_petal_rain(cv, W, H, t)
        cp = self.cpage_bloom
        info = _cy_phase_of(self)
        tab = cp.get("tab", 0)
        tabs = (("today", "T"), ("calendar", "C"), ("insights", "I"), ("wheel", "W"))
        segs = []
        for i2, (nm, hot) in enumerate(tabs):
            cur = (i2 == tab)
            segs.append(("▸ " if cur else "  ", C_GOLD if cur else C_SLATE))
            segs.append((nm.upper() if cur else nm, C_GOLD if cur else C_DIM))
            segs.append(("   ", C_DIM))
        put_segs(cv, max(2, (W - disp_width("".join(x for x, _ in segs))) // 2), 1, segs)
        if cp.get("msg") and (time.monotonic() - cp.get("msg_t", 0)) < 4.0:
            m2 = "✿ " + cp["msg"]
            cv.put(max(2, (W - disp_width(m2)) // 2), 2, m2, C_GOLD)
        cx = W // 2
        if tab == 0:
            opent = cp.get("tab_open_t") or 0.0
            if info:
                ph = info["phase"]
                ph_name, ph_emoji, ph_msg = PHASES[ph]
                self._sanct_day_block(cv, cx, max(4, H // 2 - 10),
                                      info["days"], t)
                self._sanct_mood_bar(cv, cx, max(4, H // 2 - 10) + 6, ph, t)
                typed = self._sanct_type_in(ph_emoji + "  " + ph_name.upper(), opent + 0.2)
                cv.put(cx - disp_width(typed) // 2, max(4, H // 2 - 10) + 8, typed,
                       C_GOLD if ph == 2 else C_PINK)
                line1, line2 = ph_msg.split("—", 1) if "—" in ph_msg else (ph_msg, "")
                q1 = self._sanct_type_in("✿ " + line1.strip(), opent + 0.7)
                cv.put(cx - disp_width(q1) // 2, max(4, H // 2 - 10) + 10, q1, C_PINK)
                if line2:
                    q2 = self._sanct_type_in("✿ " + line2.strip(), opent + 1.2)
                    cv.put(cx - disp_width(q2) // 2, max(4, H // 2 - 10) + 11, q2, C_PINK)
                st = _pd_load()
                ds2 = []
                for i2 in range(1, min(len(st["starts"]), 7)):
                    a2p = _pd_parse(st["starts"][-i2])
                    b2p = _pd_parse(st["starts"][-i2 - 1])
                    if a2p and b2p:
                        dd = (time.mktime(a2p) - time.mktime(b2p)) / 86400.0
                        if 15 < dd < 60:
                            ds2.append(int(dd))
                sc = st.get("_streak_hint") or 0
                momo_face, momo_line = MOMO_CARE[PHASES[ph][0]]
                mtxt = "momo " + momo_face + "  " + momo_line
                mt = self._sanct_type_in(mtxt, opent + 1.8)
                cv.put(cx - disp_width(mt) // 2, max(4, H // 2 - 10) + 14, mt, C_LABEL)
                sym = st["symptoms"].get(time.strftime("%Y-%m-%d"))
                sy0 = max(4, H // 2 - 10) + 16
                cv.put(cx - 10, sy0, "♡ log symptom:", C_FUCHSIA)
                for i2, sm in enumerate(SYMPTOMS):
                    col = C_VALUE if sym and sym["s"] == sm else C_SLATE
                    tail = " " + str(sym["v"]) + "/5" if sym and sym["s"] == sm else ""
                    cv.put(cx - 10 + (i2 % 3) * 11, sy0 + 1 + i2 // 3,
                           str(i2 + 1) + "." + sm + tail, col)
                if cp.get("sev_for"):
                    cv.put(cx - 10, sy0 + 3, "severity 1-5: " +
                           cp.get("sev_txt", "") + "▌", C_GOLD)
            else:
                self._sanct_day_block(cv, cx, max(4, H // 2 - 8), 0, t)
                m2 = self._sanct_type_in("🌷 apna pehla cycle log karo — S dabao", opent)
                cv.put(cx - disp_width(m2) // 2, max(4, H // 2 - 2), m2, C_PINK)
        elif tab == 1:
            st2 = cp.setdefault("cal_state", {"off": 0, "dx": 0, "dy": 0})
            base = time.localtime()
            tot = base.tm_year * 12 + base.tm_mon - 1 + st2.get("off", 0)
            yy2, mm2 = tot // 12, (tot % 12) + 1
            try:
                import calendar as _cal
                grid = _cal.monthcalendar(yy2, mm2)
                mname = _cal.month_name[mm2]
            except Exception:
                grid = []
                mname = "?"
            mt2 = "← " + mname.upper() + " " + str(yy2) + " →"
            cv.put(cx - disp_width(mt2) // 2, 4, mt2, C_TITLE)
            d = _pd_load()
            marks = {}
            period_len = 5
            if d["ends"] and d["starts"]:
                lp = _pd_parse(d["starts"][-1])
                ep = _pd_parse(d["ends"][-1])
                if lp and ep:
                    period_len = clamp(int((time.mktime(ep) -
                                            time.mktime(lp)) / 86400.0) + 1, 2, 10)
            for st3 in d["starts"]:
                lp = _pd_parse(st3)
                if not lp:
                    continue
                for k in range(period_len):
                    tt2 = time.localtime(time.mktime(lp) + k * 86400.0)
                    if tt2.tm_year == yy2 and tt2.tm_mon == mm2:
                        marks[tt2.tm_mday] = "p"
            avg = _pd_avg_cycle(d["starts"]) if d["starts"] else 28
            if d["starts"]:
                lp = _pd_parse(d["starts"][-1])
                if lp:
                    nd = time.localtime(time.mktime(lp) + avg * 86400.0)
                    if nd.tm_year == yy2 and nd.tm_mon == mm2:
                        marks.setdefault(nd.tm_mday, "pred")
            heads = "Mo  Tu  We  Th  Fr  Sa  Su"
            cv.put(cx - disp_width(heads) // 2, 6, heads, C_LABEL)
            rowy = 8
            for wk in grid:
                segs2 = []
                for di, day in enumerate(wk):
                    if day == 0:
                        segs2.append(("    ", C_OUT))
                        continue
                    cell = "%2d" % day
                    if day in marks and marks[day] == "p":
                        segs2.append((cell + "🌷", C_RED))
                    elif marks.get(day) == "pred":
                        segs2.append((cell + "· ", C_GOLD))
                    elif day == base.tm_mday and mm2 == base.tm_mon:
                        segs2.append(("[" + cell + "]", C_WHITE))
                    else:
                        segs2.append((" " + cell + " ", C_OUT))
                put_segs(cv, cx - disp_width("".join(x for x, _ in segs2)) // 2,
                         rowy, segs2)
                rowy += 1
            leg = "🌷 logged    · predicted    [ ] aaj    n/p month"
            cv.put(cx - disp_width(leg) // 2, rowy + 1, leg, C_DIM)
        elif tab == 2:
            st = _pd_load()
            cv.put(cx - 8, 4, "◆ YOUR PATTERNS", C_TITLE)
            if len(st["starts"]) >= 2:
                ds2 = []
                for i2 in range(1, min(len(st["starts"]), 7)):
                    a2p = _pd_parse(st["starts"][-i2])
                    b2p = _pd_parse(st["starts"][-i2 - 1])
                    if a2p and b2p:
                        dd = (time.mktime(a2p) - time.mktime(b2p)) / 86400.0
                        if 15 < dd < 60:
                            ds2.append(int(dd))
                if ds2:
                    avgg = sum(ds2) // len(ds2)
                    reg = "✓ regular" if max(ds2) - min(ds2) <= 3 else "⚠ varying"
                    cv.put(cx - 10, 6, "avg cycle", C_LABEL)
                    cv.put(cx + 4, 6, str(avgg) + " days", C_GOLD)
                    cv.put(cx - 10, 7, "rhythm", C_LABEL)
                    cv.put(cx + 4, 7, reg, C_CYAN if "✓" in reg else C_GOLD)
                    cv.put(cx - 10, 9, "── recent cycles ──", C_SLATE)
                    rowy = 11
                    show = list(reversed(ds2))[:6]
                    for i2, dd in enumerate(show):
                        bw2 = clamp(dd, 8, 40)
                        lbl = time.strftime("%b", time.localtime(
                            time.mktime(_pd_parse(st["starts"][-1 - (len(show) - 1 - i2)]))))
                        cv.put(cx - 10, rowy, lbl.ljust(4), C_LABEL)
                        cv.put(cx - 5, rowy, "▓" * bw2, grad(i2 / max(1, len(show) - 1)))
                        cv.put(cx - 5 + bw2 + 1, rowy, str(dd) + "d", C_VALUE)
                        rowy += 1
                    rowy += 1
                    cv.put(cx - 10, rowy, "⚠ 3 mahine irregular? doctor",
                           scale(C_GOLD, 0.9))
                    cv.put(cx - 10, rowy + 1, "🔒 data sirf tere laptop me",
                           scale(C_SLATE, 0.9))
            else:
                m2 = "kam se kam 2 cycles ke baad patterns dikhenge"
                cv.put(cx - disp_width(m2) // 2, 8, m2, C_DIM)
        else:
            if info:
                frac = clamp(info["days"] / float(max(1, info["avg"])), 0.0, 1.0)
                ang_now = frac * 6.283 - 1.5708
                cx2, cy2 = cx, H // 2
                WR = min(9, (H - 12) // 2)
                for step in range(72):
                    a2 = step / 72.0 * 6.283 - 1.5708
                    ph = _pd_phase(int(step / 72.0 * info["avg"]) + 1,
                                   info["avg"], info["plen"])
                    rc = [C_RED, (60, 200, 100), C_GOLD, C_VIOLET][ph]
                    x2 = int(cx2 + math.cos(a2) * WR * 2.0)
                    y2 = int(cy2 + math.sin(a2) * WR)
                    done = a2 <= ang_now + 0.02
                    cv.set(x2, y2, "●" if done else "○",
                           scale(rc, 1.0 if done else 0.4))
                px2 = int(cx2 + math.cos(ang_now) * WR * 2.0)
                py2 = int(cy2 + math.sin(ang_now) * WR)
                cv.set(px2, py2, "✦", C_WHITE)
                dn = str(info["days"])
                cv.put(cx2 - disp_width(dn) // 2, cy2 - 1, dn, C_GOLD)
                cv.put(cx2 - 2, cy2, "DAYS", scale(C_SLATE, 0.85))
                for step in range(0, 72, 18):
                    a2 = step / 72.0 * 6.283 - 1.5708
                    ph = _pd_phase(int(step / 72.0 * info["avg"]) + 1,
                                   info["avg"], info["plen"])
                    ex = int(cx2 + math.cos(a2) * (WR + 2) * 2.0)
                    ey = int(cy2 + math.sin(a2) * (WR + 2))
                    cv.set(ex, ey, PHASES[ph][1][0], C_PINK)
            else:
                cv.put(cx - 8, H // 2, "koi data nahi — T pe S dabao", C_DIM)
        fy = H - 3
        if info:
            face, line = MOMO_CARE[PHASES[info["phase"]][0]]
        else:
            face, line = "( ^..^ )", "momo yahan hamesha rahegi ♡"
        cv.put(3, fy, face, C_PINK)
        cv.put(11, fy, clip(line, W - 15), C_LABEL)
        hint = "← → tabs • S start • E end • 1-8 log • Q exit"
        cv.put(max(2, (W - disp_width(hint)) // 2), H - 2, hint, C_SLATE)
        return cv.render()


    # ── v31: SELF-CARE PAGE + BREATHE PAGE ──

    def handle_care_event(self, ev):
        kind, ch = ev[0], ev[1]
        cp = self.care
        if kind == "EOF":
            self.running = False
            return
        if kind in ("CTRL_C", "CTRL_Q", "ESC") or (kind == "CHAR" and ch in ("q", "Q")):
            self.care = None
            return
        if kind == "CHAR" and ch and ch.isdigit() and ch != "0":
            i2 = int(ch) - 1
            if 0 <= i2 < len(SC_TASKS):
                d2 = _care_load()
                e2 = _sc_today(d2)
                if i2 + 1 in e2["ids"]:
                    e2["ids"].remove(i2 + 1)
                else:
                    e2["ids"].append(i2 + 1)
                    self.add_xp(1)
                _care_save(d2)
                if len(e2["ids"]) == len(SC_TASKS):
                    cp["msg"] = "✿ POORA DIN COMPLETE! momo proud 😻"
                    cp["conf_t"] = time.monotonic()
                    self.confetti_until = time.monotonic() + 3.0
                    cols = list(GRAD_STOPS) + [C_GOLD, C_WHITE]
                    self.confetti = [{"x": random.uniform(0, self.cv.w),
                                      "y": random.uniform(-24, 0),
                                      "vy": random.uniform(10, 26),
                                      "c": random.choice(cols),
                                      "ch": random.choice("✦*·+•")}
                                     for _ in range(60)]
                elif len(e2["ids"]) == 1:
                    cp["msg"] = "pehla step! baaki bhi ho jayenge ♡"
                cp["msg_t"] = time.monotonic()
                stk = _sc_streak(d2)
                if stk >= 5:
                    self.award("sc_streak5")

    def build_care_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        b = C_TERM_BORDER
        cv.put(0, 0, "╭" + "─" * (W - 2) + "╮", b)
        cv.put(0, H - 1, "╰" + "─" * (W - 2) + "╯", b)
        for yy in range(1, H - 1):
            cv.put(0, yy, "│", b)
            cv.put(W - 1, yy, "│", b)
        self._sanct_petal_rain(cv, W, H, t)
        cp = self.care
        d2 = _care_load()
        cv.put(2, 1, "✿ SELF-CARE GARDEN", C_TITLE)
        stk = _sc_streak(d2)
        cv.put(W - 2 - (10 + len(str(stk))), 1,
               "🌷 streak " + str(stk), C_GOLD if stk else C_SLATE)
        y2 = 4
        x2 = max(4, W // 2 - 26)
        e2 = _sc_today(d2)
        for i2, task in enumerate(SC_TASKS):
            done = (i2 + 1) in e2["ids"]
            box = "[✓]" if done else "[ ]"
            cv.put(x2, y2 + i2 * 2, box, C_GOLD if done else C_SLATE)
            cv.put(x2 + 4, y2 + i2 * 2,
                   str(i2 + 1) + ". " + task,
                   C_VALUE if done else C_OUT)
            if done:
                cv.put(x2 + 4 + disp_width(task) + 2, y2 + i2 * 2, "✿",
                       scale(C_PINK, 0.8))
        gy2 = y2 + len(SC_TASKS) * 2 + 1
        cv.put(x2, gy2, "garden:", C_LABEL)
        cur = time.time() - 13 * 86400.0
        segs = []
        for i2 in range(14):
            dd = time.strftime("%Y-%m-%d", time.localtime(cur))
            done = any(x2b["d"] == dd and x2b.get("ids") for x2b in d2["sc"])
            segs.append(("🌷" if done else "·", C_PINK if done else C_SLATE))
            cur += 86400.0
        put_segs(cv, x2 + 8, gy2, segs)
        msg = cp.get("msg") or ""
        if msg and (time.monotonic() - cp.get("msg_t", 0)) < 5.0:
            cv.put(max(2, (W - disp_width(msg)) // 2), gy2 + 2, msg, C_GOLD)
        cv.put(3, H - 3, "( ^..^ )", C_PINK)
        cv.put(12, H - 3, "momo: ek-ek kadam bhi count hota hai ♡", C_LABEL)
        cv.put(max(2, (W - 34) // 2), H - 2,
               "1-6 toggle • Q exit • sab local 🔒", C_SLATE)
        return cv.render()

    def handle_breathe_event(self, ev):
        kind, ch = ev[0], ev[1]
        if kind == "EOF":
            self.running = False
            return
        if kind in ("CTRL_C", "CTRL_Q", "ESC") or (kind == "CHAR" and ch in ("q", "Q")):
            self.breathe = None
            return
        if self.breathe.get("done") and kind in ("ENTER", "CHAR"):
            self.breathe = None

    def build_breathe_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        b = C_TERM_BORDER
        cv.put(0, 0, "╭" + "─" * (W - 2) + "╮", b)
        cv.put(0, H - 1, "╰" + "─" * (W - 2) + "╯", b)
        for yy in range(1, H - 1):
            cv.put(0, yy, "│", b)
            cv.put(W - 1, yy, "│", b)
        bp = self.breathe
        el = t - bp["t0"]
        if not bp.get("done") and el >= 6 * 14.0:
            bp["done"] = True
            bp["done_t"] = t
            self.award("breathe1")
            self.confetti_until = t + 3.0
            cols = list(GRAD_STOPS) + [C_GOLD, C_WHITE]
            self.confetti = [{"x": random.uniform(0, W), "y": random.uniform(-24, 0),
                              "vy": random.uniform(10, 26),
                              "c": random.choice(cols),
                              "ch": random.choice("✦*·+•")} for _ in range(60)]
            self.add_xp(5)
        cx2, cy2 = W // 2, H // 2 - 1
        if not bp.get("done"):
            cyy = el % 14.0
            bn = int(el // 14.0) + 1
            if cyy < 4.0:
                f = cyy / 4.0
                lab, col = "saans ANDAR lo ♡", C_CYAN
            elif cyy < 8.0:
                f = 1.0
                lab, col = "rokoo . . .", C_VIOLET
            else:
                f = 1.0 - (cyy - 8.0) / 6.0
                lab, col = "dheere se CHHODO . . .", C_PINK
            f = f * f * (3 - 2 * f)
            R = 4 + f * (min(9, (H - 10) // 2) - 4)
            for k in range(12):
                a2 = k / 12.0 * 6.283 + t * 0.35
                x2 = int(cx2 + math.cos(a2) * R * 2.0)
                y2 = int(cy2 + math.sin(a2) * R)
                pet = "⚘" if (k + int(t * 2)) % 3 else "✿"
                cv.set(x2, y2, pet, scale(mix(C_PINK, col, f * 0.6),
                                          0.55 + 0.45 * f))
            for k in range(8):
                a2 = k / 8.0 * 6.283 - t * 0.5
                x2 = int(cx2 + math.cos(a2) * R * 1.1)
                y2 = int(cy2 + math.sin(a2) * R * 0.55)
                cv.set(x2, y2, "·", scale(C_WHITE, 0.35 + 0.4 * f))
            cv.put(cx2 - 1, cy2, "⚘", scale(C_PINK, 0.8 + 0.2 * math.sin(t * 3.0)))
            cv.put(cx2 - disp_width(lab) // 2, cy2 + R + 2, lab, col)
            prog = "●" * bn + "○" * (6 - bn)
            cv.put(cx2 - 3, cy2 + R + 4, prog, C_SLATE)
            cv.put(3, H - 3, "( -.- )", C_PINK)
            cv.put(12, H - 3, "momo bhi saans le rahi hai… hum saath hai ♡", C_LABEL)
        else:
            big = "kitni shaant 🌸"
            cv.put(cx2 - disp_width(big) // 2, cy2, big, C_GOLD)
            sub = "6 breaths complete — jab chahiye, momo yahi hai"
            cv.put(cx2 - disp_width(sub) // 2, cy2 + 2, sub, C_LABEL)
            cv.put(3, H - 3, "( ^ω^ )", C_PINK)
        cv.put(max(2, (W - 24) // 2), H - 2, "Q exit • 4-4-6 rhythm", C_SLATE)
        self._draw_confetti(cv, t)
        return cv.render()


    def handle_fancy_event(self, ev):
        kind, ch = ev[0], ev[1]
        if kind == "EOF":
            self.running = False
            return
        if kind in ("CTRL_C", "CTRL_Q", "ESC") or (kind == "CHAR" and ch in ("q", "Q")):
            self.fancy = None

    def build_fancy_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        cv.put(2, 1, "quote: type quote • fireworks: Q exit", C_SLATE)
        return cv.render()


    # ── v3.3.0: PRIDE PAGE ──

    def handle_pride_event(self, ev):
        kind, ch = ev[0], ev[1]
        cp = self.pridepage
        if kind == "EOF":
            self.running = False
            return
        if kind in ("CTRL_C", "CTRL_Q", "ESC") or (kind == "CHAR" and ch in ("q", "Q")):
            self.pridepage = None
            return
        if kind == "CHAR" and ch:
            low = ch.lower()
            d3 = _pr_load()
            td = time.strftime("%Y-%m-%d")
            if low == "h":
                d3["hrt"].append({"d": td, "k": "e"})
                d3["hrt"] = d3["hrt"][-120:]
                _pr_save(d3)
                if len(d3["hrt"]) >= 30:
                    self.award("hrt30")
                cp["msg"] = "💗 HRT logged — journey aage badhi"
                cp["msg_t"] = time.monotonic()
                self.add_xp(2)
            elif low == "a":
                cp["msg"] = random.choice(AFFIRM)
                cp["msg_t"] = time.monotonic()
                self.add_xp(1)
            elif low == "j":
                cp["msg"] = "jaldi: pride journal <baat> (panel me seedha jaldi likhna next update)"
                cp["msg_t"] = time.monotonic()
            elif low == "p":
                cp["msg"] = "pride mode: rainbow petal rain ON 🏳️‍🌈"
                cp["pride_on"] = True
                cp["msg_t"] = time.monotonic()
                self.award("pride")

    def build_pride_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        b = C_TERM_BORDER
        cv.put(0, 0, "╭" + "─" * (W - 2) + "╮", b)
        cv.put(0, H - 1, "╰" + "─" * (W - 2) + "╯", b)
        for yy in range(1, H - 1):
            cv.put(0, yy, "│", b)
            cv.put(W - 1, yy, "│", b)
        cp = self.pridepage
        pride_on = cp.get("pride_on", False)
        PCOLS = [(91, 33, 180), (224, 90, 160), (255, 255, 255), (140, 200, 255)]
        for k in range(10):
            px2 = (k * 83 + int(t * (5.0 + k * 0.5))) % (W + 8) - 4
            py2 = (k * 41 + int(t * (2.0 + k * 0.3))) % (H + 6) - 3
            xx = int(px2 + math.sin(t * 1.1 + k) * 2.0)
            yy = int(py2)
            if 1 <= yy < H - 2 and 2 <= xx < W - 3:
                col = PCOLS[k % 4] if pride_on else                     [(244, 114, 182), C_VIOLET, (140, 200, 255)][k % 3]
                cv.set(xx, yy, ["·", "✿", "✦", "*"][k % 4],
                       scale(col, 0.22 + 0.10 * math.sin(t + k)))
        title = "🏳️‍⚧️ CUTIE PRIDE 🏳️‍⚧️"
        cv.put(max(2, (W - disp_width(title)) // 2), 1, title,
               mix(C_CYAN, C_PINK, 0.5 + 0.4 * math.sin(t * 2.0)))
        d3 = _pr_load()
        nm = d3.get("name") or ""
        pr = d3.get("pronouns") or ""
        if nm:
            line2 = "✦ " + nm + ("  •  " + pr if pr else "")
            cv.put(max(2, (W - disp_width(line2)) // 2), 3, line2, C_FUCHSIA)
        else:
            line2 = "apna naam set karo — pride name <naam>"
            cv.put(max(2, (W - disp_width(line2)) // 2), 3, line2, C_DIM)
        hrt = d3["hrt"]
        cx2 = W // 2
        cv.put(cx2 - 12, 6, "◆ HRT JOURNEY", C_TITLE)
        if hrt:
            cnt = {}
            for e3 in hrt:
                cnt[e3["k"]] = cnt.get(e3["k"], 0) + 1
            ry2 = 8
            for k2, v2 in sorted(cnt.items(), key=lambda x: -x[1]):
                nm2 = HRT_KINDS.get(k2, k2)
                cv.put(cx2 - 12, ry2, nm2.ljust(13), C_LABEL)
                cv.put(cx2 + 2, ry2, "▓" * clamp(v2, 1, 20), C_PINK)
                cv.put(cx2 + 23, ry2, str(v2), C_VALUE)
                ry2 += 1
            lastd = hrt[-1]["d"]
            cv.put(cx2 - 12, ry2 + 1, "last dose: " + lastd, C_SLATE)
            cv.put(cx2 - 12, ry2 + 2, "total logs: " + str(len(hrt)), C_LABEL)
        else:
            cv.put(cx2 - 12, 8, "(abhi koi log nahi)", C_DIM)
            cv.put(cx2 - 12, 9, "pride hrt e  —  e/t/b/p/o", C_SLATE)
        mx2 = max(2, W - 34)
        cv.put(mx2, 6, "◆ AFFIRM", C_TITLE)
        af = random.choice(AFFIRM)
        cv.put(mx2, 8, "✿ " + af[:24], C_VALUE)
        cv.put(mx2, 9, "  " + af[24:48], C_VALUE)
        cv.put(mx2, 11, "◆ KEYS", C_FUCHSIA)
        cv.put(mx2, 12, "H = hrt dose log", C_LABEL)
        cv.put(mx2, 13, "A = affirmation", C_LABEL)
        cv.put(mx2, 14, "J = journal note", C_LABEL)
        cv.put(mx2, 15, "P = pride petals 🏳️‍🌈", C_LABEL)
        msg = cp.get("msg") or ""
        if msg and (time.monotonic() - cp.get("msg_t", 0)) < 6.0:
            cv.put(max(2, (W - disp_width(msg)) // 2), H - 5,
                   clip(msg, W - 6), C_GOLD)
        cv.put(3, H - 3, "( ^..^ )", C_PINK)
        cv.put(12, H - 3, "momo: tu yahan aane layak hai, isi liye banaya tha ♡", C_LABEL)
        cv.put(max(2, (W - 30) // 2), H - 2,
               "H hrt • A affirm • P pride • Q exit", C_SLATE)
        return cv.render()


    def handle_gshop_event(self, ev):
        kind, ch = ev[0], ev[1]
        # ── GLOBAL EXITS — hamesha, har state me ──
        if kind == "EOF":
            self.running = False
            return
        if kind == "CTRL_C":
            if self.term.busy:
                self.kill_capture()
            self.gshop = None
            self.gshop_out = False
            return
        if kind in ("ESC", "CTRL_Q") or (kind == "CHAR" and ch in ("q", "Q")):
            if self.term.busy:
                self.kill_capture()
            self.gshop = None
            self.gshop_out = False
            return
        gs = self.gshop
        # ── busy: spinner phase — sirf cancel allowed (upar handled) ──
        if gs.get("busy"):
            return
        # ── severity/mini states nahi hain gshop me, seedha main flow ──
        if gs.get("qinp"):
            if kind == "BACKSPACE":
                gs["q"] = gs["q"][:-1]
                return
            if kind == "CHAR" and ch and ch not in ("\n", "\r"):
                gs["q"] = (gs["q"] + ch)[:60]
                return
            if kind == "ENTER" and gs["q"].strip():
                scr = os.path.expanduser("~/momo-web.py")
                if os.path.isfile(scr):
                    gs["busy"] = True
                    self.gshop_out = True
                    gs["_capture_pending"] = True
                    gs["_json_seen"] = False
                    gs["_json_received"] = False
                    gs["_json_error"] = None
                    gs["status"] = "searching"
                    gs["done"] = False
                    gs["qinp"] = False
                    gs["results"] = []
                    self.start_capture("python3 " + shlex.quote(scr) + " " +
                                       shlex.quote(gs["q"]) + " 10")
                    self.cap_t0 = time.monotonic()
                else:
                    gs["msg"] = "✗ momo-web.py nahi mila"
                    gs["msg_t"] = time.monotonic()
            return
        tab = gs.get("tab", 0)
        if kind in ("LEFT",):
            gs["tab"] = (tab - 1) % 3
            return
        if kind in ("RIGHT",):
            gs["tab"] = (tab + 1) % 3
            return
        if kind == "CHAR" and ch:
            low = ch.lower()
            if low == "/":
                gs["qinp"] = True
                gs["q"] = ""
                return
            if tab == 0 and ch.isdigit() and ch != "0":
                i2 = int(ch) - 1
                if 0 <= i2 < len(gs.get("results", [])):
                    it = gs["results"][i2]
                    gs.setdefault("cart", []).append(it)
                    gs["msg"] = "🛒 cart: " + it["t"][:28]
                    gs["msg_t"] = time.monotonic()
                return
            if tab == 1 and ch.isdigit() and ch != "0":
                i2 = int(ch) - 1
                if 0 <= i2 < len(gs.get("cart", [])):
                    gs["cart"].pop(i2)
                return
            if tab == 2 and low == "c":
                if gs.get("cart"):
                    txt = ("A Special Gift For You ✨\n" +
                           "\n".join("- [%s%s] %s" % (r2["c"], r2["p"],
                                                      r2["t"][:50])
                                      for r2 in gs["cart"]))
                    if shutil.which("wl-copy"):
                        subprocess.run(["wl-copy"], input=txt.encode(),
                                       stdout=subprocess.DEVNULL, timeout=4)
                        gs["msg"] = "📋 cart copied!"
                    else:
                        gs["msg"] = txt[:60]
                    gs["msg_t"] = time.monotonic()
                return


    def build_gshop_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        cv.clear()
        gs = self.gshop

        # ═══ SHELL ─ single border, corner-only accents ═══
        for i in range(W):
            c = scale(grad(i / max(1, W - 1)), 0.85)
            cv.set(i, 0, "─", c)
            cv.set(i, H - 1, "─", c)
        for j in range(1, H - 1):
            c = scale(grad(j / max(1, H - 1)), 0.85)
            cv.set(0, j, "│", c)
            cv.set(W - 1, j, "│", c)
        for (x, y, ch) in ((0, 0, "╭"), (W - 1, 0, "╮"),
                           (0, H - 1, "╰"), (W - 1, H - 1, "╯")):
            cv.set(x, y, ch, scale(grad(0.5), 0.9))

        # ═══ HEADER ZONE ═══
        ttl = "⌘  G L O B A L   B A Z A A R"
        cv.put(max(2, (W - disp_width(ttl)) // 2), 1, ttl,
               mix(C_CYAN, C_FUCHSIA, 0.5 + 0.4 * math.sin(t * 1.6)))
        tabs = ("SEARCH", "CART", "EXPORT")
        segs = []
        for i2, nm in enumerate(tabs):
            cur = (i2 == gs.get("tab", 0))
            segs.append((("[" + nm + "]") if cur else (" " + nm + " "),
                         C_GOLD if cur else C_DIM))
            segs.append(("  ", C_DIM))
        put_segs(cv, max(2, (W - disp_width("".join(x for x, _ in segs))) // 2),
                 2, segs)
        if gs.get("msg") and (time.monotonic() - gs.get("msg_t", 0)) < 5:
            cv.put(2, 3, clip("✿ " + gs["msg"], W - 4), C_GOLD)

        # ═══ CONTENT ZONE (y=5 .. H-4) ═══
        top = 5
        bot = H - 4
        if gs.get("busy"):
            sp = SPIN[int(t * 10) % len(SPIN)]
            m1 = sp + " momo duniya ghoom rahi hai…"
            cv.put(max(2, (W - disp_width(m1)) // 2), (top + bot) // 2 - 1,
                   m1, C_CYAN)
            m2 = "⏳ ~5 sec • CTRL+C cancel"
            cv.put(max(2, (W - disp_width(m2)) // 2), (top + bot) // 2 + 1,
                   m2, C_SLATE)
        elif gs.get("tab") == 0:
            rows = max(1, bot - top)
            res = gs.get("results", [])
            if gs.get("qinp"):
                cv.put(4, top, "🔍 " + gs["q"] + "▌", C_WHITE)
                cv.put(4, top + 1, "ENTER = search • ESC = cancel", C_SLATE)
            elif not res:
                m1 = "🔍 /  dabao — duniya ka bazaar khulega"
                cv.put(max(2, (W - disp_width(m1)) // 2), (top + bot) // 2 - 1,
                       m1, C_DIM)
                m2 = "flags: 🇮🇳 🇺🇸 🇬🇧 🇩🇪 🇯🇵 — sab desho ke bhaav"
                cv.put(max(2, (W - disp_width(m2)) // 2), (top + bot) // 2 + 1,
                       m2, scale(C_SLATE, 0.85))
            else:
                vis = min(len(res), rows - 1)
                for i2 in range(vis):
                    it = res[i2]
                    yy = top + i2 * 3
                    if yy > bot - 3:
                        break
                    fl = FLAGS.get(it["r"], "🌎")
                    cv.put(3, yy, "%d." % (i2 + 1), C_GOLD)
                    cv.put(6, yy, fl + ((" [" + it["c"] + "]") if it["c"] else ""),
                           C_FUCHSIA)
                    cv.put(6 + 8, yy, clip(it["t"], W - 26), C_VALUE)
                    if it["p"]:
                        cv.put(W - 16, yy, clip("💰 " + it["p"], 14), C_GOLD)
                    cv.put(6, yy + 1, "🏪 " + it["h"], C_SLATE)
                    cv.put(6, yy + 2, "💬 " + it["s"][:W - 12] if it["s"] else "",
                           scale(C_SLATE, 0.8))
        elif gs.get("tab") == 1:
            cart = gs.get("cart", [])
            cv.put(3, top, "🛒 CART — %d item%s" % (len(cart),
                   "s" if len(cart) != 1 else ""), C_FUCHSIA)
            if cart:
                tot_cur = {}
                for i2, it in enumerate(cart[:max(1, bot - top - 2)]):
                    yy = top + 2 + i2 * 2
                    cv.put(4, yy, "%d. %s" % (i2 + 1, FLAGS.get(it["r"], "🌎")),
                           C_SLATE)
                    cv.put(8, yy, clip(it["t"], W - 30), C_VALUE)
                    if it["p"]:
                        cv.put(W - 16, yy, "💰 " + it["p"], C_GOLD)
                        cur2 = it["c"] or "?"
                        tot_cur[cur2] = tot_cur.get(cur2, 0) + 1
                yl = top + 2 + min(len(cart), bot - top - 2) * 2
                segs2 = [("mix: ", C_DIM)]
                for k2, v2 in tot_cur.items():
                    segs2.append((k2 + "×" + str(v2) + "  ", C_LABEL))
                put_segs(cv, 4, yl, segs2)
            else:
                cv.put(max(2, (W - 22) // 2), (top + bot) // 2,
                       "(cart khaali — SEARCH me 1-9 dabao)", C_DIM)
        else:
            cart = gs.get("cart", [])
            cv.put(3, top, "📤 EXPORT — %d items" % len(cart), C_FUCHSIA)
            if cart:
                yy = top + 2
                cv.put(4, yy, "A Special Gift For You ✨", C_GOLD)
                yy += 1
                for it in cart[:bot - top - 4]:
                    yy += 1
                    cv.put(6, yy, clip("- [%s%s] %s" %
                           (it["c"], it["p"], it["t"][:40]), W - 8), C_OUT)
                cv.put(4, bot - 1, "C = clipboard copy ✨", C_GOLD)
            else:
                cv.put(max(2, (W - 22) // 2), (top + bot) // 2,
                       "(cart khaali)", C_DIM)

        # ═══ FOOTER ZONE ═══
        cv.put(3, H - 3, "( ^ω^ )", C_PINK)
        cv.put(12, H - 3, "momo: global bazaar tere console me 🌍", C_LABEL)
        hint = "/ search  •  1-9 cart  •  ←→ tabs  •  C copy  •  Q exit"
        cv.put(max(2, (W - disp_width(hint)) // 2), H - 2, hint, C_SLATE)
        return cv.render()



    def handle_gm_event(self, ev):
        kind, ch = ev[0], ev[1]
        if kind == "EOF":
            self.running = False
            return
        if kind in ("CTRL_C", "CTRL_Q", "ESC") or (kind == "CHAR" and ch in ("q", "Q")):
            self.gmpage = None
            return
        if kind == "CHAR" and ch in ("b", "B"):
            self.gmpage = None
            tool_breathe(self, [])

    def build_gm_frame(self, t):
        cv = self.cv
        W, H = cv.w, cv.h
        b = C_TERM_BORDER
        cv.put(0, 0, "╭" + "─" * (W - 2) + "╮", b)
        cv.put(0, H - 1, "╰" + "─" * (W - 2) + "╯", b)
        for yy in range(1, H - 1):
            cv.put(0, yy, "│", b)
            cv.put(W - 1, yy, "│", b)
        for k in range(8):
            px2 = (k * 71 + int(t * 3.0)) % (W + 6) - 3
            py2 = (k * 47 + int(t * 1.3)) % (H + 4) - 2
            xx = int(px2 + math.sin(t + k) * 2)
            yy = int(py2)
            if 1 <= yy < H - 2 and 2 <= xx < W - 3:
                cv.set(xx, yy, ["·", "✿", "🌷"][k % 3], scale(C_PINK, 0.2))
        gp = self.gmpage
        hr = time.localtime().tm_hour
        if 5 <= hr < 12:
            greet, gcol, emj = "GOOD MORNING", C_GOLD, "☀"
        elif 12 <= hr < 17:
            greet, gcol, emj = "GOOD AFTERNOON", C_CYAN, "🌤"
        elif 17 <= hr < 21:
            greet, gcol, emj = "GOOD EVENING", C_FUCHSIA, "🌆"
        else:
            greet, gcol, emj = "SO JA AB", C_VIOLET, "🌙"
        nick = load_nick() or "cutie"
        cv.put(max(2, (W - len(greet) - 4) // 2), max(3, H // 2 - 7),
               emj + " " + greet, gcol)
        cv.put(max(2, (W - disp_width(nick) - 4) // 2), max(3, H // 2 - 6),
               nick + " ♡", C_FUCHSIA)
        seed = int(time.strftime("%Y%m%d"))
        line = random.Random(seed).choice(GM_LINES)
        typed = line[:max(0, int((t - gp["open_t"]) * 28))]
        if len(typed) < len(line):
            typed += "▌"
        cv.put(max(2, (W - disp_width(line)) // 2), max(3, H // 2 - 2),
               clip(typed, W - 6), C_VALUE)
        care = _jload("care.json", {})
        bits = []
        sc = [x2 for x2 in care.get("sc", []) if x2.get("ids")]
        if sc:
            bits.append("🌷 " + str(len(sc)))
        td = time.strftime("%Y-%m-%d")
        m2b = next((mm2 for mm2 in reversed(care.get("mood", []))
                    if mm2.get("d") == td), None)
        if m2b and 1 <= m2b.get("v", 3) <= 6:
            bits.append(CARE_FACES[m2b["v"] - 1])
        if bits:
            cv.put(max(2, (W - disp_width("   ".join(bits))) // 2),
                   max(3, H // 2 + 1), "   ".join(bits), C_SLATE)
        cv.put(max(2, (W - 14) // 2), max(3, H // 2 + 3), "⚘ ⚘ ⚘",
               scale(C_PINK, 0.7 + 0.3 * math.sin(t * 2.0)))
        cv.put(3, H - 3, "( ^..^ )", C_PINK)
        cv.put(12, H - 3, "momo: roz yahi milegi — bas aana ♡", C_LABEL)
        cv.put(max(2, (W - 22) // 2), H - 2, "B breathe • Q wapas", C_SLATE)
        return cv.render()



# ───────────────────────────── self check / main# ───────────────────────────── self check / main# ───────────────────────────── self check / main# ───────────────────────────── self check / main# ───────────────────────────── self check / main# ───────────────────────────── self check / main# ───────────────────────────── self check / main# ───────────────────────────── self check / main# ───────────────────────────── self check / main# ───────────────────────────── self check / main# ───────────────────────────── self check / main# ───────────────────────────── self check / main ───────────────────────────


def self_check():
    print("CUTIE OS %s — self check" % VERSION)
    checks = [
        ("os", os_pretty()), ("kernel", platform.release()),
        ("cpu", cpu_model()[:44]), ("gpu", gpu_info()[:44]),
        ("mem", str(mem_info())), ("disk", str(disk_info())),
        ("temp", str(temp_info())), ("battery", str(battery_info())),
        ("packages", pkg_count()), ("shell", str(shell_info())),
        ("audio", audio_info()), ("tty", sys.stdin.isatty()),
    ]
    for k, v in checks:
        print("  %-10s %s" % (k, v))
    cv = Canvas(80, 24)
    paint_logo(cv, 2, 2, 1.0)
    r = cv.render()
    print("  canvas     %d bytes rendered — %s" % (len(r), "ok" if r else "FAIL"))
    for h in (20, 24, 30, 40, 60):
        L = Layout(120, h)
        print("  layout %2d  too_small=%s anim=%d out=%d" % (h, L.too_small, L.anim_rows, L.out_rows))
    for b in (b"\x1b[A", b"\x1b[5~", b"a", b"\x03", b"\x7f"):
        print("  key %-8r → %s" % (b, KeyReader.parse_bytes(b)[0]))
    print("  tools      %d registered" % len(TOOLS))
    print("  macros     %d loaded" % len(load_macros()))
    print("  ✓ check complete")
    return 0


def main():
    argv = sys.argv[1:]
    if "--help" in argv or "-h" in argv:
        print(USAGE)
        return 0
    if "--version" in argv:
        print("CUTIE OS %s — %s" % (VERSION, EDITION))
        return 0
    if "--check" in argv:
        return self_check()
    if sys.platform in ("win32", "cygwin") and not HAS_TERMIOS:
        if not sys.stdin.isatty():
            print("CUTIE OS needs a real terminal. On Windows, please use Windows Terminal, PowerShell, or WSL2.", file=sys.stderr)
            return 1
    if not sys.stdin.isatty():
        print("cutie os needs a real terminal (tty).", file=sys.stderr)
        return 1
    no_intro = "--no-intro" in argv or os.environ.get("CUTIE_NO_INTRO") == "1"
    intro_arg = None
    if "--intro" in argv:
        i = argv.index("--intro")
        if i + 1 < len(argv):
            intro_arg = argv[i + 1].lower()
    app = App(no_intro=no_intro, intro_arg=intro_arg)
    return app.run()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)
