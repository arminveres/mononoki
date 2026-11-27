#!/usr/bin/env bash
# Build export/ from src/. Run inside `nix-shell` (see shell.nix).
# Usage: ./build.sh [--nerd]   (--nerd also writes "mononoki Nerd Font Mono" to export/nerd/)
set -euo pipefail
cd "$(dirname "$0")"

fontforge -quiet -script build.py

python3 - <<'PY'
from fontTools.feaLib.builder import addOpenTypeFeatures
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont


def bounds(font, char):
    gs = font.getGlyphSet()
    pen = BoundsPen(gs)
    gs[font.getBestCmap()[ord(char)]].draw(pen)
    return pen.bounds


for style, src in [("Regular", "Regular"), ("Italic", "Italic"), ("Bold", "Bold"), ("BoldItalic", "Bold-Italic")]:
    for ext in ("otf", "ttf"):
        path = f"export/mononoki-{style}.{ext}"
        font = TTFont(path)
        addOpenTypeFeatures(font, f"src/mononoki-{src}.ufo/features.fea")
        font.save(path)
        # self-check: one cell width everywhere, bold keeps regular's vertical metrics
        assert {w for w, _ in font["hmtx"].metrics.values()} <= {0, 575}, path
        regular = TTFont(f"export/mononoki-{'Italic' if 'Italic' in style else 'Regular'}.{ext}")
        for ch in "xHdgO":
            assert abs(bounds(font, ch)[1] - bounds(regular, ch)[1]) <= 2, (path, ch)
            assert abs(bounds(font, ch)[3] - bounds(regular, ch)[3]) <= 2, (path, ch)
        for ch in "◧◨◩◪⬒⬓⬔⬕":  # half-filled squares match ■ □ (loading bars)
            assert all(abs(a - b) <= 2 for a, b in zip(bounds(font, ch), bounds(font, "□"))), (path, ch)
PY

for f in export/mononoki-*.ttf; do
  ttfautohint "$f" "$f.hinted" && mv "$f.hinted" "$f"
done

if [[ "${1:-}" == --nerd ]]; then
  mkdir -p export/nerd
  for f in export/mononoki-*.ttf; do
    nerd-font-patcher --complete --mono --quiet --outputdir export/nerd "$f"
  done
fi
