from PIL import Image, ImageDraw, ImageFont
import os,aiohttp,json,time
import asyncio

from typing import List, Dict, Union, Optional, Tuple

from src.libraries.secrets import DF_Dev_Token
from src.libraries.image_range import get_qq_logo
from src.libraries.maimai.static_lists_and_dicts import info_to_file_dict, version_abbr_list, version_abbr_str, level_list, rank_list_upper, fc_list_upper, fs_list_upper, rank_list_lower, fc_list_lower, fs_list_lower
from src.libraries.query import query_user
from src.libraries.maimai.maimai_network import mai_api
from src.libraries.maimai.maimai_type import Music, MusicList, Chart, BestRecord, BestRecordList, MusicChart, Plate
from src.libraries.maimai.maimaidx_music import total_list, best_record_list, music_chart_list, user_list
from src.libraries.maimai.database import database_api

class PlateGenerator(object):
    """
    生成用户的 plate
    """

    @classmethod
    async def filt_music(cls, version_ids: Optional[Union[int, List[int]]] = None, diff: Optional[List[int]] = None, levels: Optional[List[str]] = None) -> List[MusicChart]:
        """
        过滤 plate
        """
        if isinstance(version_ids, int):
            version_ids = [version_ids]
        
        record = await total_list.filter(
            version_indices=version_ids,
            diff_indices=diff,
            levels=levels,
            order=['-ds', '+music_id']
        )

        record_list = record["music_charts"]

        revived_chart_ids = await total_list.get_revived_music_list()

        # 过滤掉已复活的曲目
        filtered_charts = [
            chart for chart in record_list
            if chart.music_id not in revived_chart_ids
        ]

        return filtered_charts
    
    @classmethod
    async def get_plate(cls, user_id: str, type: str, version: str) -> Plate:
        """ 
        获取用户的 plate
        """

        user = await user_list.by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found.")
        
        if version in version_abbr_str:
            version_ids = [i for i, v in enumerate(version_abbr_list) if version in v]
        elif version == '舞':
            version_ids = [i for i in range(0, 13)] # 包括所有舞代曲版本
        else:
            raise ValueError(f"Invalid version: {version}. Must be one of {version_abbr_str} or '舞'.")
        
        if type in ['极', '将', '神', '舞舞']:
            type_dict = {
                '极': 'fc',
                '将': 'sss',
                '神': 'ap',
                '舞舞': 'fsd'
            }
            type = type_dict[type]
        if (not type) or (type not in rank_list_lower + fc_list_lower + fs_list_lower):
            raise ValueError(f"Invalid type: {type}. Must be one of ['极', '将', '神', '舞舞']")
            
        charts = []
        charts_all = []

        if version == '舞':
            charts_all.append(await cls.filt_music(version_ids=version_ids, diff=[0, 1, 2, 3, 4]))
        else:
            charts_all.append(await cls.filt_music(version_ids=version_ids, diff=[0, 1, 2, 3]))

        if version == '舞':
            charts.append(await cls.filt_music(version_ids=version_ids, diff=[3, 4]))
        else:
            charts.append(await cls.filt_music(version_ids=version_ids, diff=[3]))

        if '真' in version:
            charts_all = [chart for chart in charts_all if chart.music_id != 70]  # 过滤掉圣诞歌
            charts = [chart for chart in charts if chart.music_id != 70]  # 过滤掉圣诞歌

        # 遍历列表获取用户的最佳记录

        plate = []
        for chart in charts:
            best_record = await best_record_list.by_user_and_music(user_id, chart.music_id, chart.diff_index)
            plate.append((chart, best_record))

        plate_all = []
        for chart in charts_all:
            best_record = await best_record_list.by_user_and_music(user_id, chart.music_id, chart.diff_index)
            plate_all.append((chart, best_record))

        plate_obj = Plate(user=user, plate=plate, plate_all=plate_all, type=type)

        return plate_obj

    async def get_level(cls, user_id: str, type: str, level: str) -> Plate:
        """
        获取用户的指定难度的 plate
        """
        if level not in level_list:
            raise ValueError(f"Invalid level: {level}. Must be one of {level_list}.")
        
        user = await user_list.by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found.")
        
        charts = await cls.filt_music(levels=[level])
        
        if type not in ['极', '将', '神', '舞舞']:
            raise ValueError(f"Invalid type: {type}. Must be one of ['极', '将', '神', '舞舞']")
        
        lev_list = []
        total_flag = True
        for chart in charts:
            best_record = await best_record_list.by_user_and_music(user_id, chart.music_id, chart.diff_index)
            if type == '极':
                flag = best_record and best_record.fc_id >= 1
            elif type == '将':
                flag = best_record and best_record.rank_id >= 12
            elif type == '神': 
                flag = best_record and best_record.fc_id >= 3
            elif type == '舞舞':
                flag = best_record and best_record.fs_id >= 4
            else:
                pass
            if not flag:
                total_flag = False
            lev_list.append((chart, best_record, flag))

        plate_obj = Plate(user=user, plate={level: lev_list}, plate_achieved=total_flag)

        return plate_obj
    
class DrawPlate(object):
    def __init__(self):
        self.cover_dir = 'src/static/mai/cover/'
        self.temp_dir = 'src/static/mai/temp/'
        self.assets_path = "src/static/mai/platequery/"
        self.plate_path = "src/static/mai/plate/"
        self.ds_img_list = {
            f"{ds/10:.1f}": Image.open(f"{self.assets_path}{ds/10:.1f}.png")
            for ds in range(10, 151)
        }
        self.base_img_list = [
            Image.open(f"{self.assets_path}{i}.png")
            for i in range(0, 5)
        ]
        self.base_dx_img_list = [
            Image.open(f"{self.assets_path}{i}dx.png")
            for i in range(0, 5)
        ]
        self.ui_img_list = {
            f"{c}": Image.open(f"{self.assets_path}UI_{c}.png")
            for c in rank_list_upper + fc_list_upper + fs_list_upper
            if c != ''
        }

        self.finish_img = Image.open(f"{self.assets_path}finish.png")
        self.unfinish_img = Image.open(f"{self.assets_path}unfinish.png")

    async def draw_one_music(self, music_chart: MusicChart, overlay: str, status: bool) -> Image.Image:
        
        # base_size = (140,140)
        base = self.base_img_list[music_chart.diff_index].convert("RGBA") if music_chart.type != 'DX' else self.base_dx_img_list[music_chart.diff_index].convert("RGBA")

        cover = await mai_api.open_cover(music_chart.music_id)
        cover = cover.convert('RGBA').resize((130,130))

        f = self.finish_img.convert("RGBA") if status else self.unfinish_img.convert("RGBA")
        cover.alpha_composite(f)
            
        base.paste(cover,(5,5),cover)
        
        overlay_img = self.ui_img_list.get(overlay, None)
        if overlay_img:
            base.paste(cover,(int((base.size[0]-cover.size[0])/2),int((base.size[1]-cover.size[1])/2)),cover)

        return base



    async def draw_rank_list(records:dict)->Image.Image:
        keys = list(records.keys())
        keys.sort(reverse=True)
        none_keys = []
        for key in keys:
            if records[key]==[]:
                none_keys.append(key)
        for key in none_keys:
            keys.remove(key)

        lines = sum([1 + int((len(records[key])-0.1)/10) for key in keys])
        img = Image.new('RGBA', (1952, lines*160), color = (0, 0, 0,0))
        line = 0
        row = 0
        for key in keys:
            head = Image.open(f"{assets_path}{key}.png").convert("RGBA")
            img.paste(head,(30,line*160+15),head)
            for record in records[key]:
                if row == 10:
                    row = 0
                    line += 1
                song_img = await draw_one_music(record)
                img.paste(song_img,(row*160+340,line*160+15),song_img)
                row += 1
            row = 0
            line += 1
        return img


def draw_status(status:dict)->Image.Image:
    img = Image.new('RGBA', (152*len(status)+150*len(status)-150, 156), color = (0, 0, 0,0))
    font_info = ImageFont.truetype("src/static/SourceHanSansCN-Bold.otf", 34,encoding="utf-8")
    for i,key in enumerate(status):
        temp = Image.open(f"{assets_path}UI_RSL_MusicJacket_Base_{key}.png").convert("RGBA")
        temp_draw = ImageDraw.Draw(temp)
        temp_draw.text((82, 3), f"{status[key]['V']}\n{status[key]['X']}\n{status[key]['-']}", font=font_info, fill=(255, 255, 255))
        temp_draw.text((81, 2), f"{status[key]['V']}\n{status[key]['X']}\n{status[key]['-']}", font=font_info, fill=(0, 0, 0))
        img.paste(temp,(i*152+i*150,0),temp)
    return img
        

async def draw_final_rank_list(info:dict,records:dict)->Image.Image:
    try:
        with open('src/users/' + info['qq'] + '.json', "r") as f:
            user_settings = json.load(f)
    except:
        user_settings = {}

    a = time.time()
    # get rank list
    rank_list = await draw_rank_list(records)

    print(time.time()-a)

    status_img = None
    finished_img = None
    # get status
    if info["status"]=={}:
        statusoffset = 0
    else:
        statusoffset = 120
        status_img = draw_status(info["status"])
        if info["dacheng"]:
            finished_img = Image.open(f"{assets_path}已达成.png").convert("RGBA")
        elif info["queren"]:
            finished_img = Image.open(f"{assets_path}已确认.png").convert("RGBA")

    print(time.time()-a)

    # create new image
    img = Image.new('RGBA', (rank_list.size[0], rank_list.size[1] + 800 + statusoffset), color = (255, 255, 255, 255))

    # draw bg
    rankbg = Image.open(f"{assets_path}rankbg.png").convert("RGBA")
    bg_times = int((img.size[1]-400)/rankbg.size[1]) + 1
    for i in range(bg_times):
        img.paste(rankbg,(0,400+i*rankbg.size[1]),rankbg)

    top = Image.open(f"{assets_path}top.png").convert("RGBA")
    img.alpha_composite(top)
    
    bott = Image.open(f"{assets_path}bott.png").convert("RGBA")
    temp = img.crop((0,img.size[1]-bott.size[1],img.size[0],img.size[1]))
    temp.alpha_composite(bott)
    img.paste(temp,(0,img.size[1]-bott.size[1]),temp)

    print(time.time()-a)
    # draw status
    if status_img:
        img.paste(status_img,(int((img.size[0]-status_img.size[0])/2),430),status_img)

    if finished_img:
        # draw plate and qq
        plate_shadow = Image.open(f"{assets_path}plate_shadow.png").convert("RGBA")
        img.paste(plate_shadow,(256-100,150),plate_shadow)
        plate = Image.open(f"{plate_path}{info['plate']}").convert("RGBA").resize((1440,232))
        img.paste(plate,(256-100,150),plate)

        user_avatar_dir = user_settings.get('avatar_dir', None)

        qqlogo = get_qq_logo(user_avatar_dir).resize((200,200))
        img.paste(qqlogo,(256+16-100,150+15),qqlogo)
        img.paste(finished_img,(1600,120),finished_img)
    else:
        # draw plate and qq
        plate_shadow = Image.open(f"{assets_path}plate_shadow.png").convert("RGBA")
        img.paste(plate_shadow,(256,150),plate_shadow)
        plate = Image.open(f"{plate_path}{info['plate']}").convert("RGBA").resize((1440,232))
        img.paste(plate,(256,150),plate)
        
        user_avatar_dir = user_settings.get('avatar_dir', None)

        qqlogo = get_qq_logo(user_avatar_dir).resize((200,200))
        img.paste(qqlogo,(256+16,150+15),qqlogo)

    # draw rank list
    img.paste(rank_list,(0,500 + statusoffset),rank_list)
    img = img.convert("RGB")

    print(time.time()-a)
    return img