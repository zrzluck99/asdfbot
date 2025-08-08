# -*- coding: utf-8 -*-
import sqlite3
import json
from pathlib import Path

source_path = Path(".") / "src"
userdata_path = source_path / "userdata.db"

def query_user(userid: str) -> str:
    try:
        with open('src/users/' + userid + '.json', "r") as f:
            user_settings = json.load(f)
    except:
        user_settings = {}

    Result = user_settings.get('divingfish_id', None)
    return Result.lower() if Result else None


def bind_user(userid: str, username: str) -> int:
    try:
        with open('src/users/' + userid + '.json', "r") as f:
            user_settings = json.load(f)
    except:
        user_settings = {}

    try:
        user_settings["divingfish_id"] = username.lower()
        with open(f"src/users/{userid}.json","w") as f:
            json.dump(user_settings, f, indent=4)

        Result = 1
    except:
        Result = -1

    return Result

def update():
    conn = sqlite3.connect(str(userdata_path))
    cur = conn.cursor()
    sql_command = '''
    SELECT * FROM UserData
    '''
    res = cur.execute(sql_command)
    res_all = res.fetchall()
    for userid, username in res_all:
        bind_user(userid, username)

