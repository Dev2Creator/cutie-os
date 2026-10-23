#!/usr/bin/env bash
# 🌸 CUTIE OS — Universal Unix One-Line Installer (Linux & macOS) 🌸
set -e

echo ""
echo "  🌸 CUTIE OS — Installing the coziest terminal home... ✨"
echo ""

# Check Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "  ✗ Python 3 not found! Please install python 3.8+ first."
    exit 1
fi

INSTALL_DIR="${HOME}/.local/share/cutie-os"
BIN_DIR="${HOME}/.local/bin"

mkdir -p "${INSTALL_DIR}"
mkdir -p "${BIN_DIR}"

echo "  ✦ Downloading CUTIE OS..."
curl -fsSL https://raw.githubusercontent.com/Dev2Creator/cutie-os/main/cutie-os.py -o "${INSTALL_DIR}/cutie-os.py"
chmod +x "${INSTALL_DIR}/cutie-os.py"

# Create launcher
cat << 'EOF' > "${BIN_DIR}/cutie"
#!/usr/bin/env bash
exec python3 "${HOME}/.local/share/cutie-os/cutie-os.py" "$@"
EOF
chmod +x "${BIN_DIR}/cutie"

echo "  ✓ Installed launcher to ${BIN_DIR}/cutie"

# Ensure ~/.local/bin is in PATH
if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
    echo "  ✦ Note: Add ~/.local/bin to your PATH in ~/.bashrc or ~/.zshrc:"
    echo "      export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo "  ★ ✦ ★ CUTIE OS IS READY! ★ ✦ ★"
echo "  Type 'cutie' in your terminal to start! (˶ᵔ ᵕ ᵔ˶) ♡"
echo ""
