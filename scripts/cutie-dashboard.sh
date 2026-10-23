#!/usr/bin/env bash

set +m
trap 'printf "\033[0m\033[?25h\033[2J\033[H"; exit' INT TERM EXIT

ESC=$'\033'
W=$(tput cols)
H=$(tput lines)

# Neon palette
RED="${ESC}[38;5;203m"
PINK="${ESC}[38;5;205m"
PURPLE="${ESC}[38;5;141m"
CYAN="${ESC}[38;5;159m"
BLUE="${ESC}[38;5;111m"
YELLOW="${ESC}[38;5;220m"
GREEN="${ESC}[38;5;118m"
WHITE="${ESC}[38;5;255m"
DIM="${ESC}[38;5;239m"
RESET="${ESC}[0m"

printf "\033[2J\033[H\033[?25l"

bar() {
    local n=$1 max=$2
    local out=""
    for ((i=0;i<max;i++)); do
        if (( i < n )); then out+="█"; else out+="░"; fi
    done
    printf '%s' "$out"
}

center() {
    local s="$1"
    local len=${#s}
    local pad=$(( (W-len)/2 ))
    ((pad<0)) && pad=0
    printf "%*s%s" "$pad" "" "$s"
}

while true; do
    W=$(tput cols)
    H=$(tput lines)

    # terminal-safe animation frame
    FRAME=$(( $(date +%s%N 2>/dev/null | cut -c1-13) / 90 % 10 ))

    # Real memory
    read -r MEM_TOTAL MEM_USED MEM_PCT < <(
        free -g | awk '/Mem:/ {printf "%d %d %d", $2, $3, ($3/$2)*100}'
    )
    [[ -z "$MEM_TOTAL" ]] && MEM_TOTAL=15
    [[ -z "$MEM_USED" ]] && MEM_USED=4
    [[ -z "$MEM_PCT" ]] && MEM_PCT=27

    # Moving neon scanline
    SCAN=$((FRAME % 70))

    printf "\033[H"

    # top frame
    printf "${PURPLE}╔══════════════════════════════════════════════════════════════════════════════════════════════╗${RESET}\n"
    printf "${DIM}║${RESET}"
    printf "${BLUE}%*s${RESET}" "$SCAN" ""
    printf "${RED}╱╲${RESET}"
    printf "${PINK}                           CUTIE OS // DAMDAAR EDITION v10                           ${RESET}"
    printf "${PURPLE}║${RESET}\n"

    # HUGE title
    printf "\n"
    center "${RED}╔═╗ ╦ ╔╦╗ ╦ ╔═╗   ╔═╗ ╔═╗${RESET}"
    printf "\n"
    center "${PINK}║  ║ ║ ║  ╠═╣ ║     ║ ║ ║${RESET}"
    printf "\n"
    center "${PURPLE}╚═╝ ╩ ╩  ╩ ╩     ╚═╝ ╚═╝${RESET}"
    printf "\n"
    center "${CYAN}━━━ CUTIE OS // ARCH LINUX // HYPRLAND ━━━${RESET}"
    printf "\n\n"

    # HUD panel
    printf "${PURPLE}╭────────────────────────────────────────────────────────────────────────────────────────────╮${RESET}\n"
    printf "${PURPLE}│${RESET} ${YELLOW}▲ OS${RESET}        ${BLUE}»${RESET} ${WHITE}Arch Linux x86_64${RESET}\n"
    printf "${PURPLE}│${RESET} ${YELLOW}▣ Kernel${RESET}    ${BLUE}»${RESET} ${WHITE}$(uname -r)${RESET}\n"
    printf "${PURPLE}│${RESET} ${YELLOW}◉ Uptime${RESET}    ${BLUE}»${RESET} ${WHITE}$(uptime -p | sed 's/up //')${RESET}\n"
    printf "${PURPLE}│${RESET} ${YELLOW}◈ Packages${RESET}  ${BLUE}»${RESET} ${WHITE}$(pacman -Q 2>/dev/null | wc -l) packages${RESET} ${PINK}|${RESET} ${CYAN}Hyprland $(hyprctl version 2>/dev/null | head -1 | awk '{print $2}' || echo '0.56.2')${RESET}\n"
    printf "${PURPLE}│${RESET} ${YELLOW}⚙ CPU${RESET}       ${BLUE}»${RESET} ${WHITE}13th Gen Intel(R) Core(TM) i5-13420H${RESET}\n"
    printf "${PURPLE}│${RESET} ${YELLOW}◉ GPU${RESET}       ${BLUE}»${RESET} ${WHITE}NVIDIA RTX 3050 Laptop GPU${RESET}\n"
    printf "${PURPLE}│${RESET} ${YELLOW}▰ Memory${RESET}    ${BLUE}»${RESET} ${WHITE}${MEM_USED}Gi / ${MEM_TOTAL}Gi${RESET}  ${GREEN}[${bar "$MEM_PCT" 20}]${RESET} ${WHITE}${MEM_PCT}%${RESET}\n"
    printf "${PURPLE}╰────────────────────────────────────────────────────────────────────────────────────────────╯${RESET}\n"

    # animated spectrum
    printf "\n"
    printf "                         "
    for ((i=0;i<35;i++)); do
        h=$(( (i*FRAME + i*i*3) % 8 + 1 ))
        printf "${PINK}"
        printf "%${h}s" "" | tr ' ' '▮'
        printf "${RESET}"
    done
    printf "\n\n"

    # Power animation
    POWER=$(( (FRAME*7) % 101 ))
    BLOCKS=$(( POWER / 5 ))

    printf "   ${RED}▰▰▰▰▰▰▰▰${RESET} "
    printf "${YELLOW}%3d%% POWER${RESET}   " "$POWER"

    case $((FRAME % 4)) in
        0) printf "${RED}» CUTIE OVERDRIVE »${RESET} ${PINK}UNSTOPPABLE${RESET}" ;;
        1) printf "${PINK}» CUTIE OVERDRIVE »${RESET} ${PURPLE}UNSTOPPABLE${RESET}" ;;
        2) printf "${PURPLE}» CUTIE OVERDRIVE »${RESET} ${CYAN}UNSTOPPABLE${RESET}" ;;
        3) printf "${CYAN}» CUTIE OVERDRIVE »${RESET} ${RED}UNSTOPPABLE${RESET}" ;;
    esac
    printf "\n\n"

    # Fake command prompt animation
    printf "${DIM}(base)${RESET} ${GREEN}➜${RESET} ${WHITE}~${RESET} "

    dots=$((FRAME % 4))
    printf "${CYAN}[CUTIE]${RESET} "
    for ((i=0;i<dots;i++)); do printf "█"; done
    printf "\n\n"

    printf "${DIM}        ◈ SYSTEM ONLINE   ◈ NEON CORE STABLE   ◈ HYPRLAND ACTIVE   ◈ RTX LINK OK${RESET}\n"
    printf "${PURPLE}╚══════════════════════════════════════════════════════════════════════════════════════════════╝${RESET}\n"

    sleep 0.09
done
