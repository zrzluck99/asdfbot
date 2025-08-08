from collections import defaultdict

from nonebot import on_command, on_regex, logger, get_driver
from nonebot.adapters.qq import Event, Bot, Message, MessageSegment
from nonebot.params import CommandArg, Arg

from src.libraries.maimai.maimaidx_music import matcher

driver = get_driver()

@driver.on_startup
async def _():
    # logger.info('正在加载maimai别名匹配器...')
    # matcher.alias_build_index()
    logger.info('maimai别名匹配器加载完成')