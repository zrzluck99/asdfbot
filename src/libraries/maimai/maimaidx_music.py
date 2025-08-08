import json, random, nltk, math
from typing import Dict, List, Optional, Union, Tuple, Any, Iterator
from src.libraries.tool_range import opencc_converter
from src.libraries.maimai.static_lists_and_dicts import SCORE_COEFFICIENT_TABLE, SCORE_COEFFICIENT_TABLE_LEGANCY
from copy import deepcopy
import requests
import aiohttp
import asyncio
import time

# from src.libraries.maimai.maimai_type import Music, Chart, Stats, MusicList
from src.libraries.maimai.maimai_type import Music, Chart, MusicChart, Stats, BestRecord, MusicList, BestRecordList, MusicChartList, UserList, maiAliasMatcher
from src.libraries.maimai.database import database_api
from src.libraries.query import query_user
from src.libraries.maimai.maimai_network import mai_api
from src.libraries.tool_range import fetch

cover_dir = 'src/static/mai/cover/'
temp_dir = 'src/static/mai/temp/'
assets_path = "src/static/mai/platequery/"
plate_path = "src/static/mai/plate/"

def get_cover_len4_id(mid) -> str:
    return mid


def compute_ra(ds:float, achievement:float, b50 = True)->int:
    if b50:
        score_table = SCORE_COEFFICIENT_TABLE
    else:
        score_table = SCORE_COEFFICIENT_TABLE_LEGANCY
    if achievement == 99.9999:
        return math.floor(score_table[-2][1]*ds*achievement/100)-1
    elif achievement == 100.4999:
        return math.floor(score_table[-1][1]*ds*achievement/100)-1
    else:
        for i in range(len(score_table)-1):
            if score_table[i][0] <= achievement < score_table[i+1][0]:
                return math.floor(score_table[i][1]*ds*achievement/100)
        return math.floor(score_table[-1][1]*ds*100.5/100)

def refresh_alias_temp():
    with open("src/static/all_alias.json", "r", encoding="utf-8") as aliasfile:
            alias_data = json.load(aliasfile)

    with open("src/static/alias_pre_process_add.json", "r", encoding="utf-8") as addfile, \
            open("src/static/alias_pre_process_remove.json", "r", encoding="utf-8") as removefile:
            alias_pre_process_add = json.load(addfile)
            alias_pre_process_remove = json.load(removefile)

    for key in alias_pre_process_add:
        for item in alias_pre_process_add[key]:
            if item not in alias_data[key]["Alias"]:
                alias_data[key]["Alias"].append(item)

    for key in alias_pre_process_remove:
        for item in alias_pre_process_remove[key]:
            if item in alias_data[key]["Alias"]:
                alias_data[key]["Alias"].remove(item)
    
    with open("src/static/all_alias_temp.json","w",encoding="utf-8") as fp:
        json.dump(alias_data,fp)
    return True

def delete_utage(data:json)->json:
    res = deepcopy(data)
    res["records"] = []
    for record in data["records"]:
        if int(record["song_id"]) < 100000: 
            res["records"].append(record)
    return res

async def refresh_player_full_data(username: str) -> None:
    """
    Refresh player full data from the API and sync it to the database.
    Args:
        username: The username to fetch data for.
    """
    full_data = await mai_api.get_player_records(username=username)
    full_data = delete_utage(full_data)
    await database_api.sync_user_records(full_data)
        

    
# with open("src/static/version_list.json", "r", encoding="utf-8") as fp:
#     version_list = json.load(fp)


async def refresh_music_data() -> None:
    resp = await mai_api.get_music_data()
    data = resp["data"]
    await database_api.sync_musiclist(data)

    print("music data refreshed successfully.")
    
    resp = await mai_api.get_chart_stats()
    data = resp["charts"]
    await database_api.sync_stats(data)

    print("chart stats refreshed successfully.")




# init alias

# music_data = refresh_music_list()

# loop = asyncio.get_event_loop()
# result = loop.run_until_complete(sync_musiclist(music_data))
# loop.close()

# music_data_byidstr = {}

# with open("src/static/all_alias.json", "r", encoding="utf-8") as aliasfile:
#         alias_data = json.load(aliasfile)

# for music in music_data:
#     music_data_byidstr[music['id']] = music
#     if music['id'] not in alias_data:
#         alias_data[music['id']] = {
#             "Name": music['title'],
#             "Alias": []
#         }
# with open("src/static/all_alias.json","w",encoding="utf-8") as fp:
#     json.dump(alias_data,fp)


# refresh_alias_temp()


total_list: MusicList = MusicList()
best_record_list: BestRecordList = BestRecordList()
music_chart_list: MusicChartList = MusicChartList()
user_list: UserList = UserList()
matcher: maiAliasMatcher = maiAliasMatcher()