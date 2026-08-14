"""Deterministic generator for the multimodal test images.

Renders every image with exact, verifiable content:
  M1: misleading truncated-axis line chart
  M2: occlusion scene with 3 red circles
  M3: login UI mockup with planted usability defects
  M4: park scene (no dog/fountain/kite) for caption mismatch test
  M5: table with a merged total cell
  MM2: handwritten purchase table with a corrected entry and wrong total
  MM3: dual-axis chart with forecast interval, missing value, and truncated axis
  MM4: two-view engineering sketch with dimensions and deliberately missing specs
"""

import math
import os

from PIL import Image, ImageDraw, ImageFont


OUT = os.path.dirname(os.path.abspath(__file__))

MM2_ROWS = [
    {"item": "矿泉水", "quantity": 3, "quantity_text": "3箱", "unit_price": 24.5, "subtotal": 73.5, "note": ""},
    {"item": "面包", "quantity": 4, "quantity_text": "4袋", "unit_price": 12, "subtotal": 48, "note": "早餐"},
    {"item": "牛奶", "quantity": 6, "quantity_text": "6盒", "unit_price": 8.5, "subtotal": 51, "note": ""},
    {"item": "苹果", "quantity": 2.5, "quantity_text": "2.5千克", "unit_price": 9.6, "subtotal": 24, "note": ""},
    {"item": "纸杯", "quantity": 2, "quantity_text": "2包", "unit_price": 7.5, "subtotal": 15, "note": ""},
    {"item": "电池", "quantity": 3, "quantity_text": "3组", "unit_price": 18, "subtotal": 54, "note": ""},
    {"item": "雨衣", "quantity": 5, "quantity_text": "5件", "unit_price": 16, "subtotal": 80, "note": "天气预报有雨"},
]
MM2_WRITTEN_TOTAL = 354.5
MM2_FOOTNOTE = "备注：有改动，以改后数字为准。"

MM3_MONTHS = ["1月", "2月", "3月", "4月", "5月", "6月"]
MM3_ACTUAL = [82, 88, 91, 87, None, 101]
MM3_FORECAST = [80, 85, 90, 94, 98, 103]
MM3_FORECAST_LOW = [None, None, None, 90, 93, 97]
MM3_FORECAST_HIGH = [None, None, None, 98, 103, 108]
MM3_RETURN_RATE = [3.1, 2.8, 3.4, 2.6, 2.2, 1.9]
MM3_SALES_AXIS_MIN = 75
MM3_SALES_AXIS_MAX = 110
MM3_MISSING_MARKER_VALUE = 77
MM3_JUNE_LABEL_SIDES = {"actual": "below", "forecast": "above"}
MM3_CHART_NOTE = "注：5月实际值未录入；4—6月预测区间分别为 90—98、93—103、97—108 万元。"

MM4_DIMENSIONS = {
    "plate_height": 360,
    "plate_width": 60,
    "hole_diameter": 10,
    "hole_center_spacing": 120,
    "max_shelf_depth": 280,
    "candidate_shelf_depth": 300,
}
MM4_DRAWING_NOTE = "说明：示意图不按比例；未标注尺寸不得量图推算。"


def _font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _font_bold(size: int):
    candidates = [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return _font(size)


def _font_handwritten(size: int, bold: bool = False):
    path = (
        "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/"
        "9fdda46cbe802833590494a09b2787378340c597.asset/AssetData/Hanzipen.ttc"
    )
    if os.path.exists(path):
        try:
            return ImageFont.truetype(path, size, index=2 if bold else 0)
        except OSError:
            pass
    return _font_bold(size) if bold else _font(size)


def _center_text(draw, cx, cy, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text((cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]), text, font=font, fill=fill)


def _hand_text(img, xy, text, font, fill="#183B66", angle=0):
    bbox = font.getbbox(text)
    pad = 18
    width = bbox[2] - bbox[0] + pad * 2
    height = bbox[3] - bbox[1] + pad * 2
    layer = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(layer)
    draw.text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=fill)
    if angle:
        layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    img.paste(layer, xy, layer)


def _dashed_line(draw, start, end, fill, width=4, dash=16, gap=10):
    x1, y1 = start
    x2, y2 = end
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    ux = (x2 - x1) / length
    uy = (y2 - y1) / length
    distance = 0
    while distance < length:
        segment_end = min(distance + dash, length)
        draw.line(
            [
                (x1 + ux * distance, y1 + uy * distance),
                (x1 + ux * segment_end, y1 + uy * segment_end),
            ],
            fill=fill,
            width=width,
        )
        distance += dash + gap


def _double_arrow(draw, start, end, fill="#35566F", width=3, head=10):
    draw.line([start, end], fill=fill, width=width)
    x1, y1 = start
    x2, y2 = end
    angle = math.atan2(y2 - y1, x2 - x1)
    for x, y, direction in [(x1, y1, angle), (x2, y2, angle + math.pi)]:
        for delta in (-0.55, 0.55):
            ex = x + head * math.cos(direction + delta)
            ey = y + head * math.sin(direction + delta)
            draw.line([(x, y), (ex, ey)], fill=fill, width=width)


def m1_chart():
    W, H = 1200, 800
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f_title = _font_bold(34)
    f_axis = _font(22)
    f_pt = _font(20)

    left, right, top, bottom = 130, 1140, 100, 690
    d.text((left, 30), "月度准时率对比（%）", font=f_title, fill="#111111")

    # Gridlines from 90 to 98
    months = ["1月", "2月", "3月", "4月", "5月", "6月"]
    ymin, ymax = 90.0, 98.0
    for v in range(90, 99):
        y = bottom - (v - ymin) / (ymax - ymin) * (bottom - top)
        d.line([(left, y), (right, y)], fill="#DDDDDD", width=1)
        _center_text(d, left - 48, y, f"{v}%", f_axis, "#333333")
    for i, m in enumerate(months):
        x = left + (i + 0.5) * (right - left) / 6
        d.line([(x, top), (x, bottom)], fill="#EEEEEE", width=1)
        _center_text(d, x, bottom + 28, m, f_axis, "#333333")

    # Axis lines
    d.line([(left, bottom), (right, bottom)], fill="#333333", width=2)
    d.line([(left, top), (left, bottom)], fill="#333333", width=2)

    series = {
        "A（新方案）": ([92.0, 94.5, 93.0, 96.5, 95.0, 97.5], (210, 60, 60)),
        "B（旧方案）": ([90.5, 91.0, 92.0, 92.5, 93.5, 94.0], (40, 90, 200)),
    }
    legend_x = 690
    for name, (_, color) in series.items():
        d.rectangle([legend_x, 44, legend_x + 28, 66], fill=color)
        d.text((legend_x + 36, 38), name, font=f_axis, fill="#111111")
        legend_x += 36 + d.textlength(name, font=f_axis) + 46

    for name, (vals, color) in series.items():
        pts = []
        for i, v in enumerate(vals):
            x = left + (i + 0.5) * (right - left) / 6
            y = bottom - (v - ymin) / (ymax - ymin) * (bottom - top)
            pts.append((x, y))
            d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=color)
            _center_text(d, x, y - 26, f"{v:.1f}", f_pt, color)
        d.line(pts, fill=color, width=5)

    d.text((left, 720), "说明：两条曲线均为按时完成订单占全部订单的百分比。", font=f_axis, fill="#555555")
    out = os.path.join(OUT, "M1_折线图.png")
    img.save(out)
    print("saved", out)


def m2_occlusion():
    W, H = 1200, 800
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    # Background floor hints (very light grid so counting is unambiguous)
    for x in range(0, W, 100):
        d.line([(x, 0), (x, H)], fill="#F2F2F2", width=1)
    for y in range(0, H, 100):
        d.line([(0, y), (W, y)], fill="#F2F2F2", width=1)

    # Red circles (drawn first, then blue square on top)
    # C1: partially covered; C2: fully covered; C3: fully visible
    d.ellipse([360, 250, 540, 430], fill=(220, 50, 50), outline=(150, 20, 20), width=4)
    d.ellipse([560, 350, 700, 490], fill=(220, 50, 50), outline=(150, 20, 20), width=4)
    d.ellipse([840, 280, 1000, 440], fill=(220, 50, 50), outline=(150, 20, 20), width=4)

    # Blue square covering C1 partially and C2 completely
    d.rectangle([500, 300, 760, 560], fill=(50, 90, 200), outline=(30, 55, 140), width=5)

    # Green triangle (left bottom), yellow diamond (right bottom)
    d.polygon([(120, 620), (220, 500), (320, 620)], fill=(60, 160, 70), outline=(30, 100, 40), width=4)
    d.polygon([(980, 700), (1060, 620), (1140, 700), (1060, 780)], fill=(235, 190, 40), outline=(160, 120, 20), width=4)

    out = os.path.join(OUT, "M2_遮挡场景.png")
    img.save(out)
    print("saved", out)


def m3_login_ui():
    W, H = 1100, 1250
    img = Image.new("RGB", (W, H), "#E9ECEF")
    d = ImageDraw.Draw(img)

    card = [150, 140, 950, 1080]
    d.rounded_rectangle(card, radius=24, fill="white", outline="#C9CDD2", width=2)

    f_title = _font_bold(44)
    f_label = _font(18)
    f_input = _font(28)
    f_error = _font(18)
    f_btn = _font_bold(26)
    f_link = _font(20)

    _center_text(d, 550, 230, "Sign In / 登录", f_title, "#1A1A1A")

    # Username label + input
    d.text((230, 360), "用户名 Username", font=f_label, fill="#444444")
    d.rounded_rectangle([230, 400, 870, 470], radius=10, outline="#888888", width=2)
    d.text((250, 418), "请输入用户名", font=f_input, fill="#BBBBBB")

    # Password label + input
    d.text((230, 530), "密码 Password", font=f_label, fill="#444444")
    d.rounded_rectangle([230, 570, 870, 640], radius=10, outline="#888888", width=2)
    d.text((250, 588), "••••••••", font=f_input, fill="#333333")

    # Low-contrast error message (planted defect #1)
    d.text((230, 690), "登录失败，请检查用户名和密码", font=f_error, fill="#DDDDDD")

    # Disabled-looking submit button (planted defect #2)
    d.rounded_rectangle([230, 750, 870, 840], radius=14, fill="#C8C8C8", outline="#AFAFAF", width=2)
    _center_text(d, 550, 795, "登 录", f_btn, "#8F8F8F")

    # Clipped link (planted defect #3): text runs past the card's right edge
    link_text = "忘记密码？ 请联系 support@example.com"
    link_w = d.textlength(link_text, font=f_link)
    d.text((940 - link_w + 40, 890), link_text, font=f_link, fill="#2B5FC4")
    # Erase the part outside the card and restore the card edge
    d.rectangle([950, 880, W, 930], fill="#E9ECEF")
    d.line([(950, 880), (950, 930)], fill="#C9CDD2", width=2)

    # Tiny helper text (planted defect #4: readability)
    d.text((230, 960), "提示：密码至少8位，包含字母和数字。", font=_font(13), fill="#777777")

    out = os.path.join(OUT, "M3_登录界面.png")
    img.save(out)
    print("saved", out)


def m4_park():
    W, H = 1200, 800
    img = Image.new("RGB", (W, H), "#87CEEB")
    d = ImageDraw.Draw(img)

    # Sky and sun
    d.rectangle([0, 0, W, 430], fill="#A7D8F0")
    d.ellipse([1020, 60, 1140, 180], fill="#F7D44B", outline="#E0B72E", width=4)

    # Grass
    d.rectangle([0, 430, W, H], fill="#79B85C")
    for _ in range(120):
        pass  # keep it simple: no random grass blades

    # Tree (trunk + canopy)
    d.rectangle([150, 300, 210, 560], fill="#7A4A22")
    d.ellipse([90, 140, 300, 360], fill="#3E8E4C", outline="#2E6E38", width=4)
    d.ellipse([120, 190, 280, 400], fill="#48A357", outline="#2E6E38", width=4)

    # Bench
    d.rectangle([480, 500, 900, 530], fill="#8B5A2B", outline="#5E3A17", width=3)
    d.rectangle([500, 530, 540, 620], fill="#6F451F", outline="#4A2C12", width=3)
    d.rectangle([840, 530, 880, 620], fill="#6F451F", outline="#4A2C12", width=3)
    for x in range(510, 900, 60):
        d.rectangle([x, 480, x + 8, 500], fill="#9C6B33", outline="#5E3A17", width=2)

    # Orange cat sitting on bench
    d.ellipse([600, 380, 780, 500], fill="#E58B2A", outline="#B86516", width=4)  # body
    d.ellipse([640, 330, 740, 430], fill="#E58B2A", outline="#B86516", width=4)  # head
    d.polygon([(650, 340), (660, 290), (690, 335)], fill="#E58B2A", outline="#B86516", width=3)
    d.polygon([(700, 335), (730, 290), (740, 340)], fill="#E58B2A", outline="#B86516", width=3)
    d.ellipse([690, 380, 740, 500], fill="#D87B20", outline="#B86516", width=3)  # tail

    out = os.path.join(OUT, "M4_公园场景.png")
    img.save(out)
    print("saved", out)


def m5_table():
    W, H = 1150, 800
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f_title = _font_bold(32)
    f_head = _font_bold(24)
    f_cell = _font(24)

    d.text((60, 30), "2026 年产品线收入（万元）", font=f_title, fill="#111111")

    cols = [260, 190, 190, 190, 190, 200]  # 产品线 + Q1..Q4 + 全年合计
    rows_y = [160, 280, 400, 520]
    x0 = 60
    xs = [x0]
    for w in cols:
        xs.append(xs[-1] + w)
    y0 = rows_y[0]

    headers = ["产品线", "Q1", "Q2", "Q3", "Q4", "全年合计"]
    for i, h in enumerate(headers):
        _center_text(d, (xs[i] + xs[i + 1]) / 2, y0 + 60, h, f_head, "#111111")

    data = [
        ["智能硬件", "120", "145", "130", "160", "555"],
        ["软件服务", "80", "95", "110", "125", "410"],
    ]
    for r, row in enumerate(data):
        cy = rows_y[1 + r] + 60
        for i, v in enumerate(row):
            _center_text(d, (xs[i] + xs[i + 1]) / 2, cy, v, f_cell, "#111111")

    # Total row: label + merged cell spanning Q1..Q4 with "965"
    ty = rows_y[3] + 60
    _center_text(d, (xs[0] + xs[1]) / 2, ty, "总计", f_head, "#111111")
    merged = [xs[1], xs[5]]
    _center_text(d, (merged[0] + merged[1]) / 2, ty, "965", f_head, "#111111")

    # Borders
    for x in xs:
        d.line([(x, rows_y[0]), (x, rows_y[-1] + 120)], fill="#555555", width=2)
    for y in [rows_y[0], rows_y[1], rows_y[2], rows_y[3], rows_y[-1] + 120]:
        d.line([(x0, y), (xs[-1], y)], fill="#555555", width=2)
    # Inner horizontal lines
    for y in rows_y[2:4]:
        d.line([(x0, y), (xs[-1], y)], fill="#BBBBBB", width=1)
    # Vertical lines inside the header/data rows only (merged cell stays clean)
    for x in xs[1:5]:
        d.line([(x, rows_y[0]), (x, rows_y[3])], fill="#BBBBBB", width=1)

    out = os.path.join(OUT, "M5_合并表格.png")
    img.save(out)
    print("saved", out)


def mm2_handwritten_table():
    W, H = 1400, 1000
    img = Image.new("RGB", (W, H), "#F5F0DF")
    d = ImageDraw.Draw(img)
    f_title = _font_handwritten(48, bold=True)
    f_head = _font_bold(27)
    f_hand = _font_handwritten(34)
    f_small = _font_handwritten(27)

    # Paper texture and a slightly imperfect hand-drawn grid.
    for y in range(95, H, 42):
        d.line([(40, y), (W - 40, y + 2)], fill="#D8E0DE", width=1)
    d.line([(72, 80), (72, H - 55)], fill="#DFA5A5", width=2)

    _hand_text(img, (445, 42), "周末露营采购单", f_title, "#173C69", angle=-1.2)
    _hand_text(img, (1040, 75), "6月14日  小林", f_small, "#173C69", angle=1.0)

    x0, y0 = 82, 150
    col_widths = [92, 240, 170, 180, 190, 360]
    xs = [x0]
    for width in col_widths:
        xs.append(xs[-1] + width)
    row_h = 84
    rows = len(MM2_ROWS) + 1
    bottom = y0 + rows * row_h

    for i, x in enumerate(xs):
        wobble = (i % 3) - 1
        d.line([(x, y0 + wobble), (x + wobble, bottom)], fill="#6F8290", width=2)
    for i in range(rows + 1):
        y = y0 + i * row_h
        wobble = (i % 2) * 2 - 1
        d.line([(x0, y), (xs[-1], y + wobble)], fill="#6F8290", width=2)

    headers = ["序号", "物品", "数量", "单价(元)", "小计(元)", "备注"]
    for i, header in enumerate(headers):
        _center_text(d, (xs[i] + xs[i + 1]) / 2, y0 + row_h / 2, header, f_head, "#243746")

    angles = [-1.5, 0.8, -0.6, 1.1, -0.9, 0.5, -1.0]
    for row_index, row in enumerate(MM2_ROWS, start=1):
        y = y0 + row_index * row_h
        cy = y + row_h / 2
        _center_text(d, (xs[0] + xs[1]) / 2, cy, str(row_index), f_hand, "#173C69")

        item_xy = (xs[1] + 24, y + 19)
        if row_index == 6:
            # The second character is intentionally covered so a model should preserve uncertainty.
            _hand_text(img, item_xy, row["item"], f_hand, "#173C69", angle=angles[row_index - 1])
            scribble_x = xs[1] + 64
            scribble_y = y + 35
            for offset in (0, 5, 11, 16):
                d.line(
                    [(scribble_x - 3, scribble_y + offset), (scribble_x + 42, scribble_y - 6 + offset)],
                    fill="#173C69",
                    width=5,
                )
        else:
            _hand_text(img, item_xy, row["item"], f_hand, "#173C69", angle=angles[row_index - 1])

        if row_index == 5:
            # Original "3" was crossed out and corrected to "2包".
            _hand_text(img, (xs[2] + 22, y + 21), "3", f_hand, "#173C69", angle=-1.0)
            d.line([(xs[2] + 16, y + 52), (xs[2] + 63, y + 30)], fill="#B43A3A", width=4)
            _hand_text(img, (xs[2] + 76, y + 10), "2包", f_hand, "#173C69", angle=1.2)
        else:
            _hand_text(img, (xs[2] + 18, y + 19), row["quantity_text"], f_hand, "#173C69", angle=-angles[row_index - 1])

        unit_price = f"{row['unit_price']:g}"
        subtotal = f"{row['subtotal']:g}"
        _hand_text(img, (xs[3] + 38, y + 19), unit_price, f_hand, "#173C69", angle=angles[row_index - 1])
        _hand_text(img, (xs[4] + 38, y + 19), subtotal, f_hand, "#173C69", angle=-angles[row_index - 1])
        if row["note"]:
            _hand_text(img, (xs[5] + 22, y + 21), row["note"], f_small, "#173C69", angle=angles[row_index - 1] / 2)

    d.rounded_rectangle([850, 855, 1315, 950], radius=12, outline="#B43A3A", width=3)
    _hand_text(
        img,
        (910, 865),
        f"合计：￥{MM2_WRITTEN_TOTAL:.1f}",
        _font_handwritten(40, bold=True),
        "#B43A3A",
        angle=-0.8,
    )
    _hand_text(img, (90, 880), MM2_FOOTNOTE, f_small, "#173C69", angle=0.6)

    out = os.path.join(OUT, "MM2_手写表格.png")
    img.save(out)
    print("saved", out)


def mm3_complex_chart():
    W, H = 1500, 1000
    img = Image.new("RGB", (W, H), "#FBFAF5")
    d = ImageDraw.Draw(img)
    f_title = _font_bold(38)
    f_axis = _font(22)
    f_label = _font_bold(21)
    f_note = _font(20)

    d.text((86, 32), "门店月度销售额与退货率（2026年1—6月）", font=f_title, fill="#172B3A")

    left, right, top, bottom = 120, 1375, 175, 760
    sales_min, sales_max = MM3_SALES_AXIS_MIN, MM3_SALES_AXIS_MAX
    rate_min, rate_max = 0, 4

    def x_for(index):
        return left + (index + 0.5) * (right - left) / len(MM3_MONTHS)

    def sales_y(value):
        return bottom - (value - sales_min) / (sales_max - sales_min) * (bottom - top)

    def rate_y(value):
        return bottom - (value - rate_min) / (rate_max - rate_min) * (bottom - top)

    for value in range(sales_min, sales_max + 1, 5):
        y = sales_y(value)
        d.line([(left, y), (right, y)], fill="#D6D9D6", width=1)
        _center_text(d, left - 52, y, str(value), f_axis, "#40525E")
    for value in range(rate_min, rate_max + 1):
        _center_text(d, right + 47, rate_y(value), f"{value}%", f_axis, "#A33131")

    d.line([(left, top), (left, bottom)], fill="#52636D", width=2)
    d.line([(right, top), (right, bottom)], fill="#52636D", width=2)
    d.line([(left, bottom), (right, bottom)], fill="#52636D", width=2)
    d.text((32, 138), "销售额（万元）", font=f_axis, fill="#40525E")
    d.text((1288, 138), "退货率", font=f_axis, fill="#A33131")

    for index, month in enumerate(MM3_MONTHS):
        x = x_for(index)
        d.line([(x, bottom), (x, bottom + 8)], fill="#52636D", width=2)
        _center_text(d, x, bottom + 32, month, f_axis, "#40525E")

    # Forecast interval is only present for April-June.
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    od = ImageDraw.Draw(overlay)
    upper = [(x_for(i), sales_y(MM3_FORECAST_HIGH[i])) for i in range(3, 6)]
    lower = [(x_for(i), sales_y(MM3_FORECAST_LOW[i])) for i in range(5, 2, -1)]
    od.polygon(upper + lower, fill=(225, 154, 56, 55))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(img)

    forecast_points = [(x_for(i), sales_y(value)) for i, value in enumerate(MM3_FORECAST)]
    for p1, p2 in zip(forecast_points, forecast_points[1:]):
        _dashed_line(d, p1, p2, "#D9822B", width=4)
    for index, (x, y) in enumerate(forecast_points):
        d.rectangle([x - 6, y - 6, x + 6, y + 6], fill="#D9822B")
        label_y = y - 25 if index == 5 else y + 24
        _center_text(d, x, label_y, str(MM3_FORECAST[index]), f_label, "#B6631D")

    # Actual values are not connected across the missing May point.
    actual_segments = [(0, 1), (1, 2), (2, 3)]
    for start_index, end_index in actual_segments:
        d.line(
            [
                (x_for(start_index), sales_y(MM3_ACTUAL[start_index])),
                (x_for(end_index), sales_y(MM3_ACTUAL[end_index])),
            ],
            fill="#245B91",
            width=5,
        )
    for index, value in enumerate(MM3_ACTUAL):
        x = x_for(index)
        if value is None:
            y = sales_y(MM3_MISSING_MARKER_VALUE)
            d.ellipse([x - 10, y - 10, x + 10, y + 10], outline="#7D858A", width=3)
            _center_text(d, x, y - 28, "缺失", f_label, "#616A70")
            continue
        y = sales_y(value)
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill="#245B91")
        label_y = y + 24 if index == 5 else y - 25
        _center_text(d, x, label_y, str(value), f_label, "#17466F")

    rate_points = [(x_for(i), rate_y(value)) for i, value in enumerate(MM3_RETURN_RATE)]
    d.line(rate_points, fill="#B83B3B", width=4)
    for index, (x, y) in enumerate(rate_points):
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill="#B83B3B")
        _center_text(d, x, y - 24, f"{MM3_RETURN_RATE[index]:.1f}%", f_label, "#A33131")

    # Legend.
    legend_y = 108
    d.line([(460, legend_y), (515, legend_y)], fill="#245B91", width=5)
    d.text((525, legend_y - 15), "实际销售额", font=f_axis, fill="#172B3A")
    _dashed_line(d, (705, legend_y), (760, legend_y), "#D9822B", width=4)
    d.text((770, legend_y - 15), "预测销售额", font=f_axis, fill="#172B3A")
    d.line([(965, legend_y), (1020, legend_y)], fill="#B83B3B", width=4)
    d.text((1030, legend_y - 15), "退货率", font=f_axis, fill="#172B3A")
    d.rectangle([1165, legend_y - 10, 1215, legend_y + 10], fill="#F0D7B6")
    d.text((1225, legend_y - 15), "预测区间", font=f_axis, fill="#172B3A")

    d.text((120, 840), MM3_CHART_NOTE, font=f_note, fill="#4C5D67")

    out = os.path.join(OUT, "MM3_复杂图表.png")
    img.save(out)
    print("saved", out)


def mm4_engineering_sketch():
    W, H = 1500, 1000
    img = Image.new("RGB", (W, H), "#F7FBFC")
    d = ImageDraw.Draw(img)
    f_title = _font_bold(38)
    f_view = _font_bold(28)
    f_dim = _font(22)
    f_note = _font(20)
    ink = "#214F66"
    dim = "#59798A"
    light = "#B8CDD6"

    d.text((72, 35), "墙面层板支架示意图（单位：mm）", font=f_title, fill="#163C4F")
    d.text((185, 115), "正视图", font=f_view, fill=ink)
    d.text((920, 115), "侧视图", font=f_view, fill=ink)
    d.line([(745, 100), (745, 850)], fill=light, width=2)

    # Front view: 60 x 360 mounting plate with three Ø10 holes.
    plate_left, plate_top = 300, 205
    plate_right, plate_bottom = 420, 745
    d.rectangle([plate_left, plate_top, plate_right, plate_bottom], outline=ink, width=5)
    hole_ys = [295, 475, 655]
    for y in hole_ys:
        d.ellipse([345, y - 15, 375, y + 15], outline=ink, width=4)
        d.line([(338, y), (382, y)], fill=light, width=1)
        d.line([(360, y - 22), (360, y + 22)], fill=light, width=1)
    d.text((445, 276), "3 × 直径10 通孔", font=f_dim, fill=ink)

    # Plate width.
    d.line([(plate_left, 785), (plate_left, 835)], fill=dim, width=2)
    d.line([(plate_right, 785), (plate_right, 835)], fill=dim, width=2)
    _double_arrow(d, (plate_left, 815), (plate_right, 815), fill=dim)
    _center_text(d, 360, 850, "60", f_dim, dim)

    # Plate height.
    d.line([(245, plate_top), (285, plate_top)], fill=dim, width=2)
    d.line([(245, plate_bottom), (285, plate_bottom)], fill=dim, width=2)
    _double_arrow(d, (260, plate_top), (260, plate_bottom), fill=dim)
    d.text((190, 455), "360", font=f_dim, fill=dim)

    # Hole center spacing.
    d.line([(455, hole_ys[0]), (520, hole_ys[0])], fill=dim, width=2)
    d.line([(455, hole_ys[1]), (520, hole_ys[1])], fill=dim, width=2)
    d.line([(455, hole_ys[2]), (520, hole_ys[2])], fill=dim, width=2)
    _double_arrow(d, (495, hole_ys[0]), (495, hole_ys[1]), fill=dim)
    _double_arrow(d, (495, hole_ys[1]), (495, hole_ys[2]), fill=dim)
    d.text((515, 370), "120", font=f_dim, fill=dim)
    d.text((515, 550), "120", font=f_dim, fill=dim)

    # Side view: wall plate, horizontal support, and diagonal brace.
    wall_x = 875
    d.line([(wall_x - 18, 185), (wall_x - 18, 770)], fill="#8FA8B3", width=8)
    d.rectangle([wall_x, 215, wall_x + 34, 745], outline=ink, width=5)
    arm_end = 1285
    d.rectangle([wall_x + 34, 250, arm_end, 285], outline=ink, width=5)
    d.polygon(
        [
            (wall_x + 34, 675),
            (wall_x + 62, 695),
            (1180, 285),
            (1142, 285),
        ],
        outline=ink,
        fill="#E9F2F5",
    )

    # 280 mm effective support depth.
    d.line([(wall_x + 34, 315), (wall_x + 34, 360)], fill=dim, width=2)
    d.line([(arm_end, 315), (arm_end, 360)], fill=dim, width=2)
    _double_arrow(d, (wall_x + 34, 345), (arm_end, 345), fill=dim)
    _center_text(d, (wall_x + 34 + arm_end) / 2, 377, "有效支撑深度 280", f_dim, dim)

    # Candidate shelf is intentionally 20 mm deeper than the support.
    shelf_end = 1315
    d.rectangle(
        [wall_x + 34, 190, shelf_end, 235],
        outline="#C46B3B",
        width=3,
    )
    for x in range(wall_x + 34, shelf_end, 22):
        d.line([(x, 190), (min(x + 14, shelf_end), 235)], fill="#E2A17D", width=2)
    d.text((1000, 155), "拟安装层板：深 300", font=f_dim, fill="#A14F25")

    d.line([(wall_x + 34, 790), (wall_x + 34, 835)], fill=dim, width=2)
    d.line([(shelf_end, 790), (shelf_end, 835)], fill=dim, width=2)
    _double_arrow(d, (wall_x + 34, 815), (shelf_end, 815), fill=dim)
    _center_text(d, (wall_x + 34 + shelf_end) / 2, 850, "300", f_dim, dim)

    d.rounded_rectangle([80, 890, 1420, 955], radius=10, outline=light, width=2)
    d.text(
        (105, 910),
        MM4_DRAWING_NOTE,
        font=f_note,
        fill="#385D6F",
    )

    out = os.path.join(OUT, "MM4_工程草图.png")
    img.save(out)
    print("saved", out)


if __name__ == "__main__":
    m1_chart()
    m2_occlusion()
    m3_login_ui()
    m4_park()
    m5_table()
    mm2_handwritten_table()
    mm3_complex_chart()
    mm4_engineering_sketch()
