# -*- coding: utf-8 -*-
import sqlite3

with sqlite3.connect("jtdata.db") as conn:
    cur = conn.cursor()
    sql_command = '''DROP TABLE IF EXISTS jtData
    '''
    cur.execute(sql_command)
    sql_command = '''CREATE TABLE jtData
    (jtName TEXT,
     jtNumber TEXT,
     jtTime TEXT)
    '''
    cur.execute(sql_command)
    conn.commit()
    cur.close()