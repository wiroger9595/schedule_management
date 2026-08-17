#!/usr/bin/env python3
"""Schedulo app icon / splash 產生器。

這支腳本就是 icon 的設計原始檔 —— 要調整外觀改下面的常數再重跑，
不要直接修 PNG（PNG 都是這裡輸出的，會被蓋掉）。

    python3 tool/generate_app_icons.py

視覺：navy 漸層底 + 白色日曆 + sky 高亮日期格 + 右上 AI 星芒。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

MOBILE = Path(__file__).resolve().parent.parent
REPO = MOBILE.parent

# 全專案共用的素材出口：web landing、文件、簡報要用圖都從這裡拿，
# 不要各自複製一份 PNG 出去改
SHARED_ICONS = REPO / "public/images/icons"
SHARED_BACKGROUNDS = REPO / "public/images/backgrounds"

# ── 品牌色（對齊 lib/theme/app_theme.dart）──────────────────────────────
NAVY_TL = (35, 71, 127)     # 漸層左上，比 primary 亮一階
NAVY_BR = (16, 41, 82)      # primaryDark #102952
NAVY = (27, 58, 110)        # primary #1B3A6E
SKY = (14, 165, 233)        # secondary #0EA5E9
SKY_LIGHT = (56, 189, 248)  # 星芒用，navy 底上要夠亮
WHITE = (255, 255, 255)
CELL = (176, 188, 207)      # 日期格；再淡下去 29px 的 icon 會糊成一片白

SPLASH_BG_LIGHT = (240, 242, 247)  # AppTheme.background
SPLASH_BG_DARK = (16, 41, 82)

MASTER = 2048  # 所有輸出都從這個尺寸 LANCZOS 縮下去

# glyph 佔畫布的比例
FRAC_FULLBLEED = 0.66  # iOS / Play 商店滿版圖
# Android adaptive 只顯示 108dp 中央的 72dp，等於再放大 1.5 倍；
# 0.44 * 108 / 72 ≈ 0.66，跟 iOS 的視覺大小一致
FRAC_ADAPTIVE = 0.44
FRAC_ROUNDED = 0.66
FRAC_CIRCLE = 0.60

# 日曆本體在左下、星芒在右上，bbox 置中會讓視覺重心偏左下，往右上補回來
GLYPH_NUDGE = (0.075, -0.065)

DPI_SCALE = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


# ── 基本繪圖 ───────────────────────────────────────────────────────────
def gradient_bg(size: int) -> Image.Image:
    """對角 navy 漸層。用 2x2 放大做出平滑的雙線性漸層。"""
    seed = Image.new("RGB", (2, 2))
    mid = tuple((a + b) // 2 for a, b in zip(NAVY_TL, NAVY_BR))
    seed.putpixel((0, 0), NAVY_TL)
    seed.putpixel((1, 0), mid)
    seed.putpixel((0, 1), mid)
    seed.putpixel((1, 1), NAVY_BR)
    return seed.resize((size, size), Image.BICUBIC)


def sparkle_points(cx: float, cy: float, r: float) -> list[tuple[float, float]]:
    """四角星芒。r(θ) 在對角線方向急遽收縮，做出內凹的尖角。"""
    pts = []
    for i in range(360):
        t = math.radians(i)
        rad = r / (1 + 5.5 * abs(math.sin(2 * t)))
        pts.append((cx + rad * math.cos(t), cy + rad * math.sin(t)))
    return pts


def draw_glyph(size: int, frac: float, *, mono: bool = False) -> Image.Image:
    """透明底的 logo 圖形，置中，佔畫布 frac。

    mono=True 產 Android 13+ themed icon 用的單色版：系統只吃 alpha 再上色，
    所以日曆本體改成描邊，不然會糊成一塊實心圓角方形。
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    g = size * frac                              # glyph 邊長
    ox = (size - g) / 2 + GLYPH_NUDGE[0] * g     # glyph 左上角
    oy = (size - g) / 2 + GLYPH_NUDGE[1] * g

    def px(u: float, v: float) -> tuple[float, float]:
        return ox + u * g, oy + v * g

    # 日曆本體：留出右上角給星芒
    bx0, by0 = px(0.0, 0.20)
    bx1, by1 = px(0.78, 1.0)
    bw, bh = bx1 - bx0, by1 - by0
    radius = 0.15 * bw
    head_h = 0.22 * bh
    ring_r = 0.048 * bw
    ring_cy = by0 + head_h * 0.52

    if mono:
        stroke = max(1, int(0.055 * bw))
        d.rounded_rectangle([bx0, by0, bx1, by1], radius=radius, outline=WHITE, width=stroke)
        # 標題條保留成實心，裝訂環從裡面挖掉
        d.rounded_rectangle(
            [bx0, by0, bx1, by0 + head_h + radius],
            radius=radius,
            fill=WHITE,
            corners=(True, True, False, False),
        )
        # 只挖內部，不要把左右描邊一起挖掉
        d.rectangle(
            [bx0 + stroke, by0 + head_h, bx1 - stroke, by0 + head_h + radius],
            fill=(0, 0, 0, 0),
        )
        for u in (0.32, 0.68):
            cx = bx0 + u * bw
            d.ellipse(
                [cx - ring_r, ring_cy - ring_r, cx + ring_r, ring_cy + ring_r],
                fill=(0, 0, 0, 0),
            )
    else:
        d.rounded_rectangle([bx0, by0, bx1, by1], radius=radius, fill=WHITE)

        # 頂部 navy 標題條（只有上面兩角是圓的）
        d.rounded_rectangle(
            [bx0, by0, bx1, by0 + head_h + radius],
            radius=radius,
            fill=NAVY,
            corners=(True, True, False, False),
        )
        d.rectangle([bx0, by0 + head_h, bx1, by0 + head_h + radius], fill=WHITE)

        # 標題條上兩顆白色裝訂環
        for u in (0.32, 0.68):
            cx = bx0 + u * bw
            d.ellipse(
                [cx - ring_r, ring_cy - ring_r, cx + ring_r, ring_cy + ring_r], fill=WHITE
            )

    # 日期格 4x3
    pad_x = 0.13 * bw
    gx0, gx1 = bx0 + pad_x, bx1 - pad_x
    gy0, gy1 = by0 + head_h + 0.13 * bh, by1 - 0.12 * bh
    step_x = (gx1 - gx0) / 4
    step_y = (gy1 - gy0) / 3
    cell = 0.60 * min(step_x, step_y)

    hi_row, hi_col = 1, 2  # 高亮「今天」
    for row in range(3):
        for col in range(4):
            cx = gx0 + (col + 0.5) * step_x
            cy = gy0 + (row + 0.5) * step_y
            highlight = (row, col) == (hi_row, hi_col)
            s = cell * 1.30 if highlight else cell
            d.rounded_rectangle(
                [cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2],
                radius=0.32 * s,
                fill=WHITE if mono else (SKY if highlight else CELL),
            )

    # AI 星芒：位置刻意避開日曆本體，四個尖角都落在 navy 底上
    scx, scy = px(0.84, 0.16)
    d.polygon(sparkle_points(scx, scy, 0.155 * g), fill=WHITE if mono else SKY_LIGHT)

    return img


def compose(size: int, frac: float) -> Image.Image:
    bg = gradient_bg(size)
    out = bg.convert("RGBA")
    out.alpha_composite(draw_glyph(size, frac))
    return out


def masked(base: Image.Image, mask: Image.Image) -> Image.Image:
    out = base.copy()
    out.putalpha(mask)
    return out


def build_masters() -> dict[str, Image.Image]:
    rr_mask = Image.new("L", (MASTER, MASTER), 0)
    ImageDraw.Draw(rr_mask).rounded_rectangle(
        [0, 0, MASTER - 1, MASTER - 1], radius=int(MASTER * 0.22), fill=255
    )
    c_mask = Image.new("L", (MASTER, MASTER), 0)
    ImageDraw.Draw(c_mask).ellipse([0, 0, MASTER - 1, MASTER - 1], fill=255)

    return {
        "full": compose(MASTER, FRAC_FULLBLEED),            # 滿版（iOS / Play）
        "fg": draw_glyph(MASTER, FRAC_ADAPTIVE),            # Android adaptive 前景
        "mono": draw_glyph(MASTER, FRAC_ADAPTIVE, mono=True),  # Android 13+ themed icon
        "bg": gradient_bg(MASTER).convert("RGBA"),          # Android adaptive 背景
        "rounded": masked(compose(MASTER, FRAC_ROUNDED), rr_mask),
        "circle": masked(compose(MASTER, FRAC_CIRCLE), c_mask),
    }


def main() -> None:
    print("繪製 master…")
    m = build_masters()
    written: list[str] = []

    def save(master: Image.Image, path: Path, size: int, *, opaque: bool = False) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        img = master.resize((size, size), Image.LANCZOS)
        if opaque:
            img = img.convert("RGB")  # App Store 主圖不允許 alpha channel
        img.save(path, "PNG")
        written.append(str(path.relative_to(REPO)))

    # ── iOS AppIcon ───────────────────────────────────────────────────
    print("iOS AppIcon…")
    ios_set = MOBILE / "ios/Runner/Assets.xcassets/AppIcon.appiconset"
    contents = json.loads((ios_set / "Contents.json").read_text())
    for entry in contents["images"]:
        side = float(entry["size"].split("x")[0])
        scale = int(entry["scale"].rstrip("x"))
        save(m["full"], ios_set / entry["filename"], int(round(side * scale)), opaque=True)

    # ── Android launcher ──────────────────────────────────────────────
    print("Android launcher…")
    res = MOBILE / "android/app/src/main/res"
    for dpi, mult in DPI_SCALE.items():
        legacy = int(48 * mult)
        save(m["rounded"], res / f"mipmap-{dpi}/ic_launcher.png", legacy)
        save(m["circle"], res / f"mipmap-{dpi}/ic_launcher_round.png", legacy)

        # adaptive icon 圖層固定是 108dp
        adaptive = int(108 * mult)
        save(m["fg"], res / f"mipmap-{dpi}/ic_launcher_foreground.png", adaptive)
        save(m["bg"], res / f"mipmap-{dpi}/ic_launcher_background.png", adaptive)
        save(m["mono"], res / f"mipmap-{dpi}/ic_launcher_monochrome.png", adaptive)

        # splash 用的置中 logo
        save(m["rounded"], res / f"drawable-{dpi}/launch_image.png", int(96 * mult))

    anydpi = res / "mipmap-anydpi-v26"
    anydpi.mkdir(parents=True, exist_ok=True)
    adaptive_xml = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@mipmap/ic_launcher_background" />
    <foreground android:drawable="@mipmap/ic_launcher_foreground" />
    <monochrome android:drawable="@mipmap/ic_launcher_monochrome" />
</adaptive-icon>
"""
    for name in ("ic_launcher.xml", "ic_launcher_round.xml"):
        (anydpi / name).write_text(adaptive_xml)
        written.append(str((anydpi / name).relative_to(REPO)))

    # ── 商店主圖 ──────────────────────────────────────────────────────
    print("商店主圖…")
    store = MOBILE / "store_assets"
    save(m["full"], store / "app_store_1024.png", 1024, opaque=True)
    save(m["full"], store / "play_store_512.png", 512, opaque=True)

    # ── iOS LaunchImage ───────────────────────────────────────────────
    print("iOS LaunchImage…")
    launch = MOBILE / "ios/Runner/Assets.xcassets/LaunchImage.imageset"
    for name, size in (("LaunchImage.png", 120), ("LaunchImage@2x.png", 240), ("LaunchImage@3x.png", 360)):
        save(m["rounded"], launch / name, size)

    # ── 全專案共用素材 ────────────────────────────────────────────────
    print("public/images…")
    save(m["full"], SHARED_ICONS / "app_icon_1024.png", 1024, opaque=True)
    save(m["rounded"], SHARED_ICONS / "app_icon_rounded_512.png", 512)
    save(m["circle"], SHARED_ICONS / "app_icon_circle_512.png", 512)
    save(m["fg"], SHARED_ICONS / "app_icon_foreground.png", 1024)
    save(m["mono"], SHARED_ICONS / "app_icon_monochrome.png", 1024)
    save(m["bg"], SHARED_BACKGROUNDS / "gradient_navy_2048.png", 2048)

    print(f"\n完成，共 {len(written)} 個檔案：")
    for p in written:
        print("  " + p)


if __name__ == "__main__":
    main()
