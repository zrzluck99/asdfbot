from nonebot.adapters.qq import Message, MessageSegment
from src.libraries.maimai.maimaidx_music import Music, Chart
from src.libraries.sendpics import pic_to_message_segment
from src.libraries.april_fool import is_April_1st, kun_jin_kao
from src.libraries.maimai.static_lists_and_dicts import version_icon_path, genre_icon_path, level_index_to_file, info_to_file_dict
from src.libraries.maimai.maimaidx_music import compute_ra
from src.libraries.maimai.maimai_network import mai_api
from PIL import Image, ImageDraw, ImageFont

assets_path = "src/static/mai/newinfo/"
cover_path = "src/static/mai/cover/"

async def chart_MessageSegment(chart: Chart, title: str) -> MessageSegment:
    LEVEL_NAMES = ['Basic', 'Advanced', 'Expert', 'Master', 'Re: MASTER']

    # 5. 提取谱面基础信息
    stats = chart.stats

    diff_info = (
        f"\n平均达成率：{stats.avg:.4f}%\n"
        f"拟合定数：{stats.fit_diff:.2f}\n"
    )

    # 7. 生成谱面详情文本
    note_lines = (f"TAP: {chart.tap}  \n"
                  f"HOLD: {chart.hold}  \n"
                  f"SLIDE: {chart.slide}  \n"
                  f"BREAK: {chart.brk}  \n"
                  f"TOUCH: {chart.touch}  \n"
                  f"MAX COMBO: {chart.notes}  \n")

    chart_info = (
        f"{LEVEL_NAMES[chart.diff_index]} {chart.level}({chart.ds})\n"
        f"{note_lines}\n"
        f"谱师: {chart.charter if chart.charter else '未知'}\n"
    )

    # 8. 发送封面 + 文本
    img = await mai_api.open_cover(chart.music_id)
    img = img.resize((190, 190))

    cover_seg = pic_to_message_segment(img)
    text_seg = MessageSegment.text(f"{chart.music_id}. {title}\n{chart_info}{diff_info}")

    if is_April_1st():
        s = kun_jin_kao(s)
    return cover_seg + text_seg


async def song_MessageSegment(music: Music):
    img = await mai_api.open_cover(music.id)
    img = img.resize((190, 190))
    
    pic = pic_to_message_segment(img)
    s = MessageSegment.text(f"{music.id}. {music.title}\n") + \
        MessageSegment.text(f"\n艺术家: {music.artist}\n".replace(".","·")) + \
        MessageSegment.text(f"分类: {music.genre}\n") + \
        MessageSegment.text(f"BPM: {music.bpm}\n") + \
        MessageSegment.text(f"版本: {music.cn_version}\n") + \
        MessageSegment.text(f"定数: {'/'.join(str(ds) for ds in music.dss)}")
    if is_April_1st():
        s = kun_jin_kao(s)
    return pic + s


async def song_MessageSegment2(music: Music):
    print(f"song_MessageSegment2: {music.id} {music.title}")
    img = await draw_music_info(music)
    return pic_to_message_segment(img)


def draw_Lv(lv: str, diff: str)->Image.Image:
    img = Image.new('RGBA', (119, 57), color = (0, 0, 0,0))
    if lv[-1]=='+':
        lv = lv[:-1]
        plus = True
    else:
        plus = False
    lv = int(lv)

    # 等级
    temp_img = Image.open(assets_path + f"UI_CMN_MusicLevel_{diff}_14.png").convert("RGBA")
    img.paste(temp_img,(-4,0),temp_img)
    if lv >= 10:
        temp_img = Image.open(assets_path + f"UI_CMN_MusicLevel_{diff}_1.png").convert("RGBA")
        img.paste(temp_img,(27,0),temp_img)
    temp_img = Image.open(assets_path + f"UI_CMN_MusicLevel_{diff}_{lv%10}.png").convert("RGBA")
    img.paste(temp_img,(55,0),temp_img)
    if plus:
        temp_img = Image.open(assets_path + f"UI_CMN_MusicLevel_{diff}_10.png").convert("RGBA")
        img.paste(temp_img,(82,0),temp_img)

    return img

num_img = Image.open(f"{assets_path}UI_DNM_LifeNum_02.png").convert("RGBA")
numbox_range = [
    (0,0,60,72),
    (60,0,120,72),
    (120,0,180,72),
    (180,0,240,72),
    (0,72,60,144),
    (60,72,120,144),
    (120,72,180,144),
    (180,72,240,144),
    (0,144,60,216),
    (60,144,120,216)
]
#裁剪每个数字
numbox = [num_img.crop(_range).resize((30,36)) for _range in numbox_range]

async def draw_music_info(music: Music) -> Image.Image:
    
    if len(music.dss)==5:
        jump = 143
        chats_sum = 5
    elif len(music.dss)==4:
        jump = 191
        chats_sum = 4
    else:
        pass

    # 打开背景
    bg = Image.open(f"{assets_path}BG_{chats_sum}.png").convert("RGBA")
    #bg = Image.open(f"{assets_path}BG_SD_5_template.png")
    img_draw = ImageDraw.Draw(bg)
    
    # 版本 流派
    version_icon = Image.open(f"{assets_path}version_icon/{version_icon_path[music.version_id]}").convert("RGBA").resize((207,100))
    bg.paste(version_icon,(145,80),version_icon)
    genre_icon = Image.open(f"{assets_path}genre_icon/{genre_icon_path[music.genre]}").convert("RGBA").resize((207,100))
    bg.paste(genre_icon,(352,80),genre_icon)

    # 标准/DX
    chartmode = "Deluxe" if music.type=="DX" else "Standard"
    type_img = Image.open(f"{assets_path}UI_TST_Infoicon_{chartmode}Mode.png").convert("RGBA")
    bg.paste(type_img,(160,195),type_img)

    # ID
    str_id = str(music.id)
    for i in range(len(str_id)):
        j = len(str_id)-i-1
        num = int(str_id[j])
        bg.paste(numbox[num],(518-i*29,202),numbox[num])

    # 封面
    cover_img = await mai_api.open_cover(music.id)
    cover_img = cover_img.convert("RGBA")
    cover_img = cover_img.resize((316,316))
    bg.paste(cover_img,(194,283),cover_img)

    # 等级
    lv_img = draw_Lv(music.levels[3],"MST")
    bg.paste(lv_img,(420,610),lv_img)

    # 曲名
    font_title = ImageFont.truetype("src/static/SourceHanSansCN-Bold.otf", 20,encoding="utf-8")
    text_length = font_title.getbbox(music.title)[2]
    if text_length>382:
        font_title = ImageFont.truetype("src/static/SourceHanSansCN-Bold.otf", int(20*382/text_length),encoding="utf-8")
        text_length = font_title.getbbox(music.title)[2]
    img_draw.text((154+(394-text_length)/2, 688), music.title, font=font_title, fill=(255, 255, 255))
    
    # 艺术家
    font_artist = ImageFont.truetype("src/static/Tahoma.ttf", 16,encoding="utf-8")
    text_length = font_artist.getbbox(music.artist)[2]
    if text_length>382:
        font_artist = ImageFont.truetype("src/static/Tahoma.ttf", int(16*382/text_length),encoding="utf-8")
        text_length = font_artist.getbbox(music.artist)[2]
    img_draw.text((154+(394-text_length)/2, 688+49), music.artist, font=font_artist, fill=(255, 255, 255))

    # BPM
    font_bpm = ImageFont.truetype("src/static/MFZhiShang_Noncommercial-Regular.otf", 16,encoding="utf-8")
    img_draw.text((454, 775), f"BPM  {music.bpm:03d}", font=font_bpm, fill=(255,255,255))

    # 每谱面信息
    for i, chart in enumerate(music.charts):
        #等级
        lv_img = draw_Lv(chart.level,level_index_to_file[i]).resize((84,40))
        bg.paste(lv_img,(917,97+i*jump),lv_img)


        font_info = ImageFont.truetype("src/static/SourceHanSansCN-Bold.otf", 16,encoding="utf-8")
        # 定数
        ds_text = f"定数 {chart.ds:>2.1f}         SSS+ {compute_ra(chart.ds, 100.5):>3d}         SSS {compute_ra(chart.ds, 100):>3d}"
        width = font_info.getbbox(ds_text)[2]
        img_draw.text((628 + int((348-width)/2), 137+i*jump), ds_text, font=font_info, fill=(255, 255, 255, 255))
        # maxcombo
        combo = chart.notes
        img_draw.text((708, 165+i*jump), f"{combo}", font=font_info, fill=(255, 255, 255))
        width = font_info.getbbox(f"{combo*3}")[2]
        img_draw.text((801 + int((180-width)/2), 181+i*jump), f"{combo*3}", font=font_info, fill=(0, 0, 0))
        # 谱师
        charter = chart.charter
        img_draw.text((626, 204+i*jump), f"{charter}", font=font_info, fill=(0, 0, 0))
        img_draw.text((625, 203+i*jump), f"{charter}", font=font_info, fill=(255, 255, 255))
        # NOTES
        tap = chart.tap
        hold = chart.hold
        slide = chart.slide
        breaks = chart.brk
        if music.type=="DX":
            touch = chart.touch
        else:
            touch = "-"
        img_draw.text((1129, 108+i*jump), f"{tap}\n{hold}\n{slide}\n{touch}\n{breaks}", font=font_info, fill=(0, 0, 0))
        
        # statistic
        stats = chart.stats
        if stats is None:
            text_list = ["--.--%"] * 8
        else:
            dist = stats.rank_dist
            sssp = (dist[-1]) /sum(dist)
            sss = (dist[-1] + dist[-2]) /sum(dist)
            ss = (dist[-1] + dist[-2] + dist[-3] + dist[-4]) /sum(dist)
            s = (dist[-1] + dist[-2] + dist[-3] + dist[-4] + dist[-5] + dist[-6]) /sum(dist)
            fc_dist = stats.fc_dist
            app = (fc_dist[-1]) /sum(fc_dist)
            ap = (fc_dist[-1] + fc_dist[-2]) /sum(fc_dist)
            fcp = (fc_dist[-1] + fc_dist[-2] + fc_dist[-3]) /sum(fc_dist)
            fc = (fc_dist[-1] + fc_dist[-2] + fc_dist[-3] + fc_dist[-4]) /sum(fc_dist)

            text_list = [f"{sssp:06.2%}",f"{sss:06.2%}",f"{ss:06.2%}",f"{s:06.2%}",f"{app:06.2%}",f"{ap:06.2%}",f"{fcp:06.2%}",f"{fc:06.2%}"]

        img_draw.text((1313, 110+i*jump), text_list[0], font=font_info, fill=(0, 0, 0))
        img_draw.text((1313, 144+i*jump), text_list[2], font=font_info, fill=(0, 0, 0))
        img_draw.text((1313, 177+i*jump), text_list[4], font=font_info, fill=(0, 0, 0))
        img_draw.text((1313, 203+i*jump), text_list[6], font=font_info, fill=(0, 0, 0))
        img_draw.text((1440, 110+i*jump), text_list[1], font=font_info, fill=(0, 0, 0))
        img_draw.text((1440, 144+i*jump), text_list[3], font=font_info, fill=(0, 0, 0))
        img_draw.text((1440, 177+i*jump), text_list[5], font=font_info, fill=(0, 0, 0))
        img_draw.text((1440, 203+i*jump), text_list[7], font=font_info, fill=(0, 0, 0))
    
    return bg