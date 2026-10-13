"""没有提供 IP 图片时，画一只戴工牌的示例橘猫，并返回嘴巴/眼睛位置。"""

from PIL import Image, ImageDraw, ImageFilter

W, H = 1000, 1250
MOUTH = [0.50, 0.487, 0.12, 0.04]
EYES = [[0.395, 0.405, 0.075, 0.065], [0.605, 0.405, 0.075, 0.065]]

ORANGE, LIGHT, DARK = (243, 156, 64), (255, 226, 184), (196, 106, 30)


def draw(path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    d.ellipse([200, 640, 800, 1250], fill=ORANGE)
    d.ellipse([320, 760, 680, 1250], fill=LIGHT)
    d.polygon([(470, 700), (530, 700), (560, 1000), (500, 1060), (440, 1000)], fill=(52, 92, 168))
    d.polygon([(455, 660), (545, 660), (530, 712), (470, 712)], fill=(40, 72, 140))
    d.rounded_rectangle([580, 860, 720, 1020], 14, fill=(255, 255, 255), outline=(90, 90, 90), width=5)
    d.rectangle([600, 880, 700, 930], fill=(120, 170, 230))
    d.line([(650, 860), (560, 700)], fill=(200, 50, 50), width=8)

    for side in (-1, 1):
        cx = 500 + side * 230
        d.polygon([(cx - side * 120, 300), (cx + side * 60, 90), (cx + side * 90, 380)], fill=ORANGE)
        d.polygon([(cx - side * 60, 300), (cx + side * 50, 160), (cx + side * 65, 340)], fill=(250, 180, 170))

    d.ellipse([150, 200, 850, 780], fill=ORANGE)
    for x0 in (420, 480, 540):
        d.polygon([(x0, 205), (x0 + 40, 205), (x0 + 20, 300)], fill=DARK)
    d.ellipse([330, 470, 670, 760], fill=LIGHT)

    for (cx, cy, w, h) in EYES:
        x, y, ew, eh = cx * W, cy * H, w * W, h * H
        d.ellipse([x - ew / 2, y - eh / 2, x + ew / 2, y + eh / 2], fill=(40, 30, 30))
        d.ellipse([x - ew / 6, y - eh / 3, x + ew / 8, y - eh / 12], fill=(255, 255, 255))

    d.polygon([(475, 575), (525, 575), (500, 605)], fill=(230, 110, 120))
    d.arc([440, 590, 502, 640], 0, 180, fill=(80, 40, 30), width=6)
    d.arc([498, 590, 560, 640], 0, 180, fill=(80, 40, 30), width=6)
    for side in (-1, 1):
        d.ellipse([500 + side * 230 - 45, 590, 500 + side * 230 + 45, 640], fill=(250, 150, 140, 160))
        for dy in (-15, 15):
            d.line([(500 + side * 130, 600 + dy), (500 + side * 320, 585 + dy * 2)], fill=(90, 60, 40), width=4)

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([180, 1180, 820, 1250], fill=(0, 0, 0, 90))
    out = Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(12)), img)
    out.save(path)
    return MOUTH, EYES
