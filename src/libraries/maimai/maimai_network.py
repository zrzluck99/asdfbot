import aiohttp
import asyncio
from typing import Optional, Union, List, Dict, Any
from PIL import Image

from src.libraries.secrets import DF_Dev_Token

class maimaiAPI:
    BASE_URL = "https://www.diving-fish.com/api/maimaidxprober"
    PUBLIC_URL = "https://www.diving-fish.com/api/maimaidxprober"
    COVER_URL = "https://www.diving-fish.com/covers"
    LOCAL_ALIAS_URL = "http://localhost:9527/api/maiAliasAPI/search"
    COVER_DIR = 'src/static/mai/cover/'

    def __init__(
        self,
        # username: Optional[str] = None,
        # password: Optional[str] = None,
        # import_token: Optional[str] = None,
        developer_token: Optional[str] = None,
        timeout: int = 10,
    ):
        """
        初始化 maimaiAPI 客户端。

        :param username: diving-fish 用户名
        :param password: diving-fish 密码
        :param import_token: 用户 Import-Token，用于获取完整成绩
        :param developer_token: Developer-Token，用于开发者端点访问
        :param timeout: 网络超时时间（秒）
        """
        # self.username = username
        # self.password = password
        self.etag = ""
        # self.import_token = import_token
        self.developer_token = developer_token
        self.timeout = timeout
        # self.jwt_token: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )

    async def close(self):
        """关闭 HTTP 会话"""
        await self.session.close()

    # async def login(self) -> None:
    #     """使用用户名和密码登录，获取并保存 jwt_token"""
    #     if not self.username or not self.password:
    #         raise ValueError("username and password must be provided for login")
    #     url = f"{self.BASE_URL}/login"
    #     async with self.session.post(url, json={"username": self.username, "password": self.password}) as resp:
    #         if resp.status != 200:
    #             text = await resp.text()
    #             raise RuntimeError(f"Login failed: {resp.status} {text}")
    #         # 提取 jwt_token 并设置到 session cookies
    #         jar = self.session.cookie_jar
    #         cookies = resp.cookies
    #         if "jwt_token" in cookies:
    #             self.jwt_token = cookies["jwt_token"].value
    #             jar.update_cookies({"jwt_token": self.jwt_token})
    #         else:
    #             raise RuntimeError("jwt_token not received")

    def _auth_headers(self) -> Dict[str, str]:
        """构建验证头部，包括 Developer-Token 或 Import-Token"""
        headers: Dict[str, str] = {}
        if self.developer_token:
            headers["Developer-Token"] = self.developer_token
        return headers

    # async def get_player_profile(self) -> Dict[str, Any]:
    #     """获取或更新用户资料"""
    #     await self._ensure_login()
    #     url = f"{self.BASE_URL}/player/profile"
    #     async with self.session.get(url, headers=self._auth_headers()) as resp:
    #         resp.raise_for_status()
    #         return await resp.json()

    # async def get_player_agreement(self) -> Dict[str, Any]:
    #     """获取 or 更新用户是否同意用户协议"""
    #     await self._ensure_login()
    #     url = f"{self.BASE_URL}/player/agreement"
    #     async with self.session.get(url) as resp:
    #         resp.raise_for_status()
    #         return await resp.json()

    # async def update_player_agreement(self, accept: bool) -> Dict[str, Any]:
    #     """更新用户协议同意状态"""
    #     await self._ensure_login()
    #     url = f"{self.BASE_URL}/player/agreement"
    #     async with self.session.post(url, json={"accept_agreement": accept}) as resp:
    #         resp.raise_for_status()
    #         return await resp.json()

    # async def import_token_generate(self) -> Dict[str, Any]:
    #     """生成并更新 Import-Token"""
    #     await self._ensure_login()
    #     url = f"{self.BASE_URL}/player/import_token"
    #     async with self.session.put(url) as resp:
    #         resp.raise_for_status()
    #         data = await resp.json()
    #         token = data.get("token")
    #         if token:
    #             self.import_token = token
    #         return data

    async def get_music_data(self) -> Union[Dict[str, Any], int]:
        """
        获取 maimai 全量歌曲数据，使用 ETag 缓存
        :return: JSON 数据或状态码 304
        """
        headers = {}
        if self.etag:
            headers["If-None-Match"] = f'"{self.etag}"'
        url = f"{self.BASE_URL}/music_data"
        await self._ensure_session()
        async with self.session.get(url, headers=headers) as resp:
            if resp.status == 304:
                return {"update": False, "data": []}
            resp.raise_for_status()
            result = await resp.json()
            # 获取新的 etag
            new_etag = resp.headers.get("etag")
            self.etag = new_etag
            return {"update": True, "data": result}

    async def get_player_records(self, username: Optional[str] = None, qq: Optional[str] = None) -> Dict[str, Any]:
        """获取用户完整成绩信息：优先 Developer-Token 端点，否则 Import-Token"""
        params = {}
        if username:
            params["username"] = username
        elif qq:
            params["qq"] = qq

        if self.developer_token:
            url = f"{self.BASE_URL}/dev/player/records"
        else:
            url = f"{self.BASE_URL}/player/records"
        await self._ensure_session()
        async with self.session.get(url, headers=self._auth_headers(), params=params) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def query_player(self, username: Optional[str] = None, qq: Optional[str] = None, b50: bool = False) -> Dict[str, Any]:
        """获取用户简略成绩信息"""
        url = f"{self.BASE_URL}/query/player"
        body: Dict[str, Any] = {}
        if username:
            body["username"] = username
        elif qq:
            body["qq"] = qq
        if b50:
            body["b50"] = 1
        await self._ensure_session()
        async with self.session.post(url, json=body) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def query_plate(self, username: Optional[str] = None, qq: Optional[str] = None, version: List[str] = None) -> Dict[str, Any]:
        """按版本获取用户成绩信息"""
        url = f"{self.BASE_URL}/query_plate"
        body: Dict[str, Any] = {}
        if username:
            body["username"] = username
        elif qq:
            body["qq"] = qq
        if version is None or not isinstance(version, list):
            raise ValueError("version must be a list of version names")
        body["version"] = version
        await self._ensure_session()
        async with self.session.post(url, json=body) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_chart_stats(self) -> Dict[str, Any]:
        """获取谱面拟合难度等数据"""
        url = f"{self.BASE_URL}/chart_stats"
        await self._ensure_session()
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_rating_ranking(self) -> List[Dict[str, Any]]:
        """获取公开的用户 rating 完整数据"""
        url = f"{self.BASE_URL}/rating_ranking"
        await self._ensure_session()
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    def _get_cover_url(self, cover_id: int) -> str:
        """获取歌曲封面 URL，自动补 5 位及区间调整"""
        mid = int(cover_id)
        # if 10000 < mid <= 11000:
        #     mid -= 10000
        return f"{self.COVER_URL}/{mid:05d}.png"
    
    def _get_cover_path(self, cover_id: int) -> str:
        """获取歌曲封面本地路径，自动补 5 位"""
        return f"{self.COVER_DIR}/{cover_id:05d}.png"
    
    async def _get_cover(self, cover_id: int) -> Optional[bytes]:
        """获取歌曲封面图片字节数据"""
        url = self._get_cover_url(cover_id)
        await self._ensure_session()
        # 尝试从网络获取封面图片
        async with self.session.get(url) as resp:
            if resp.status == 404:
                return None
            resp.raise_for_status()
            return await resp.read()
        
    async def save_cover(self, cover_id: int) -> str:
        """保存歌曲封面到本地文件"""
        filename = self._get_cover_path(cover_id)
        cover_data = await self._get_cover(cover_id)
        if cover_data is None:
            return self._get_cover_path(0)  # 返回默认路径
        with open(filename, 'wb') as f:
            f.write(cover_data)
        return filename
    
    async def open_cover(self, cover_id: int) -> Optional[Image.Image]:
        """打开并返回歌曲封面图片"""
        path = self._get_cover_path(cover_id)
        try:
            return Image.open(path)
        except FileNotFoundError:
            # 如果本地没有封面，尝试从网络获取并保存
            path = await self.save_cover(cover_id)
            return Image.open(path)
            
    # async def _ensure_login(self):
    #     """确保已登录以访问需要登录验证的端点"""
    #     if not self.jwt_token:
    #         await self.login()

    async def query_alias(self, name: str, top_k: int = 5) -> Dict[str, Any]:
        # post请求到本地别名服务
        await self._ensure_session()
        async with self.session.post(self.LOCAL_ALIAS_URL, json={"query": name, "top_k": top_k}) as resp:
            resp.raise_for_status()
            return await resp.json()

mai_api = maimaiAPI(developer_token=DF_Dev_Token)


# Example usage:
# async def main():
#     client = maimaiAPI(username="your", password="pw", developer_token="devtok")
#     profile = await client.get_player_profile()
#     print(profile)
#     await client.close()
#
# asyncio.run(main())
