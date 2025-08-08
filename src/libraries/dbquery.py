# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
from typing import Dict, Any, Tuple

source_path = Path(".") / "src"
userdata_path = source_path / "dabingdata.db"

def db_query_user(userid: str) -> Tuple[str, str]:
    try:
        conn = sqlite3.connect(str(userdata_path))
        cur = conn.cursor()
        sql_command = '''
        SELECT DabingUsername, DabingPassword FROM UserData WHERE OpenId = ?
        '''
        res = cur.execute(sql_command, (userid,))
        res_one = res.fetchone()
        if res_one is None:
            Result = None
        else:
            Result = res_one
    except Exception:
        Result = None
    return Result

def db_bind_user(userid: str, username: str, password: str) -> int:
    Result = 1
    try: 
        conn = sqlite3.connect(str(userdata_path))
        cur = conn.cursor()
        sql_command = '''
        SELECT * FROM UserData WHERE OpenId = ?
        '''
        res = cur.execute(sql_command, (userid,))
        if not (res.fetchone() is None):
            Result = db_delete_user(userid)
        sql_command = '''
        INSERT INTO UserData (OpenId, DabingUsername, DabingPassword) VALUES
            (?, ?, ?)
        '''
        cur.execute(sql_command, (userid, username, password))
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        Result = -1
    return Result

def db_delete_user(userid: str) -> int:
    try:
        conn = sqlite3.connect(str(userdata_path))
        cur = conn.cursor()
        sql_command = '''
        DELETE FROM UserData WHERE OpenId = ?
        '''
        cur.execute(sql_command, (userid,))
        Result = 1
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        Result = -1
    return Result
