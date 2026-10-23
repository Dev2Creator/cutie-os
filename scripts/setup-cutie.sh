#!/usr/bin/env bash
# CUTIE OS — PyPI package setup (Anika)
set -e

echo "── 1/5 files banaye ja rahe hain ──"
if [ ! -f "$HOME/cutie-os.py" ]; then
  echo "✗ ~/cutie-os.py nahi mila! pehle script wapas laao"
  exit 1
fi

rm -rf "$HOME/cutie-os-pkg"
mkdir -p "$HOME/cutie-os-pkg/cutie_os"
cp "$HOME/cutie-os.py" "$HOME/cutie-os-pkg/cutie_os/__init__.py"
cd "$HOME/cutie-os-pkg"

cat > pyproject.toml <<'TOML'
[build-system]
requires = ["setuptools>=64"]
build-backend = "setuptools.build_meta"

[project]
name = "cutie-os"
version = "13.0.0"
description = "CUTIE OS - cinematic fastfetch-style console by Anika - 50+ real tools, snake game, sudo-in-PTY, 6 themes, 5 languages"
readme = "README.md"
requires-python = ">=3.8"
license = { text = "MIT" }
authors = [{ name = "Anika" }]
keywords = ["terminal", "tui", "fastfetch", "neofetch", "hyprland", "arch", "linux", "dashboard"]
classifiers = [
  "Environment :: Console",
  "Operating System :: POSIX :: Linux",
  "Programming Language :: Python :: 3",
  "Topic :: System :: Monitoring",
  "Topic :: Terminals",
]

[project.urls]
Homepage = "https://github.com/Dev2Creator/cutie-os"

[project.scripts]
cutie = "cutie_os.cli:main"

[tool.setuptools]
packages = ["cutie_os"]
TOML

cat > cutie_os/cli.py <<'PY'
import sys


def main():
    try:
        from cutie_os import main as _main
        sys.exit(_main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)


if __name__ == "__main__":
    main()
PY

cat > README.md <<'MD'
# CUTIE OS — cinematic terminal console

by **Anika** ([Dev2Creator](https://github.com/Dev2Creator))

Fastfetch-style animated console for Arch / Hyprland / kitty with **50+ real tools**.

    pipx install cutie-os
    cutie

- Animated intros (10 native + 20 TTE effects)
- 50+ real tools: sysinfo, net, pkg big, weather, speed, hypr, temp...
- sudo password prompt WORKS (real PTY)
- Ghost autocomplete, Snake game, 6 themes, 5 languages

> Linux only. Best on Arch + kitty + Hyprland.
MD

cat > LICENSE <<'LIC'
MIT License

Copyright (c) 2025 Anika (Dev2Creator)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
LIC

echo "── 2/5 venv ──"
cd "$HOME/cutie-os-pkg"
python -m venv .venv
source .venv/bin/activate

echo "── 3/5 build + twine install (thoda time lagega) ──"
pip install -q --upgrade pip build twine

echo "── 4/5 package build ──"
python -m build

echo "── 5/5 smoke test ──"
pip install -q dist/cutie_os-13.0.0-py3-none-any.whl --force-reinstall
cutie --check

echo ""
echo "★✦★ SAB TAIYAAR ANIKA! ★✦★"
echo "ab upload ke liye ye chalao:"
echo "  python -m twine upload dist/*"
