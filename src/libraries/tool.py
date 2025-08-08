import aiohttp
import json
import time
from pathlib import Path
from typing import Any, Union

import aiofiles


async def async_get(url, headers=None, params=None):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=10) as response:
                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/json' in content_type:
                    data = await response.json()
                    return {"type": content_type, "data": data}
                else:
                    data = await response.read()
                    return {"type": content_type, "data": data}
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return {"type": None, "data": None}

async def async_post(url, headers=None, data=None):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=10) as response:
                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/json' in content_type:
                    data = await response.json()
                    return {"type": content_type, "data": data}
                else:
                    data = await response.read()
                    return {"type": content_type, "data": data}
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return {"type": None, "data": None}

def hash(qq: int):
    days = int(time.strftime("%d", time.localtime(time.time()))) + 31 * int(
        time.strftime("%m", time.localtime(time.time()))) + 77
    return (days * qq) >> 8


async def openfile(file: Path) -> Union[dict, list]:
    async with aiofiles.open(file, 'r', encoding='utf-8') as f:
        data = json.loads(await f.read())
    return data


async def writefile(file: Path, data: Any) -> bool:
    async with aiofiles.open(file, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=4))
    return True