# Author: xyb, Diving_Fish

import os, aiohttp, random, heapq, io, time, json
import matplotlib.pyplot as plt
import numpy as np

from typing import Optional, Dict, List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from src.libraries.maimai.maimai_type import Music, MusicChart, User, BestRecord, BestTable
from src.libraries.maimai.maimai_network import mai_api
from src.libraries.maimai.maimaidx_music import total_list, best_record_list, music_chart_list, user_list
from src.libraries.image_range import get_qq_logo
from src.libraries.maimai.static_lists_and_dicts import platename_to_file, pnconvert, rank_list_upper, fc_list_upper, fs_list_upper
from src.libraries.tool_range import is_fools_day


class BestTableGenerator(object):
    """
        从数据库中获取用户的最佳记录，并生成一个 BestTable 对象
    """
        
    @classmethod
    async def table_b50(cls, user_id: str,
                        fc_indices: Optional[List[int]] = None, 
                        fs_indices: Optional[List[int]] = None,
                        levels: Optional[List[str]] = None) -> BestTable:
        """
        获取用户的 b50/xxb50 等数据
        """
        user = await user_list.by_id(user_id)
        b50 = True
        
        # old best
        old_best = []
        old_rating = 0
        old_records = await best_record_list.filter(user_id=user_id,
                                                    is_new=False,
                                                    pagination=(0, 35), 
                                                    order=['-ra', '+music_id'],
                                                    fc_indices=fc_indices,
                                                    fs_indices=fs_indices,
                                                    levels=levels)

        for record in old_records["record_list"]:
            record.ra = record.ra_b50  # 确保 ra 字段被正确赋值
            music_chart = await music_chart_list.by_id(record.music_id, record.diff_index)
            old_best.append((music_chart, record))
            old_rating += record.ra


        # new best
        new_best = []
        new_rating = 0
        new_records = await best_record_list.filter(user_id=user_id,
                                                    is_new=True,
                                                    pagination=(0, 15), 
                                                    order=['-ra', '+music_id'],
                                                    fc_indices=fc_indices,
                                                    fs_indices=fs_indices,
                                                    levels=levels)

        for record in new_records["record_list"]:
            record.ra = record.ra_b50
            music_chart = await music_chart_list.by_id(record.music_id, record.diff_index)
            new_best.append((music_chart, record))
            new_rating += record.ra

        rating = old_rating + new_rating

        # 生成 BestTable 对象
        best_table = BestTable(
            user=user,
            old_best=old_best,
            new_best=new_best,
            b50=b50,
            old_rating=old_rating,
            new_rating=new_rating,
            rating=rating
        )

        return best_table
    
    @classmethod
    async def table_b40(cls, user_id: str) -> BestTable:
        """
        获取用户的 B40 数据
        """
        user = await user_list.by_id(user_id)
        b50 = False
        
        # old best
        old_best = []
        old_rating = 0
        old_records = await best_record_list.filter(user_id=user_id,
                                                    is_new=False,
                                                    order=['+music_id'])
        old_records_list = sorted(old_records["record_list"], key=lambda x: x.ra_b40, reverse=True)[:25]
        
        for record in old_records_list:
            record.ra = record.ra_b40
            music_chart = await music_chart_list.by_id(record.music_id, record.diff_index)
            old_best.append((music_chart, record))
            old_rating += record.ra

        # new best
        new_best = []
        new_rating = 0
        new_records = await best_record_list.filter(user_id=user_id,
                                                    is_new=True,
                                                    order=['+music_id'])
        new_records_list = sorted(new_records["record_list"], key=lambda x: x.ra_b40, reverse=True)[:15]

        for record in new_records_list:
            record.ra = record.ra_b40
            music_chart = await music_chart_list.by_id(record.music_id, record.diff_index)
            new_best.append((music_chart, record))
            new_rating += record.ra

        rating = old_rating + new_rating

        # 生成 BestTable 对象
        best_table = BestTable(
            user=user,
            old_best=old_best,
            new_best=new_best,
            b50=b50,
            old_rating=old_rating,
            new_rating=new_rating,
            rating=rating
        )

        return best_table
    
    @classmethod
    async def table_stats(cls, user_id: str) -> BestTable:
        """
        获取用户的统计数据
        """
        user = await user_list.by_id(user_id)
        b50 = True
        
        # old best
        old_best = []
        old_rating = 0
        old_records = await best_record_list.filter(user_id=user_id,
                                                    is_new=False,
                                                    order=['+music_id'])
        old_records_list = sorted(old_records["record_list"], key=lambda x: x.ra_stats, reverse=True)[:35]

        for record in old_records_list:
            record.ra = record.ra_stats
            music_chart = await music_chart_list.by_id(record.music_id, record.diff_index)
            if music_chart.stats is not None:
                if music_chart.stats.fit_diff is not None:
                    music_chart.ds = round(music_chart.stats.fit_diff, 1)
            old_best.append((music_chart, record))
            old_rating += record.ra

        # new best
        new_best = []
        new_rating = 0
        new_records = await best_record_list.filter(user_id=user_id,
                                                    is_new=True,
                                                    order=['+music_id'])
        new_records_list = sorted(new_records["record_list"], key=lambda x: x.ra_stats, reverse=True)[:15]

        for record in new_records_list:
            record.ra = record.ra_stats
            music_chart = await music_chart_list.by_id(record.music_id, record.diff_index)
            if music_chart.stats is not None:
                if music_chart.stats.fit_diff is not None:
                    music_chart.ds = round(music_chart.stats.fit_diff, 1)
            new_best.append((music_chart, record))
            new_rating += record.ra

        rating = old_rating + new_rating

        # 生成 BestTable 对象
        best_table = BestTable(
            user=user,
            old_best=old_best,
            new_best=new_best,
            b50=b50,
            old_rating=old_rating,
            new_rating=new_rating,
            rating=rating
        )

        return best_table
    


class DrawBest(object):

    def __init__(self):

        # 静态资源整理:
        # 目录
        self.pic_dir = 'src/static/mai/pic/'
        self.cover_dir = 'src/static/mai/cover/'
        self.plate_dir = 'src/static/mai/plate/'
        self.icon_dir = 'src/static/mai/icon/'
        self.rank_dir = 'src/static/mai/rank/'
        self.temp_dir = 'src/static/mai/temp/'

        # 参数
        self.MusicBlockW_b40 = 164
        self.MusicBlockW = 131
        self.MusicBlockH = 88
        self.COLUMNS_RATING_b40 = [86, 100, 115, 130, 145]
        self.COLUMNS_RATING = [86-5, 100-6, 115-7, 130-8, 145-9]
        self.ROWS_IMG = [2]
        for i in range(6):
            self.ROWS_IMG.append(116 + 96 * i)
        self.COLUMNS_IMG_b40 = []
        for i in range(6):
            self.COLUMNS_IMG_b40.append(2 + 172 * i)
        for i in range(4):
            self.COLUMNS_IMG_b40.append(888 + 172 * i)
        self.COLUMNS_IMG = []
        for i in range(8):
            self.COLUMNS_IMG.append(2 + 138 * i)
        for i in range(4):
            self.COLUMNS_IMG.append(988 + 138 * i)

        # PIL预加载
        self.background = Image.open(self.pic_dir + 'UI_TTR_BG_Base_Plus.png')
        self.dxrating_img_list = [
            Image.open(self.pic_dir + f'UI_CMN_DXRating_S_{num:02d}_2023.png')
            for num in range(1, 12)
        ]
        self.dxrating_img_list_b40 = [
            Image.open(self.pic_dir + f'UI_CMN_DXRating_S_{num:02d}.png')
            for num in range(1, 11)
        ]
        self.numbers_img_list = [
            Image.open(self.pic_dir + f'UI_NUM_Drating_{num}.png')
            for num in range(10)
        ]
        self.platemask_img = Image.open(self.pic_dir + 'UI_TST_PlateMask.png')
        self.namedx_img = Image.open(self.pic_dir + 'UI_CMN_Name_DX.png')
        self.daniplate_img_list = [
            Image.open(self.rank_dir + f'UI_DNM_DaniPlate_{num:02d}.png')
            for num in range(24)
        ]
        self.shougou_img = Image.open(self.pic_dir + 'UI_CMN_Shougou_Rainbow.png')
        self.ranks_img_list = [
            Image.open(self.pic_dir + f'UI_GAM_Rank_{rank}.png')
            for rank in rank_list_upper
        ]
        self.combos_img_list = [
            Image.open(self.pic_dir + f'UI_MSS_MBase_Icon_{combo+"_S" if combo else "none"}.png')
            for combo in fc_list_upper
        ]
        self.fss_img_list = [
            Image.open(self.pic_dir + f'UI_MSS_MBase_Icon_{fs+"_S" if fs else "none"}.png')
            for fs in fs_list_upper
        ]
        self.minidialog_img = Image.open(self.pic_dir + 'UI_CMN_MiniDialog_01.png')
        self.sd_parts_img = Image.open(self.pic_dir + 'UI_RSL_MBase_Parts_01.png')
        self.dx_parts_img = Image.open(self.pic_dir + 'UI_RSL_MBase_Parts_02.png')

        # 字体
        self.titleFontName = 'src/static/adobe_simhei.otf'
        self.nameFontName = 'src/static/msyh.ttc'

    def update_settings(self, user_qq_id: str, best_table: BestTable):
        self.user_qq_id = user_qq_id
        self.best_table = best_table
        
    def _getCharWidth(self, o) -> int:
        widths = [
            (126, 1), (159, 0), (687, 1), (710, 0), (711, 1), (727, 0), (733, 1), (879, 0), (1154, 1), (1161, 0),
            (4347, 1), (4447, 2), (7467, 1), (7521, 0), (8369, 1), (8426, 0), (9000, 1), (9002, 2), (11021, 1),
            (12350, 2), (12351, 1), (12438, 2), (12442, 0), (19893, 2), (19967, 1), (55203, 2), (63743, 1),
            (64106, 2), (65039, 1), (65059, 0), (65131, 2), (65279, 1), (65376, 2), (65500, 1), (65510, 2),
            (120831, 1), (262141, 2), (1114109, 1),
        ]
        if o == 0xe or o == 0xf:
            return 0
        for num, wid in widths:
            if o <= num:
                return wid
        return 1

    def _columnWidth(self, s:str):
        res = 0
        for ch in s:
            res += self._getCharWidth(ord(ch))
        return res

    def _changeColumnWidth(self, s:str, len:int) -> str:
        res = 0
        sList = []
        for ch in s:
            res += self._getCharWidth(ord(ch))
            if res <= len:
                sList.append(ch)
        return ''.join(sList)

    def _resizePic(self, img:Image.Image, time:float) -> Image.Image:
        """按比例缩放图片"""
        return img.resize((int(img.size[0] * time), int(img.size[1] * time)))

    def _findRaPic(self, b50: bool = True) -> Image.Image:
        if b50:
            thresholds = [
                (14999, 11),
                (14499, 10),
                (13999, 9),
                (12999, 8),
                (11999, 7),
                (9999,  6),
                (6999,  5),
                (3999,  4),
                (1999,  3),
                (999,   2)
            ]
        else:
            thresholds = [
                (8499,  10),
                (7999,  9),
                (6999,  8),
                (5999,  7),
                (4999,  6),
                (3999,  5),
                (2999,  4),
                (1999,  3),
                (999,   2)
            ]
        num = 1
        for threshold, value in thresholds:
            if self.best_table.rating > threshold:
                num = value
                break
        if b50:
            return self.dxrating_img_list[num - 1]
        else:
            return self.dxrating_img_list_b40[num - 1]
        

    def _drawRating(self, ratingBaseImg: Image.Image, b50: bool = True) -> None:
        if b50:
            COLUMNS_RATING = self.COLUMNS_RATING
        else:
            COLUMNS_RATING = self.COLUMNS_RATING_b40

        theRa = self.best_table.rating
        i = 4

        if is_fools_day():
            theRa += 10000

        while theRa:
            digit = theRa % 10
            theRa = theRa // 10
            digitImg = self.numbers_img_list[digit].convert('RGBA')
            digitImg = self._resizePic(digitImg, 0.6)
            ratingBaseImg.paste(digitImg, (COLUMNS_RATING[i] - 2, 9), mask=digitImg.split()[3])
            i = i - 1

    async def _drawMusicBlock(self, chart: MusicChart, record: BestRecord, num: int, b50: bool = True) -> Image.Image:
        """绘制单个块"""

        if b50:
            MusicBlockW = self.MusicBlockW
        else:
            MusicBlockW = self.MusicBlockW_b40
        MusicBlockH = self.MusicBlockH

        # 背景
        temp = await mai_api.open_cover(chart.music_id)
        temp = self._resizePic(temp, MusicBlockW / temp.size[0])
        temp = temp.crop((0, (temp.size[1] - MusicBlockH) / 2, MusicBlockW, (temp.size[1] + MusicBlockH) / 2))
        temp = temp.filter(ImageFilter.GaussianBlur(3))
        temp = temp.point(lambda p: int(p * 0.72))
        
        # 折角
        levelTriangle = [(MusicBlockW, 0), (MusicBlockW - 27, 0), (MusicBlockW, 27)]
        color = [(69, 193, 36), (255, 186, 1), (255, 90, 102), (134, 49, 200), (217, 197, 233)]
        tempDraw = ImageDraw.Draw(temp)
        tempDraw.polygon(levelTriangle, color[chart.diff_index])

        # 标题
        font = ImageFont.truetype(self.titleFontName, 16, encoding='utf-8')
        title = chart.title
        if self._columnWidth(title) > 15:
            title = self._changeColumnWidth(title, 12) + '...'
        tempDraw.text((8, 8), title, 'white', font)

        # 达成率
        font = ImageFont.truetype(self.titleFontName, 12, encoding='utf-8')
        if is_fools_day():
            tempDraw.text((7, 28), f'{"%d" % int(record.achievements * 10000)}%', 'white', font)
        else:
            tempDraw.text((7, 28), f'{"%.4f" % record.achievements}%', 'white', font)

        # Rank
        rankImg = self.ranks_img_list[record.rank_id].convert('RGBA')
        if b50:
            rankImg = self._resizePic(rankImg, 0.5)
            temp.paste(rankImg, (50, 61), rankImg.split()[3])
        else:
            rankImg = self._resizePic(rankImg, 0.3)
            temp.paste(rankImg, (88, 28), rankImg.split()[3])

        # Combo
        if record.fc_id:
            comboImg = self.combos_img_list[record.fc_id].convert('RGBA')
            if b50:
                comboImg = self._resizePic(comboImg, 0.6)
                temp.paste(comboImg, (72, 22), comboImg.split()[3])
            else:
                comboImg = self._resizePic(comboImg, 0.45)
                temp.paste(comboImg, (119, 27), comboImg.split()[3])
            

        # FS
        if record.fs_id:
            fsImg = self.fss_img_list[record.fs_id].convert('RGBA')
            if b50:
                fsImg = self._resizePic(fsImg, 0.6)
                temp.paste(fsImg, (100, 22), fsImg.split()[3])

        # DS -> RA
        font = ImageFont.truetype(self.titleFontName, 12, encoding='utf-8')
        tempDraw.text((8, 44), f'Base: {chart.ds} -> {record.ra}', 'white', font)

        # 排名
        font = ImageFont.truetype(self.titleFontName, 18, encoding='utf-8')
        tempDraw.text((8, 60), f'#{num}', 'white', font)

        return temp

    def _drawBlankBlock(self, MusicBlockW, MusicBlockH) -> Image.Image:
        temp = Image.open(self.cover_dir + '00000.png').convert('RGB')
        temp = self._resizePic(temp, MusicBlockW / temp.size[0])
        temp = temp.crop((0, (temp.size[1] - MusicBlockH) / 2, MusicBlockW, (temp.size[1] + MusicBlockH) / 2))
        temp = temp.filter(ImageFilter.GaussianBlur(1))
        return temp


    async def _drawBestList(self, img: Image.Image, best_table: BestTable, b50: bool = True) -> None:
        """绘制主列表"""

        if b50:
            MusicBlockW = self.MusicBlockW
            COLUMNS_IMG = self.COLUMNS_IMG
        else:
            MusicBlockW = self.MusicBlockW_b40
            COLUMNS_IMG = self.COLUMNS_IMG_b40
        MusicBlockH = self.MusicBlockH
        ROWS_IMG = self.ROWS_IMG
        # 获取空白块
        MusicBlockBase = Image.new('RGBA', (MusicBlockW, MusicBlockH), 'black').point(lambda p: int(p * 0.8))
        BlankBlock = self._drawBlankBlock(MusicBlockW, MusicBlockH)


        # old best

        old_length = 35 if best_table.b50 else 25

        for num, (chart, record) in enumerate(best_table.old_best):
            if b50:
                i, j = num // 7, num % 7
            else:
                i, j = num // 5, num % 5
            MusicBlock = await self._drawMusicBlock(chart, record, num + 1, b50=b50)           
            img.paste(MusicBlockBase, (COLUMNS_IMG[j] + 5, ROWS_IMG[i + 1] + 5))
            img.paste(MusicBlock, (COLUMNS_IMG[j] + 4, ROWS_IMG[i + 1] + 4))

        for num in range(len(best_table.old_best), old_length):
            if b50:
                i, j = num // 7, num % 7
            else:
                i, j = num // 5, num % 5
            img.paste(MusicBlockBase, (COLUMNS_IMG[j] + 5, ROWS_IMG[i + 1] + 5))
            img.paste(BlankBlock, (COLUMNS_IMG[j] + 4, ROWS_IMG[i + 1] + 4))

        # new best

        new_length = 15

        for num, (chart, record) in enumerate(best_table.new_best):
            i, j = num // 3, num % 3
            MusicBlock = await self._drawMusicBlock(chart, record, num + 1, b50=b50)
            if b50:
                img.paste(MusicBlockBase, (COLUMNS_IMG[j + 8] + 5, ROWS_IMG[i + 1] + 5))
                img.paste(MusicBlock, (COLUMNS_IMG[j + 8] + 4, ROWS_IMG[i + 1] + 4))
            else:
                img.paste(MusicBlockBase, (COLUMNS_IMG[j + 6] + 5, ROWS_IMG[i + 1] + 5))
                img.paste(MusicBlock, (COLUMNS_IMG[j + 6] + 4, ROWS_IMG[i + 1] + 4))

        for num in range(len(best_table.new_best), new_length):
            i, j = num // 3, num % 3
            if b50:
                img.paste(MusicBlockBase, (COLUMNS_IMG[j + 8] + 5, ROWS_IMG[i + 1] + 5))
                img.paste(BlankBlock, (COLUMNS_IMG[j + 8] + 4, ROWS_IMG[i + 1] + 4))
            else:
                img.paste(MusicBlockBase, (COLUMNS_IMG[j + 6] + 5, ROWS_IMG[i + 1] + 5))
                img.paste(BlankBlock, (COLUMNS_IMG[j + 6] + 4, ROWS_IMG[i + 1] + 4))

    def _getUserSettings(self) -> Dict:
        try:
            with open('src/users/' + self.user_qq_id + '.json', "r") as f:
                user_settings = json.load(f)
        except:
            user_settings = {}

        return user_settings

    def _getPlate(self, user_settings: Optional[Dict] = None) -> Image.Image:
        """获取用户的 plate 图片"""

        user_plate_dir = user_settings.get('mai_plate_dir', None)

        if user_plate_dir:
            try:
                return Image.open(user_plate_dir).convert('RGBA')
            except:
                pass

        if self.best_table.user.plate in platename_to_file:
            return Image.open(self.plate_dir + 'main_plate/' + platename_to_file[self.best_table.user.plate]).convert('RGBA')
        else:
            try:
                return Image.open(self.plate_dir + 'private_plate/' + self.best_table.user.plate).convert('RGBA')
            except:
                plates = os.listdir(self.plate_dir + 'other_plate/')
                return Image.open(self.plate_dir + 'other_plate/' + random.choice(plates)).convert('RGBA')

    def _getAvatar(self, user_settings: Optional[Dict] = None) -> Image.Image:
        """获取用户的头像图片"""
        user_avatar_dir = user_settings.get('avatar_dir', None)
        iconLogo = get_qq_logo(user_avatar_dir)
        return iconLogo

    def _getDaniPlate(self) -> Image.Image:
        """获取用户的段位牌图片"""
        try:
            return self.daniplate_img_list[self.best_table.user.additional_rating]
        except IndexError:
            return self.daniplate_img_list[0]
        


    async def draw(self, b50: bool = True) -> Image.Image:
        """绘制b40/b50图片"""
        img = self.background.convert('RGB')

        user_settings = self._getUserSettings()

        # 牌子
        PlateImg = self._getPlate(user_settings).convert('RGBA')
        img.paste(PlateImg, (5, 3), mask=PlateImg.split()[3])
        
        # 头像
        iconLogo = self._getAvatar(user_settings).convert('RGBA')
        iconLogo = iconLogo.resize((98,98))
        img.paste(iconLogo, (14, 12), mask=iconLogo.split()[3])

        # rating
        ratingBaseImg = self._findRaPic(b50=b50).convert('RGBA')
        self._drawRating(ratingBaseImg, b50=b50)
        ratingBaseImg = self._resizePic(ratingBaseImg, 0.95)
        img.paste(ratingBaseImg, (119, 10), mask=ratingBaseImg.split()[3])

        # 姓名框
        namePlateImg = self.platemask_img.convert('RGBA')
        if b50:
            namePlateImg = namePlateImg.resize((253, 36))
        else:
            namePlateImg = namePlateImg.resize((253, 32))
        namePlateDraw = ImageDraw.Draw(namePlateImg)
        font1 = ImageFont.truetype(self.nameFontName, 22, encoding='unic')
        namePlateDraw.text((8, 0), ' '.join(list(self.best_table.user.nickname)), 'black', font1)

        # 段位牌 / dx图标
        if b50:
            nameDxImg = self._getDaniPlate().convert('RGBA')
            nameDxImg = self._resizePic(nameDxImg, 0.2)
        else:
            nameDxImg = self.namedx_img.convert('RGBA')
            nameDxImg = self._resizePic(nameDxImg, 0.9)
        namePlateImg.paste(nameDxImg, (200-30, 0+1), mask=nameDxImg.split()[3])
        img.paste(namePlateImg, (119, 47), mask=namePlateImg.split()[3])

        # 称号
        shougouImg = self.shougou_img.convert('RGBA')
        shougouDraw = ImageDraw.Draw(shougouImg)
        font2 = ImageFont.truetype(self.titleFontName, 14, encoding='utf-8')
        playCountInfo = f'Old: {self.best_table.old_rating} + New: {self.best_table.new_rating} = {self.best_table.rating}'
        shougouImgW, shougouImgH = shougouImg.size
        # playCountInfoW, playCountInfoH = shougouDraw.textsize(playCountInfo, font2)
        bbox = shougouDraw.textbbox((0, 0), playCountInfo, font=font2)
        playCountInfoW, playCountInfoH = bbox[2] - bbox[0], bbox[3] - bbox[1]
        textPos = ((shougouImgW - playCountInfoW - font2.getbbox(playCountInfo)[0]) / 2, 5)
        shougouDraw.text((textPos[0] - 1, textPos[1]), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0] + 1, textPos[1]), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0], textPos[1] - 1), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0], textPos[1] + 1), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0] - 1, textPos[1] - 1), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0] + 1, textPos[1] - 1), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0] - 1, textPos[1] + 1), playCountInfo, 'black', font2)
        shougouDraw.text((textPos[0] + 1, textPos[1] + 1), playCountInfo, 'black', font2)
        shougouDraw.text(textPos, playCountInfo, 'white', font2)
        shougouImg = self._resizePic(shougouImg, 0.88)
        img.paste(shougouImg, (119, 88), mask=shougouImg.split()[3])

        # 列表
        await self._drawBestList(img, self.best_table, b50=b50)

        # 生成作者板
        font3 = ImageFont.truetype(self.titleFontName, 12, encoding='utf-8')
        authorBoardImg = self.minidialog_img.convert('RGBA')
        authorBoardImg = self._resizePic(authorBoardImg, 0.35)
        authorBoardDraw = ImageDraw.Draw(authorBoardImg)
        authorBoardDraw.text((35, 18), '        Credit to\nXybBot & Chiyuki\n   Generated By\nRange & asdfbot', 'black', font3)
        img.paste(authorBoardImg, (1224, 19), mask=authorBoardImg.split()[3])

        # 生成小标题
        font = ImageFont.truetype(self.titleFontName, 17, encoding='utf-8')
        dxImg = self.dx_parts_img.convert('RGBA')
        imgdraw = ImageDraw.Draw(dxImg)
        imgdraw.text((17,22), "New:" + str(self.best_table.new_rating) , (0,0,0), font)
        if b50:
            img.paste(dxImg, (988, 65), mask=dxImg.split()[3])
        else:
            img.paste(dxImg, (890, 65), mask=dxImg.split()[3])
        sdImg = self.sd_parts_img.convert('RGBA')
        imgdraw = ImageDraw.Draw(sdImg)
        imgdraw.text((11,22), "Old:" + str(self.best_table.old_rating) , (0,0,0), font)
        if b50:
            img.paste(sdImg, (865, 65), mask=sdImg.split()[3])
        else:
            img.paste(sdImg, (758, 65), mask=sdImg.split()[3])

        return img

draw_best = DrawBest()


# async def generateb50_water_msg(player_data,userid):
#     sd_best = BestList(35)
#     dx_best = BestList(15)
#     for rec in player_data['records']:
#         if total_list.by_id(rec["song_id"]).is_new:
#             dx_best.push(ChartInfo.from_json(rec))
#         else:
#             sd_best.push(ChartInfo.from_json(rec))
#     sd_best.sort()
#     dx_best.sort()
#     id_record_list = []

#     fit_diffs = []
#     tempmusic = {
#         "id": "",
#         "title": "",
#         "dsdistance": 100,
#         "ds": 0,
#         "fitds": 0
#     }

#     min_ds_sd = 20
#     min_ds_dx = 20

#     for chartinfo in sd_best:
#         if chartinfo.ds < min_ds_sd:
#             min_ds_sd = chartinfo.ds
#         id_record_list.append(chartinfo.idNum)
#         try:
#             ds = float(chartinfo.ds)
#             fitds = float(total_list.by_id(chartinfo.idNum).stats[chartinfo.diff]['fit_diff'])
#         except:
#             continue
#         distance = ds-fitds
#         fit_diffs.append(distance)
#         if distance < tempmusic["dsdistance"]:
#             tempmusic["id"] = chartinfo.idNum
#             tempmusic["title"] = chartinfo.title
#             tempmusic["dsdistance"] = distance
#             tempmusic["ds"] = ds
#             tempmusic["fitds"] = fitds
#     for chartinfo in dx_best:
#         if chartinfo.ds < min_ds_dx:
#             min_ds_dx = chartinfo.ds
#         id_record_list.append(chartinfo.idNum)
#         try:
#             ds = float(chartinfo.ds)
#             fitds = float(total_list.by_id(chartinfo.idNum).stats[chartinfo.diff]['fit_diff'])
#         except:
#             continue
#         distance = ds-fitds
#         fit_diffs.append(distance)
#         if distance < tempmusic["dsdistance"]:
#             tempmusic["id"] = chartinfo.idNum
#             tempmusic["title"] = chartinfo.title
#             tempmusic["dsdistance"] = distance
#             tempmusic["ds"] = ds
#             tempmusic["fitds"] = fitds
#     img = await draw_water_pic(fit_diffs)
#     msg = f"您的b50中平均含水量为{np.mean(fit_diffs)*100:.2f}毫升。\n"
#     msg += f"含水量标准差为{np.std(fit_diffs)*100:.2f}毫升。\n"
#     msg += f"最有含金量谱面为 {tempmusic['id']}.{tempmusic['title']}\n"
#     msg += f"该谱面定数：{tempmusic['ds']} 拟合定数：{tempmusic['fitds']}\n"

#     min_ds = max(min_ds_sd,min_ds_dx)

#     musics = await total_list.filter(ds_range=(round(min_ds+0.1,1),round(min_ds+0.3,1)))
#     random.shuffle(musics)
#     temp = ""
#     for music in musics:
#         if int(music.id)<100000 and int(music.id) not in id_record_list:
#             for j in range(len(music['ds'])):
#                 if (round(min_ds+0.1,1)<=music['ds'][j]<=round(min_ds+0.4,1)) and ('fit_diff' in music.stats[j]) and (music.stats[j]['fit_diff']-music['ds'][j] > 0.1):
#                     temp = f"推荐降水推分金曲\n{music.id}.{music.title}[{diffs[j]}]\n定数：{music['ds'][j]}\n拟合定数：{music.stats[j]['fit_diff']}\n"
#                     break
#     msg += temp
#     return img, msg