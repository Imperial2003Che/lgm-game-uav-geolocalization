# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path("outputs") / "VLGeo云层遮蔽暗光" / "figures_redrawn_from_paper"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


F_TITLE = font(34, True)
F_SUB = font(20)
F_HEAD = font(22, True)
F_BODY = font(18)
F_SMALL = font(15)
F_TINY = font(13)


PALETTE = {
    "ink": (27, 38, 59),
    "muted": (93, 105, 126),
    "line": (78, 93, 117),
    "blue": (219, 239, 255),
    "blue_line": (31, 138, 206),
    "green": (224, 246, 236),
    "green_line": (16, 157, 120),
    "orange": (255, 240, 214),
    "orange_line": (237, 138, 31),
    "purple": (239, 229, 255),
    "purple_line": (128, 72, 212),
    "gray": (246, 248, 251),
    "gray_line": (172, 183, 197),
    "red": (255, 230, 224),
    "red_line": (230, 86, 64),
}


def rounded(draw: ImageDraw.ImageDraw, box, fill, outline, radius=18, width=3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_center(draw: ImageDraw.ImageDraw, box, lines, fnt=F_BODY, fill=None, spacing=6):
    fill = fill or PALETTE["ink"]
    if isinstance(lines, str):
        lines = lines.split("\n")
    heights = [draw.textbbox((0, 0), line, font=fnt)[3] for line in lines]
    total_h = sum(heights) + spacing * (len(lines) - 1)
    y = box[1] + (box[3] - box[1] - total_h) / 2
    for line, h in zip(lines, heights):
        bbox = draw.textbbox((0, 0), line, font=fnt)
        x = box[0] + (box[2] - box[0] - (bbox[2] - bbox[0])) / 2
        draw.text((x, y), line, font=fnt, fill=fill)
        y += h + spacing


def draw_arrow(draw: ImageDraw.ImageDraw, start, end, color=None, width=4, bend=None):
    color = color or PALETTE["line"]
    if bend is None:
        draw.line([start, end], fill=color, width=width)
    else:
        draw.line([start, bend, end], fill=color, width=width, joint="curve")
    x1, y1 = end
    x0, y0 = bend if bend is not None else start
    dx, dy = x1 - x0, y1 - y0
    if abs(dx) >= abs(dy):
        sign = 1 if dx >= 0 else -1
        pts = [(x1, y1), (x1 - 14 * sign, y1 - 8), (x1 - 14 * sign, y1 + 8)]
    else:
        sign = 1 if dy >= 0 else -1
        pts = [(x1, y1), (x1 - 8, y1 - 14 * sign), (x1 + 8, y1 - 14 * sign)]
    draw.polygon(pts, fill=color)


def pseudo_image(draw: ImageDraw.ImageDraw, box, seed=0, dark=False):
    base = (52, 66, 83) if dark else (204, 220, 229)
    draw.rounded_rectangle(box, radius=12, fill=base, outline=(90, 103, 120), width=2)
    x0, y0, x1, y1 = box
    colors = [
        (92, 132, 157), (126, 157, 111), (196, 170, 116),
        (143, 98, 104), (88, 104, 139), (180, 192, 201)
    ]
    for i in range(7):
        x = x0 + 12 + ((i * 37 + seed * 29) % max(20, x1 - x0 - 50))
        y = y0 + 12 + ((i * 31 + seed * 17) % max(20, y1 - y0 - 50))
        w = 24 + ((i + seed) % 3) * 16
        h = 18 + ((i * 2 + seed) % 4) * 10
        c = colors[(i + seed) % len(colors)]
        if dark:
            c = tuple(max(20, int(v * 0.55)) for v in c)
        draw.rectangle((x, y, min(x + w, x1 - 8), min(y + h, y1 - 8)), fill=c, outline=(238, 242, 245), width=1)
    if dark:
        overlay = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 60))
        return overlay
    return None


def draw_fig5():
    W, H = 2200, 1280
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    d.text((70, 50), "图5  暗光鲁棒的多模态特征融合与语义门控网络", font=F_TITLE, fill=PALETTE["ink"])
    d.text((72, 96), "面向云层遮蔽暗光场景：加入遮蔽评分 α、增强掩码 Mu 与语义修复门控 g，形成可计算的跨视角检索闭环。", font=F_SUB, fill=PALETTE["muted"])

    # Input cards
    inputs = [
        ((90, 190, 430, 340), "无人机实时图像 Iu", "云层/薄雾/阴雨\n低亮度、低对比度", PALETTE["orange"], PALETTE["orange_line"]),
        ((90, 465, 430, 615), "卫星候选图像 Is", "俯视视角\n多季节、多分辨率", PALETTE["blue"], PALETTE["blue_line"]),
        ((90, 740, 430, 890), "卫星三元组文本 Ts", "目标地物 / 可见属性\n空间关系", PALETTE["green"], PALETTE["green_line"]),
    ]
    for box, title, body, fill, line in inputs:
        rounded(d, box, fill, line)
        text_center(d, (box[0], box[1] + 10, box[2], box[1] + 58), title, F_HEAD)
        text_center(d, (box[0] + 10, box[1] + 62, box[2] - 10, box[3] - 10), body, F_BODY, fill=PALETTE["muted"])

    # Branch modules
    modules = [
        ((560, 170, 865, 295), "遮蔽暗光感知", "亮度/对比度/暗区比例\n边缘响应/雾化指标 → α", PALETTE["orange"], PALETTE["orange_line"]),
        ((560, 315, 865, 440), "自适应暗光增强", "Mu 控制局部增强\n保留边缘、抑制伪影", PALETTE["orange"], PALETTE["orange_line"]),
        ((560, 495, 865, 620), "CLIP ViT-B", "卫星视觉特征 Fs", PALETTE["blue"], PALETTE["blue_line"]),
        ((560, 770, 865, 895), "BERT 文本编码", "光照不变语义 Ft", PALETTE["green"], PALETTE["green_line"]),
    ]
    for box, title, body, fill, line in modules:
        rounded(d, box, fill, line, radius=16)
        text_center(d, (box[0], box[1] + 8, box[2], box[1] + 52), title, F_HEAD)
        text_center(d, (box[0] + 8, box[1] + 56, box[2] - 8, box[3] - 8), body, F_SMALL, fill=PALETTE["muted"])

    rounded(d, (965, 235, 1325, 410), PALETTE["blue"], PALETTE["blue_line"], radius=18)
    text_center(d, (965, 250, 1325, 305), "无人机视觉双分支", F_HEAD)
    text_center(d, (985, 305, 1305, 395), "Fu0 = 原始特征\nFue = 增强特征", F_BODY, fill=PALETTE["muted"])

    fusion_box = (1040, 520, 1510, 825)
    rounded(d, fusion_box, PALETTE["purple"], PALETTE["purple_line"], radius=22, width=4)
    text_center(d, (fusion_box[0], fusion_box[1] + 18, fusion_box[2], fusion_box[1] + 75), "语义引导特征修复门控", F_HEAD)
    text_center(d, (fusion_box[0] + 20, fusion_box[1] + 88, fusion_box[2] - 20, fusion_box[3] - 72),
                "g = σ(Wg[Fu0; Fue; Ft; α] + bg)\n暗光强时提高文本语义校正权重\n暗光弱时保留更多增强视觉特征", F_BODY, fill=PALETTE["ink"], spacing=11)
    rounded(d, (1115, 755, 1435, 810), (250, 245, 255), PALETTE["purple_line"], radius=10, width=2)
    text_center(d, (1115, 755, 1435, 810), "输出修复特征 Fr", F_BODY, fill=PALETTE["purple_line"])

    align_box = (1610, 265, 2030, 790)
    rounded(d, align_box, PALETTE["gray"], PALETTE["gray_line"], radius=22, width=3)
    text_center(d, (align_box[0], align_box[1] + 20, align_box[2], align_box[1] + 76), "跨视角对齐与检索", F_HEAD)
    smalls = [
        ((1660, 365, 1980, 430), "图像-图像 InfoNCE"),
        ((1660, 455, 1980, 520), "图像-文本 InfoNCE"),
        ((1660, 545, 1980, 610), "修复一致性 Lcon"),
        ((1660, 635, 1980, 700), "MLP 融合与 Top-K 排序"),
    ]
    for b, lab in smalls:
        rounded(d, b, "white", PALETTE["gray_line"], radius=10, width=2)
        text_center(d, b, lab, F_BODY)

    rounded(d, (1620, 900, 2025, 1050), PALETTE["green"], PALETTE["green_line"], radius=18, width=4)
    text_center(d, (1620, 912, 2025, 968), "输出", F_HEAD)
    text_center(d, (1640, 968, 2005, 1038), "Top-K 卫星候选图像\n及其地理坐标", F_BODY, fill=PALETTE["muted"])

    # Arrows
    draw_arrow(d, (430, 265), (560, 232), PALETTE["orange_line"])
    draw_arrow(d, (865, 232), (1035, 285), PALETTE["orange_line"], bend=(940, 232))
    draw_arrow(d, (865, 378), (965, 350), PALETTE["orange_line"])
    draw_arrow(d, (430, 540), (560, 557), PALETTE["blue_line"])
    draw_arrow(d, (865, 557), (1040, 610), PALETTE["blue_line"], bend=(940, 557))
    draw_arrow(d, (430, 815), (560, 832), PALETTE["green_line"])
    draw_arrow(d, (865, 832), (1040, 720), PALETTE["green_line"], bend=(960, 832))
    draw_arrow(d, (1325, 322), (1510, 600), PALETTE["blue_line"], bend=(1460, 322))
    draw_arrow(d, (1510, 670), (1610, 520), PALETTE["purple_line"])
    draw_arrow(d, (1510, 745), (1610, 610), PALETTE["purple_line"])
    draw_arrow(d, (2030, 705), (1825, 900), PALETTE["green_line"], bend=(2100, 850))

    # Innovation strip
    strip = (90, 1105, 2030, 1205)
    rounded(d, strip, (248, 250, 253), (205, 214, 226), radius=16, width=2)
    d.text((120, 1130), "核心创新：", font=F_HEAD, fill=PALETTE["ink"])
    d.text((255, 1134), "不再仅做常规图文融合；新增暗光遮蔽评分 α、增强掩码 Mu、语义修复门控 g 和一致性约束，专门处理云层遮蔽导致的无人机暗光退化。", font=F_BODY, fill=PALETTE["muted"])

    path = OUT_DIR / "redrawn_fig5_darklight_multimodal_fusion.png"
    img.save(path)
    return path


def draw_fig6():
    W, H = 2200, 1280
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((70, 50), "图6  暗光无人机图像的 Top-K 检索与候选验证示意", font=F_TITLE, fill=PALETTE["ink"])
    d.text((72, 96), "本发明的工程流程示意：强调暗光评分驱动的增强、语义修复和候选重排序。", font=F_SUB, fill=PALETTE["muted"])

    cols = [
        (130, 240, "输入无人机暗光图像", PALETTE["orange"], PALETTE["orange_line"]),
        (575, 240, "候选卫星图像库", PALETTE["blue"], PALETTE["blue_line"]),
        (1080, 240, "语义/结构一致性验证", PALETTE["purple"], PALETTE["purple_line"]),
        (1620, 240, "Top-K 输出", PALETTE["green"], PALETTE["green_line"]),
    ]
    for x, y, title, fill, line in cols:
        rounded(d, (x, y - 85, x + 360, y - 15), fill, line, radius=14)
        text_center(d, (x, y - 85, x + 360, y - 15), title, F_HEAD)

    # UAV queries
    query_boxes = []
    for i, label in enumerate(["Q1 云层遮蔽", "Q2 薄雾低对比", "Q3 阴雨暗光"]):
        y = 245 + i * 235
        b = (150, y, 455, y + 150)
        query_boxes.append(b)
        pseudo_image(d, b, seed=i + 1, dark=True)
        rounded(d, (170, y + 108, 435, y + 190), (255, 248, 236), PALETTE["orange_line"], radius=12, width=2)
        text_center(d, (170, y + 112, 435, y + 148), label, F_BODY)
        text_center(d, (170, y + 148, 435, y + 186), "α↑  Mu↑  需语义修复", F_SMALL, fill=PALETTE["muted"])

    # Candidate gallery tiles
    for row in range(3):
        for col in range(4):
            x = 565 + col * 110
            y = 250 + row * 195
            pseudo_image(d, (x, y, x + 82, y + 82), seed=row * 4 + col, dark=False)
            d.text((x + 6, y + 92), f"S{row*4+col+1}", font=F_TINY, fill=PALETTE["muted"])
    rounded(d, (550, 835, 1010, 930), (248, 250, 253), PALETTE["gray_line"], radius=14, width=2)
    text_center(d, (560, 845, 1000, 920), "离线缓存：卫星视觉特征 Fs + 三元组文本语义 Ft", F_BODY, fill=PALETTE["muted"])

    # Verification matrix
    metric_labels = ["道路骨架", "建筑布局", "水体/植被边界", "暗光鲁棒分数"]
    for i, lab in enumerate(metric_labels):
        y = 260 + i * 110
        rounded(d, (1085, y, 1460, y + 72), "white", PALETTE["purple_line"], radius=12, width=2)
        d.text((1110, y + 18), lab, font=F_BODY, fill=PALETTE["ink"])
        for k in range(5):
            bar_x = 1285 + k * 28
            h = 18 + ((i + k * 2) % 4) * 9
            d.rectangle((bar_x, y + 48 - h, bar_x + 16, y + 48), fill=PALETTE["purple_line"])
    rounded(d, (1095, 760, 1465, 900), PALETTE["purple"], PALETTE["purple_line"], radius=14, width=3)
    text_center(d, (1110, 775, 1450, 835), "重排序得分", F_HEAD)
    text_center(d, (1110, 835, 1450, 890), "S(u,s) + 语义一致性 + 暗光置信度", F_SMALL, fill=PALETTE["muted"])

    # Top-K output
    topk = [
        ("Top-1", 0.92, PALETTE["green_line"]),
        ("Top-2", 0.86, PALETTE["blue_line"]),
        ("Top-3", 0.79, PALETTE["orange_line"]),
        ("Top-4", 0.68, PALETTE["gray_line"]),
        ("Top-5", 0.61, PALETTE["gray_line"]),
    ]
    for i, (name, score, color) in enumerate(topk):
        y = 260 + i * 120
        rounded(d, (1635, y, 1985, y + 82), "white", color, radius=13, width=3)
        d.text((1660, y + 18), name, font=F_HEAD, fill=PALETTE["ink"])
        d.rectangle((1760, y + 27, 1935, y + 47), fill=(238, 242, 247), outline=(210, 216, 224))
        d.rectangle((1760, y + 27, int(1760 + 175 * score), y + 47), fill=color)
        d.text((1945, y + 22), f"{score:.2f}", font=F_SMALL, fill=PALETTE["muted"])
    rounded(d, (1635, 900, 1985, 1028), PALETTE["green"], PALETTE["green_line"], radius=15, width=3)
    text_center(d, (1650, 912, 1970, 970), "输出地理位置", F_HEAD)
    text_center(d, (1650, 970, 1970, 1018), "卫星候选坐标 + 置信度\n供应急巡检/导航使用", F_SMALL, fill=PALETTE["muted"])

    # Cross-column arrows
    for b in query_boxes:
        draw_arrow(d, (455, (b[1] + b[3]) // 2), (565, (b[1] + b[3]) // 2), PALETTE["line"])
    draw_arrow(d, (1010, 450), (1085, 405), PALETTE["line"])
    draw_arrow(d, (1465, 830), (1635, 935), PALETTE["purple_line"])
    draw_arrow(d, (1460, 405), (1635, 300), PALETTE["green_line"])

    # Bottom notes
    rounded(d, (120, 1100, 2030, 1208), (248, 250, 253), (205, 214, 226), radius=16, width=2)
    d.text((150, 1128), "说明：", font=F_HEAD, fill=PALETTE["ink"])
    d.text((230, 1132), "候选图块为示意化绘制，用于说明暗光条件下的检索、验证和输出关系；输出结果按重排序得分形成 Top-K 候选位置。", font=F_BODY, fill=PALETTE["muted"])

    path = OUT_DIR / "redrawn_fig6_topk_retrieval_validation.png"
    img.save(path)
    return path


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [draw_fig5(), draw_fig6()]
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
