#!/usr/bin/env python3
import os
import sys
import time
import random
import shutil
import subprocess
import signal
import select
import termios
import tty
import re

ESC = "\033["
RESET = ESC + "0m"
BOLD = ESC + "1m"
DIM = ESC + "2m"
HIDE = ESC + "?25l"
SHOW = ESC + "?25h"
ALT = ESC + "?1049h"
MAIN = ESC + "?1049l"

# ---------- PALETTE ----------
def rgb(r, g, b, text, bold=False):
    return f"{ESC}{'1;' if bold else ''}38;2;{r};{g};{b}m{text}{RESET}"

PINK   = lambda s: rgb(255, 105, 190, s, True)
ROSE   = lambda s: rgb(255, 125, 155, s, True)
PURPLE = lambda s: rgb(185, 125, 255, s, True)
CYAN   = lambda s: rgb(90, 225, 255, s, True)
MINT   = lambda s: rgb(100, 255, 190, s, True)
GREEN  = lambda s: rgb(80, 255, 135, s, True)
YELLOW = lambda s: rgb(255, 220, 110, s, True)
WHITE  = lambda s: rgb(245, 245, 255, s, True)
GRAY   = lambda s: rgb(105, 112, 130, s)
DARK   = lambda s: rgb(45, 49, 61, s)

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

def vislen(s):
    return len(ANSI_RE.sub("", s))

def put(row, col, text=""):
    return f"{ESC}{row};{col}H{text}"

def run(cmd, fallback=""):
    try:
        return subprocess.check_output(
            cmd, shell=True, text=True, stderr=subprocess.DEVNULL,
            timeout=2.0
        ).strip() or fallback
    except Exception:
        return fallback

def meminfo():
    raw = run(
        "free -m | awk '/Mem:/ {printf \"%d %d %d\",$2,$3,($3/$2)*100}'",
        "15657 4200 27"
    )
    try:
        total, used, pct = map(int, raw.split())
        return total, used, pct
    except Exception:
        return 15657, 4200, 27

def diskinfo():
    raw = run("df -h / | awk 'NR==2 {print $3,$2,$5}'", "42G 48G 88%")
    parts = raw.split()
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    return "—", "—", "—"

def cpu_temp():
    for pattern in (
        "/sys/class/thermal/thermal_zone*/temp",
        "/sys/class/hwmon/hwmon*/temp*_input",
    ):
        for path in sorted(__import__('glob').glob(pattern)):
            try:
                with open(path) as fh:
                    v = int(fh.read().strip())
                if v > 1000:
                    return f"{v/1000:.0f}°C"
            except Exception:
                pass
    return "—"

def battery():
    cap = run("cat /sys/class/power_supply/BAT0/capacity 2>/dev/null", "")
    status = run("cat /sys/class/power_supply/BAT0/status 2>/dev/null", "")
    if cap:
        return f"{cap}% {status}"
    return "AC / N/A"

def clean_value(value, width):
    text = str(value).replace("\n", " ").strip()
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[:width-1] + "…"

# ---------- DETAILED KITTY ART ----------

def cat_art(blink=False, tail=0, step=0):
    bs = chr(92)
    eyes = "-   -" if blink else "◕   ◕"
    mouth = "ᴗ" if step % 3 == 0 else "ω"
    tails = [f"{bs}~~~~", f"{bs}~~~", "~~~~/", f"~~/{bs}"]
    return [
        f"          /{bs}_____{bs}/",
        f"         /  {eyes}  {bs}",
        f"        (     {mouth}     )",
        f"        /|   .---.   |{bs}",
        f"       / |  /  ♡  {bs}  | {bs}",
        f"      /__|_/{'_'*5}{bs}_|__{bs}" + tails[tail % len(tails)],
        f"     /    {bs}__   __/    {bs}",
        f"    /___/|   {bs}_/   |{bs}___{bs}",
        f"       /_|  /   {bs}  |_{bs}",
        f"      (_/_/     {bs}__{bs}__)",
        f"        /_/       {bs}_{bs}",
    ]

HEARTS = ["♡", "♥", "✦", "✧", "❀", "·", "⋆", "✿"]

# ---------- REAL COMMAND INPUT ----------
input_buffer = ""
command_output = []
old_term = None


def terminal_cleanup():
    global old_term
    try:
        if old_term is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_term)
            old_term = None
    except Exception:
        pass
    sys.stdout.write(RESET + SHOW + MAIN + ESC + "2J" + ESC + "H")
    sys.stdout.flush()


def stop(*_):
    terminal_cleanup()
    raise SystemExit

signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)

try:
    old_term = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
except Exception:
    old_term = None

# ---------- STATIC INFO ----------
kernel = run("uname -r", "7.2.4-arch1-2")
packages = run("pacman -Q 2>/dev/null | wc -l", "1139")
cpu = clean_value(run(
    "lscpu 2>/dev/null | sed -n 's/^Model name:[[:space:]]*//p' | head -1",
    "13th Gen Intel(R) Core(TM) i5-13420H"
), 31)
gpu = clean_value(run(
    "lspci 2>/dev/null | grep -Ei 'NVIDIA.*(VGA|3D)|NVIDIA' | sed 's/.*: //' | head -1",
    "NVIDIA GeForce RTX 3050 Laptop GPU"
), 31)
hypr = run(
    "hyprctl version 2>/dev/null | awk '/Hyprland version/{print $3; exit}'",
    "0.56.2"
)
shell = os.environ.get("SHELL", "/bin/zsh").rsplit("/", 1)[-1]
hostname = os.uname().nodename

sys.stdout.write(ALT + ESC + "2J" + HIDE)
sys.stdout.flush()

frame = 0
boot = time.monotonic()

while True:
    W, H = shutil.get_terminal_size((118, 44))

    if W < 100 or H < 38:
        sys.stdout.write(ESC + "2J" + ESC + "H")
        sys.stdout.write(put(2, 2, PINK("CUTIE OS needs a terminal at least 100x38.")))
        sys.stdout.write(put(4, 2, CYAN(f"Current size: {W}x{H}  •  please enlarge the kitty window.")))
        sys.stdout.write(put(6, 2, GRAY("Ctrl+C to exit.")))
        sys.stdout.flush()
        time.sleep(0.2)
        continue

    total, used, pct = meminfo()
    disk_used, disk_total, disk_pct = diskinfo()
    temp = cpu_temp()
    bat = battery()
    uptime = int(time.monotonic() - boot)
    hh, rem = divmod(uptime, 3600)
    mm, ss = divmod(rem, 60)

    # ---------- CUTE ANIMATION STATE ----------
    anim = frame // 3
    bob = [0, 0, 1, 1, 0, -1][(frame // 3) % 6]
    cat_y = 21 + bob
    scene_left = max(5, (W - 80) // 2)
    scene_width = min(80, W - 10)
    walk_span = max(12, scene_width - 26)
    cycle = anim % (walk_span * 2)
    cat_x = scene_left + 7 + (cycle if cycle <= walk_span else walk_span * 2 - cycle)

    particles = []
    for i in range(15):
        px = scene_left + 4 + ((i * 11 + anim * (1 + i % 3)) % max(10, scene_width - 8))
        py = 22 + ((i * 3 + anim // 2) % 8)
        sym = HEARTS[(i + frame // 10) % len(HEARTS)]
        particles.append((px, py, sym))

    pulse = ["✦", "✧", "★", "✧"][frame // 5 % 4]
    dots = "." * (1 + (frame // 8) % 3)
    blink = frame % 44 in (0, 1, 2)
    tail = (frame // 6) % 4
    step = (frame // 9) % 3

    # ---------- CLEAR ----------
    sys.stdout.write(ESC + "H" + ESC + "2J")

    # ---------- FRAME ----------
    sys.stdout.write(put(1, 1, PURPLE("╭" + "─"*(W-2) + "╮")))
    sys.stdout.write(put(H, 1, PURPLE("╰" + "─"*(W-2) + "╯")))

    sys.stdout.write(put(2, 4, GRAY("CUTIE OS  •  PERSONAL CONSOLE")))
    sys.stdout.write(put(2, max(4, W-30), MINT("● ALL SYSTEMS PURRING")))

    # ---------- TITLE ----------
    title = "C U T I E   O S"
    tx = max(2, (W - len(title)) // 2)
    sys.stdout.write(put(4, tx, PINK(title)))
    subtitle = "— DAMDAAR EDITION v10 • cute mode —"
    sx = max(2, (W - len(subtitle)) // 2)
    sys.stdout.write(put(6, sx, CYAN(subtitle)))

    # ---------- SPECS ----------
    top = 9
    panel_gap = 4
    panel_w = max(38, min(49, (W - 13) // 2))
    left_x = 4
    right_x = left_x + panel_w + panel_gap + 1
    right_w = W - right_x - 4

    if right_w < 38:
        right_w = 38

    # left panel
    sys.stdout.write(put(top, left_x, PURPLE("╭" + "─"*panel_w + "╮")))
    for r in range(top+1, top+8):
        sys.stdout.write(put(r, left_x, PURPLE("│")))
        sys.stdout.write(put(r, left_x + panel_w + 1, PURPLE("│")))
    sys.stdout.write(put(top+8, left_x, PURPLE("╰" + "─"*panel_w + "╯")))

    left_specs = [
        ("OS", "Arch Linux x86_64"),
        ("KERNEL", kernel),
        ("UPTIME", f"{hh:02d}:{mm:02d}:{ss:02d}"),
        ("PACKAGES", f"{packages} installed"),
        ("CPU", cpu),
        ("GPU", gpu),
        ("SHELL", shell),
    ]
    for i, (label, value) in enumerate(left_specs, top+1):
        v = clean_value(value, panel_w - 16)
        sys.stdout.write(put(i, left_x+2, YELLOW(f"{label:<9}") + PURPLE("»") + " " + WHITE(v)))

    # right panel
    sys.stdout.write(put(top, right_x, PURPLE("╭" + "─"*right_w + "╮")))
    for r in range(top+1, top+8):
        sys.stdout.write(put(r, right_x, PURPLE("│")))
        sys.stdout.write(put(r, right_x + right_w + 1, PURPLE("│")))
    sys.stdout.write(put(top+8, right_x, PURPLE("╰" + "─"*right_w + "╯")))

    right_specs = [
        ("MEMORY", f"{used/1024:.1f}Gi / {total/1024:.1f}Gi  {pct}%", GREEN),
        ("DISK", f"{disk_used} / {disk_total}  {disk_pct}", WHITE),
        ("HYPRLAND", hypr, PINK),
        ("WAYLAND", "active", CYAN),
        ("TEMP", temp, ROSE),
        ("BATTERY", bat, YELLOW),
        ("DISPLAY", "kitty + Hyprland", PURPLE),
    ]
    for i, (label, value, color_fn) in enumerate(right_specs, top+1):
        v = clean_value(value, right_w - 16)
        sys.stdout.write(put(i, right_x+2, CYAN(f"{label:<9}") + PURPLE("»") + " " + color_fn(v)))

    # RAM meter inside lower border gap
    meter_w = min(22, max(12, right_w - 22))
    filled = round(meter_w * pct / 100)
    meter = GREEN("█"*filled) + DARK("░"*(meter_w-filled))
    sys.stdout.write(put(top+10, right_x+2, CYAN("RAM ") + "[" + meter + "]" + WHITE(f" {pct}%")))

    # ---------- DETAILED CUTE ANIMATION STAGE ----------
    stage_y = 19
    stage_x = scene_left
    stage_h = 12

    sys.stdout.write(put(stage_y-1, stage_x, PURPLE("╭" + "─"*scene_width + "╮")))
    sys.stdout.write(put(stage_y+stage_h, stage_x, PURPLE("╰" + "─"*scene_width + "╯")))

    stage_title = "✦  KITTY CORE  •  LOVE MODE  ✦"
    stx = stage_x + max(2, (scene_width-len(stage_title))//2)
    sys.stdout.write(put(stage_y, stx, PINK(stage_title)))
    sys.stdout.write(put(stage_y+1, stage_x+4, GRAY("fluffy fur • soft paws • tiny bell • maximum cuteness")))

    # floating hearts, flowers and stars
    for px, py, sym in particles:
        if stage_x+2 <= px <= stage_x+scene_width-2 and stage_y+2 <= py <= stage_y+stage_h-2:
            color = PINK if sym in ("♡","♥","❀","✿") else YELLOW if sym in ("★","✦") else PURPLE
            sys.stdout.write(put(py, px, color(sym)))

    # detailed 10-line kitty: blink, bounce, tail sway and walking cycle
    art = cat_art(blink=blink, tail=tail, step=step)[:10]
    max_cat_width = max(map(len, art))
    cx = max(stage_x+3, min(cat_x, stage_x+scene_width-max_cat_width-2))

    for j, line in enumerate(art):
        if j <= 2:
            colour = ROSE
        elif j in (3,4,5):
            colour = PINK
        elif j in (6,7,8):
            colour = WHITE
        else:
            colour = PURPLE
        sys.stdout.write(put(cat_y+j, cx, colour(line)))

    # shimmer on collar / bell
    sys.stdout.write(put(cat_y+4, cx+11, YELLOW("♡" if (frame//5)%2 else "✦")))

    # moving paw trail
    paw_y = min(stage_y+stage_h-2, cat_y+9)
    paw_sets = ["·   ·   ❀", " ·   ✦   ·", "·   ♡   ·", " ✧   ·   ✧"]
    sys.stdout.write(put(paw_y, max(stage_x+4, cx-5), GRAY(paw_sets[step % len(paw_sets)])))

    status = [
        "making tiny system noises",
        "checking your CPU beans",
        "hugging the GPU",
        "warming up the kitty core",
        "guarding your terminal",
        "being suspiciously adorable",
        "deploying emergency cuddles",
        "purring at 100% utilization",
    ][(frame//16)%8]
    sys.stdout.write(put(stage_y+stage_h-1, stage_x+4, CYAN("♡ ") + WHITE(status + dots)))

    # animated energy strip below the kitty, safely above LIVE TERMINAL
    load_y = stage_y + stage_h + 1
    load_x = max(4, (W-72)//2)
    loader_pos = (frame//3) % 9
    loader = "♡" + "·"*loader_pos + pulse + "·"*(8-loader_pos) + "♡"
    sys.stdout.write(put(load_y, load_x, PINK(loader)))
    sys.stdout.write(put(load_y, load_x+20, YELLOW("CUTIE ENERGY")))
    sys.stdout.write(put(load_y, load_x+36, MINT("∞ 100% happy  ♡")))

    # ---------- LIVE TERMINAL ----------
    input_row = H - 6
    log_top = max(stage_y + stage_h + 3, input_row - 5)
    log_width = min(78, W - 8)

    sys.stdout.write(put(log_top, 4, PURPLE("╭─ LIVE TERMINAL " + "─"*max(0, log_width-19) + "╮")))
    for i in range(1, 4):
        text = command_output[-i] if i <= len(command_output) else ""
        text = clean_value(text, log_width - 6)
        sys.stdout.write(put(log_top+i, 4, PURPLE("│")))
        sys.stdout.write(put(log_top+i, 6, WHITE(text)))
        sys.stdout.write(put(log_top+i, log_width+4, PURPLE("│")))
    sys.stdout.write(put(log_top+4, 4, PURPLE("╰" + "─"*log_width + "╯")))

    # ---------- COMMAND INPUT ----------
    prompt = f"cutie@{hostname[:14]}:{os.path.basename(os.getcwd())} $ "
    cursor = PINK("█" if (frame//4)%2 else "▌")
    sys.stdout.write(put(input_row, 4, CYAN(prompt) + WHITE(input_buffer) + cursor))

    sys.stdout.write(
        put(
            H-2, 4,
            PURPLE("◈") + " " + MINT("READY") +
            "   " + GRAY("ENTER run command  •  BACKSPACE edit  •  Ctrl+C exit")
        )
    )

    sys.stdout.flush()

    # ---------- INPUT ----------
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if ready:
        ch = sys.stdin.read(1)
        if ch in ("\r", "\n"):
            command = input_buffer.strip()
            if command:
                if command in ("exit", "quit"):
                    stop()
                elif command in ("clear", "cls"):
                    command_output.clear()
                else:
                    output = run(command, "")
                    command_output.append("$ " + command)
                    if output:
                        lines = output.splitlines()
                        command_output.extend(lines[-2:])
                    else:
                        command_output.append("[done]")
                    command_output = command_output[-3:]
                input_buffer = ""
        elif ch in ("\x7f", "\b"):
            input_buffer = input_buffer[:-1]
        elif ch == "\t":
            input_buffer += "    "
        elif ord(ch) >= 32:
            if len(input_buffer) < min(120, W-25):
                input_buffer += ch

    frame += 1
    time.sleep(1/24)
