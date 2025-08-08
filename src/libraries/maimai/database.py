import aiosqlite
from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict, Any
from src.libraries.maimai.static_lists_and_dicts import version_list, rank_list_lower, fc_list_lower, fs_list_lower

databasePath = Path(".") / "src" / "db" / "maimai.db"
database_path = databasePath.resolve()

# Placeholder mapping functions, implement according to your schema
def get_rank_id(rank_str: str) -> int:
    return rank_list_lower.index(rank_str) if rank_str in rank_list_lower else 0

def get_fc_id(fc_str: str) -> int:
    return fc_list_lower.index(fc_str) if fc_str in fc_list_lower else 0

def get_fs_id(fs_str: str) -> int:
    # Similar lookup in fs_status table
    return fs_list_lower.index(fs_str) if fs_str in fs_list_lower else 0


class DatabaseAPI:

    async def get_database_connection(self) -> aiosqlite.Connection:
        """
        Get a connection to the SQLite database.

        Returns:
            aiosqlite.Connection: An asynchronous connection to the database.
        """
        return await aiosqlite.connect(database_path)


    async def sync_musiclist(self, music_list: List[Dict]) -> None:
        """
        Synchronize the given MusicList object to the SQLite database.

        Args:
            music_list: MusicList instance containing Music dicts to upsert.
        """
        # Open connection
        async with aiosqlite.connect(database_path) as db:
            # Ensure foreign keys are enforced
            await db.execute("PRAGMA foreign_keys = ON;")
            # Begin transaction for bulk upsert
            await db.execute("BEGIN;")

            # Upsert music entries
            music_sql = '''
            INSERT OR REPLACE INTO music(
                id, title, type, artist, genre,
                bpm, release_date, version, is_new, version_id
            ) VALUES(
                :id, :title, :type, :artist, :genre,
                :bpm, :release_date, :version, :is_new, :version_id
            );
            '''

            chart_sql = '''
            INSERT OR REPLACE INTO chart(
                music_id, diff_index, ds, level,
                notes, tap, hold, slide, touch, "break", charter
            ) VALUES(
                :music_id, :diff_index, :ds, :level,
                :notes, :tap, :hold, :slide, :touch, :brk, :charter
            );
            '''

            for music in music_list:
                # 忽略宴谱
                if int(music['id']) >= 100000:
                    continue
                # Prepare music parameters
                music_params = {
                    'id': int(music['id']),
                    'title': music['title'],
                    'type': music['type'],
                    'artist': music['basic_info']['artist'],
                    'genre': music['basic_info']['genre'],
                    'bpm': int(music['basic_info']['bpm']),
                    'release_date': music['basic_info']['release_date'],
                    'version': music['basic_info']['from'],
                    'is_new': 1 if music['basic_info']['is_new'] else 0,
                    'version_id': version_list.index(music['basic_info']['from']) if music['basic_info']['from'] in version_list else -1
                }
                await db.execute(music_sql, music_params)

                # Upsert related charts
                for diff_index, ds_val in enumerate(music['ds'] or []):
                    level_val = music['level'][diff_index]
                    # Decompose note counts
                    charts_info = music['charts'][diff_index]['notes']
                    if len(charts_info) == 4:
                        tap, hold, slide, brk = charts_info
                        touch = 0
                    elif len(charts_info) == 5:
                        tap, hold, slide, touch, brk = charts_info
                    else:
                        tap, hold, slide, touch, brk = [0,0,0,0,0]
                    notes = tap + hold + slide + touch + brk 
                    charter = music['charts'][diff_index]['charter']

                    chart_params = {
                        'music_id': int(music['id']),
                        'diff_index': diff_index,
                        'ds': float(ds_val),
                        'level': level_val,
                        'notes': notes,
                        'tap': tap,
                        'hold': hold,
                        'slide': slide,
                        'touch': touch,
                        'brk': brk,
                        'charter': charter
                    }
                    await db.execute(chart_sql, chart_params)

            # Commit transaction
            await db.commit()

    async def sync_stats(self, stats: Dict[str, Any]) -> None:
        """
        Synchronize the given Stats object to the SQLite database.

        Args:
            stats: Stats instance containing statistics to upsert.
        """
        async with aiosqlite.connect(database_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            # Begin transaction

            await db.execute("BEGIN;")

            # Upsert stats
            stats_sql = '''
            INSERT OR REPLACE INTO chart_stats(
                music_id, diff_index, level, cnt,
                fit_diff, avg, avg_dx, std_dev
            ) VALUES(
                :music_id, :diff_index, :level, :cnt,
                :fit_diff, :avg, :avg_dx, :std_dev
            );
            '''
            
            for music_id, chart_stats in stats.items():
                # 忽略宴谱
                if int(music_id) >= 100000:
                    continue
                for diff_index, stat in enumerate(chart_stats):
                    # Skip if no stats available
                    if not stat or not isinstance(stat, dict):
                        continue
                    # Prepare parameters
                    params = {
                        'music_id': int(music_id),
                        'diff_index': diff_index,
                        'level': stat.get('diff', ''),
                        'cnt': stat.get('cnt', 0),
                        'fit_diff': stat.get('fit_diff', 0.0),
                        'avg': stat.get('avg', 0.0),
                        'avg_dx': stat.get('avg_dx', 0.0),
                        'std_dev': stat.get('std_dev', 0.0)
                    }
                    await db.execute(stats_sql, params)

            stats_sql_rank = '''
            INSERT OR REPLACE INTO chart_rating_dist(
                music_id, diff_index, rating_index, count
            ) VALUES(
                :music_id, :diff_index, :rating_index, :count
            );
            '''

            # Upsert rank distribution
            for music_id, chart_stats in stats.items():
                # 忽略宴谱
                if int(music_id) >= 100000:
                    continue
                for diff_index, stat in enumerate(chart_stats):
                    if 'dist' in stat:
                        for rating_index, count in enumerate(stat['dist']):
                            params = {
                                'music_id': int(music_id),
                                'diff_index': diff_index,
                                'rating_index': rating_index,
                                'count': count
                            }
                            await db.execute(stats_sql_rank, params)

            stats_sql_fc = '''
            INSERT OR REPLACE INTO chart_fc_dist(
                music_id, diff_index, fc_index, count
            ) VALUES(
                :music_id, :diff_index, :fc_index, :count
            );
            '''

            # Upsert full combo distribution
            for music_id, chart_stats in stats.items():
                # 忽略宴谱
                if int(music_id) >= 100000:
                    continue
                for diff_index, stat in enumerate(chart_stats):
                    if 'fc_dist' in stat:
                        for fc_index, count in enumerate(stat['fc_dist']):
                            params = {
                                'music_id': int(music_id),
                                'diff_index': diff_index,
                                'fc_index': fc_index,
                                'count': count
                            }
                            await db.execute(stats_sql_fc, params)

            # Commit transaction
            await db.commit()


    async def sync_user_records(self, user_json: Dict[str, Any]) -> None:
        """
        Synchronize user profile and best records into SQLite database.

        Args:
            user_json: JSON object parsed as dict with keys:
                - username (user_id)
                - additional_rating, nickname, plate, rating
                - records: list of record dicts
        """
        async with aiosqlite.connect(database_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            # Begin transaction
            await db.execute("BEGIN;")

            # Upsert user profile
            user_sql = '''
            INSERT OR REPLACE INTO user(
                id, additional_rating, nickname, plate, rating, ts
            ) VALUES(
                :id, :additional_rating, :nickname, :plate, :rating, CURRENT_TIMESTAMP
            );
            '''
            user_params = {
                'id': user_json.get('username').lower(),  # Ensure username is lowercase
                'additional_rating': user_json.get('additional_rating'),
                'nickname': user_json.get('nickname'),
                'plate': user_json.get('plate'),
                'rating': user_json.get('rating')
            }
            await db.execute(user_sql, user_params)

            # Upsert each best record
            record_sql = '''
            INSERT OR REPLACE INTO best_record(
                user_id, music_id, diff_index,
                achievements, ra, dxscore, rank_id, fc_id, fs_id, ts
            ) VALUES(
                :user_id, :music_id, :diff_index,
                :achievements, :ra, :dxscore, :rank_id, :fc_id, :fs_id, CURRENT_TIMESTAMP 
            );
            '''
            user_id = user_json.get('username').lower()  # Ensure user_id is lowercase
            for rec in user_json.get('records', []):
                # Resolve fc_id and fs_id if mapping tables exist
                fc_str = rec.get('fc', '')
                fs_str = rec.get('fs', '')
                fc_id = get_fc_id(fc_str)
                fs_id = get_fs_id(fs_str)

                params = {
                    'user_id': user_id,
                    'music_id': rec.get('song_id'),
                    'diff_index': rec.get('level_index'),
                    'achievements': rec.get('achievements'),
                    'ra': rec.get('ra'),
                    'dxscore': rec.get('dxScore'),
                    'rank_id': get_rank_id(rec.get('rate', 'd')),  # Default to 'd' if not present
                    'fc_id': fc_id,
                    'fs_id': fs_id
                }

                # print(f"Upserting record for user {user_id}, music {params['music_id']}, diff {params['diff_index']}")
                await db.execute(record_sql, params)

            # Commit transaction
            await db.commit()
    
    async def check_user_exists(self, username: str) -> bool:
        """
        Check if a user exists in the database.

        Args:
            username: The user ID to check.

        Returns:
            bool: True if the user exists, False otherwise.
        """
        async with aiosqlite.connect(database_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM user WHERE id = ?", (username,))
            count = await cursor.fetchone()
            return count[0] > 0
        
    async def check_user_outdated(self, username: str) -> bool:
        """
        Check if a user's data is outdated.

        Args:
            username: The user ID to check.

        Returns:
            bool: True if the user's data is outdated, False otherwise.
        """
        async with aiosqlite.connect(database_path) as db:
            cursor = await db.execute("SELECT ts FROM user WHERE id = ?", (username,))
            row = await cursor.fetchone()
            if row:
                last_update = row[0]
                # Compare with current time, assuming outdated if older than 24 hours
                # sqlite stores timestamps as strings in ISO format, so we should parse it.
                last_update_dt = datetime.fromisoformat(last_update)
                current_time = datetime.now()
                return (current_time - last_update_dt).total_seconds() > 86400  # 24 hours
            return True

database_api = DatabaseAPI()