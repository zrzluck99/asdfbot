from nonebot import on_command, on_regex, logger
from nonebot.params import CommandArg, RegexGroup
from nonebot.adapters.qq import Bot, Event, Message, MessageSegment, C2CMessageCreateEvent, GroupAtMessageCreateEvent
from nonebot.exception import FinishedException
from nonebot.rule import to_me

from src.libraries.tool_range import hash
from src.libraries.maimai.maimaidx_music import *
from src.libraries.image_range import *
from libraries.maimai.maimai_best_legacy import generate, generateb40_by_player_data
from libraries.maimai.maimai_best import BestTableGenerator, draw_best 
from src.libraries.maimai.maimaidx_musicinfo import song_MessageSegment2, song_MessageSegment, chart_MessageSegment
from src.libraries.sendpics import pic_to_message_segment
from src.libraries.query import query_user
from src.libraries.april_fool import is_April_1st, kun_jin_kao

import re, datetime, random

DEFAULT_PRIORITY = 10

cover_dir = 'src/static/mai/cover/'




# spec_rand = on_regex(r"^/?随个(?:dx|sd|标准)?[绿黄红紫白]?[0-9]+\+?", rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
# @spec_rand.handle()
# async def _(event: Event):
#     #level_labels = ['绿', '黄', '红', '紫', '白']
#     regex = r"^/?随个(dx|sd|标准)?([绿黄红紫白]?)([0-9]+\+?)"
#     res = re.match(regex, str(event.get_message().extract_plain_text()).lower())
#     if res.groups()[0] == "dx":
#         tp = ["DX"]
#     elif res.groups()[0] == "sd" or res.groups()[0] == "标准":
#         tp = ["SD"]
#     else:
#         tp = ["SD", "DX"]
#     level = res.groups()[2]
#     if res.groups()[1] == "":
#         music_data = await total_list.filter(levels=level, types=tp)
#     else:
#         music_data = await total_list.filter(levels=level, diff=['绿黄红紫白'.index(res.groups()[1])], types=tp)
#     if len(music_data) == 0:
#         rand_result = MessageSegment.text("没有这样的乐曲哦。\n")
#     else:
#         rand_result = song_MessageSegment2(random.choice(music_data))
#     await spec_rand.finish(rand_result)



query_score = on_command('分数线', rule=to_me(), priority = DEFAULT_PRIORITY, block = True)
@query_score.handle()
async def _(event: Event, message: Message = CommandArg()):
    r = "([绿黄红紫白])(id)?([0-9]+)"
    argv = str(message).strip().split(" ")
    if len(argv) == 1 and argv[0] == '帮助':
        s = '''此功能为查找某首歌分数线设计。
命令格式：分数线 <难度+歌曲id> <分数线>'''
        await query_score.finish(pic_to_message_segment(text_to_image(s), args={"fool": False, "shift_row": 0}))
    elif len(argv) == 2:
        try:
            grp = re.match(r, argv[0]).groups()
            level_labels = ['绿', '黄', '红', '紫', '白']
            level_labels2 = ['Basic', 'Advanced', 'Expert', 'Master', 'Re:MASTER']
            level_index = level_labels.index(grp[0])
            chart_id = grp[2]
            line = float(argv[1])
            music = total_list.by_id(chart_id)
            chart: Dict[Any] = music['charts'][level_index]
            tap = int(chart['notes'][0])
            slide = int(chart['notes'][2])
            hold = int(chart['notes'][1])
            touch = int(chart['notes'][3]) if len(chart['notes']) == 5 else 0
            brk = int(chart['notes'][-1])
            total_score = 500 * tap + slide * 1500 + hold * 1000 + touch * 500 + brk * 2500
            break_bonus = 0.01 / brk
            break_50_reduce = total_score * break_bonus / 4
            reduce = 101 - line
            if reduce <= 0 or reduce >= 101:
                raise ValueError
            await query_score.finish(f'''{music['title']} {level_labels2[level_index]}
分数线 {line}% 允许的最多 TAP GREAT 数量为 {(total_score * reduce / 10000):.2f}(每个-{10000 / total_score:.4f}%),
BREAK 50落(一共{brk}个)等价于 {(break_50_reduce / 100):.3f} 个 TAP GREAT(-{break_50_reduce / total_score * 100:.4f}%)''')
        except FinishedException:
            pass
        except Exception:
            await query_score.finish("格式错误，输入“/分数线 帮助”以查看帮助信息")

temp_dir = 'src/static/mai/temp/'


