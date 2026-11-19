"""Draw a one-page, pixel-rendered newspaper for 19 November 2026."""

import os
import struct
import zlib


W = H = 1024
PAPER = (248, 246, 238)
INK = (25, 31, 34)
RED = (166, 54, 43)
pixels = bytearray(bytes(PAPER) * (W * H))


# A compact hand-drawn 5x7 bitmap alphabet. Each row is a five-bit mask.
FONT = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    "A": (14, 17, 17, 31, 17, 17, 17), "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14), "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31), "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15), "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (31, 4, 4, 4, 4, 4, 31), "J": (7, 2, 2, 2, 18, 18, 12),
    "K": (17, 18, 20, 24, 20, 18, 17), "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17), "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14), "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13), "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30), "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14), "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 21, 10), "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4), "Z": (31, 1, 2, 4, 8, 16, 31),
    "0": (14, 17, 19, 21, 25, 17, 14), "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 2, 4, 8, 31), "3": (30, 1, 1, 14, 1, 1, 30),
    "4": (2, 6, 10, 18, 31, 2, 2), "5": (31, 16, 16, 30, 1, 1, 30),
    "6": (14, 16, 16, 30, 17, 17, 14), "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14), "9": (14, 17, 17, 15, 1, 1, 14),
    ".": (0, 0, 0, 0, 0, 12, 12), ",": (0, 0, 0, 0, 4, 4, 8),
    ":": (0, 12, 12, 0, 12, 12, 0), ";": (0, 12, 12, 0, 4, 4, 8),
    "!": (4, 4, 4, 4, 4, 0, 4), "?": (14, 17, 1, 2, 4, 0, 4),
    "-": (0, 0, 0, 31, 0, 0, 0), "+": (0, 4, 4, 31, 4, 4, 0),
    "/": (1, 1, 2, 4, 8, 16, 16), "'": (4, 4, 8, 0, 0, 0, 0),
    '"': (10, 10, 20, 0, 0, 0, 0), "&": (12, 18, 20, 8, 21, 18, 13),
    "=": (0, 31, 0, 31, 0, 0, 0), "|": (4, 4, 4, 4, 4, 4, 4),
    "(": (2, 4, 8, 8, 8, 4, 2), ")": (8, 4, 2, 2, 2, 4, 8),
}


def pixel(x, y, color):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        pixels[i:i + 3] = bytes(color)


def rect(x, y, w, h, color):
    if w <= 0 or h <= 0:
        return
    x0, x1 = max(0, x), min(W, x + w)
    y0, y1 = max(0, y), min(H, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    row = bytes(color) * (x1 - x0)
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        pixels[i:i + len(row)] = row


def line(x0, y0, x1, y1, color, thick=1):
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        rect(x0 - thick // 2, y0 - thick // 2, thick, thick, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def circle(cx, cy, radius, color, fill=False, thickness=2):
    r2 = radius * radius
    inner = max(0, radius - thickness) ** 2
    for yy in range(cy - radius, cy + radius + 1):
        for xx in range(cx - radius, cx + radius + 1):
            d2 = (xx - cx) ** 2 + (yy - cy) ** 2
            if d2 <= r2 and (fill or d2 >= inner):
                pixel(xx, yy, color)


def polygon(points, color, fill=True, thickness=2):
    if fill:
        ymin = max(0, min(y for _, y in points))
        ymax = min(H - 1, max(y for _, y in points))
        for yy in range(ymin, ymax + 1):
            crossings = []
            for i, (x1, y1) in enumerate(points):
                x2, y2 = points[(i + 1) % len(points)]
                if (y1 <= yy < y2) or (y2 <= yy < y1):
                    crossings.append(round(x1 + (yy - y1) * (x2 - x1) / (y2 - y1)))
            crossings.sort()
            for i in range(0, len(crossings) - 1, 2):
                rect(crossings[i], yy, crossings[i + 1] - crossings[i] + 1, 1, color)
    for i, point in enumerate(points):
        nxt = points[(i + 1) % len(points)]
        line(point[0], point[1], nxt[0], nxt[1], color, thickness)


def text_width(value, scale, gap=1):
    return max(0, len(value) * (5 * scale + gap) - gap)


def draw_text(value, x, y, scale=2, color=INK, gap=1):
    value = value.upper()
    cursor = x
    for char in value:
        glyph = FONT.get(char, FONT["?"])
        for row, bits in enumerate(glyph):
            for col in range(5):
                if bits & (1 << (4 - col)):
                    rect(cursor + col * scale, y + row * scale, scale, scale, color)
        cursor += 5 * scale + gap
    return cursor - x - gap


def outlined_box(x, y, w, h, color=INK, weight=2):
    rect(x, y, w, weight, color)
    rect(x, y + h - weight, w, weight, color)
    rect(x, y, weight, h, color)
    rect(x + w - weight, y, weight, h, color)


def tiny_flag(x, y, kind):
    w, h = 48, 28
    outlined_box(x, y, w, h, INK, 1)
    if kind == "USA":
        for band in range(4):
            if band % 2 == 0:
                rect(x + 1, y + 1 + band * 6, w - 2, 5, RED)
        rect(x + 1, y + 1, 19, 12, INK)
        for sx, sy in ((5, 4), (11, 4), (16, 4), (8, 9), (14, 9)):
            pixel(x + sx, y + sy, PAPER)
    elif kind == "CHINA":
        rect(x + 1, y + 1, w - 2, h - 2, RED)
        circle(x + 10, y + 10, 4, PAPER, True)
        for sx, sy in ((20, 5), (25, 10), (24, 17), (18, 21)):
            circle(x + sx, y + sy, 1, PAPER, True)
    else:
        rect(x + 1, y + 1, w - 2, 8, PAPER)
        rect(x + 1, y + 9, w - 2, 9, INK)
        rect(x + 1, y + 18, w - 2, 9, RED)


def draw_summit_art():
    # APEC flag row and three leader busts around a shared table.
    flags = ((702, "USA", "USA"), (804, "CHINA", "CHINA"), (906, "RUSSIA", "RUSSIA"))
    for fx, kind, label in flags:
        line(fx - 4, 172, fx - 4, 218, INK, 2)
        tiny_flag(fx, 174, kind)
        draw_text(label, fx - 1, 208, 1, INK)

    centers = (731, 833, 935)
    names = ("TRUMP", "XI", "PUTIN")
    for idx, (cx, name) in enumerate(zip(centers, names)):
        # Hair shapes distinguish the three editorially without claiming portrait likeness.
        circle(cx, 267, 22, INK, fill=False, thickness=2)
        circle(cx, 267, 18, PAPER, fill=True)
        circle(cx - 7, 267, 2, INK, True)
        circle(cx + 7, 267, 2, INK, True)
        line(cx - 5, 276, cx + 5, 276, INK, 1)
        if idx == 0:
            polygon(((cx - 18, 258), (cx - 13, 245), (cx + 4, 244), (cx + 19, 251),
                     (cx + 9, 255), (cx - 8, 252)), RED, True, 1)
        elif idx == 1:
            polygon(((cx - 17, 255), (cx - 11, 246), (cx + 10, 246), (cx + 17, 255)), INK, True, 1)
        else:
            polygon(((cx - 15, 254), (cx - 10, 246), (cx + 11, 246), (cx + 16, 254)), INK, True, 1)
        polygon(((cx - 28, 297), (cx - 21, 290), (cx + 21, 290), (cx + 28, 297),
                 (cx + 31, 340), (cx - 31, 340)), PAPER, True, 2)
        polygon(((cx - 6, 291), (cx, 301), (cx + 6, 291), (cx + 4, 331), (cx - 4, 331)), RED, True, 1)
        draw_text(name, cx - text_width(name, 1) // 2, 315, 1, INK)

    # Table lip foreground establishes the summit setting.
    polygon(((688, 341), (975, 341), (956, 366), (707, 366)), INK, True, 2)
    polygon(((694, 342), (969, 342), (952, 359), (710, 359)), PAPER, True, 1)
    line(713, 350, 950, 350, RED, 2)
    for cx in centers:
        circle(cx, 350, 4, INK, True)


def icon_game(x, y):
    # Vice City skyline and a simple controller.
    for bx, bw, bh in ((x + 2, 11, 25), (x + 17, 14, 37), (x + 35, 10, 29), (x + 48, 12, 43)):
        rect(bx, y + 45 - bh, bw, bh, INK)
        for wy in range(y + 45 - bh + 6, y + 43, 9):
            rect(bx + 3, wy, 2, 3, PAPER)
    line(x, y + 46, x + 65, y + 46, RED, 2)
    circle(x + 31, y + 53, 11, INK, False, 2)
    line(x + 25, y + 53, x + 37, y + 53, RED, 2)
    line(x + 31, y + 47, x + 31, y + 59, RED, 2)
    circle(x + 46, y + 51, 2, RED, True)


def icon_capitol(x, y):
    polygon(((x + 5, y + 35), (x + 33, y + 16), (x + 61, y + 35)), INK, False, 2)
    circle(x + 33, y + 17, 5, RED, False, 2)
    rect(x + 7, y + 36, 52, 5, RED)
    for cx in (x + 13, x + 25, x + 37, x + 49):
        rect(cx, y + 42, 4, 21, INK)
    rect(x + 4, y + 63, 58, 4, INK)


def icon_middle_east(x, y):
    # Missile over Gulf waves; the pointed shape is clearly directional.
    polygon(((x + 14, y + 17), (x + 42, y + 3), (x + 35, y + 31), (x + 27, y + 36)), INK, True, 1)
    polygon(((x + 14, y + 17), (x + 6, y + 10), (x + 10, y + 24)), RED, True, 1)
    line(x + 25, y + 31, x + 19, y + 43, RED, 3)
    line(x + 20, y + 43, x + 28, y + 39, RED, 2)
    for yy in (49, 57, 65):
        for xx in (4, 24, 44):
            line(xx + x, yy + y, xx + x + 12, yy + y - 3, INK, 2)


def icon_europe(x, y):
    circle(x + 24, y + 31, 21, INK, False, 2)
    for sx, sy in ((24, 12), (35, 16), (43, 25), (42, 37), (34, 46), (22, 49), (13, 41), (12, 27)):
        circle(x + sx, y + sy, 2, RED, True)
    rect(x + 45, y + 39, 22, 19, PAPER)
    outlined_box(x + 45, y + 39, 22, 19, INK, 2)
    draw_text("45", x + 49, y + 44, 1, RED)


def icon_india(x, y):
    # Cyclone spiral and a coastline marker.
    circle(x + 32, y + 33, 25, INK, False, 2)
    circle(x + 32, y + 33, 17, RED, False, 2)
    circle(x + 32, y + 33, 9, INK, False, 2)
    circle(x + 32, y + 33, 3, RED, True)
    line(x + 57, y + 8, x + 57, y + 59, INK, 2)
    circle(x + 57, y + 14, 4, RED, True)
    circle(x + 57, y + 54, 4, RED, True)


def icon_space(x, y):
    # Voyager probe with antenna dish, long boom, and outgoing signal arcs.
    circle(x + 20, y + 34, 15, INK, False, 2)
    line(x + 8, y + 45, x + 32, y + 23, RED, 2)
    line(x + 20, y + 34, x + 47, y + 34, INK, 3)
    rect(x + 34, y + 29, 16, 10, INK)
    polygon(((x + 47, y + 29), (x + 60, y + 21), (x + 60, y + 47), (x + 47, y + 39)), PAPER, True, 2)
    line(x + 49, y + 34, x + 64, y + 34, RED, 2)
    line(x + 51, y + 28, x + 63, y + 20, INK, 1)
    line(x + 51, y + 40, x + 63, y + 48, INK, 1)


def icon_markets(x, y):
    outlined_box(x + 8, y + 6, 50, 42, INK, 2)
    for off in (17, 28, 39):
        line(x + off, y + 2, x + off, y + 8, RED, 2)
        line(x + off, y + 48, x + off, y + 54, RED, 2)
        line(x + 2, y + off, x + 8, y + off, RED, 2)
        line(x + 58, y + off, x + 64, y + off, RED, 2)
    polygon(((x + 17, y + 39), (x + 27, y + 29), (x + 36, y + 33), (x + 49, y + 15)), RED, False, 3)
    polygon(((x + 44, y + 15), (x + 50, y + 15), (x + 50, y + 21)), RED, True, 1)


def icon_faith(x, y):
    circle(x + 31, y + 33, 27, INK, False, 2)
    # Crescent is made by two clean circular arcs on a shared ground.
    circle(x + 26, y + 31, 17, RED, False, 3)
    circle(x + 33, y + 27, 17, PAPER, False, 4)
    for sx, sy in ((44, 17), (50, 29), (43, 45)):
        circle(x + sx, y + sy, 2, RED, True)


ICONS = (icon_game, icon_capitol, icon_middle_east, icon_europe,
         icon_india, icon_space, icon_markets, icon_faith)


def draw_headline_panel():
    x, y, w, h = 28, 143, 968, 338
    outlined_box(x, y, w, h, INK, 2)
    rect(x + 2, y + 2, w - 4, 5, RED)
    draw_text("SHENZHEN / APEC SIDELINES", 48, 158, 2, RED)
    draw_text("TRUMP, XI & PUTIN", 48, 188, 5, INK, 2)
    draw_text("MEET IN SHENZHEN", 48, 240, 5, INK, 2)
    draw_text("FIRST-EVER TRILATERAL SUMMIT", 48, 292, 3, RED)
    summary = (
        "An unprecedented three-way meeting",
        "runs alongside APEC. Topics include:",
        "Ukraine, Iran, trade, AI chips and",
        "nuclear arms. No result is reported.",
    )
    for i, row in enumerate(summary):
        draw_text(row, 48, 326 + i * 20, 2, INK)
    draw_text("PUTIN EXPECTS SUBSTANTIAL UPSIDE", 48, 414, 2, RED)
    draw_text("TRUMP AND PUTIN ALSO HOLD BILATERAL TALKS", 48, 434, 2, INK)

    line(660, 161, 660, 461, INK, 2)
    draw_summit_art()
    draw_text("THREE FLAGS / ONE TABLE", 714, 382, 2, INK)
    draw_text("TALKS, NOT A DEAL", 747, 411, 2, RED)
    line(701, 400, 960, 400, RED, 1)


STORIES = (
    ("GAMES", "GTA VI: VICE CITY", "Global launch; 1 in 5 US workers take leave."),
    ("WASHINGTON", "DEMS PICK JEFFRIES", "Could be House's first Black Speaker."),
    ("MIDDLE EAST", "US-IRAN FIRE AGAIN", "US hit Qeshm; Iran strikes Kuwait + Bahrain."),
    ("EUROPE", "45B FOR UKRAINE", "EU loan due after Russian reparations."),
    ("INDIA", "AKVAN NEARS INDIA", "Likely path: Machilipatnam to Puri."),
    ("SPACE", "VOYAGER 1 / 1 DAY", "NASA briefing Thursday may confirm distance."),
    ("MARKETS", "NVIDIA'S NEW CHIEF", "Pay rises sooner; China H-series halted."),
    ("FAITH", "ISLAM BY 2035", "Pew projects Islam as largest religion."),
)


def draw_card(index, story):
    label, headline, summary = story
    col, row = index % 2, index // 2
    x = 28 + col * 493
    y = 497 + row * 123
    w, h = 475, 114
    outlined_box(x, y, w, h, INK, 2)
    # Red serial tab gives the grid the rhythm of a printed front page.
    rect(x + 2, y + 2, 28, 5, RED)
    draw_text(label, x + 14, y + 10, 2, RED)
    # At 4x, the compact headline has a 28-pixel cap height.
    draw_text(headline, x + 14, y + 30, 4, INK, 0)
    icon_x, icon_y = x + 405, y + 6
    ICONS[index](icon_x, icon_y)
    # Every brief uses one 14-pixel cap-height summary line.
    if text_width(headline, 4, 0) > 382 or text_width(summary, 2, 0) > 440:
        raise ValueError("story text does not fit its panel")
    draw_text(summary, x + 14, y + 77, 2, INK, 0)


def draw_page():
    # Fine inset frame and newspaper masthead.
    outlined_box(13, 13, 998, 998, INK, 2)
    draw_text("GLOBAL EDITION / 9 DISPATCHES", 30, 20, 2, RED)
    draw_text("THE WORLD IN ONE DAY", 30, 42, 5, INK, 2)
    draw_text("THURSDAY 19 NOVEMBER 2026", 30, 88, 4, INK, 1)
    line(28, 126, 996, 126, RED, 4)
    line(28, 134, 996, 134, INK, 1)

    draw_headline_panel()
    for i, story in enumerate(STORIES):
        draw_card(i, story)

    line(28, 985, 996, 985, RED, 2)
    draw_text("19 NOVEMBER 2026 / THE WORLD IN ONE IMAGE", 30, 991, 2, INK)
    draw_text("VOL. 19", 890, 991, 2, RED)


def png_chunk(kind, payload):
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)


def encode_png():
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        start = y * stride
        raw.extend(pixels[start:start + stride])
    return (b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
            + png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + png_chunk(b"IEND", b""))


def main():
    draw_page()
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "entry.png"), "wb") as output:
        output.write(encode_png())


if __name__ == "__main__":
    main()
