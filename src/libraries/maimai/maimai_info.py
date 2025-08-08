from PIL import Image, ImageDraw, ImageFont
from src.libraries.maimai.maimaidx_music import Music, Chart, BestRecord, total_list
from src.libraries.maimai.maimai_network import mai_api

from src.libraries.tool_range import is_fools_day
import asyncio



assets_path = "src/static/mai/newinfo/"
cover_path = "src/static/mai/cover/"

# ========== 1. 全局预加载 ==========
# mapping lists
diffs_short = ["BSC", "ADV", "EXP", "MST", "MST_Re"]
chart_modes = ["Standard", "Deluxe"]
rank_order = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]  # D, C, B, BB, BBB, A, AA, AAA, S, Sp, SS, SSp, SSS, SSSp
rank_list = ["D", "C", "B", "BB", "BBB", "A", "AA", "AAA", "S", "Sp", "SS", "SSp", "SSS", "SSSp"]
fc_list = ["Blank", "FC", "FCp", "AP", "APp"]
fs_list = ["Blank", "SP", "FS", "FSp", "FSD", "FSDp", "FSD", "FSDp"]


# ========== 2. 预加载图片资源 ==========
# 主边框
main_frame = {
    diff_short: Image.open(assets_path + f"UI_TST_MBase_{diff_short}.png").convert("RGBA") for diff_short in diffs_short
}

# 边框头
head_frame = {
    diff_short: Image.open(assets_path + f"UI_TST_MBase_{diff_short}_Tab.png").convert("RGBA") for diff_short in diffs_short
}

# DX/SD
mode_icon = {
    chart_mode: Image.open(assets_path + f"UI_TST_Infoicon_{chart_mode}Mode.png").convert("RGBA") for chart_mode in chart_modes
}

# LV
LV_frame = {
    diff_short: Image.open(assets_path + f"UI_TST_MBase_LV_{diff_short}.png").convert("RGBA") for diff_short in diffs_short
}

# 等级
musiclevel_icon_list = "0123456789+-,.L"
musiclevel_icon = {
    diff_short: {
        musiclevel_icon_list[i]: Image.open(assets_path + f"UI_CMN_MusicLevel_{diff_short}_{i}.png").convert("RGBA") for i in range(15)
    } for diff_short in diffs_short
}

# 星级背景
star_background = {
    i: Image.open(assets_path + f"BG_{i}_stars.png").convert("RGBA") for i in range(6)
}

# 评价图标
rank_icons = {
    rank: Image.open(assets_path + f"UI_MSS_Rank_{rank}.png").convert("RGBA") for rank in rank_list
}

# FC图标
fc_icons = {
    fc: Image.open(assets_path + f"UI_MSS_MBase_Icon_{fc}.png").convert("RGBA") for fc in fc_list
}

# FS图标
fs_icons = {
    fs: Image.open(assets_path + f"UI_MSS_MBase_Icon_{fs}.png").convert("RGBA") for fs in fs_list
}

# ========== 3. 宏定义 ==========

diff_replace = {
    0: "BSC",
    1: "ADV",
    2: "EXP",
    3: "MST",
    4: "MST_Re",
}

# chartmode_replace = {
#     "Standard": "SD",
#     "Deluxe": "DX",
# }

def calculate_stars(dxscore: int, dxscore_max: int) -> int:
    """
    根据DX分数计算星级
    :param dxscore: DX分数
    :param dxscore_max: DX分数最大值
    :return: 星级（0-5）
    """
    if dxscore / dxscore_max >= 0.97:
        return 5
    elif dxscore / dxscore_max >= 0.95:
        return 4
    elif dxscore / dxscore_max >= 0.93:
        return 3
    elif dxscore / dxscore_max >= 0.90:
        return 2
    elif dxscore / dxscore_max >= 0.85:
        return 1
    else:
        return 0

# ========== 4. 函数定义 ==========

async def draw_new_info(record: BestRecord, music: Music)->Image.Image:

    # 确保 record 与 music 对应
    if record.music_id != music.id:
        raise ValueError("Record's music_id does not match the provided Music object's id.")

    chart = music.charts[record.diff_index]

    diff = diff_replace[record.diff_index]

    chartmode = "Deluxe" if music.type=="DX" else "Standard"

    music_id = record.music_id

    if chart.level[-1] == "+":
        lv = int(chart.level[:-1])
        plus = True
    else:
        lv = int(chart.level)
        plus = False

    music_title = music.title
    if len(music_title) > 50:
        music_title = music_title[:47] + "..."

    artist = music.artist

    dxscore = record.dxscore
    dxscore_max = chart.notes * 3
    stars = calculate_stars(dxscore, dxscore_max)

    achievement = record.achievements
    rank = rank_list[record.rank_id]

    fc = fc_list[record.fc_id]

    fs = fs_list[record.fs_id]

    notes_designer = chart.charter

    bpm = int(music.bpm)


    img= Image.new('RGBA', (394, 678), color = (0, 0, 0,0))
    img_draw = ImageDraw.Draw(img)
 
    # 主边框
    temp_img = main_frame[diff].convert("RGBA")
    img.paste(temp_img,(0,62),temp_img)

    # 边框头
    temp_img = head_frame[diff].convert("RGBA")
    img.paste(temp_img,(0,0),temp_img)

    # DX/SD
    temp_img = mode_icon[chartmode].convert("RGBA")
    img.paste(temp_img,(6,6),temp_img)

    # 封面
    temp_img = await mai_api.open_cover(music_id)
    temp_img = temp_img.convert("RGBA")
    temp_img = temp_img.resize((316,316),resample=Image.Resampling.BILINEAR)
    img.paste(temp_img,(40,94))

    # LV
    temp_img = LV_frame[diff].convert("RGBA")
    img.paste(temp_img,(217,363),temp_img)

    # 等级
    temp_img = musiclevel_icon[diff]["L"].convert("RGBA")
    img.paste(temp_img,(262,402),temp_img)
    if lv >= 10:
        temp_img = musiclevel_icon[diff]["1"].convert("RGBA")
        img.paste(temp_img,(293,402),temp_img)
    temp_img = musiclevel_icon[diff][str(lv%10)].convert("RGBA")
    img.paste(temp_img,(321,402),temp_img)
    if plus:
        temp_img = musiclevel_icon[diff]["+"].convert("RGBA")
        img.paste(temp_img,(348,402),temp_img)

    # 曲名
    font_title = ImageFont.truetype("src/static/SourceHanSansCN-Bold.otf", 20,encoding="utf-8")
    text_length = font_title.getbbox(music_title)[2]
    if text_length>382:
        font_title = ImageFont.truetype("src/static/SourceHanSansCN-Bold.otf", int(20*382/text_length),encoding="utf-8")
        text_length = font_title.getbbox(music_title)[2]
    img_draw.text(((394-text_length)/2, 482), music_title, font=font_title, fill=(255, 255, 255, 255))
    
    # 艺术家
    font_artist = ImageFont.truetype("src/static/Tahoma.ttf", 16,encoding="utf-8")
    text_length = font_artist.getbbox(artist)[2]
    if text_length>382:
        font_artist = ImageFont.truetype("src/static/Tahoma.ttf", int(16*382/text_length),encoding="utf-8")
        text_length = font_artist.getbbox(artist)[2]
    img_draw.text(((394-text_length)/2, 531), artist, font=font_artist, fill=(255, 255, 255, 255))

    # 星级背景
    temp_img = star_background[stars].convert("RGBA")
    img.paste(temp_img,(4,563),temp_img)

    # 分数
    font_score = ImageFont.truetype("src/static/MFZhiShang_Noncommercial-Regular.otf", 20,encoding="utf-8")

    if is_fools_day():
        score_text = f"{int(achievement*10000):>7d}".replace(" ","   ")
    else:
        score_text = f"{achievement:>8.4f}".replace(" ","   ")
    score_text += " %"
    temp_img = Image.new('RGBA', (font_score.getbbox(score_text)[2], font_score.getbbox(score_text)[3]), color = (0, 0, 0,0))
    temp_img_draw = ImageDraw.Draw(temp_img)
    temp_img_draw.text((0, 0), score_text, font=font_score, fill=(227, 178, 24))
    temp_img = temp_img.resize((int(temp_img.size[0]*1.13),temp_img.size[1]),resample=Image.Resampling.BILINEAR)
    img.paste(temp_img,(18,571),temp_img)

    # 评价
    temp_img = rank_icons[rank].convert("RGBA")
    img.paste(temp_img,(183,570),temp_img)
    temp_img = fc_icons[fc].convert("RGBA")
    img.paste(temp_img,(250,570),temp_img)
    temp_img = fs_icons[fs].convert("RGBA")
    img.paste(temp_img,(316,570),temp_img)

    # DX分
    font_dxscore = ImageFont.truetype("src/static/Tahoma.ttf", 20,encoding="utf-8")
    img_draw.text((140, 598), f"{dxscore:>4d}a/a{dxscore_max:>4d}".replace(" ","  ").replace("a"," "), font=font_dxscore, fill=(255, 255, 255, 255))

    # 谱师
    font_notes_designer = ImageFont.truetype("src/static/Tahoma.ttf", 16,encoding="utf-8")
    text_length = font_notes_designer.getbbox(notes_designer)[2]
    if text_length>260:
        notes_designer = notes_designer[:int(260/text_length*len(notes_designer))]
    img_draw.text((12, 645), notes_designer, font=font_notes_designer, fill=(34,81,146))

    # BPM
    font_bpm = ImageFont.truetype("src/static/MFZhiShang_Noncommercial-Regular.otf", 16,encoding="utf-8")
    img_draw.text((290, 647), f"BPM  {bpm:03d}", font=font_bpm, fill=(0,0,0))

    #游玩次数
    # if plct and "playCount" in record:
    #     playcount = record["playCount"]
    #     font_title_small = ImageFont.truetype("src/static/SourceHanSansCN-Bold.otf", 16,encoding="utf-8")
    #     lens = font_title_small.getbbox(f"游玩次数：{playcount}")[2]
    #     img_draw.text((380-lens+1, 66+1), f"游玩次数：{playcount}", font=font_title_small, fill=(255,255,255))
    #     img_draw.text((380-lens, 66), f"游玩次数：{playcount}", font=font_title_small, fill=(0,0,0))

    return img

async def draw_new_infos(records: list[BestRecord]) -> Image.Image:
    # asyncio 同时绘制多个记录
    tasks = []
    for record in records:
        music = await total_list.by_id(record.music_id)
        if music is None:
            raise ValueError(f"Music with ID {record.music_id} not found in total_list.")
        tasks.append(draw_new_info(record, music))
    imgs = await asyncio.gather(*tasks)

    # 合并图片
    width_sum = 5
    for img in imgs:
        width_sum += img.size[0]+5
    final_img = Image.new("RGB",(width_sum,imgs[0].size[1]+10),(255,255,255))
    width_pos = 5
    for img in imgs:
        final_img.paste(img,(width_pos,5),img)
        width_pos += img.size[0]+5
    font_title = ImageFont.truetype("src/static/SourceHanSansCN-Bold.otf", 20,encoding="utf-8")
    img_draw = ImageDraw.Draw(final_img)
    img_draw.text((width_sum-156,5),"Generated By",(0,0,0),font_title)
    img_draw.text((width_sum-156,27),"Range & asdfbot",(0,0,0),font_title)
    return final_img





