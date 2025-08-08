import datetime
import hashlib
import json
import aiohttp
import asyncio
import pickle
import unicodedata
import heapq
from opencc import OpenCC
from pathlib import Path
from typing import Union, List, Tuple, Optional, Any

def hash(qq) -> int:
    s = datetime.datetime.now().strftime("%y%m%d")+str(qq)
    return int(hashlib.sha256(s.encode()).hexdigest(),16)
# def hash(qq: int):
#     days = int(time.strftime("%d", time.localtime(time.time()))) + 31 * int(
#         time.strftime("%m", time.localtime(time.time()+28800))) + 77
#     return (days * qq) >> 8

# async def offlineinit():
#     s = ""
#     k=1
#     try:
#         async with aiohttp.request('GET', 'https://www.diving-fish.com/api/maimaidxprober/music_data') as resp:
#             if resp.status == 200:
#                 s += "music_data.json下载成功\n"
#                 with open("src/static/music_data.json", "w", encoding= "utf-8") as f:
#                     j = await resp.json()
#                     json.dump(j, f, ensure_ascii=False)
#             else:
#                 s += "music_data.json下载失败\n"
#                 k=0
#     except:
#                 s += "music_data.json下载失败\n"
#                 k=0
#     try:
#         async with aiohttp.request('GET', 'https://www.diving-fish.com/api/maimaidxprober/chart_stats') as resp:
#             if resp.status == 200:
#                 s += "chart_stats.json下载成功\n"
#                 with open("src/static/chart_stats.json", "w", encoding= "utf-8") as f:
#                     j = await resp.json()
#                     json.dump(j, f, ensure_ascii=False)
#             else:
#                 s += "chart_stats.json下载失败\n"
#                 k=0
#     except:
#                 s += "chart_stats.json下载失败\n"
#                 k=0
#     try:
#         async with aiohttp.request('GET', 'https://api.yuzuchan.moe/maimaidx/maimaidxalias') as resp:
#             if resp.status == 200:
#                 s += "all_alias.json下载成功\n"
#                 with open("src/static/all_alias.json", "w", encoding= "utf-8") as f:
#                     j = await resp.json()
#                     content = j['content']
#                     format_js = {}
#                     for item in content:
#                         format_js[item["SongID"]] = {
#                             "Name": item["Name"],
#                             "Alias": item["Alias"]
#                         }

#                     json.dump(format_js, f, ensure_ascii=False)
#             else:
#                 s += "all_alias.json下载失败\n"
#     except:
#                 s += "all_alias.json下载失败\n"
#     try:
#         async with aiohttp.request('GET', 'https://www.diving-fish.com/api/chunithmprober/music_data') as resp:
#             if resp.status == 200:
#                 s += "chunithm_music_data.json下载成功\n"
#                 with open("src/static/chunithm/chuni_music_g.json", "w", encoding= "utf-8") as f:
#                     j = await resp.json()
#                     json.dump(j, f, ensure_ascii=False)
#             else:
#                 s += "chunithm_music_data.json下载失败\n"
#     except:
#                 s += "chunithm_music_data.json下载失败\n"
#     try:
#         #"https://chunithm.sega.jp/storage/json/music.json"
#         async with aiohttp.request('GET', 'https://chunithm.sega.jp/storage/json/music.json') as resp:
#             if resp.status == 200:
#                 s += "chunithm_music.json下载成功\n"
#                 with open("src/static/chunithm/chuni_music.json", "w", encoding= "utf-8") as f:
#                     j = await resp.json()
#                     json.dump(j, f, ensure_ascii=False)
#             else:
#                 s += "chunithm_music.json下载失败\n"
#     except:
#                 s += "chunithm_music.json下载失败\n"
#     return k,s

async def fetch(session: aiohttp.ClientSession, url: str, method: str = "GET", params: dict = {}, headers: dict = {}, post_process=None) -> Any:
    """
    通用下载并返回 JSON 的函数。
    - session: aiohttp 客户端
    - url: 目标 URL
    - post_process: 可选的后处理函数，接收原始 JSON，返回要 dump 的对象
    """
    try:
        async with session.request(method, url, params=params, headers=headers, timeout=10) as resp:
            resp.raise_for_status()
            data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        raise Exception(f"[Error] 下载 {url} 失败：{e}")

    # 如果需要拆分或格式化 JSON，可以传入 post_process
    result = post_process(data) if post_process else data

    return result

async def fetch_and_save(session: aiohttp.ClientSession, url: str, save_path: Path, method: str = "GET", params: dict = {}, headers: dict = {}, post_process=None) -> None:
    """
    通用下载并保存 JSON 的函数。
    - session: aiohttp 客户端
    - url: 目标 URL
    - save_path: 保存文件路径
    - post_process: 可选的后处理函数，接收原始 JSON，返回要 dump 的对象
    """
    try:
        async with session.request(method, url, params=params, headers=headers, timeout=10) as resp:
            resp.raise_for_status()
            data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        raise Exception(f"[Error] 下载 {url} 失败：{e}")

    # 如果需要拆分或格式化 JSON，可以传入 post_process
    result = post_process(data) if post_process else data

    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print(f"[Info] 已保存 {save_path.name}")

async def offlineinit() -> tuple[bool, str]:
    urls = [
        {
            "url": "https://www.diving-fish.com/api/maimaidxprober/music_data",
            "path": Path("src/static/music_data.json"),
        },
        {
            "url": "https://www.diving-fish.com/api/maimaidxprober/chart_stats",
            "path": Path("src/static/chart_stats.json"),
        },
        {
            "url": "https://api.yuzuchan.moe/maimaidx/maimaidxalias",
            "path": Path("src/static/all_alias.json"),
            "post_process": lambda j: {
                item["SongID"]: {"Name": item["Name"], "Alias": item["Alias"]}
                for item in j.get("content", [])
            },
        },
        {
            "url": "https://www.diving-fish.com/api/chunithmprober/music_data",
            "path": Path("src/static/chunithm/chuni_music_g.json"),
        },
        {
            "url": "https://chunithm.sega.jp/storage/json/music.json",
            "path": Path("src/static/chunithm/chuni_music.json"),
        },
    ]

    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_and_save(
                session,
                info["url"],
                info["path"],
                post_process=info.get("post_process")
            )
            for info in urls
        ]
        results = await asyncio.gather(*tasks)

    success_count = sum(results)
    messages = [
        f"{urls[i]['path'].name} {'成功' if ok else '失败'}"
        for i, ok in enumerate(results)
    ]
    message = "\n".join(messages)
    overall_success = success_count == len(urls)
    return overall_success, message

class OpenCCConverter:
    """
    OpenCC 转换器，用于简体中文、繁体中文和日语汉字之间的转换。
    """
    
    def __init__(self):
        self.converter_s2t = OpenCC('s2t')
        self.converter_t2s = OpenCC('t2s')
        self.converter_t2jp = OpenCC('t2jp')
        self.converter_jp2t = OpenCC('jp2t')

    def convert_cn2jp(self, text: str) -> str:
        """
            将简体中文转换为日语汉字（常用汉字）。
            使用 OpenCC 进行转换。
        """
        
        # unicode 规范化
        text = unicodedata.normalize("NFC", text)

        # openCC 转换

        text = self.converter_s2t.convert(text)
        text = self.converter_t2jp.convert(text)

        return text

    def convert_jp2cn(self, text: str) -> str:
        """
            将日语汉字转换为简体中文。
            使用 OpenCC 进行转换。
        """
        
        # unicode 规范化
        text = unicodedata.normalize("NFC", text)

        text = self.converter_jp2t.convert(text)
        text = self.converter_t2s.convert(text)

        return text

    def is_equal_kanji(self, text1: str, text2: str) -> bool:
        """
        判断两个字符串是否为相同的日语汉字。
        使用 Unicode 规范化和 OpenCC 转换。
        """
        # 规范化
        text1 = unicodedata.normalize("NFC", text1)
        text2 = unicodedata.normalize("NFC", text2)

        # 转换为简体中文
        text1_cn = self.convert_jp2cn(text1)
        text2_cn = self.convert_jp2cn(text2)

        return text1_cn == text2_cn
    
opencc_converter = OpenCCConverter()


def get_nickname_from_event(event_str: str) -> str:
    event_json = json.loads(event_str)
    return event_json["sender"]["nickname"]

def is_fools_day() -> bool:
    return datetime.datetime.now().month == 4 and datetime.datetime.now().day == 1


