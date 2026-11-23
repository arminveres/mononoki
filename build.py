"""FontForge part of the build, run by build.sh: outlines and metrics from the regular/italic UFOs.

- Bold styles are generated from Regular/Italic with a vertical "squish" so bold
  keeps the exact x-height, cap height and ascenders of regular (as in monofoki).
- Line height is increased; box drawing / block / powerline glyphs are stretched
  so they still connect from line to line.
- Powerline extra glyphs that were ~1.7 cells wide are fit into one cell.
- Missing symbols are added from monofoki, so terminals don't fall back to wide fonts.
- A few more shapes (◎ ◆ ◇ ◌ ⚠ ...) are derived from ●, ■ and !.
- Operators, arrows, bullets and shapes are centred vertically in the cell.
OpenType features are added afterwards by build.sh (FontForge cannot parse our features.fea).
"""
import math
import os
import plistlib
import unicodedata
import fontforge
import psMat

OLD_ASC, OLD_DESC = 900, 250
ASC, DESC = 910, 320  # +80 units line height, same as monofoki
WIDTH = 575
BOLD_STROKE = 20  # regular stems 85 -> bold 105, as in the old bold

CELL = list(range(0x2500, 0x25A0)) + list(range(0xE0B0, 0xE0C0))  # box, blocks, powerline
TOO_WIDE = range(0xE0B8, 0xE0C0)

STYLES = [  # (source, style name, bold)
    ("Regular", "Regular", False),
    ("Italic", "Italic", False),
    ("Regular", "Bold", True),
    ("Italic", "BoldItalic", True),
]


def cell_glyphs(font):
    return [g for g in font.glyphs() if g.unicode in CELL]


def remove_overlap(g):
    before, bbox = g.foreground, g.boundingBox()
    g.removeOverlap()
    if max(abs(a - b) for a, b in zip(bbox, g.boundingBox())) > 2:  # FontForge sometimes mangles a glyph
        print("removeOverlap failed, keeping overlaps:", g.glyphname)
        g.foreground = before
        return False
    return True


def fix_direction(g):
    # FontForge wants clockwise outer contours or changeWeight thins instead of emboldens. Flip whole glyphs
    # (not correctDirection) so overlapping contours like in "plus" keep their winding relative to each other.
    layer = g.foreground
    if len(layer):
        outer = max(layer, key=lambda c: (lambda b: (b[2] - b[0]) * (b[3] - b[1]))(c.boundingBox()))
        if not outer.isClockwise():
            for c in layer:
                c.reverseDirection()
            g.foreground = layer


def relink(font, refs):
    """Set references bases-first; FontForge caches component outlines, so composites otherwise go stale."""
    def restore(name):
        for base, *_ in refs.get(name, ()):
            restore(base)
        if name in refs:
            font[name].references = ()  # assigning the same tuple alone does not refresh
            font[name].references = refs.pop(name)

    for name in list(refs):
        restore(name)


def unlink(font, g):
    for name, *_ in g.references:  # nested components first, unlinkRef only copies one level
        unlink(font, font[name])
    g.unlinkRef()


def add_symbols(font, source):
    """Symbols mononoki lacks (arrows, check marks, shapes, math, e.g. the zsh prompt arrow U+279C).
    Without them terminals fall back to a proportional font, so they render about two cells wide.
    Taken from monofoki (OFL, a mononoki derivative); Italic gaps are filled from Regular."""
    for sym_style in dict.fromkeys((source, "Regular")):
        symbols = fontforge.open(f"src/monofoki-symbols/{sym_style}.sfd")
        have = {g.unicode for g in font.glyphs()}  # `cp in font` does not match code points
        for s in symbols.glyphs():
            if s.unicode not in have:
                g = font.createChar(s.unicode, f"uni{s.unicode:04X}")
                g.foreground = s.foreground
                g.width = WIDTH
        symbols.close()


def add_derived_shapes(font):
    """Shapes that neither mononoki nor monofoki have (e.g. ◎ ◆ in jj/git graphs), built from ● ■ so they
    match; missing ones fall back to a proportional font and look shifted in the cell."""
    by_u = {g.unicode: g for g in font.glyphs()}
    cx = WIDTH / 2
    _, ymin, _, ymax = by_u[0x25CF].boundingBox()
    cy, r = (ymin + ymax) / 2, (ymax - ymin) / 2
    ring_w = 38  # stroke of ○
    box_w = 80  # stroke of □

    def shape(u, size, filled=True, stroke=0, angle=0):
        """● (u=0x25CF) or ■ (0x25A0) scaled to `size` wide, optionally hollow, centred in the cell."""
        layer = fontforge.layer()
        for outer, size_, rev in ((True, size, False), (False, size - 2 * stroke, True)):
            if not outer and filled:
                break
            part = by_u[u].foreground
            x0, y0, x1, y1 = by_u[u].boundingBox()
            m = psMat.translate(-(x0 + x1) / 2, -(y0 + y1) / 2)
            m = psMat.compose(m, psMat.scale(size_ / (x1 - x0), size_ / (y1 - y0)))
            m = psMat.compose(m, psMat.rotate(math.radians(angle)))
            part.transform(psMat.compose(m, psMat.translate(cx, cy)))
            if rev:
                for c in part:
                    c.reverseDirection()
            layer += part
        return layer

    d = 2 * r
    diamond = d / math.sqrt(2)  # rotated square as wide as ●
    new = {
        0x25CE: shape(0x25CF, d, False, ring_w) + shape(0x25CF, d * 0.55, False, ring_w),  # ◎
        0x25C9: shape(0x25CF, d, False, ring_w) + shape(0x25CF, d * 0.55),  # ◉
        0x25EF: shape(0x25CF, d, False, ring_w),  # ◯
        0x2B24: shape(0x25CF, d),  # ⬤
        0x25E6: shape(0x25CF, d * 0.5, False, ring_w),  # ◦
        0x25AA: shape(0x25A0, d * 0.5),  # ▪
        0x25AB: shape(0x25A0, d * 0.5, False, ring_w),  # ▫
        0x25C6: shape(0x25A0, diamond, angle=45),  # ◆
        0x25C7: shape(0x25A0, diamond, False, box_w / math.sqrt(2), 45),  # ◇
        0x25C8: shape(0x25A0, diamond, False, box_w / math.sqrt(2), 45) + shape(0x25A0, diamond * 0.4, angle=45),  # ◈
    }
    dot = fontforge.layer()  # ◌: ring of 12 dots
    for i in range(12):
        a = 2 * math.pi * i / 12
        part = shape(0x25CF, ring_w * 1.4)
        part.transform(psMat.translate((r - ring_w) * math.cos(a), (r - ring_w) * math.sin(a)))
        dot += part
    new[0x25CC] = dot
    # ⚠: filled triangle with ! knocked out, so bare U+26A0 does not fall back to a wide font
    tri = fontforge.contour()
    tri.moveTo(20, 0)
    tri.lineTo(WIDTH / 2, 0.866 * (WIDTH - 40))
    tri.lineTo(WIDTH - 20, 0)
    tri.closed = True
    warn = fontforge.layer()
    warn += tri
    excl = by_u[0x21].foreground
    x0, y0, x1, y1 = by_u[0x21].boundingBox()
    excl.transform(psMat.compose(psMat.translate(-(x0 + x1) / 2, -y0), psMat.compose(psMat.scale(0.45), psMat.translate(cx, 40))))
    for c in excl:
        if c.isClockwise() == tri.isClockwise():
            c.reverseDirection()
        warn += c
    new[0x26A0] = warn
    for u, layer in new.items():
        if u not in by_u:
            g = font.createChar(u, f"uni{u:04X}")
            g.foreground = layer
            g.width = WIDTH


def is_centered_symbol(u):
    """Operators, arrows, bullets, shapes: things that should share one vertical axis."""
    if u < 0 or 0x2500 <= u <= 0x259F or 0x2800 <= u <= 0x28FF:  # box/block drawing, braille: cell-positioned
        return False
    if u in (0x2044, 0x2215) or unicodedata.decomposition(chr(u)).startswith(("<super>", "<sub>")):
        return False  # fraction/division slash sit like "/", super/subscripts have their own position
    cat = unicodedata.category(chr(u))
    return cat == "Sm" or cat == "Pd" or u in (0x2A, 0x2022) or (cat == "So" and 0x2190 <= u <= 0x2BFF)


def center_symbols(font):
    """Centre symbols in the cell, so e.g. ∙●∙, ->=> or ◎─╮ line up regardless of who drew them or the slant."""
    axis = (ASC - DESC) / 2

    def depth(g):
        return 1 + max(depth(font[r[0]]) for r in g.references) if g.references else 0

    moved = []
    for g in sorted(font.glyphs(), key=depth):  # bases first; composites then see the moved base
        if not is_centered_symbol(g.unicode):
            continue
        xmin, ymin, xmax, ymax = g.boundingBox()
        if ymax <= ymin or ymax - ymin > 750:  # empty, or spans the line like | and integral signs
            continue
        g.transform(psMat.translate(WIDTH / 2 - (xmin + xmax) / 2, axis - (ymin + ymax) / 2))
        g.width = WIDTH
        moved.append(g.glyphname)
    return moved


def build(source, style, bold):
    font = fontforge.open(f"src/mononoki-{source}.ufo")
    add_symbols(font, source)
    add_derived_shapes(font)

    for glyph in font.glyphs():
        if glyph.unicode in CELL:
            unlink(font, glyph)  # so transforms below are not applied twice via components
        layer = glyph.foreground
        if any(len(c) < 2 for c in layer):  # stray single points (e.g. italic uni042E) blow up the bbox
            clean = fontforge.layer()
            for c in layer:
                if len(c) > 1:
                    clean += c
            glyph.foreground = clean
        fix_direction(glyph)
    relink(font, {g.glyphname: g.references for g in font.glyphs() if g.references})
    centered = center_symbols(font)

    # fit over-wide powerline glyphs into one cell
    for g in font.glyphs():
        if g.unicode in TOO_WIDE:
            xmin, _, xmax, _ = g.boundingBox()
            g.transform(psMat.compose(psMat.translate(-xmin, 0), psMat.scale(WIDTH / (xmax - xmin), 1)))
            g.width = WIDTH

    # stretch full-height glyphs from the old line box to the new one
    sy = (ASC + DESC) / (OLD_ASC + OLD_DESC)
    stretch = psMat.compose(psMat.translate(0, OLD_DESC), psMat.compose(psMat.scale(1, sy), psMat.translate(0, -DESC)))
    for g in cell_glyphs(font):
        g.transform(stretch)
        g.width = WIDTH

    if bold:
        for g in font.glyphs():
            remove_overlap(g)  # changeWeight cannot squish overlapping contours
        # embolden contours only; components follow their emboldened base glyphs
        # (changeWeight skips glyphs used as components, so set all refs aside)
        refs = {g.glyphname: g.references for g in font.glyphs() if g.references}
        for name in refs:
            font[name].references = ()
        font.selection.select(*[g for g in font.glyphs() if g.unicode not in CELL and len(g.foreground)])
        font.changeWeight(BOLD_STROKE, "auto", 0, 0, "squish")
        relink(font, refs)
        center_symbols(font)  # changeWeight's zone squish can grow symbols unevenly
        for g in font.glyphs():
            g.width = WIDTH if g.width else 0
        font.weight = "Bold"
        font.os2_weight = 700
        font.macstyle |= 1
        font.os2_stylemap = (font.os2_stylemap & ~0x40) | 0x20  # BOLD, not REGULAR
        font.private["StemSnapH"] = (97,)
        font.private["StemSnapV"] = (105,)

    font.fontname = f"mononoki-{style}"
    font.fullname = "mononoki" if style == "Regular" else f"mononoki {'Bold Italic' if style == 'BoldItalic' else style}"
    subfamily = "Bold Italic" if style == "BoldItalic" else style
    font.appendSFNTName("English (US)", "SubFamily", subfamily)
    font.appendSFNTName("English (US)", "Preferred Styles", subfamily)

    font.hhea_ascent, font.hhea_ascent_add = ASC, 0
    font.hhea_descent, font.hhea_descent_add = -DESC, 0
    font.hhea_linegap = 0
    font.os2_winascent, font.os2_winascent_add = ASC, 0
    font.os2_windescent, font.os2_windescent_add = DESC, 0
    font.os2_typoascent, font.os2_typoascent_add = 750, 0
    font.os2_typodescent, font.os2_typodescent_add = -250, 0
    font.os2_typolinegap = ASC + DESC - 1000
    panose = list(font.os2_panose)
    panose[3] = 9  # bProportion: monospaced
    font.os2_panose = tuple(panose)

    for g in font.glyphs():
        unlink(font, g)
    with open(f"src/mononoki-{source}.ufo/lib.plist", "rb") as f:
        for name in plistlib.load(f).get("public.skipExportGlyphs", []):
            font.removeGlyph(name)
    for g in font.glyphs():
        if remove_overlap(g):
            g.correctDirection()  # safe without overlaps; changeWeight can leave contours reversed
        else:
            fix_direction(g)
        g.round()
        g.addExtrema("all")

    for name in centered:  # self-check: still centred after bold/unlink/overlap removal
        xmin, ymin, xmax, ymax = font[name].boundingBox()
        assert abs((ymin + ymax) / 2 - (ASC - DESC) / 2) <= 3, (style, name, ymin, ymax)
        assert abs((xmin + xmax) / 2 - WIDTH / 2) <= 3, (style, name, xmin, xmax)

    os.makedirs("export", exist_ok=True)
    for ext in ("otf", "ttf"):
        font.generate(f"export/mononoki-{style}.{ext}", flags=("opentype",))
    font.close()


os.chdir(os.path.dirname(os.path.abspath(__file__)))
for args in STYLES:
    build(*args)
