import aiohttp
import os
from io import BytesIO
from typing import Dict, List, Optional, Union, Tuple, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from nonebot import on_command, on_regex, logger
from nonebot.typing import T_State
from nonebot.adapters.qq import Event, Bot, Message, MessageSegment
from nonebot.params import CommandArg, Arg
from pathlib import Path

from src.libraries.tool import async_get
from src.libraries.april_fool import is_April_1st, add_tv_distortion

# async def uploadpics(headers: Dict, payload: Dict):
#     async with aiohttp.request(method="POST", url="https://sm.ms/api/v2/upload", headers=headers, data=payload) as resp:
#         if resp.status == 400:
#             return None, 400
#         if resp.status == 403:
#             return None, 403
#         obj = await resp.json()
#         logger.info(obj)
#         return obj['data']['url'], obj['data']['hash'], 0
    
# async def deletepics(hash: str, headers: Dict):
#     async with aiohttp.request(method="GET", url=f"https://sm.ms/api/v2/delete/{hash}", headers=headers) as resp:
#         return resp.status
    
async def sendpics(obj: object, img: Image):
    b_img = BytesIO()
    img.save(b_img, format='png')
    b_img = b_img.getvalue()
    await obj.send(Message([
        MessageSegment.file_image(b_img)
    ]))

def pic_to_message_segment(img: Image.Image, format: str = 'png', args: dict = {}):
    fool = args.get("fool", True)
    if fool and is_April_1st():
        img = add_tv_distortion(img, shift_row = args.get("shift_row", 2))
    b_img = BytesIO()
    img.save(b_img, format=format)
    b_img = b_img.getvalue()
    return MessageSegment.file_image(b_img)

async def get_image(url: str, file_path: Path) -> str: 
    suffix_dict = {"image/gif": ".gif", "image/jpeg": ".jpg", "image/png": ".png", "image/tiff": ".tiff", "image/fax": ".fax", "image/x-icon": ".ico", "image/pnetvue": ".net", "image/vnd.rn-realpix": ".rp", "image/vnd.wap.wbmp": ".wbmp"}
    try:
        resp = await async_get(url=url)
        if "image" not in resp["type"]:
            raise Exception("TypeError")
        data = resp["data"]
        file_path = file_path.with_suffix(suffix_dict.get(resp["type"], ".jpg"))

        with open(file_path, 'wb') as f:
            f.write(data)

        return file_path
    except Exception as e:
        raise e