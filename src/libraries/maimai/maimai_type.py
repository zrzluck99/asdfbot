import json, random, nltk, math
from typing import Dict, List, Optional, Union, Tuple, Any
import aiosqlite
from dataclasses import dataclass

from src.libraries.tool_range import opencc_converter
from src.libraries.maimai.database import database_api
from src.libraries.maimai.static_lists_and_dicts import version_list, cn_version_list, level_list, rank_list_lower, fc_list_lower, fs_list_lower
from src.libraries.alias import HybridStringMatcher


# —— 数据模型层 —— #

@dataclass
class Stats(Dict):
    cnt: Optional[int] = None
    fit_diff: Optional[float] = None
    avg: Optional[float] = None
    avg_dx: Optional[float] = None
    std_dev: Optional[float] = None
    rank_dist: Optional[List[int]] = None 
    fc_dist: Optional[List[int]] = None

    @classmethod
    async def from_db(cls, db: aiosqlite.Connection, music_id: int, diff_index: int) -> Optional["Stats"]:
        """
        从数据库中获取指定曲目和难度的统计信息
        """
        cursor = await db.execute(
            "SELECT * FROM chart_stats WHERE music_id = ? AND diff_index = ?",
            (music_id, diff_index)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        # 获取 rank_dist
        cursor = await db.execute(
            "SELECT * FROM chart_rating_dist WHERE music_id = ? AND diff_index = ?",
            (music_id, diff_index)
        )
        rating_rows = await cursor.fetchall()
        rank_dist = [0] * 14
        for r in rating_rows:
            if 0 <= r["rating_index"] < len(rank_dist):
                rank_dist[r["rating_index"]] = r["count"]
        # 获取 fc_dist
        cursor = await db.execute(
            "SELECT * FROM chart_fc_dist WHERE music_id = ? AND diff_index = ?",
            (music_id, diff_index)
        )
        fc_rows = await cursor.fetchall()
        fc_dist = [0] * 5
        for f in fc_rows:
            if 0 <= f["fc_index"] < len(fc_dist):
                fc_dist[f["fc_index"]] = f["count"]
        # 返回 Stats 对象
        print(f"Stats.from_db: music_id={music_id}, diff_index={diff_index}, cnt={row['cnt']}, fit_diff={row['fit_diff']}, avg={row['avg']}, avg_dx={row['avg_dx']}, std_dev={row['std_dev']}")
        return cls(
            cnt=row["cnt"],
            fit_diff=row["fit_diff"],
            avg=row["avg"],
            avg_dx=row["avg_dx"],
            std_dev=row["std_dev"],
            rank_dist=rank_dist,
            fc_dist=fc_dist
        )
    
    @classmethod
    async def by_charts(cls, db: aiosqlite.Connection, charts: List[Optional[Union["Chart", "MusicChart"]]]) -> Dict[Tuple[int, int], "Stats"]:
        """
        根据 Chart/MusicChart 列表获取对应的 Stats
        返回一个字典，键为 (music_id, diff_index)，值为 Stats 对象
        """
        if not charts:
            return {}

        # 构造查询语句
        placeholders = ",".join("(?, ?)" for _ in charts)
        sql = f"""
        SELECT * FROM chart_stats
        WHERE (music_id, diff_index) IN ({placeholders})
        """
        params = [(c.music_id, c.diff_index) for c in charts]
        params = [item for sublist in params for item in sublist]  # 扁平化参数列表
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()

        # 构造结果字典
        stats_map: Dict[Tuple[int, int], Stats] = {}
        for row in rows:
            stats_map[(row["music_id"], row["diff_index"])] = Stats(
                cnt=row["cnt"],
                fit_diff=row["fit_diff"],
                avg=row["avg"],
                avg_dx=row["avg_dx"],
                std_dev=row["std_dev"],
                rank_dist=[],
                fc_dist=[]
            )

        # 获取 rank_dist
        for (music_id, diff_index), stats in stats_map.items():
            cursor = await db.execute(
                "SELECT * FROM chart_rating_dist WHERE music_id = ? AND diff_index = ?",
                (music_id, diff_index)
            )
            rating_rows = await cursor.fetchall()
            stats.rank_dist = [0] * 14
            for r in rating_rows:
                if 0 <= r["rating_index"] < len(stats.rank_dist):
                    stats.rank_dist[r["rating_index"]] = r["count"]
        # 获取 fc_dist
        for (music_id, diff_index), stats in stats_map.items():
            cursor = await db.execute(
                "SELECT * FROM chart_fc_dist WHERE music_id = ? AND diff_index = ?",
                (music_id, diff_index)
            )
            fc_rows = await cursor.fetchall()
            stats.fc_dist = [0] * 5
            for f in fc_rows:
                if 0 <= f["fc_index"] < len(stats.fc_dist):
                    stats.fc_dist[f["fc_index"]] = f["count"]
        # 返回结果
        return stats_map

@dataclass
class Chart:
    music_id: Optional[int] = None
    diff_index: Optional[int] = None
    ds: Optional[float] = None
    level: Optional[str] = None
    notes: Optional[int] = None
    tap: Optional[int] = None
    hold: Optional[int] = None
    slide: Optional[int] = None
    touch: Optional[int] = None
    brk: Optional[int] = None
    charter: Optional[str] = None
    stats: Optional[Stats] = None

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "Chart":
        # 假设 row 包含字段：music_id, diff_index, ds, level, notes, tap, hold, slide, touch, break, charter
        return cls(
            music_id=row["music_id"],
            diff_index=row["diff_index"],
            ds=row["ds"],
            level=row["level"],
            notes=row["notes"],
            tap=row["tap"],
            hold=row["hold"],
            slide=row["slide"],
            touch=row["touch"],
            brk=row["break"],
            charter=row["charter"]
        )
        

@dataclass
class Music(Dict):
    id: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None
    artist: Optional[str] = None
    genre: Optional[str] = None
    bpm: Optional[int] = None
    release_date: Optional[str] = None
    version: Optional[str] = None
    is_new: Optional[bool] = None
    version_id: Optional[int] = None

    charts: Optional[List[Chart]] = None
    statss: Optional[List[Stats]] = None
    alias: Optional[List[str]] = None
    cn_version: Optional[str] = None

    diff: Optional[List[int]] = None
    dss: Optional[List[float]] = None
    levels: Optional[List[str]] = None

    @classmethod
    async def from_db(cls, db: aiosqlite.Connection, music_id: int) -> Optional["Music"]:
        # 获取 music 元信息
        cursor = await db.execute(
            "SELECT * FROM music WHERE id = ?",
            (music_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        # 获取所有 chart
        cursor = await db.execute(
            "SELECT * FROM chart WHERE music_id = ? ORDER BY diff_index",
            (music_id,)
        )
        chart_rows = await cursor.fetchall()
        charts_tmp = [Chart.from_row(row) for row in chart_rows]
        cn_version = cn_version_list[row["version_id"]] if 0 <= row["version_id"] < len(cn_version_list) else "未知版本"
        diff = [int(c.diff_index) for c in charts_tmp]
        dss = [c.ds for c in charts_tmp]
        levels = [c.level for c in charts_tmp]

        # 获取所有 stats
        statss: List[Stats] = []
        charts: List[Chart] = []
        for chart in charts_tmp:
            stat = await Stats.from_db(db, music_id, chart.diff_index)
            if stat is not None:
                statss.append(stat)
                chart.stats = stat
                charts.append(chart)
            else:
                # 如果没有 stats，仍然添加 chart，stats 为空数据
                stat = None
                statss.append(stat)
                chart.stats = stat
                charts.append(chart)

        return cls(
            id=row["id"],
            title=row["title"],
            type=row["type"],
            artist=row["artist"],
            genre=row["genre"],
            bpm=row["bpm"],
            release_date=row["release_date"],
            version=row["version"],
            is_new=bool(row["is_new"]),
            version_id=row["version_id"],
            charts=charts,
            statss=statss,
            diff=diff,
            dss=dss,
            levels=levels,
            cn_version=cn_version
        )
    
@dataclass
class MusicChart(Music, Chart):
    """
    MusicChart 继承自 Music 和 Chart，表示一个曲目的具体难度信息
    """
    
    @classmethod
    async def from_db(cls, db: aiosqlite.Connection, music_id: int, diff_index: int) -> Optional["MusicChart"]:
        """
        从数据库中获取指定曲目和难度的 MusicChart
        """
        cursor = await db.execute(
            "SELECT * FROM music WHERE id = ?",
            (music_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        
        # 获取 chart 信息
        cursor = await db.execute(
            "SELECT * FROM chart WHERE music_id = ? AND diff_index = ?",
            (music_id, diff_index)
        )
        chart_row = await cursor.fetchone()
        if not chart_row:
            return None
        
        # 获取 stats 信息
        stats = await Stats.from_db(db, music_id, diff_index)

        return cls(
            id=row["id"],
            title=row["title"],
            type=row["type"],
            artist=row["artist"],
            genre=row["genre"],
            bpm=row["bpm"],
            release_date=row["release_date"],
            version=row["version"],
            is_new=bool(row["is_new"]),
            version_id=row["version_id"],
            cn_version=cn_version_list[row["version_id"]] if 0 <= row["version_id"] < len(cn_version_list) else "未知版本",
            
            music_id=chart_row["music_id"],
            diff_index=chart_row["diff_index"],
            ds=chart_row["ds"],
            level=chart_row["level"],
            notes=chart_row["notes"],
            tap=chart_row["tap"],
            hold=chart_row["hold"],
            slide=chart_row["slide"],
            touch=chart_row["touch"],
            brk=chart_row["break"],
            charter=chart_row["charter"],
            stats=stats
        )
       
    @classmethod
    async def from_music(cls, musics: Union[Music, List[Music]]) -> List["MusicChart"]:
        """
        从 Music 或 Music 列表中获取指定难度的 MusicChart
        """
        if isinstance(musics, Music):
            musics = [musics]
        if not isinstance(musics, list):
            raise ValueError("musics must be a Music object or a list of Music objects.")
        result = []
        for music in musics:
            if not music.charts:
                continue
            for chart in music.charts:
                if chart.music_id == music.id:
                    mc = cls(
                        music_id=music.id,
                        title=music.title,
                        type=music.type,
                        artist=music.artist,
                        genre=music.genre,
                        bpm=music.bpm,
                        release_date=music.release_date,
                        version=music.version,
                        is_new=music.is_new,
                        version_id=music.version_id,
                        cn_version=music.cn_version,

                        diff_index=chart.diff_index,
                        ds=chart.ds,
                        level=chart.level,
                        notes=chart.notes,
                        tap=chart.tap,
                        hold=chart.hold,
                        slide=chart.slide,
                        touch=chart.touch,
                        brk=chart.brk,
                        charter=chart.charter,
                        stats=chart.stats
                    )
                    result.append(mc)
        return result

@dataclass
class BestRecord(Dict):
    user_id: Optional[str] = None
    music_id: Optional[int] = None
    diff_index: Optional[int] = None
    achievements: Optional[float] = None
    ra: Optional[int] = None
    rank_id: Optional[int] = None  # 新增 rank_id 字段
    fc_id: Optional[int] = None
    fs_id: Optional[int] = None
    dxscore: Optional[int] = None
    ra_b50: Optional[int] = None  # 新增 ra_b50 字段
    ra_b40: Optional[int] = None  # 新增 ra_b40 字段
    ra_stats: Optional[int] = None  # 新增 ra_stats 字段

    @classmethod
    def calc_ra(cls, ds: float, achievements: float, b50: bool) -> int:
        """
        计算 RA 值
        """
        ranges = [
            (100.5000, 14.0, 100.5000),
            (100.4999, 13.9, None),
            (100.0000, 13.5, None),
            (99.9999, 13.4, None),
            (99.5000, 13.2, None),
            (99.0000, 13.0, None),
            (98.9999, 12.9, None),
            (98.0000, 12.7, None),
            (97.0000, 12.5, None),
            (96.9999, 11.0, None),
            (94.0000, 10.5, None),
            (93.9999, 10.0, None), # ?
            (90.0000, 9.5, None),
            (89.9999, 9.0, None), # ?
            (80.0000, 8.5, None),
            (79.9999, 7.6, None),
            (75.0000, 7.5, None),
            (70.0000, 7.0, None),
            (60.0000, 6.0, None),
            (50.0000, 5.0, None),
            (40.0000, 4.0, None),
            (30.0000, 3.0, None),
            (20.0000, 2.0, None),
            (10.0000, 1.0, None)
        ]

        if ds is None or achievements is None:
            return 0.0
        # 优化：用区间和系数列表简化分支

        ds = round(ds, 1)  # 保留一位小数

        for threshold, coeff, fixed_ach in ranges:
            if achievements >= threshold:
                achv = fixed_ach if fixed_ach is not None else achievements
                adj_coeff = math.floor(coeff * 1.6 * 10) / 10 if b50 else coeff
                return int(adj_coeff * ds * achv * 0.01)
        return 0

    @classmethod
    async def from_db(cls, db: aiosqlite.Connection, user_id: str, music_id: int, diff_index: int) -> Optional["BestRecord"]:
        """
        从数据库中获取指定用户、曲目和难度的最佳记录
        """
        cursor = await db.execute(
            "SELECT * FROM best_record WHERE user_id = ? AND music_id = ? AND diff_index = ?",
            (user_id, music_id, diff_index)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        
        cursor = await db.execute(
            "SELECT ds FROM chart WHERE music_id = ? AND diff_index = ?",
            (music_id, diff_index)
        )
        chart_row = await cursor.fetchone()
        if not chart_row:
            return None
        
        cursor = await db.execute(
            "SELECT * FROM chart_stats WHERE music_id = ? AND diff_index = ?",
            (music_id, diff_index)
        )
        stats_row = await cursor.fetchone()
        if not stats_row:
            return None

        return cls(
            user_id=row["user_id"],
            music_id=row["music_id"],
            diff_index=row["diff_index"],
            achievements=row["achievements"],
            ra=None, # 留空
            rank_id=row["rank_id"],   
            fc_id=row["fc_id"],
            fs_id=row["fs_id"],
            dxscore=row["dxscore"],
            ra_b50=BestRecord.calc_ra(chart_row["ds"], row["achievements"], b50=True),
            ra_b40=BestRecord.calc_ra(chart_row["ds"], row["achievements"], b50=False),
            ra_stats=BestRecord.calc_ra(stats_row["fit_diff"] if row["fit_diff"] is not None else row["ds"], row["achievements"], b50=True)
        )
    
@dataclass
class User(Dict):
    """
    User 用于存储用户信息
    """
    id: Optional[str] = None
    additional_rating: Optional[int] = None
    nickname: Optional[str] = None
    plate: Optional[str] = None
    rating: Optional[int] = None

    @classmethod
    def _Q2B(cls, uchar):
        """单个字符 全角转半角"""
        inside_code = ord(uchar)
        if inside_code == 0x3000:
            inside_code = 0x0020
        else:
            inside_code -= 0xfee0
        if inside_code < 0x0020 or inside_code > 0x7e: #转完之后不是半角字符返回原来的字符
            return uchar
        return chr(inside_code)

    @classmethod
    def _stringQ2B(cls, ustring):
        """把字符串全角转半角"""
        return "".join([User._Q2B(uchar) for uchar in ustring])

    @classmethod
    async def from_db(cls, db: aiosqlite.Connection, user_id: str) -> Optional["User"]:
        """
        从数据库中获取指定用户的详细信息
        """
        cursor = await db.execute(
            "SELECT * FROM user WHERE id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return cls(
            id=row["id"],
            additional_rating=row["additional_rating"],
            nickname=User._stringQ2B(row["nickname"]),
            plate=row["plate"],
            rating=row["rating"]
        )

@dataclass
class BestTable(Dict):
    """
    BestTable 用于存储 Best40 or Best50
    """
    user: Optional[User] = None
    old_best: Optional[List[Tuple[MusicChart, BestRecord]]] = None
    new_best: Optional[List[Tuple[MusicChart, BestRecord]]] = None
    b50: Optional[bool] = None
    old_rating: Optional[int] = None
    new_rating: Optional[int] = None
    rating: Optional[int] = None
    
@dataclass
class Plate(Dict):
    """
    Plate 用于存储用户的 plate 信息
    """
    user: Optional[User] = None
    plate: List[Tuple[MusicChart, BestRecord]] = None
    plate_all: List[Tuple[MusicChart, BestRecord]] = None
    type: Optional[str] = None

    @classmethod
    def single_achieved(cls, mtype: Optional[str], record: BestRecord) -> bool:
        """
        检查单个 record 是否达成指定的 plate 类型
        """
        if (not mtype) or (mtype not in rank_list_lower + fc_list_lower + fs_list_lower):
            raise ValueError(f"Invalid type: {mtype}. Must be one of {rank_list_lower + fc_list_lower + fs_list_lower}")
        if mtype in rank_list_lower:
            return record and record.rank_id >= rank_list_lower.index(mtype)
        elif mtype in fc_list_lower:
            return record and record.fc_id >= fc_list_lower.index(mtype)
        elif mtype in fs_list_lower:
            return record and record.fs_id >= fs_list_lower.index(mtype)
        else:
            return False

    def plate_achieved(self) -> bool:
        """
        检查 plate 是否全部达成
        """
        for chart, best_record in self.plate_all:
            if not best_record:
                return False
            if not Plate.single_achieved(self.type, best_record):
                return False
        return True
    
    def plate_ensured(self) -> bool:
        """
        检查 plate 是否确定
        """
        for chart, best_record in self.plate:
            if not best_record:
                return False
            if not Plate.single_achieved(self.type, best_record):
                return False
        return True

    def get_lists_by_level(self) -> Dict[str, List[Tuple[MusicChart, BestRecord]]]:
        """
        获取所有难度的 plate 列表，按 level 分类
        """
        if not self.plate_all:
            return {}
        result: Dict[str, List[Tuple[MusicChart, BestRecord]]] = {}
        for chart, record in self.plate_all:
            if chart.level not in result:
                result[chart.level] = []
            result[chart.level].append((chart, record))
        return result
    
    def get_lists_by_ds(self) -> Dict[float, List[Tuple[MusicChart, BestRecord]]]:
        """
        获取所有难度的 plate 列表，按 ds 分类
        """
        if not self.plate_all:
            return {}
        result: Dict[float, List[Tuple[MusicChart, BestRecord]]] = {}
        for chart, record in self.plate_all:
            if chart.ds not in result:
                result[chart.ds] = []
            result[chart.ds].append((chart, record))
        return result


    


# —— DAO / 接口层 —— #

class MusicList:
    async def _connect(self):
        conn = await database_api.get_database_connection()
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    async def _from_rows(self, rows: List[aiosqlite.Row]) -> Tuple[List[Music], List[MusicChart]]:
        # 按 music_id 分组，把符合条件的 chart 列表化
        # 先生成 music_chart 列表
        music_charts = []
        for row in rows:
            music_chart = MusicChart(
                music_id=row["music_id"],
                diff_index=row["diff_index"],
                ds=row["ds"],
                level=row["level"],
                notes=row["notes"],
                tap=row["tap"],
                hold=row["hold"],
                slide=row["slide"],
                touch=row["touch"],
                brk=row["break"],
                charter=row["charter"],
                id=row["music_id"],
                title=row["title"],
                type=row["type"],
                artist=row["artist"],
                genre=row["genre"],
                bpm=row["bpm"],
                release_date=row["release_date"],
                version=row["version"],
                is_new=bool(row["is_new"]),
                version_id=row["version_id"],
                cn_version=cn_version_list[row["version_id"]] if 0 <= row["version_id"] < len(cn_version_list) else "未知版本",
                stats=None  # stats 会在后续处理
            )
            music_charts.append(music_chart)

        # 获取所有 charts 的 stats

        db = await self._connect()
        try:
            stats_map = await Stats.by_charts(db, music_charts)
        finally:
            await db.close()

        # 将 stats 填充到 music_charts 中
        for music_chart in music_charts:
            diff_index = music_chart.diff_index
            music_chart.stats = stats_map.get((music_chart.music_id, diff_index), None)

        # 按 music_id 分组，构造 Music 对象
        music_map = {}
        for music_chart in music_charts:
            mid = music_chart.music_id
            if mid not in music_map:
                music_map[mid] = {
                    "id": mid,
                    "title": music_chart.title,
                    "type": music_chart.type,
                    "artist": music_chart.artist,
                    "genre": music_chart.genre,
                    "bpm": music_chart.bpm,
                    "release_date": music_chart.release_date,
                    "version": music_chart.version,
                    "is_new": music_chart.is_new,
                    "version_id": music_chart.version_id,
                    "cn_version": music_chart.cn_version,
                    "charts": [],
                    "statss": [],
                    "diff": [],
                    "dss": [],
                    "levels": []
                }
            chart = Chart(
                music_id = mid,
                diff_index = music_chart.diff_index,
                ds = music_chart.ds,
                level = music_chart.level,
                notes = music_chart.notes,
                tap = music_chart.tap,
                hold = music_chart.hold,
                slide = music_chart.slide,
                touch = music_chart.touch,
                brk = music_chart.brk,
                charter = music_chart.charter,
                stats = music_chart.stats
            )
            music_map[mid]["charts"].append(chart)
            music_map[mid]["statss"].append(music_chart.stats)
            music_map[mid]["diff"].append(int(music_chart.diff_index))
            music_map[mid]["dss"].append(music_chart.ds)
            music_map[mid]["levels"].append(music_chart.level)

        # 用分组结果构造 Music 对象列表
        result: List[Music] = []
        for data in music_map.values():
            music = Music(
                id=data["id"],
                title=data["title"],
                type=data["type"],
                artist=data["artist"],
                genre=data["genre"],
                bpm=data["bpm"],
                release_date=data["release_date"],
                version=data["version"],
                is_new=data["is_new"],
                version_id=data["version_id"],
                cn_version=data["cn_version"],
                charts=data["charts"],
                statss=data["statss"],
                diff=data["diff"],
                dss=data["dss"],
                levels=data["levels"]
            )
            result.append(music)

        return result, music_charts


    async def by_id(self, music_id: int) -> Optional[Music]:
        db = await self._connect()
        try:
            return await Music.from_db(db, music_id)
        finally:
            await db.close()
        
    async def by_title(self, title: str) -> Optional[Music]:
        """
        根据标题模糊搜索曲目
        """
        title = opencc_converter.convert_cn2jp(title.lower())

        sql = "SELECT id FROM music WHERE title LIKE '%' || ? || '%'"
        db = await self._connect()
        try:
            cursor = await db.execute(sql, (title,))
            row = await cursor.fetchone()
            if not row:
                return None
            return await Music.from_db(db, row["id"])
        finally:
            await db.close()

    async def filter(
        self,
        pagination:   Optional[Tuple[int, int]] = None,
        order:        Optional[Union[str, List[str]]] = None,
        levels:       Optional[Union[str, List[str]]]      = None,
        ds_range:     Optional[Union[float, List[float], Tuple[float, float]]] = None,
        title_search: Optional[str]            = None,
        genres:       Optional[Union[str, List[str]]]      = None,
        bpm_range:    Optional[Union[float, List[float], Tuple[float, float]]] = None,
        types:        Optional[Union[str, List[str]]]      = None,
        diff_indices: Optional[Union[int, List[int]]]      = None,
        charter:      Optional[str]            = None,
        artist:       Optional[str]            = None,
        is_new:       Optional[bool]           = None,
        version_indices:   Optional[Union[int, List[int]]] = None
    ) -> Dict[str, Union[int, List[Music]]]:
        """
        按照以下条件筛选 Chart：
          - levels:      chart.level 匹配列表
          - ds_range:    chart.ds 在 [min,max] 之间
          - title_search: music.title 包含子串（不区分大小写）
          - genres:      music.genre 在列表中
          - bpm_range:   music.bpm 在 [min,max] 之间
          - types:       music.type ('SD'/'DX') 在列表中
          - diff_indices: chart.diff_index 在列表中
          - charter:     chart.charter 包含子串（不区分大小写）
          - artist:      music.artist 包含子串（不区分大小写）
          - is_new:      music.is_new 是否为 True
          - version_indices: music.version_id 在列表中
        pagination: 可选，(offset, limit) 元组，指定结果的分页
        order: 可选，指定排序顺序，格式为 ['(+/-)term1', '(+/-)term2', ...]

        返回一个字典：
        {
            music_count: int,  # 符合条件的曲目数量
            chart_count: int,  # 符合条件的 chart 数量
            music_list: List[Music]  # 符合条件的曲目列表
            music_charts: List[MusicChart]  # 符合条件的 music_chart 列表
        }
        """
        # 基础查询，选出所有符合条件的 chart
        sql = """
        SELECT
          m.id      AS music_id,
          m.title   AS title,
          m.type    AS type,
          m.artist  AS artist,
          m.genre   AS genre,
          m.bpm     AS bpm,
          m.release_date AS release_date,
          m.version AS version,
          m.is_new AS is_new,
          m.version_id AS version_id,
          c.diff_index,
          c.ds,
          c.level,
          c.notes,
          c.tap,
          c.hold,
          c.slide,
          c.touch,
          c.break,
          c.charter
        FROM music     AS m
        JOIN chart     AS c
          ON m.id = c.music_id
        WHERE 1=1
        """
        params: List = []

        # 动态拼接 WHERE
        if levels:
            # 确保 levels 是一个列表
            if isinstance(levels, str):
                levels = [levels]
            elif isinstance(levels, (list, tuple)):
                levels = list(levels)
            else:
                raise ValueError("levels must be a list or string.")
            placeholders = ",".join("?" for _ in levels)
            sql += f" AND c.level IN ({placeholders})"
            params += levels

        if ds_range:
            # 确保 ds_range 是一个包含两个元素的元组
            if isinstance(ds_range, (int, float)):
                ds_range = (ds_range, ds_range)
            elif isinstance(ds_range, (list, tuple)):
                ds_range = tuple(ds_range)
            else:
                raise ValueError("ds_range must be a list, tuple, or single number.")
            if len(ds_range) == 1:
                ds_range = (ds_range[0], ds_range[0])
            elif len(ds_range) > 2:
                ds_range = (ds_range[0], ds_range[1])

            sql += " AND c.ds BETWEEN ? AND ?"
            params.extend(ds_range)

        if title_search:
            # 确保 title_search 是一个字符串
            if not isinstance(title_search, str):
                raise ValueError("title_search must be a string.")
            title_search = opencc_converter.convert_cn2jp(title_search.lower())

            sql += " AND LOWER(m.title) LIKE '%' || LOWER(?) || '%'"
            params.append(title_search)

        if genres:
            # 确保 genres 是一个列表
            if isinstance(genres, str):
                genres = [genres]
            elif isinstance(genres, (list, tuple)):
                genres = list(genres)
            else:
                raise ValueError("genres must be a list or string.")
            
            placeholders = ",".join("?" for _ in genres)
            sql += f" AND m.genre IN ({placeholders})"
            params += genres

        if bpm_range:
            # 确保 bpm_range 是一个包含两个元素的元组
            if isinstance(bpm_range, (int, float)):
                bpm_range = (bpm_range, bpm_range)
            elif isinstance(bpm_range, (list, tuple)):
                bpm_range = tuple(bpm_range)
            else:
                raise ValueError("bpm_range must be a list, tuple, or single number.")
            if len(bpm_range) == 1:
                bpm_range = (bpm_range[0], bpm_range[0])
            elif len(bpm_range) > 2:
                bpm_range = (bpm_range[0], bpm_range[1])

            sql += " AND m.bpm BETWEEN ? AND ?"
            params.extend(bpm_range)

        if types:
            # 确保 types 是一个列表
            if isinstance(types, str):
                types = [types]
            elif isinstance(types, (list, tuple)):
                types = list(types)
            else:
                raise ValueError("types must be a list or string.")
            
            placeholders = ",".join("?" for _ in types)
            sql += f" AND m.type IN ({placeholders})"
            params += types

        if diff_indices is not None:
            # 确保 diff_indices 是一个列表
            if isinstance(diff_indices, int):
                diff_indices = [diff_indices]
            elif isinstance(diff_indices, (list, tuple)):
                diff_indices = list(diff_indices)
            else:
                raise ValueError("diff_indices must be a list or integer.")

            placeholders = ",".join("?" for _ in diff_indices)
            sql += f" AND c.diff_index IN ({placeholders})"
            params += diff_indices

        if charter:
            # 确保 charter 是一个字符串
            if not isinstance(charter, str):
                raise ValueError("charter must be a string.")
            charter = opencc_converter.convert_cn2jp(charter.lower().strip())

            sql += " AND LOWER(c.charter) LIKE '%' || LOWER(?) || '%'"
            params.append(charter)

        if artist:
            # 确保 artist 是一个字符串
            if not isinstance(artist, str):
                raise ValueError("artist must be a string.")
            artist = opencc_converter.convert_cn2jp(artist.lower().strip())

            sql += " AND LOWER(m.artist) LIKE '%' || LOWER(?) || '%'"
            params.append(artist)

        if is_new is not None:
            # 确保 is_new 是一个布尔值
            if not isinstance(is_new, bool):
                raise ValueError("is_new must be a boolean.")
            sql += " AND m.is_new = ?"
            params.append(1 if is_new else 0)

        if version_indices is not None:
            # 确保 version_indices 是一个列表
            if isinstance(version_indices, int):
                version_indices = [version_indices]
            elif isinstance(version_indices, (list, tuple)):
                version_indices = list(version_indices)
            else:
                raise ValueError("version_indices must be a list or integer.")

            placeholders = ",".join("?" for _ in version_indices)
            sql += f" AND m.version_id IN ({placeholders})"
            params += version_indices
            
        # 添加排序
        if order:
            if not isinstance(order, (str, list, tuple, set)):
                raise ValueError("order must be a string or a list.")
            if isinstance(order, str):
                order = [order]
            supported_columns = ["title", "music_id", "version_id", "ds", "diff_index",
                                 "-title", "-music_id", "-version_id", "-ds", "-diff_index",
                                 "+title", "+music_id", "+version_id", "+ds", "+diff_index"]
            s = " ORDER BY"
            for term in order:
                if not term in supported_columns:
                    raise ValueError("Unsupported column name.")
                if '-' in term:
                    s += f" {term[1:]} DESC,"
                elif '+' in term:
                    s += f" {term[1:]} ASC,"
                else:
                    s += f" {term} ASC,"
            s = s[:-1]
            sql += s

        # 添加分页支持
        if pagination:
            if not isinstance(pagination, tuple) or len(pagination) != 2:
                raise ValueError("pagination must be a tuple of (offset, limit).")
            offset, limit = pagination
            if not isinstance(offset, int) or not isinstance(limit, int):
                raise ValueError("Both offset and limit must be integers.")
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        # 执行查询并聚合
        db = await self._connect()
        try:
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
        finally:
            await db.close()

        # 统计符合条件的曲目和 chart 数量
        music_count = len(set(row["music_id"] for row in rows))  # 唯一曲目数量
        chart_count = len(rows)  # 总 chart 数量
        result, music_charts = await self._from_rows(rows)

        return {
            "music_count": music_count,
            "chart_count": chart_count,
            "music_list": result,
            "music_charts": music_charts
        }

    async def filt_by_name(self, title_search: str) -> Music:
        key = title_search.lower().strip()
        sdflag = key.startswith("标") or key.startswith("sd")
        dxflag = key.startswith("dx")
        # 如果是标记曲或 DX 曲，去掉前缀
        if sdflag or dxflag:
            key = key.replace("标", "").replace("sd","").replace("dx", "").strip()

        db = await self._connect()
        try:
            # 1) 曲名完全匹配
            # 这里匹配两种字形
            sql1 = "SELECT id FROM music WHERE LOWER(title) IN (?, ?)"
            params1 = [key, opencc_converter.convert_cn2jp(key)]
            if sdflag or dxflag:
                sql1 += " AND id " + ("< 10000" if sdflag else ">= 10000")
            cur = await db.execute(sql1, params1)
            rows = await cur.fetchone()
            if rows:
                return await Music.from_db(db, rows["id"])

            # 2) 别名完全匹配
            sql2 = """
            SELECT DISTINCT a.music_id
            FROM alias a
            WHERE LOWER(a.alias_text) IN (?, ?)
            """
            params2 = [key, opencc_converter.convert_cn2jp(key)]
            if sdflag or dxflag:
                sql2 += " AND a.music_id " + ("< 10000" if sdflag else ">= 10000")
            cur = await db.execute(sql2, params2)
            rows = await cur.fetchone()
            if rows:
                return await Music.from_db(db, rows["music_id"])

            # 3) 别名子串匹配
            sql3 = """
            SELECT DISTINCT a.music_id
            FROM alias a
            WHERE LOWER(a.alias_text) LIKE '%' || ? || '%'
            """
            if sdflag or dxflag:
                sql3 += " AND a.music_id " + ("< 10000" if sdflag else ">= 10000")
            cur = await db.execute(sql3, (key,))
            rows = await cur.fetchone()
            if rows:
                return await Music.from_db(db, rows["music_id"])

            # 4) ngram 相似度：最优 FTS5 匹配
            #    如果使用 FTS5，可以利用 BM25 排序近似 ngram 效果
            cur = await db.execute(
                "SELECT music_id FROM alias_fts WHERE alias_fts MATCH ? ORDER BY bm25(alias_fts) LIMIT 1",
                (key,)
            )
            row = await cur.fetchone()
            if row:
                return await Music.from_db(db, row["music_id"])

            # 回退：返回空
            return None
        finally:
            await db.close()

    async def random(self, n: int = 1) -> Optional[List[Music]]:
        """
        随机获取n首曲子
        """
        sql = "SELECT id FROM music ORDER BY RANDOM() LIMIT ?"
        n = 1 if n < 1 else n  # 确保 n 至少为 1
        db = await self._connect()
        try:
            cursor = await db.execute(sql, (n,))
            rows = await cursor.fetchall()
            if not rows:
                return None
            result = []
            for row in rows:
                music = await Music.from_db(db, row["id"])
                if music:
                    result.append(music)
            return result
        finally:
            await db.close()

    async def random_by_seed(self, seed: int) -> Optional[Music]:
        """
        海量数据场景下的可重复随机选曲：
          1. SELECT COUNT(*) 得到记录总数 count
          2. idx = seed % count
          3. 用 LIMIT 1 OFFSET idx 查询对应的 id
          4. 调用 Music.from_db 构造并返回 Music 对象
        """
        db = await self._connect()
        try:
            # 1) 查询总数
            count_row = await (await db.execute("SELECT COUNT(*) AS cnt FROM music")).fetchone()
            count = count_row["cnt"]
            if count == 0:
                return None

            # 2) 计算偏移下标
            idx = seed % count

            # 3) 按 id 顺序取出对应那条记录的 id
            row = await (await db.execute(
                "SELECT id FROM music ORDER BY id LIMIT 1 OFFSET ?",
                (idx,)
            )).fetchone()
            if not row:
                return None

            music_id = row["id"]

            # 4) 返回完整 Music 对象（假设已有 Music.from_db 方法）
            return await Music.from_db(db, music_id)
        finally:
            await db.close()
        
    async def get_revived_music_list(self) -> List[int]:
        """
        获取 revived_music 表的所有 id
        """
        db = await self._connect()
        try:
            sql = "SELECT id FROM revived_music ORDER BY id"
            cursor = await db.execute(sql)
            rows = await cursor.fetchall()
            res = [r["id"] for r in rows]
            return res
        finally:
            db.close()

class MusicChartList:
    async def _connect(self):
        conn = await database_api.get_database_connection()
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    async def by_id(self, music_id: int, diff_index: int) -> Optional[MusicChart]:
        """
        根据曲目 ID 和难度索引获取 MusicChart
        """
        db = await self._connect()
        try:
            return await MusicChart.from_db(db, music_id, diff_index)
        finally:
            await db.close()


class BestRecordList:
    async def _connect(self):
        conn = await database_api.get_database_connection()
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    async def by_user_and_music(self, user_id: str, music_id: int, diff_index: int) -> Optional[BestRecord]:
        """
        根据用户 ID、曲目 ID 和难度索引获取最佳记录
        """
        db = await self._connect()
        try:
            return await BestRecord.from_db(db, user_id, music_id, diff_index)
        finally:
            await db.close()

    async def filter(
        self,
        user_id: Optional[str],
        pagination: Optional[Tuple[int, int]] = None,
        order: Optional[Union[str, List[str]]] = None,
        chart_list: Optional[List[Tuple[int, int]]] = None, # [(music_id, diff_index), ...] or None if no filter
        achievements_range: Optional[Tuple[float, float]] = None,
        ra_range: Optional[Tuple[int, int]] = None,
        fc_indices: Optional[List[int]] = None,
        fs_indices: Optional[List[int]] = None,
        dxscore_range: Optional[Tuple[int, int]] = None,
        is_new: Optional[bool] = None,
        version_indices: Optional[Union[int, List[int]]] = None,
        diff_indices: Optional[Union[int, List[int]]] = None,
        ds_range: Optional[Union[float, List[float], Tuple[float, float]]] = None,
        levels: Optional[Union[str, List[str]]] = None
    ) -> Dict[str, Union[int, List[BestRecord]]]:
        """
        根据以下条件筛选最佳记录：
          - user_id: 用户 ID
          - pagination: 可选，(offset, limit) 元组，指定结果的分页
          - order: 可选，指定排序顺序，格式为 ['(+/-)term1', '(+/-)term2', ...]
          - chart_list: 可选，[(music_id, diff_index), ...] 列表，指定要查询的曲目和难度索引
          - achievements_range: 可选，(min, max) 元组，指定成就值范围
          - ra_range: 可选，(min, max) 元组，指定 RA 范围
          - fc_indices: 可选，FC ID 列表
          - fs_indices: 可选，FS ID 列表
          - dxscore_range: 可选，(min, max) 元组，指定 DX 分数范围
          - is_new: 可选，是否只查询新曲目
          - version_indices: 可选，版本索引列表
          - diff_indices: 可选，难度索引列表
          - ds_range: 可选，(min, max) 元组，指定 DS
          - levels: 可选，chart.level 在列表中
        返回一个字典：
        {
            record_count: int,  # 符合条件的记录数量
            record_list: List[BestRecord]  # 符合条件的最佳记录列表
        }
        """
        sql = """
        SELECT 
            br.user_id AS user_id,
            br.music_id AS music_id,
            br.diff_index AS diff_index,
            br.achievements,
            br.ra,
            br.rank_id,
            br.fc_id,
            br.fs_id,
            br.dxscore,
            c.ds AS ds,
            cs.fit_diff AS fit_diff
        FROM best_record AS br
        JOIN music AS m ON br.music_id = m.id
        JOIN chart AS c ON br.music_id = c.music_id AND br.diff_index = c.diff_index
        LEFT JOIN chart_stats AS cs ON br.music_id = cs.music_id AND br.diff_index = cs.diff_index
        WHERE 1=1
        """

        params: List[Any] = []
        if user_id:
            sql += " AND br.user_id = ?"
            params.append(user_id)

        if chart_list:
            if not isinstance(chart_list, list):
                raise ValueError("chart_list must be a list of (music_id, diff_index) tuples.")
            placeholders = ",".join("(?, ?)" for _ in chart_list)
            sql += f" AND (br.music_id, br.diff_index) IN ({placeholders})"
            params.extend([item for sublist in chart_list for item in sublist])

        if achievements_range:
            if not isinstance(achievements_range, tuple) or len(achievements_range) != 2:
                raise ValueError("achievements_range must be a tuple of (min, max).")
            sql += " AND br.achievements BETWEEN ? AND ?"
            params.extend(achievements_range)

        if ra_range:
            if not isinstance(ra_range, tuple) or len(ra_range) != 2:
                raise ValueError("ra_range must be a tuple of (min, max).")
            sql += " AND br.ra BETWEEN ? AND ?"
            params.extend(ra_range)

        if fc_indices:
            if not isinstance(fc_indices, list):
                raise ValueError("fc_indices must be a list.")
            placeholders = ",".join("?" for _ in fc_indices)
            sql += f" AND br.fc_id IN ({placeholders})"
            params.extend(fc_indices)

        if fs_indices:
            if not isinstance(fs_indices, list):
                raise ValueError("fs_indices must be a list.")
            placeholders = ",".join("?" for _ in fs_indices)
            sql += f" AND br.fs_id IN ({placeholders})"
            params.extend(fs_indices)

        if dxscore_range:
            if not isinstance(dxscore_range, tuple) or len(dxscore_range) != 2:
                raise ValueError("dxscore_range must be a tuple of (min, max).")
            sql += " AND br.dxscore BETWEEN ? AND ?"
            params.extend(dxscore_range)

        if is_new is not None:
            if not isinstance(is_new, bool):
                raise ValueError("is_new must be a boolean.")
            sql += " AND m.is_new = ?"
            params.append(1 if is_new else 0)

        if version_indices is not None:
            if isinstance(version_indices, int):
                version_indices = [version_indices]
            elif isinstance(version_indices, (list, tuple)):
                version_indices = list(version_indices)
            else:
                raise ValueError("version_indices must be a list or integer.")
            placeholders = ",".join("?" for _ in version_indices)
            sql += f" AND m.version_id IN ({placeholders})"
            params.extend(version_indices)

        if diff_indices is not None:
            if isinstance(diff_indices, int):
                diff_indices = [diff_indices]
            elif isinstance(diff_indices, (list, tuple)):
                diff_indices = list(diff_indices)
            else:
                raise ValueError("diff_indices must be a list or integer.")
            placeholders = ",".join("?" for _ in diff_indices)
            sql += f" AND br.diff_index IN ({placeholders})"
            params.extend(diff_indices)

        if ds_range:
            if isinstance(ds_range, (int, float)):
                ds_range = (ds_range, ds_range)
            elif isinstance(ds_range, (list, tuple)):
                ds_range = tuple(ds_range)
            else:
                raise ValueError("ds_range must be a list, tuple, or single number.")
            if len(ds_range) == 1:
                ds_range = (ds_range[0], ds_range[0])
            elif len(ds_range) > 2:
                ds_range = (ds_range[0], ds_range[1])
            sql += " AND c.ds BETWEEN ? AND ?"
            params.extend(ds_range)

        if levels:
            # 确保 levels 是一个列表
            if isinstance(levels, str):
                levels = [levels]
            elif isinstance(levels, (list, tuple)):
                levels = list(levels)
            else:
                raise ValueError("levels must be a list or string.")
            placeholders = ",".join("?" for _ in levels)
            sql += f" AND c.level IN ({placeholders})"
            params.extend(levels)

        # 添加排序
        if order:
            if not isinstance(order, (str, list, tuple, set)):
                raise ValueError("order must be a string or a list.")
            if isinstance(order, str):
                order = [order]
            supported_columns = ["music_id", "diff_index", "achievements", "ra", "fc_id", "fs_id", "dxscore", "ds",
                                 "-music_id", "-diff_index", "-achievements", "-ra", "-fc_id", "-fs_id", "-dxscore", "-ds",
                                 "+music_id", "+diff_index", "+achievements", "+ra", "+fc_id", "+fs_id", "+dxscore", "+ds"]
            s = " ORDER BY"
            for term in order:
                if not term in supported_columns:
                    raise ValueError("Unsupported column name.")
                if '-' in term:
                    s += f" {term[1:]} DESC,"
                elif '+' in term:
                    s += f" {term[1:]} ASC,"
                else:
                    s += f" {term} ASC,"
            s = s[:-1]
            sql += s

        # 添加分页支持
        if pagination: 
            if not isinstance(pagination, tuple) or len(pagination) != 2:
                raise ValueError("pagination must be a tuple of (offset, limit).")
            offset, limit = pagination
            if not isinstance(offset, int) or not isinstance(limit, int):
                raise ValueError("Both offset and limit must be integers.")
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        # 执行查询并获取结果
        db = await self._connect()
        try:
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
        finally:
            await db.close()

        # 统计符合条件的记录数量
        record_count = len(rows)

        # 构造 BestRecord 对象列表
        record_list = []
        for row in rows:
            record = BestRecord(
                user_id=row["user_id"],
                music_id=row["music_id"],
                diff_index=row["diff_index"],
                achievements=row["achievements"],
                ra=None,  # 留空
                rank_id=row["rank_id"],
                fc_id=row["fc_id"],
                fs_id=row["fs_id"],
                dxscore=row["dxscore"],
                ra_b50=BestRecord.calc_ra(row["ds"], row["achievements"], b50=True),
                ra_b40=BestRecord.calc_ra(row["ds"], row["achievements"], b50=False),
                ra_stats=BestRecord.calc_ra(row["fit_diff"] if row["fit_diff"] is not None else row["ds"], row["achievements"], b50=True),
            )
            record_list.append(record)

        return {
            "record_count": record_count,
            "record_list": record_list
        }
    
class UserList:
    async def _connect(self):
        conn = await database_api.get_database_connection()
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    async def by_id(self, user_id: str) -> Optional[User]:
        """
        根据用户 ID 获取 User 对象
        """
        db = await self._connect()
        try:
            return await User.from_db(db, user_id)
        finally:
            await db.close()

class maiAliasMatcher(HybridStringMatcher):
    ALIAS_FILE = "src/static/all_alias_temp.json"

    def alias_build_index(self):
        with open(self.ALIAS_FILE, "r", encoding="utf-8") as aliasfile:
            alias_data_raw = json.load(aliasfile)

        alias_data: Dict[int, List[str]] = {}
        for music_id, music_alias in alias_data_raw.items():
            alias_data[int(music_id)] = music_alias.get("Alias", [])

        self.build_index(alias_data)
        