from PIL import Image, ImageDraw, ImageChops, ImageEnhance, ImageFilter
import numpy as np
import random
import datetime

def is_April_1st():
    now = datetime.datetime.now()
    if now.month == 4 and now.day == 1:
        return True
    return False

encoding_list = ["utf-8", "gbk", "iso-8859-1", "gb2312", "big5", "latin-1"]

def kun_jin_kao(s: str) -> str:
    s = str(s)
    encode_char_list = random.sample(range(0, len(s)), int(len(s)*0.3))
    for i in encode_char_list:
        encoding_pair = random.sample(encoding_list, 2)
        s = s[:i] + s[i].encode(encoding_pair[0], errors="replace").decode(encoding_pair[1], errors="replace") + s[i+1:]
    result = s
    return result

def random_shift_rows_numpy(img, shift):
    width, height = img.size
    img_mode = img.mode
    arr = np.array(img)
    
    # 生成每行的随机平移量（-5到5）
    shifts = np.random.randint(-shift, shift+1, size=height)
    
    
    for y in range(height):
        arr[y] = np.roll(arr[y], shifts[y], axis=0)
    
    # 转换回PIL图像并保留元数据
    out_img = Image.fromarray(arr)

    return out_img

def add_noise(image, noise_value=16):
    reverse_p = 0.7

    # 将图像转换为numpy数组
    r, g, b, a = image.split()
    img_array_r = np.array(r)
    print(img_array_r)
    img_array_g = np.array(g)
    img_array_b = np.array(b)
    img_array_a = np.array(a)
    
    # 生成噪声
    noise_r = np.random.normal(0, noise_value, img_array_r.shape)
    noise_g = np.random.normal(0, noise_value, img_array_g.shape)
    noise_b = np.random.normal(0, noise_value, img_array_b.shape)
    
    mask_r = np.random.rand(*img_array_r.shape) < reverse_p
    noisy_img_array_r = np.where(mask_r, np.mod(img_array_r + noise_r, 256), np.clip(img_array_r + noise_r, 0, 255))
    noisy_img_array_r = np.clip(noisy_img_array_r, 0, 255).astype(np.uint8)  # 确保数据类型为uint8
    
    # 添加噪声到图像
    
    mask_g = np.random.rand(*img_array_g.shape) < reverse_p
    noisy_img_array_g = np.where(mask_g, np.mod(img_array_g + noise_g, 256), np.clip(img_array_g + noise_g, 0, 255))
    noisy_img_array_g = np.clip(noisy_img_array_g, 0, 255).astype(np.uint8)  # 确保数据类型为uint8

    mask_b = np.random.rand(*img_array_b.shape) < reverse_p
    noisy_img_array_b = np.where(mask_b, np.mod(img_array_b + noise_b, 256), np.clip(img_array_b + noise_b, 0, 255))
    noisy_img_array_b = np.clip(noisy_img_array_b, 0, 255).astype(np.uint8)  # 确保数据类型为uint8

    # 将numpy数组转换回图像
    noisy_image = Image.fromarray(np.stack((noisy_img_array_r, noisy_img_array_g, noisy_img_array_b, img_array_a), axis=-1), 'RGBA')
    
    return noisy_image

def add_tv_distortion(img, shift_row):
    # 加载原始图像
    img = img.convert('RGBA')

    if shift_row:
        img = random_shift_rows_numpy(img, shift_row)  # 随机行偏移
    width, height = img.size
    
    # 添加噪声
    img = add_noise(img)
    
    # 生成彩色条纹
    stripe = Image.new('RGBA', (width, height))
    draw = ImageDraw.Draw(stripe)
    # # 水平条纹
    # for y in range(0, height, 5):
    #     if random.random() < 0.3:
    #         draw.line([(0,y), (width,y)], 
    #                  fill=random.choice(["red","blue","green"]), 
    #                  width=random.randint(1,2))
    # 垂直条纹
    for x in range(0, width, 15):
        if random.random() < 0.2:
            draw.line([(x,0), (x,height)], 
                     fill="white", 
                     width=random.randint(1,2))
    
    # 生成扫描线（使用半透明线条）
    scan_lines = Image.new("RGBA", (width, height))
    sdraw = ImageDraw.Draw(scan_lines)
    for y in range(0, height, 3):
        sdraw.line([(0,y), (width,y)], 
                  fill=(0,0,0,90),  # 半透明黑色
                  width=1)
    
    # 合成流程
    img = ImageChops.screen(img, stripe)  # 叠加彩色条纹
    
    # 通道偏移
    r, g, b, a = img.split()
    offset = random.randint(1,3)
    r = r.transform(r.size, Image.AFFINE, (1,0,offset,0,1,0))
    b = b.transform(b.size, Image.AFFINE, (1,0,-offset,0,1,0))
    img = Image.merge("RGBA", (r,g,b,a))
    
    # 添加扫描线（使用复合叠加）
    img.paste(scan_lines, (0,0), scan_lines)
    
    # 最终对比度调整
    # img = ImageEnhance.Contrast(img).enhance(1.2)
    


    return img

if __name__ == "__main__":
    # 测试代码
    if is_April_1st():
        img = Image.open("1.webp")
        img = add_tv_distortion(img)
        img.save("output.png")
    else:
        print("今天不是愚人节！")