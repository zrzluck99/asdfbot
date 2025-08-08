from nonebot import on_command, on_regex, on_message
from nonebot.params import CommandArg, Arg, RegexStr, ArgPlainText, RegexGroup
from nonebot.adapters.qq import Bot, Event, Message, MessageSegment, C2CMessageCreateEvent, GroupAtMessageCreateEvent
from nonebot.matcher import Matcher
from nonebot.rule import to_me
from nonebot.exception import FinishedException

from src.libraries.tool_range import offlineinit, opencc_converter
from src.libraries.maimai.maimai_type import Music, MusicList, Chart, BestRecord, BestRecordList
from src.libraries.maimai.maimaidx_music import total_list, best_record_list, refresh_music_data, refresh_alias_temp, refresh_player_full_data
from src.libraries.image_range import text_to_image
from src.libraries.maimai.maimai_best import BestTableGenerator, draw_best
from src.libraries.maimai.maimai_plate_query import *
from src.libraries.secrets import *
from src.libraries.maimai.maimai_info import draw_new_infos
from src.libraries.maimai.maimaidx_musicinfo import song_MessageSegment2, song_MessageSegment, chart_MessageSegment
from src.libraries.maimai.static_lists_and_dicts import pnconvert, platename_to_file, level_index_to_file, ptv, version_list, version_abbr_list, version_abbr_str
from src.libraries.maimai.find_cover import find_cover_id

from src.libraries.sendpics import pic_to_message_segment
from src.libraries.query import query_user
from src.libraries.april_fool import is_April_1st, kun_jin_kao

from PIL import Image, ImageDraw, ImageFont
import re,random,os,json
from pathlib import Path
from typing import List, Dict, Union, Optional, Tuple

DEFAULT_PRIORITY = 9

Root: Path = Path('src')
static: Path = Root / 'static'
cover_dir = 'src/static/mai/cover/'
long_dir_ = 'src/static/long/'
plate_path = "src/static/mai/plate/"

DIFF_LIST = ["绿", "黄", "红", "紫", "白"]

with open("src/static/musicGroup.json","r",encoding="utf-8") as f:
    musicGroup = json.load(f)

async def refresh(username: str) -> Tuple[int, str]:
    """
        刷新用户数据
        :param username: 用户名
        :return: (状态码, 状态信息)
        状态码:
            0: 成功
            1: 失败，不抛出异常
            2: 失败，抛出异常
    """

    if not username:
        return 2, "未找到此玩家，请先使用 /bind <用户名> 绑定您的用户名。"
    
    try:
        await refresh_player_full_data(username=username)
    except aiohttp.ClientResponseError as e:
        if e.status == 400:
            return 2, "未找到此玩家，请确登陆diving-fish 录入分数，并正确填写用户名与QQ号。"
        elif e.status == 403:
            return 1, "请勿频繁刷新成绩，稍后再试。"
        else:
            return 2, f"发生错误：{e.status} {e.message}"
    except asyncio.TimeoutError:
        return 1, "请求超时，请稍后再试。"
    except Exception as e:
        return 2, f"发生错误：{str(e)}"
    return 0, "刷新成功"

# test_test = on_command("测试", rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
# @test_test.handle()
# async def _(event: Event, message: Message = CommandArg()):
#     """
#         测试指令
#     """
#     music = await total_list.by_id(8)
#     await test_test.finish(f"{music.charts[3].stats.rank_dist}\n")


mr = on_regex(r"^/?.*maimai.*什么$", rule=to_me(), priority = 18 , block = True)
@mr.handle()
async def _():
    await mr.finish(song_MessageSegment2(total_list.random()))


search_music = on_regex(r"^/?查歌(.+)", rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@search_music.handle()
async def _(event: Event, regex_res: Tuple = RegexGroup()):
    
    name = regex_res[0].strip()
    if name == "":
        return
    res = await total_list.filter(title_search=name, pagination=(0, 50), order=["+music_id"])
    
    if res["music_count"] == 0:
        alias_music = await total_list.filt_by_name(name)
        if alias_music is None:
            await search_music.finish("没有找到这样的乐曲")
        else:
            await search_music.finish(MessageSegment.text("您要找的是不是：\n") + await song_MessageSegment2(alias_music))
    elif res["music_count"] == 1:
        # 只有一首歌
        music = res["music_list"][0]
        await search_music.finish(await song_MessageSegment2(music))
    else:
        music_list = res["music_list"]
        s = "找到以下乐曲（最多50首）：\n"
        for music in music_list:
            s += f"{music.id}. {music.title}\n"
        await search_music.finish(pic_to_message_segment(text_to_image(s), args={"fool": False, "shift_row": 0}))


query_chart = on_regex(
    r"^/?([绿黄红紫白]?) ?id ?([0-9]+)",
    rule=to_me(),
    priority=DEFAULT_PRIORITY,
    block=True
)
@query_chart.handle()
async def handle_query_chart(event: Event, regex_res: Tuple = RegexGroup()):
    
    LEVEL_LABELS = ['绿', '黄', '红', '紫', '白']
    
    # 1. 解析 ID 并拉取 music
    level_prefix, id_str = regex_res
    print(level_prefix, id_str)
    music_id = int(id_str)
    music = await total_list.by_id(music_id)
    if music is None:
        await query_chart.finish("未找到该谱面")

    # 2. 仅 ID 查询（无前缀，且 id<100000）
    if level_prefix == "" and music_id < 100000:
        await query_chart.finish(await song_MessageSegment2(music))
        return

    # 4. 指定颜色前缀
    diff_index = LEVEL_LABELS.index(level_prefix)
    chart = music.charts[diff_index]
    title = music.title

    await query_chart.finish(await chart_MessageSegment(chart, title))
    


wm_list = ['拼机', '推分', '越级', '下埋', '夜勤', '练底力', '练手法', '打旧框', '干饭', '抓绝赞', '收歌']
jrwm = on_command('今日舞萌', rule=to_me(), aliases={'今日mai'}, priority = DEFAULT_PRIORITY, block = True)
@jrwm.handle()
async def _(event: Event, message: Message = CommandArg()):
    userid = event.get_user_id()
    h = hash(userid)
    dawumeng = (h >> 250)&1
    dazhonger = (h >> 251)&1
    dayinji = (h >> 252)&1
    rp = h % 100
    wm_value = []
    for i in range(len(wm_list)):
        wm_value.append(h & 3)
        h >>= 2
    s = f"今日人品值：{rp}\n"
    for i in range(len(wm_list)):
        if wm_value[i] == 3:
            s += f'宜 {wm_list[i]}\n'
        elif wm_value[i] == 0:
            s += f'忌 {wm_list[i]}\n'
    if dazhonger == 1:
        s += "宜 打中二\n"
    else:
        s += "忌 打中二\n"
    if dayinji == 1:
        s += "宜 打音击\n"
    else:
        s += "忌 打音击\n"
   
    s += "然哥提醒您：打几把舞萌快去学习\n谁拆机，我拆谁\n"
    music = await total_list.random_by_seed(h)
    print(music.id, music.title, music.artist, music.genre, music.bpm, music.cn_version)

    if is_April_1st():
        s = kun_jin_kao(s)
    await jrwm.finish(MessageSegment.text(s) + await song_MessageSegment(music))


"""-----------(maibot删除功能：是什么歌)-----------"""


find_song = on_regex(r"^/?(.+)是什么歌$", rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@find_song.handle()
async def _(event: Event, regex_res: Tuple = RegexGroup()):
    name = regex_res[0].strip()
    if not name:
        await find_song.finish("请输入曲名。")
    music = await total_list.filt_by_name(name)
    if music is None:
        alias_json = await mai_api.query_alias(name=name, top_k=1)
        # print(alias_json)
        music_list = list(alias_json.get("results", {}))
        if not music_list:
            await find_song.finish("没有找到这样的乐曲。")
        music_id = music_list[0]
        music = await total_list.by_id(music_id)
    if music is None:
        pic_path : Path = static / "donotplay.png"
        await find_song.finish(MessageSegment.text("你要找的歌曲可能未登录国服或已删除。") + MessageSegment.file_image(pic_path))
    
    await find_song.finish(MessageSegment.text("您要找的是不是：\n") + await song_MessageSegment2(music))

# find_song_by_cover = on_message(priority = DEFAULT_PRIORITY, block = False)
# @find_song_by_cover.handle()
# async def _(event: Event, matcher: Matcher):
#     msg = json.loads(event.json())["message"]
#     if len(msg)!=2:
#         return
#     if msg[0]["type"] == "image" and msg[1]["type"] == "text":
#         img_url = msg[0]["data"]["file"]
#         text = msg[1]["data"]["text"]
#     elif msg[1]["type"] == "image" and msg[0]["type"] == "text":
#         img_url = msg[1]["data"]["file"]
#         text = msg[0]["data"]["text"]
#     else:
#         return
#     if text.strip() != "是什么歌":
#         return
#     matcher.stop_propagation()
#     try:
#         r = requests.get(img_url, stream=True)
#         file_io = io.BytesIO(r.content)
#         img = Image.open(file_io).convert("RGB")
#     except:
#         await find_song_by_cover.finish("图片获取失败")
#     music_id = find_cover_id(img)
#     cover_id = f'{int(music_id):05d}'
#     music = total_list.by_id(music_id)
#     if music == None:
#         filenames = os.listdir(cover_dir)
#         if cover_id + ".png" in filenames:
#             img = Image.open(cover_dir + cover_id + ".png").convert('RGB').resize((190, 190))
#             await find_song_by_cover.finish(MessageSegment.text("匹配到相似图片，但该歌曲未登录国服或已删除：\n") + pic_to_message_segment(img))
#         else:
#             await find_song_by_cover.finish("未知错误")
#     else:
#         await find_song_by_cover.finish(MessageSegment.text("您要找的是不是：\n") + song_MessageSegment2(music))

update_music_data = on_command("更新歌曲列表", rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@update_music_data.handle()
async def _(event: Event, message: Message = CommandArg()):
    try:
        await refresh_music_data()
    except Exception as e:
        raise e
    else:
        await update_music_data.finish("更新成功")

"""-----------谱师查歌&曲师查歌&新歌列表&BPM查歌&版本查歌-----------"""
hardlist = ['Basic','Advance','Expert','Master','Re:Master']

charter_search = on_command('谱师查歌', rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@charter_search.handle()
async def _(event: Event, message: Message = CommandArg()):
    """
        输入格式:
        谱师查歌 <谱师名> <分页(可选)>    
    """

    args = str(message).strip().split(" ")
    if len(args) == 0:
        await charter_search.finish("请输入谱师名。")
    charter = args[0].strip()
    page = 1  # 默认分页为1
    pagination = (0, 100)  # 默认分页参数，假设每页100条数据
    if len(args) > 1:
        if args[1].isdigit():
            page = int(args[1])
            if page < 0:
                await charter_search.finish("分页数不能为负数。")
            else:
                # 计算分页参数
                start = (page - 1) * 100
                pagination = (start, 100)  # 每页100条数据
        else:
            await charter_search.finish("分页参数必须为数字。")

    # 定义难度映射
    temp_dict = {
        2:"红",
        3:"紫",
        4:"白"
    }

    # 先查询所有符合谱师名的 chart 数量
    complete_data = await total_list.filter(charter=charter, diff_indices=[2, 3, 4])
    complete_count = complete_data['chart_count']
    if complete_count == 0:
        await charter_search.finish("没有找到结果，请检查搜索条件。")

    # 计算总页数
    total_pages = (complete_count + 99) // 100  # 每页100条数据
    if page > total_pages:
        page = total_pages  # 如果请求的页数超过总页数，则返回最后一页

    # 分页查询
    pagination_data = await total_list.filter(charter=charter, pagination=pagination, diff_indices=[2, 3, 4])
    pagination_list = pagination_data['music_list']

    # 处理分页查询结果
    s = f"\n结果如下: (第 {page}/{total_pages} 页)\n"
    k = page * 100 - 99  # 计算当前页的起始编号
    for music in pagination_list:
        for chart in music.charts:
            s += f"No.{k:03d} {chart.charter} [{music.id}][{temp_dict[chart.diff_index]}]{music.title}\n"
            k += 1

    await charter_search.finish(pic_to_message_segment(text_to_image(s), args={"fool": False, "shift_row": 0}))


artist_search = on_command('曲师查歌', rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@artist_search.handle()
async def _(event: Event, message: Message = CommandArg()):
    """
        输入格式:
        曲师查歌 <曲师名>   
    """

    artist = str(message).strip()
    if not artist:
        await artist_search.finish("请输入曲师名。")

    # 直接查询
    complete_data = await total_list.filter(artist=artist)
    complete_count = complete_data['music_count']
    if complete_count == 0:
        await artist_search.finish("没有找到结果，请检查搜索条件。")
    elif complete_count > 100:
        await artist_search.finish(f"结果过多（{complete_count} 条），请缩小搜索范围。")
    complete_list = complete_data['music_list']

    s = f"\n结果如下: \n"
    k = 1
    for music in complete_list:
        s += f"No.{k:03d} {music.artist} [{music.id}]{music.title}\n"
        k += 1

    await artist_search.finish(pic_to_message_segment(text_to_image(s), args={"fool": False, "shift_row": 0}))


new_search = on_command('新歌列表', rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@new_search.handle()
async def _(event: Event, message: Message = CommandArg()):
    """
        输入格式:
        新歌列表
    """

    new_data = await total_list.filter(is_new=True)
    new_list = new_data['music_list']
    s = "\n结果如下：\n"
    for i, music in enumerate(new_list):
        s += f"No.{i+1:02d} [{music.id}] {music.title}\n"
    await new_search.finish(pic_to_message_segment(text_to_image(s), args={"fool": False, "shift_row": 0}))


bpm_search = on_command('bpm查歌' , rule=to_me(), aliases={"BPM查歌","Bpm查歌"}, priority = DEFAULT_PRIORITY, block = True)
@bpm_search.handle()
async def _(event: Event, message: Message = CommandArg()):
    """
        输入格式:
        bpm查歌 <bpm值>
        或者
        bpm查歌 <bpm下限>-<bpm上限>
    """

    args = str(message).strip().split(" ")
    if len(args) == 0:
        await bpm_search.finish("请输入bpm值或范围。")
    
    try:
        if len(args) == 1:
            argv = args.strip().split("-")
            if len(argv) == 1:
                bpm = int(args[0])
                bpm_range = (bpm, bpm)
            elif len(argv) == 2:
                bpm_range = (int(argv[0]), int(argv[1]))
            else:
                await bpm_search.finish("输入格式错误。请使用：\n bpm查歌 <bpm值> 或 bpm查歌 <bpm下限>-<bpm上限>。")
        else:
            await bpm_search.finish("输入格式错误。请使用：\n bpm查歌 <bpm值> 或 bpm查歌 <bpm下限>-<bpm上限>。")
    except ValueError:
        await bpm_search.finish("bpm值必须是数字。")

    # 查询符合条件的曲目
    complete_data = await total_list.filter(bpm_range=bpm_range)
    complete_count = complete_data['music_count']
    if complete_count == 0:
        await bpm_search.finish("没有找到符合条件的曲目。")
    elif complete_count > 100:
        await bpm_search.finish(f"结果过多（{complete_count} 条），请缩小搜索范围。")
    
    complete_list = complete_data['music_list']
    s = f"\n结果如下: \n"
    for i, music in enumerate(complete_list):
        s += f"No.{i+1:03d} [{music.id}] {music.title} - BPM: {music.bpm}\n"

    await bpm_search.finish(pic_to_message_segment(text_to_image(s), args={"fool": False, "shift_row": 0}))


version_search = on_command('版本查歌', rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@version_search.handle()
async def _(event: Event, message: Message = CommandArg()):
    """
        输入格式:
        版本查歌 <版本缩写>
        版本缩写可以是：真、超、檄、橙、晓、桃、樱、紫、堇、白、雪、辉、熊、华、爽、煌、宙、星、祭、祝
    """

    msg = str(message).strip()
    if msg == "":
        await version_search.finish("请在版本查歌后输入版本缩写，如“版本查歌 真超檄”")

    search_list = set()  # 使用集合来存储版本，避免重复
    for char in msg:
        for i, version_abbr in enumerate(version_abbr_list):
            if opencc_converter.convert_jp2cn(char) in version_abbr:
                search_list.add(i)  # 将版本缩写的索引添加到集合中
                break
    
    if not search_list:
        await version_search.finish("版本缩写输入错误，请检查输入。")

    # 查询符合条件的曲目
    complete_data = await total_list.filter(version_indices=list(search_list))
    complete_count = complete_data['music_count']
    if complete_count == 0:
        await version_search.finish("没有找到符合条件的曲目。")
    elif complete_count > 200:
        await version_search.finish(f"结果过多（{complete_count} 条），请缩小搜索范围。")
    complete_list = complete_data['music_list']
    
    s = "\n结果如下：\n"
    for music in complete_list:
        s += f"[{music.id:05d}] {music.title} ({music.type}) {'/'.join(str(ds) for ds in music.ds)}\n"    

    await version_search.finish(pic_to_message_segment(text_to_image(s), args={"fool": False, "shift_row": 0}))


ds_search = on_command('定数查歌', rule=to_me(), priority = DEFAULT_PRIORITY, block = True)

@ds_search.handle()
async def _(event: Event, message: Message = CommandArg()):
    """
        输入格式:
        定数查歌 <定数> <分页(可选)>
        或
        定数查歌 <定数下限>-<定数上限> <分页(可选)>
    """

    args = str(message).strip().split(" ")
    if len(args) == 0:
        await ds_search.finish("请输入bpm值或范围。")
    
    try:
        if len(args) <= 2:
            argv = args[0].strip().split("-")
            if len(argv) == 1:
                ds = float(argv[0])
                ds_range = (ds, ds)
            elif len(argv) == 2:
                ds_range = (float(argv[0]), float(argv[1]))
            else:
                await ds_search.finish("输入格式错误。命令格式为：\n/定数查歌 <定数> <分页(可选)>\n/定数查歌 <定数下限> <定数上限> <分页(可选)>。")
        else:
            await ds_search.finish("输入格式错误。命令格式为：\n/定数查歌 <定数> <分页(可选)>\n/定数查歌 <定数下限> <定数上限> <分页(可选)>。")
    except ValueError:
        await ds_search.finish("定数必须是数字。")

    page = 1  # 默认分页为1
    pagination = (0, 100)  # 默认分页参数，假设每页100条数据
    if len(args) > 1:
        if args[1].isdigit():
            page = int(args[1])
            if page < 0:
                await ds_search.finish("分页数不能为负数。")
            else:
                # 计算分页参数
                start = (page - 1) * 100
                pagination = (start, 100)  # 每页100条数据
        else:
            await ds_search.finish("分页参数必须为数字。")

    # 先查询所有符合定数范围的 chart 数量
    complete_data = await total_list.filter(ds_range=ds_range, order=['+ds', '+music_id'])
    complete_count = complete_data['chart_count']
    if complete_count == 0:
        await ds_search.finish("没有找到结果，请检查搜索条件。")

    # 计算总页数
    total_pages = (complete_count + 99) // 100  # 每页100条数据
    if page > total_pages:
        page = total_pages  # 如果请求的页数超过总页数，则返回最后一页

    # 分页查询
    pagination_data = await total_list.filter(ds_range=ds_range, order=['+ds', '+music_id'], pagination=pagination)
    pagination_list = pagination_data['music_list']

    # 处理分页查询结果
    s = f"\n结果如下: (第 {page}/{total_pages} 页)\n"
    k = page * 100 - 99  # 计算当前页的起始编号
    for music in pagination_list:
        for chart in music.charts:
            s += f"No.{k:03d} [{music.id:>5}] [{DIFF_LIST[chart.diff_index]}] ({music.type}) {music.title} Lv. {chart.ds}\n"
            k += 1   

    await ds_search.finish(pic_to_message_segment(text_to_image(s), args={"fool": False, "shift_row": 0}))






revived_query = on_command('复活曲列表', rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@revived_query.handle()
async def _(event: Event, message: Message = CommandArg()):
    id_list = await total_list.get_revived_music_list()
    music_list = [await total_list.by_id(id) for id in id_list]
    s = "\n结果如下：\n"
    for music in music_list:
        s += f"[{music.id:05d}] {music.title} ({music.type}) from: <{music.cn_version}>\n"    
    await revived_query.finish(pic_to_message_segment(text_to_image(s), args={"fool": False, "shift_row": 0}))


plate_temp_str = version_abbr_str + opencc_converter.convert_cn2jp(version_abbr_str) + "霸覇舞"
plate_regex = rf'^/?([{plate_temp_str}])([極极将舞神者])(舞?)(?:进度|完成表|完成度)\s?(全?)$'

plate = on_regex(plate_regex, rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@plate.handle()
async def _plate(event: Event):
    arg = str(event.get_message().extract_plain_text())
    res = re.match(plate_regex, arg).groups()
    if ((opencc_converter.is_equal_kanji(res[0], "霸") ^ opencc_converter.is_equal_kanji(res[1], "者")) 
        or (opencc_converter.is_equal_kanji(res[1], "舞") ^ opencc_converter.is_equal_kanji(res[2], "舞"))):
        await plate.finish("¿")
    version = pnconvert[res[0]]
    if version == "霸":
        version = "舞"
    if version in "新的":
        ids = []
        for music in total_list:
            if music.cn_version == ptv["祭"]:
                ids.append(music.id)
    else:
        ids = musicGroup[version]
    if version == "舞":
        remids = musicGroup["舞ReMASTER"]
    else:
        remids = []
    
    status = {
        "MST_Re": {
            "V":0,
            "X":0,
            "-":len(remids)
        },
        "MST":{
            "V":0,
            "X":0,
            "-":len(ids)
        },
        "EXP":{
            "V":0,
            "X":0,
            "-":len(ids)
        },
        "ADV":{
            "V":0,
            "X":0,
            "-":len(ids)
        },
        "BSC":{
            "V":0,
            "X":0,
            "-":len(ids)
        }
    }

    userid = str(event.get_user_id())
    if not_exist_data(userid):
        await plate.send("每天第一次查询自动刷新成绩，可能需要较长时间。若需手动刷新请发送 刷新成绩")
    player_data,success = await read_full_data(userid)
    if success == 400:
        await plate.finish("未找到此玩家，请确登陆diving-fish 录入分数，并正确填写用户名与QQ号。")
    
    record_selected = {}
    for rec in player_data['records']:
        if ((str(rec['song_id']) in ids) and (rec['level_index'] != 4)) or ((str(rec['song_id']) in remids) and (rec['level_index'] == 4)):
            tmp = {
                "id":rec['song_id'],
                "level_index": rec['level_index'],
                "ds": rec['ds']
                }
            status[level_index_to_file[rec['level_index']]]["-"] -= 1
            if res[1] in "極极":
                tmp["cover"] = rec['fc']
                if rec['fc'] != "":
                    tmp["finished"] = True
                    status[level_index_to_file[rec['level_index']]]["V"] += 1
                else:
                    tmp["finished"] = False
                    status[level_index_to_file[rec['level_index']]]["X"] += 1
 
            if res[1] == "将":
                tmp["cover"] = rec['rate']
                if rec['achievements'] >= 100:
                    tmp["finished"] = True
                    status[level_index_to_file[rec['level_index']]]["V"] += 1
                else:
                    tmp["finished"] = False
                    status[level_index_to_file[rec['level_index']]]["X"] += 1

            if res[1] == "神":
                tmp["cover"] = rec['fc']
                if rec['fc'][:2] == 'ap':
                    tmp["finished"] = True
                    status[level_index_to_file[rec['level_index']]]["V"] += 1
                else:
                    tmp["finished"] = False
                    status[level_index_to_file[rec['level_index']]]["X"] += 1

            if res[1] == "舞":
                tmp["cover"] = rec['fs']
                if rec['fs'][:3] == 'fsd':
                    tmp["finished"] = True
                    status[level_index_to_file[rec['level_index']]]["V"] += 1
                else:
                    tmp["finished"] = False
                    status[level_index_to_file[rec['level_index']]]["X"] += 1

            if res[1] == "者":
                tmp["cover"] = rec['rate']
                if rec['achievements'] >= 80:
                    tmp["finished"] = True
                    status[level_index_to_file[rec['level_index']]]["V"] += 1
                else:
                    tmp["finished"] = False
                    status[level_index_to_file[rec['level_index']]]["X"] += 1

            record_selected[f"{rec['song_id']}_{rec['level_index']}"] = tmp

    if version != "舞":
        status.pop("MST_Re")

    records = {}
    for id in ids:
        music = total_list.by_id(id)
        if music == None:
            continue
        lev = music["level"][3]
        if lev not in records:
            records[lev] = []
        if f"{id}_3" in record_selected:
            records[lev].append(record_selected[f"{id}_3"])
        else:
            records[lev].append({
                "id":id,
                "level_index":3,
                "ds": music["ds"][3],
                "cover":"",
                "finished":False
            })
    for id in remids:
        music = total_list.by_id(id)
        lev = music["level"][4]
        if lev not in records:
            records[lev] = []
        if f"{id}_4" in record_selected:
            records[lev].append(record_selected[f"{id}_4"])
        else:
            records[lev].append({
                "id":id,
                "level_index":4,
                "ds": music["ds"][4],
                "cover":"",
                "finished":False
            })

    if version == "舞" and res[3] != "全":
        keys = list(records.keys())
        for key in keys:
            if key not in ["15","14+","14"]:
                records.pop(key)
    
    if res[1] in "極极":
        plate_file = "main_plate/" + platename_to_file[pnconvert[res[0]] + "极"]
    elif res[1] == "将":
        plate_file = "main_plate/" + platename_to_file[pnconvert[res[0]] + "将"]
    elif res[1] == "神":
        plate_file = "main_plate/" + platename_to_file[pnconvert[res[0]] + "神"]
    elif res[1] == "舞":
        plate_file = "main_plate/" + platename_to_file[pnconvert[res[0]] + "舞舞"]
    else:
        plate_file = "main_plate/" + platename_to_file["霸者"]

    dacheng = True
    for diff in status:
        if status[diff]["-"] != 0 or status[diff]["X"] != 0:
            dacheng = False
            break

    queren = True
    for lev in records:
        if lev in ["15","14+","14","13+"]:
            for rec in records[lev]:
                if not rec["finished"]:
                    queren = False
                    break
            if not queren:
                break

    info = {
        "qq": str(event.get_user_id()),
        "plate": plate_file,
        "status": status,
        "queren": queren,
        "dacheng": dacheng
    }
    img = await draw_final_rank_list(info = info,records = records)

    if img.size[1]>3000:
        b64 = pic_to_message_segment(img, format="JPEG")
    else:
        b64 = pic_to_message_segment(img, format="PNG")

    if version == "舞" and res[3] != "全":
        s = "舞系默认只展示14难度及以上。若需查看全部进度请在查询命令后加上“全”，如“舞将进度全”\n"
    elif version in "熊華":
        s = "请注意，国服熊代与華代成就需一同清谱舞萌DX版本获得\n"
    elif version in "爽煌":
        s = "请注意，国服爽代与煌代成就需一同清谱舞萌DX2021版本获得\n"
    elif version in "宙星":
        s = "请注意，国服宙代与星代成就需一同清谱舞萌DX2022版本获得\n"
    elif version in "祭祝":
        s = "请注意，国服祭代与祝代成就需一同清谱舞萌DX2023版本获得\n"
    elif version in "真" and res[1] == "将":
        s = "真代没有真将，但是我可以假装帮你查\n"
    else:
        s = ""

    s += "您的" + event.get_message().extract_plain_text().strip('/') + "为：" + "\n"
    await plate.finish(
        MessageSegment.text(s) + \
        b64
    )


refresh_data = on_command("刷新成绩", rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@refresh_data.handle()
async def _(event: Event, message: Message = CommandArg()):
    userid = str(event.get_user_id())
    username = query_user(userid)
    status, message = await refresh(username)
    await refresh_data.finish(message)
        



levelquery = on_regex(r"^/?([0-9]+)([＋\+]?)(?:进度|完成表|完成度|定数表)$",rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@levelquery.handle()
async def _levelquery(event: Event):
    regex = r"^/?([0-9]+)([＋\+]?)(?:进度|完成表|完成度|定数表)$"
    res = re.match(regex, str(event.get_message().extract_plain_text()))
    level = int(res.group(1))
    if (level >= 15) or (level <= 0):
        await levelquery.finish("蓝的盆")
    
    userid = str(event.get_user_id())
    if str(event.get_message().extract_plain_text()).endswith("定数表"):
        player_data = {
            'records':[]
        }
    else:
        if not_exist_data(userid):
            await levelquery.send("每天第一次查询自动刷新成绩，可能需要较长时间。若需手动刷新请发送 刷新成绩")
        player_data,success = await read_full_data(userid)
        if success == 400:
            await levelquery.finish("未找到此玩家，请确登陆diving-fish 录入分数，并正确填写用户名与QQ号。")
    
    plus = res.group(2)
    records = {}
    if plus != "":
        for suffix in [".6",".7",".8",".9"]:
            records[str(level)+suffix] = []
    else:
        for suffix in [".0",".1",".2",".3",".4",".5"]:
            records[str(level)+suffix] = []
    
    record_selected = {}
    for rec in player_data['records']:
        if str(rec['ds']) in records:
            tmp = {
                "id":rec['song_id'],
                "level_index": rec['level_index'],
                "ds": rec['ds']
                }
            if rec['fc'][:2] == 'ap':
                tmp['cover'] = rec['fc']
            else:
                tmp['cover'] = rec['rate']
            if rec['achievements']>=100:
                tmp['finished'] = True
            else:
                tmp['finished'] = False
            record_selected[f"{rec['song_id']}_{rec['level_index']}"] = tmp
            
    for music in music_data:
        if int(music["id"]) >= 100000:
            continue
        for i,ds in enumerate(music['ds']):
            if str(ds) in records:
                if f"{music['id']}_{i}" in record_selected:
                    records[str(ds)].append(record_selected[f"{music['id']}_{i}"])
                else:
                    records[str(ds)].append({
                    "id": music['id'],
                    "level_index": i,
                    "ds": ds,
                    "cover": "",
                    "finished": False
                    })

    plate_file_path = "other_plate/" + random.choice(os.listdir(plate_path + "other_plate"))

    info = {
        "qq": str(event.get_user_id()),
        "plate": plate_file_path,
        "status":{},
        "queren": False,
        "dacheng": False
    }

    img = await draw_final_rank_list(info = info,records = records)
    
    if img.size[1]>3000:
        b64 = pic_to_message_segment(img,format="JPEG")
    else:
        b64 = pic_to_message_segment(img,format="PNG")

    await levelquery.finish(
        MessageSegment.text("您的" + event.get_message().extract_plain_text().strip('/') + "为：") + \
        b64
    )
    

singlequery = on_command("info", rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@singlequery.handle()
async def _(event: Event, message: Message = CommandArg()):
    """
        输入格式:
        info <id> 或 info <部分歌名>
        例如：info 12345 或 info 提亚马特
    """
    msg = str(message).strip()
    if msg == "":
        await singlequery.finish("请输入正确的查询命令，格式：info+id或info+部分歌名。")
    
    music = None
    if msg.isdigit():
        # 如果是纯数字，尝试作为歌曲ID查询
        music = await total_list.by_id(int(msg))
    if music is None:
        # 如果不是纯数字，尝试作为歌曲名查询
        music = await total_list.filt_by_name(msg)
    if music is None:
        await singlequery.finish("没有找到这样的乐曲。")


    userid = str(event.get_user_id())
    username = query_user(userid)
    if not username:
        await singlequery.finish("未找到此玩家，请先使用 /bind <用户名> 绑定您的用户名。")

    if await database_api.check_user_outdated(username):
        await singlequery.send("每天第一次查询自动刷新成绩，可能需要较长时间。若需手动刷新请发送 刷新成绩")
        status, message = await refresh(username)
        if status == 2:
            await singlequery.finish(message)
        elif status == 1:
            await singlequery.send(message)


    chart_list = [(music.id, diff) for diff in music.diff]
    record_result = await best_record_list.filter(user_id=username, chart_list=chart_list, order=['+music_id', '+diff_index'])
    if record_result['record_count'] == 0:
        await singlequery.finish(f"您查询的是{music.title}\n没有查到成绩。")

    final_img = await draw_new_infos(record_result['record_list'])
    await singlequery.finish(pic_to_message_segment(final_img))




def get_compare_value(record:dict):
    try:
        ds = float(total_list.by_id(record['song_id']).stats[record['level_index']]['fit_diff'])
    except:
        ds = record['ds']
    return ds + max(record['achievements']-100.8,0)


"""------------随机牛逼/随机丢人------------"""
random_niubi = on_regex(r'^/?随机([牛菜AaFf][逼PpDd][Xx]?)\s*(\d*)$', rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@random_niubi.handle()
async def _random_niubi(event: Event, regex_res: Tuple = RegexGroup()):
    userid = str(event.get_user_id())
    choice, msg = regex_res
    choice = choice.lower()
    
    if choice not in ["牛逼", "菜逼", "ap", "fdx"]:
        return

    username = query_user(userid)
    if not username:
        await random_niubi.finish("未找到此玩家，请先使用 /bind <用户名> 绑定您的用户名。")

    if await database_api.check_user_outdated(username):
        await random_niubi.send("每天第一次查询自动刷新成绩，可能需要较长时间。若需手动刷新请发送 刷新成绩")
        status, message = await refresh(username)
        if status == 2:
            await random_niubi.finish(message)
        elif status == 1:
            await random_niubi.send(message)
    
    # 判断msg是否为数字
    n = 1
    if msg.isdigit():
        n = int(msg) if 0 < int(msg) <= 10 else 1
        
    music_result = await total_list.filter(diff_indices=[3, 4])
    music_list = music_result['music_list']
    chart_tuple_list = [(music.id, diff) for music in music_list for diff in music.diff]
    # 一次 sqlite 查询最多 900 条数据，将查询结果分批次获取
    record_list = []
    for i in range(0, len(chart_tuple_list), 900):
        chart_batch = chart_tuple_list[i:i + 900]
        if choice == "牛逼":
            # 随机牛逼，获取最好的成绩
            achievements_range = (100.8, 101.1)
            record_result = await best_record_list.filter(user_id=username, chart_list=chart_batch, achievements_range=achievements_range)
        elif choice == "菜逼":
            # 随机菜逼，获取最差的成绩
            achievements_range = (0, 97.0)
            record_result = await best_record_list.filter(user_id=username, chart_list=chart_batch, achievements_range=achievements_range)
        elif choice == "ap":
            # 随机AP，获取AP成绩
            record_result = await best_record_list.filter(user_id=username, chart_list=chart_batch, fc_indices=[3, 4])
        elif choice == "fdx":
            # 随机FDX，获取FDX成绩
            record_result = await best_record_list.filter(user_id=username, chart_list=chart_batch, fs_indices=[4, 5])
        record_list.extend(record_result['record_list'])

    if len(record_list) == 0:
        await random_niubi.finish(f"您没有{choice}的成绩，无法随机{choice}。")
    if len(record_list) > n:
        records = random.sample(record_list, n)
    else:
        records = record_list

    final_img = await draw_new_infos(records)
    
    await random_niubi.finish(pic_to_message_segment(final_img))






"""-----------------随n个x-----------------"""
rand_n = on_regex(r"^/?随([0-9]+)?[个|首]([标SsDd][准DdXx])?([绿黄红紫白])?([0-9]+)([＋\+])?(只要|不要)?(.*)?", rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@rand_n.handle()
async def _rand_n(event: Event, regex_res: Tuple = RegexGroup()):
    """
        输入格式:
        随<数量>个(标准|sd|dx)(难度)<等级>(+)(只要|不要)(条件)
        例如：随3个sd红10+只要真
    """
    # 龙图
    dirlist = os.listdir(long_dir_)
    a = random.randint(0,len(dirlist)-1)
    img_path = Path(long_dir_ + dirlist[a])



    n, ctype, diff, level, plus, condition, versions = regex_res

    if n is None or n == "":
        n = 1
    n = int(n)
    if n <= 0 or n > 30:
        await rand_n.finish(MessageSegment.file_image(img_path))

    ctype = ctype.upper() if ctype else ""
    if ctype not in ["", "标准", "SD", "DX"]:
        await rand_n.finish(MessageSegment.file_image(img_path))
    else:
        ctype = "SD" if ctype == "标准" else ctype

    if diff:
        diff = DIFF_LIST.index(diff)

    level = int(level)
    if level <= 0 or level > 15:
        await rand_n.finish(MessageSegment.file_image(img_path))
    level = f"{level}+" if plus else str(level)

    versions = versions.strip()
    if condition:
        if not versions:
            await rand_n.finish(MessageSegment.file_image(img_path))
        condition = True if condition.startswith("只要") else False
    else:
        condition = False
    version_pickup = set() if condition else set([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]) 

    if versions:
        for c in versions:
            if c not in version_abbr_str:
                pass
                # await rand_n.finish(MessageSegment.file_image(img_path))
            else:
                c = opencc_converter.convert_jp2cn(c)
                for index, version_abbr in enumerate(version_abbr_list):
                    if c in version_abbr:
                        if condition:
                            version_pickup.add(index)
                        else:
                            version_pickup.discard(index)

    
    result = await total_list.filter(
        types=ctype if ctype else ["SD", "DX"],
        diff_indices=[diff] if diff is not None else [0, 1, 2, 3, 4],
        levels=level,
        version_indices=list(version_pickup),
        order=['+music_id']
    )
    
    music_list = result['music_list']
    music_count = result['music_count']

    s = ""
    if music_count == 0:
        await rand_n.finish("没有这样的乐曲哦。\n")
    elif music_count < n:
        s += f"满足条件的谱面只有 {music_count} 个，结果如下：\n"
    else:
        s += f"结果如下：\n"
        music_list = random.sample(music_list, n)
    
    if len(music_list) > 1:
        s += "\n"
        for i, music in enumerate(music_list):
            s += f"No.{i+1:>2} 【{music.id}】{music.title}\n"
        msg = pic_to_message_segment(text_to_image(s))
    else:
        # 注意：这里 music_list 中的歌曲 chart 不全，需要通过 music.id 获取完整的歌曲信息 
        music = await total_list.by_id(music_list[0].id)
        msg = MessageSegment.text(s) + await song_MessageSegment2(music)

    await rand_n.finish(msg)

        

"""-----------------分数列表-----------------"""
fslb = on_regex(r"^/?([0-9]+)([＋\+]?)分数列?表([1-9]?)$", rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@fslb.handle()
async def _fslb(event: Event):
    pattern = r"^/?([0-9]+)([＋\+]?)分数列?表([1-9]?)$"
    res = re.match(pattern, str(event.get_message().extract_plain_text()))
    level = int(res.group(1))
    if (level > 15) | (level < 1) :
        return
    if res.group(2) == '':
        ds_l = level
        ds_h = level + 0.6
    else:
        ds_l = level + 0.7
        ds_h = level + 0.9
    userid = str(event.get_user_id())
    if not_exist_data(userid):
        await fslb.send("每天第一次查询自动刷新成绩，可能需要较长时间。若需手动刷新请发送 刷新成绩")
    player_data,success = await read_full_data(userid)
    if success == 400:
        await fslb.finish("未找到此玩家，请确登陆diving-fish 录入分数，并正确填写用户名与QQ号。")
    querylist = []
    for song in player_data['records']:
        if song['ds'] >= ds_l and song['ds'] <= ds_h:
            querylist.append(song)
    if len(querylist) == 0:
        await fslb.finish("您还没有打过这个定数的谱面")
    querylist.sort(key = lambda x:x["achievements"],reverse=True)
    leveldict = ["绿","黄","红","紫","白"]
    s = f"""您的{res.group(1)}{res.group(2)}分数列表为:"""
    if res.group(3) == '':
        page = 1
    else:
        page = int(res.group(3))
    if (page-1)*100>len(querylist)-1:
        page = int(len(querylist)/100-0.01)+1
    maxpage = int(len(querylist)/100-0.01)+1
    querylist = querylist[(page-1)*100:page*100]

    for i,song in enumerate(querylist):
        addstr = ""
        if song['fc']:
            addstr += f"({song['fc']})"
        if song['fs']:
            addstr += f"({song['fs']})"
        s += f"""
{((page-1)*100 + i+1):>3}:【ID:{song['song_id']:>5}】{song['achievements']:>8.4f}% ({song['type']})({leveldict[song['level_index']]}) {song['title']}{addstr}"""
    s += f"""
第{page}页，共{maxpage}页"""
    await fslb.finish(pic_to_message_segment(text_to_image(s), args={"fool": False, "shift_row": 0}))

"""-----------------别名增删查----------------"""
select_alias_vip = on_command("别名", rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@select_alias_vip.handle()
async def _select_alias_vip(event: Event, message: Message = CommandArg()):
    msg = str(message).strip().split(" ")
    if len(msg) == 1 and msg[0] != "":
        id = msg[0]
        with open("src/static/all_alias_temp.json", "r", encoding='utf-8') as fp:
            alias_data = json.load(fp)
        if id not in alias_data:
            await select_alias_vip.finish("未找到该乐曲，请直接输入乐曲id。")
        else:
            s = f"{id}. {alias_data[id]['Name']}的别名有：\n"
            for i in range(len(alias_data[id]['Alias'])):
                if alias_data[id]['Alias'][i] != total_list.by_id(id)['title']:
                    s += f"{alias_data[id]['Alias'][i]}\n"
            await select_alias_vip.finish(pic_to_message_segment(text_to_image(s), args={"fool": False, "shift_row": 0}))
    elif len(msg) == 3:
        userid = str(event.get_user_id())
        id = msg[1]
        with open("src/static/all_alias_temp.json", "r", encoding='utf-8') as fp:
            alias_data = json.load(fp)
        if id not in alias_data:
            await select_alias_vip.finish("未找到该乐曲，请直接输入乐曲id。")
        else:
            if ("增" in msg[0]) or ("加" in msg[0]):
                if msg[2] in alias_data[id]["Alias"]:
                    await select_alias_vip.finish("该别名已存在。")
                else:
                    with open("src/static/alias_pre_process_add.json", "r", encoding='utf-8') as fp:
                        alias_pre_process_add = json.load(fp)
                    if id in alias_pre_process_add:
                        alias_pre_process_add[id].append(msg[2])
                    else:
                        alias_pre_process_add[id] = [msg[2]]
                    with open("src/static/alias_pre_process_add.json", "w", encoding='utf-8') as fp:
                        json.dump(alias_pre_process_add, fp, ensure_ascii=False, indent=4)
                    with open("src/static/alias_pre_process_remove.json", "r", encoding='utf-8') as fp:
                        alias_pre_process_remove = json.load(fp)
                    if id in alias_pre_process_remove:
                        if msg[2] in alias_pre_process_remove[id]:
                            alias_pre_process_remove[id].remove(msg[2])
                    with open("src/static/alias_pre_process_remove.json", "w", encoding='utf-8') as fp:
                        json.dump(alias_pre_process_remove, fp, ensure_ascii=False, indent=4)
                    with open("src/static/alias_log.csv", "a", encoding='utf-8') as fp:
                        fp.write(f"{userid},{','.join(msg)}\n")
                    if refresh_alias_temp():
                        await select_alias_vip.finish(f"添加成功。\n已为 {id}.{alias_data[id]['Name']} 添加别名：\n{msg[2]}")
            elif ("删" in msg[0]) or ("减" in msg[0]):
                if msg[2] not in alias_data[id]["Alias"]:
                    await select_alias_vip.finish("该别名不存在。")
                else:
                    with open("src/static/alias_pre_process_remove.json", "r", encoding='utf-8') as fp:
                        alias_pre_process_remove = json.load(fp)
                    if id in alias_pre_process_remove:
                        alias_pre_process_remove[id].append(msg[2])
                    else:
                        alias_pre_process_remove[id] = [msg[2]]
                    with open("src/static/alias_pre_process_remove.json", "w", encoding='utf-8') as fp:
                        json.dump(alias_pre_process_remove, fp, ensure_ascii=False, indent=4)
                    with open("src/static/alias_pre_process_add.json", "r", encoding='utf-8') as fp:
                        alias_pre_process_add = json.load(fp)
                    if id in alias_pre_process_add:
                        if msg[2] in alias_pre_process_add[id]:
                            alias_pre_process_add[id].remove(msg[2])
                    with open("src/static/alias_pre_process_add.json", "w", encoding='utf-8') as fp:
                        json.dump(alias_pre_process_add, fp, ensure_ascii=False, indent=4)
                    with open("src/static/alias_log.csv", "a", encoding='utf-8') as fp:
                        fp.write(f"{userid},{','.join(msg)}\n")
                    if refresh_alias_temp():
                        await select_alias_vip.finish("删除成功")
            else:
                await select_alias_vip.finish('输入格式错误。\n查别名请输入“别名 id”\n增加别名请输入“别名 增 id 别名”\n删除别名请输入“别名 删 id 别名”')

    else:
        await select_alias_vip.finish('输入格式错误。\n查别名请输入“别名 id”\n增加别名请输入“别名 增 id 别名”\n删除别名请输入“别名 删 id 别名”\n')

"""-----------------有什么别名----------------"""
select_alias = on_regex(r"^/?([0-9]+)有什么别名$", rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@select_alias.handle()
async def _select_alias(event: Event):
    msg = str(event.get_message().extract_plain_text()).strip()
    pattern = r"^/?([0-9]+)有什么别名$"
    res = re.match(pattern, msg)
    id = str(int(res.group(1)))
    with open("src/static/all_alias_temp.json", "r", encoding='utf-8') as fp:
        alias_data = json.load(fp)
    if id not in alias_data:
        await select_alias.finish("未找到该乐曲，输入乐曲id。")
    else:
        s = f"{id}. {alias_data[id]['Name']}的别名有：\n"
        for i in range(1, len(alias_data[id]['Alias'])):
            s += f"{alias_data[id]['Alias'][i]}\n"
        await select_alias.finish(pic_to_message_segment(text_to_image(s), args={"fool": False, "shift_row": 0}))

"""-----------------b40----------------"""
best_40_pic = on_command('b40', rule=to_me(), aliases={"逼四十", "逼40", "比四十", "比40", }, priority = DEFAULT_PRIORITY, block = True)
@best_40_pic.handle()
async def _(event: Event, message: Message = CommandArg()):
    username = str(message).strip()

    if not username:
        userid = str(event.get_user_id())
        username = query_user(userid)
    else:
        userid = ""

    if not username:
        await best_40_pic.finish("未找到此玩家，请先使用 /bind <用户名> 绑定您的用户名。")

    if await database_api.check_user_outdated(username):
        await best_40_pic.send("每天第一次查询自动刷新成绩，可能需要较长时间。若需手动刷新请发送 刷新成绩")
        status, message = await refresh(username)
        if status == 2:
            await best_40_pic.finish(message)
        elif status == 1:
            await best_40_pic.send(message)

    best_table = await BestTableGenerator.table_b40(username)
    draw_best.update_settings(userid, best_table)
    img = await draw_best.draw(b50=False)
    await best_40_pic.finish(MessageSegment.text("旧版b40已停止维护，对结果不负责")+pic_to_message_segment(img, args={"shift_row": 0}))

"""-----------------b50----------------"""
best_50_pic = on_command('b50', rule=to_me(), aliases={"逼五十", "逼50", "比五十", "比50", }, priority = DEFAULT_PRIORITY, block = True)
@best_50_pic.handle()
async def _(event: Event, message: Message = CommandArg()):
    username = str(message).strip()
    if username == "娱乐版":
        await best_50_pic.send("提示: 请使用 /娱乐版b50 来查询娱乐版b50。")

    if not username:
        userid = str(event.get_user_id())
        username = query_user(userid)
    else:
        userid = ""

    if not username:
        await best_50_pic.finish("未找到此玩家，请先使用 /bind <用户名> 绑定您的用户名。")

    if await database_api.check_user_outdated(username):
        await best_50_pic.send("每天第一次查询自动刷新成绩，可能需要较长时间。若需手动刷新请发送 刷新成绩")
        status, message = await refresh(username)
        if status == 2:
            await best_50_pic.finish(message)
        elif status == 1:
            await best_50_pic.send(message)

    best_table = await BestTableGenerator.table_b50(username)
    draw_best.update_settings(userid, best_table)
    img = await draw_best.draw()
    await best_50_pic.finish(pic_to_message_segment(img, args={"shift_row": 0}))

"""-----------------apb50----------------"""
apb50 = on_command("apb50", rule=to_me(), aliases = {"ap50"}, priority = DEFAULT_PRIORITY, block = True)
@apb50.handle()
async def _(event: Event, message: Message = CommandArg()):
    username = str(message).strip()

    if not username:
        userid = str(event.get_user_id())
        username = query_user(userid)
    else:
        userid = ""

    if not username:
        await apb50.finish("未找到此玩家，请先使用 /bind <用户名> 绑定您的用户名。")

    if await database_api.check_user_outdated(username):
        await apb50.send("每天第一次查询自动刷新成绩，可能需要较长时间。若需手动刷新请发送 刷新成绩")
        status, message = await refresh(username)
        if status == 2:
            await apb50.finish(message)
        elif status == 1:
            await apb50.send(message)

    best_table = await BestTableGenerator.table_b50(username, fc_indices=[3, 4])
    draw_best.update_settings(userid, best_table)
    img = await draw_best.draw()
    await apb50.finish(pic_to_message_segment(img, args={"shift_row": 0}))

"""-----------------fdxb50----------------"""
fdxb50 = on_command("fdxb50", rule=to_me(), aliases = {"fdx50"}, priority = DEFAULT_PRIORITY, block = True)
@fdxb50.handle()
async def _(event: Event, message: Message = CommandArg()):
    username = str(message).strip()

    if not username:
        userid = str(event.get_user_id())
        username = query_user(userid)
    else:
        userid = ""

    if not username:
        await fdxb50.finish("未找到此玩家，请先使用 /bind <用户名> 绑定您的用户名。")

    if await database_api.check_user_outdated(username):
        await fdxb50.send("每天第一次查询自动刷新成绩，可能需要较长时间。若需手动刷新请发送 刷新成绩")
        status, message = await refresh(username)
        if status == 2:
            await fdxb50.finish(message)
        elif status == 1:
            await fdxb50.send(message)

    best_table = await BestTableGenerator.table_b50(username, fs_indices=[4, 5])
    draw_best.update_settings(userid, best_table)
    img = await draw_best.draw()
    await fdxb50.finish(pic_to_message_segment(img, args={"shift_row": 0}))

"""-----------------b50娱乐版----------------"""
b50_yuleban = on_command('娱乐版b50', rule=to_me(), aliases={"娱乐版逼五十"}, priority = DEFAULT_PRIORITY - 1, block = True)
@b50_yuleban.handle()
async def _(event: Event, message: Message = CommandArg()):
    username = str(message).strip()

    if not username:
        userid = str(event.get_user_id())
        username = query_user(userid)
    else:
        userid = ""

    if not username:
        await b50_yuleban.finish("未找到此玩家，请先使用 /bind <用户名> 绑定您的用户名。")

    if await database_api.check_user_outdated(username):
        await b50_yuleban.send("每天第一次查询自动刷新成绩，可能需要较长时间。若需手动刷新请发送 刷新成绩")
        status, message = await refresh(username)
        if status == 2:
            await b50_yuleban.finish(message)
        elif status == 1:
            await b50_yuleban.send(message)

    best_table = await BestTableGenerator.table_stats(username)
    draw_best.update_settings(userid, best_table)
    img = await draw_best.draw()
    msg = "\n"
    msg += "本功能根据拟合定数进行计算，仅供娱乐，不具有任何参考价值，请勿上纲上线！\n下图为您b50的娱乐版\n"
    await b50_yuleban.finish(MessageSegment.text(msg) + pic_to_message_segment(img, args={"shift_row": 0}))

"""-----------------b50水分检测----------------"""
b50_water = on_command('b50水分检测', rule=to_me(), aliases={"逼五十水分检测"}, priority = DEFAULT_PRIORITY - 1, block = True)
@b50_water.handle()
async def _b50_water(event: Event, message: Message = CommandArg()):
    s = str(message).strip()
    if s != "":
        return
    
    userid = str(event.get_user_id())
    if not_exist_data(userid):
        await b50_water.send("每天第一次查询自动刷新成绩，可能需要较长时间。若需手动刷新请发送 刷新成绩")
    player_data,success = await read_full_data(userid)
    if success == 400:
        await b50_water.finish("未找到此玩家，请确登陆diving-fish 录入分数，并正确填写用户名与QQ号。")
    msg = "\n"
    msg += "本功能根据拟合定数进行计算，仅供娱乐，不具有任何参考价值，请勿上纲上线！\n下图为您b50的含水图\n"
    img,msg2 = await generateb50_water_msg(player_data,userid)
    await b50_water.finish(MessageSegment.text(msg) + pic_to_message_segment(img) + MessageSegment.text(msg2))


    







plate_change = on_command('plate', rule=to_me(), priority = DEFAULT_PRIORITY - 1, block = True)
@plate_change.handle()
async def _plate_change(event: Event, message: Message = CommandArg()):
    s = str(message).strip()
    userid = str(event.get_user_id())

    if s:
        try:
            with open("src/static/mai/plate_info.json","r") as f:
                plate_info = json.load(f)
        except:
            plate_info = {}
        
        try:
            with open(f"src/users/{userid}.json","r") as f:
                user_settings = json.load(f)
        except:
            user_settings = {}

        try:
            user_settings["mai_plate_dir"] = f"src/static/mai/plate/other_plate/{plate_info[s]}"
        except:
            user_settings["mai_plate_dir"] = ""

        with open(f"src/users/{userid}.json","w") as f:
            json.dump(user_settings, f, indent=4)
        await plate_change.finish("背景板设置成功~")
    

@plate_change.got("message2", prompt=Message([
            MessageSegment.file_image(Path("src/static/mai/plate_info.png")),
            MessageSegment.text("请输入编号，若取消使用自定义背景板请输入0")
        ]))
async def _(event: Event, message2: str = ArgPlainText()):
    s = str(message2).strip()
    userid = str(event.get_user_id())

    try:
        with open("src/static/mai/plate_info.json","r") as f:
            plate_info = json.load(f)
    except:
        plate_info = {}
    
    print(plate_info)

    try:
        with open(f"src/users/{userid}.json","r") as f:
            user_settings = json.load(f)
    except:
        user_settings = {}

    print(user_settings)

    try:
        user_settings["mai_plate_dir"] = f"src/static/mai/plate/other_plate/{plate_info[s]}"
    except:
        user_settings["mai_plate_dir"] = ""

    with open(f"src/users/{userid}.json","w") as f:
        json.dump(user_settings, f, indent=4)
    await plate_change.finish("背景板设置成功~")

