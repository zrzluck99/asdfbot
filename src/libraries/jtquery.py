# -*- coding: utf-8 -*-
import sqlite3
from nonebot import logger
from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path
import os

source_path = Path(".") / "src"
jtdata_path = source_path / "jtdata.db"

def query_record(jt_name: str) -> Any:
    try:
        conn = sqlite3.connect(str(jtdata_path))
        cur = conn.cursor()
        sql_command = '''
        SELECT jtNumber, openTimeStamp, closeTimeStamp, updateTimeStamp, openTime, closeTime, alias, aliasEnabled FROM jtData WHERE jtName = ?
        '''
        res = cur.execute(sql_command, (jt_name,))
        res_one = res.fetchone()
        if res_one is None:
            Result = (0, None)
        else:
            Result = (1, res_one)
        return Result
    except Exception as e:
        raise e
    finally:
        cur.close()
        conn.close()

def update_record(jt_name: str, jt_number: str, open_timestamp: int, close_timestamp: int, update_timestamp: int, open_time: str, close_time: str, alias: str, alias_enabled: int) -> None:
    try:
        conn = sqlite3.connect(str(jtdata_path))
        cur = conn.cursor()
        sql_command = '''
        DELETE FROM jtData WHERE jtName = ?
        '''
        cur.execute(sql_command, (jt_name,))
        sql_command = '''
        INSERT INTO jtData (jtName, jtNumber, openTimeStamp, closeTimeStamp, updateTimeStamp, openTime, closeTime, alias, aliasEnabled) VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        cur.execute(sql_command, (jt_name, jt_number, open_timestamp, close_timestamp, update_timestamp, open_time, close_time, alias, alias_enabled))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def query_jt(query_timestamp: int, jt_name: str) -> str:
    try:
        status, data = query_record(jt_name=jt_name)
        if 0 == status:
            Result = (0, None)
        else:
            jt_number, open_timestamp, close_timestamp, update_timestamp, open_time, close_time, alias, alias_enabled = data
            if open_timestamp > query_timestamp > close_timestamp:
                Result = (2, None)
            else:
                if query_timestamp >= open_timestamp:
                    update_jt(jt_name=jt_name, jt_number="0", update_timestamp=open_timestamp)
                    if alias_enabled:
                        Result = (3, data)
                    else:
                        Result = query_record(jt_name=jt_name)
                else:
                    if alias_enabled:
                        Result = (3, data)
                    else:
                        Result = (1, data)
    except Exception as e:
        logger.error(f"Error: {e}")
        Result = (-1, None)
    print(Result)
    return Result



def string_to_timedelta(time_str):
    hours, minutes = map(int, time_str.split(':'))
    return timedelta(hours=hours, minutes=minutes, seconds=0)

def calc_timestamp(update_timestamp: int, open_time: str, close_time: str):
    update_datetime = datetime.fromtimestamp(update_timestamp)
    open_datetime = datetime(update_datetime.year, update_datetime.month, update_datetime.day, 0, 0, 0) + string_to_timedelta(open_time)
    if open_datetime <= update_datetime:
        open_datetime += timedelta(days=1)
    close_datetime = datetime(open_datetime.year, open_datetime.month, open_datetime.day, 0, 0, 0) + string_to_timedelta(close_time)
    if close_datetime >= open_datetime:
        close_datetime -= timedelta(days=1)
    open_timestamp = int(open_datetime.timestamp())
    close_timestamp = int(close_datetime.timestamp())
    return open_timestamp, close_timestamp


def update_jt(update_timestamp: int, jt_name: str, jt_number: str) -> int:
    try: 
        status, data = query_record(jt_name=jt_name)
        if 0 == status:
            Result = 0
        else:
            _, _, _, _, open_time, close_time, alias, alias_enabled = data
            open_timestamp, close_timestamp = calc_timestamp(update_timestamp, open_time, close_time)

            if open_timestamp > update_timestamp > close_timestamp:
                Result = 2
            else:
                update_record(jt_name=jt_name, jt_number=jt_number, open_timestamp=open_timestamp, close_timestamp=close_timestamp, update_timestamp=update_timestamp, open_time=open_time, close_time=close_time, alias=alias, alias_enabled=alias_enabled)
                Result = 1

            if alias_enabled:
                Result = 3
    except Exception as e:
        logger.error(f"Error: {e}")
        Result = -1
    return Result

def create_jt(create_timestamp: int, jt_name: str, open_time: str = "10:00", close_time: str = "22:00", alias: str = "", alias_enabled: int = 0) -> int:
    try: 
        status, data = query_record(jt_name=jt_name)
        if 1 == status:
            Result = 0
        else:
            open_timestamp, close_timestamp = calc_timestamp(update_timestamp=create_timestamp, open_time=open_time, close_time=close_time)
            update_record(jt_name=jt_name, jt_number=0, open_timestamp=open_timestamp, close_timestamp=close_timestamp, update_timestamp=open_timestamp-86400, open_time=open_time, close_time=close_time, alias=alias, alias_enabled=alias_enabled)
            Result = 1
    except Exception:
        Result = -1
    return Result

def delete_jt(jt_name: str) -> int:
    try: 
        conn = sqlite3.connect(str(jtdata_path))
        cur = conn.cursor()
        sql_command = '''
        DELETE FROM jtData WHERE jtName = ?
        '''
        cur.execute(sql_command, (jt_name,))
        Result = 1
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        Result = -1
    return Result