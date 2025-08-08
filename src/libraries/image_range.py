import base64, os, requests, random
from pathlib import Path
from io import BytesIO

from PIL import ImageFont, ImageDraw, Image

from src.libraries.april_fool import is_April_1st, kun_jin_kao

fontpath = "src/static/msyh.ttc"
cover_dir = 'src/static/mai/cover/'

Root: Path = Path('src')
static: Path = Root / 'static'

def get_cover_len5_id(mid) -> str:
    mid = int(mid)
    if mid < 100000:
        return f'{int(mid):05d}'
    else:
        mid = mid % 100000
        if mid >= 20000:
            return f'{(10000 + mid % 10000):05d}'
        else:
            return f'{mid:05d}'

def draw_text(img_pil, text, offset_x):
    draw = ImageDraw.Draw(img_pil)
    font = ImageFont.truetype(fontpath, 48)
    width, height = draw.textsize(text, font)
    x = 5
    if width > 390:
        font = ImageFont.truetype(fontpath, int(390 * 48 / width))
        width, height = draw.textsize(text, font)
    else:
        x = int((400 - width) / 2)
    draw.rectangle((x + offset_x - 2, 360, x + 2 + width + offset_x, 360 + height * 1.2), fill=(0, 0, 0, 255))
    draw.text((x + offset_x, 360), text, font=font, fill=(255, 255, 255, 255))


def text_to_image(text:str)->Image:
    if is_April_1st():
        text = kun_jin_kao(text)
    text = text.replace(' ', '  ')
    font = ImageFont.truetype(fontpath, 24)
    padding = 10
    margin = 4
    text_list = text.split('\n')
    max_width = 0
    max_height = 0
    for text in text_list:
        text_bbox = font.getbbox(text)
        w, h = text_bbox[2], text_bbox[3]
        max_width = max(max_width, w)
        max_height = max(max_height, h)
    h = max_height
    wa = max_width + padding * 2
    ha = h * len(text_list) + margin * (len(text_list) - 1) + padding * 2
    i = Image.new('RGB', (wa, ha), color=(255, 255, 255))
    draw = ImageDraw.Draw(i)
    for j in range(len(text_list)):
        text = text_list[j]
        draw.text((padding, padding + j * (margin + h)), text, font=font, fill=(0, 0, 0))
    return i


def image_to_base64(img, format='PNG'):
    output_buffer = BytesIO()
    img.save(output_buffer, format)
    byte_data = output_buffer.getvalue()
    base64_str = base64.b64encode(byte_data)
    return base64_str


def get_qq_logo(given_path) -> Image.Image:
    # if mode == 0:
    #     return Image.open('src/static/mai/icon/no_qlogo.png').convert('RGBA')
    # elif mode != 2 and os.path.exists(f'src/static/mai/icon/{qq}.png'):
    #     return Image.open(f'src/static/mai/icon/{qq}.png').convert('RGBA')
    # else:
    #     r = requests.get(f"https://q.qlogo.cn/g?b=qq&nk={qq}&s=640")
    #     if r.status_code == 200:
    #         logo = Image.open(BytesIO(r.content))
    #         logo = logo.convert('RGBA')
    #         return logo
    #     else:
    #         return Image.open('src/static/mai/icon/default.png').convert('RGBA')
    try:
        img = Image.open(str(given_path)).convert('RGBA')
    except:
        hjm_path = static / 'hjm' 
        pic_list = os.listdir(hjm_path)
        pic = random.choice(pic_list)
        img = Image.open(str(hjm_path / pic)).convert('RGBA')
        
    return img