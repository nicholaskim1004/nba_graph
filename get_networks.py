import time
import sqlite3
import pandas as pd


con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

yr = '2024-25'

shots_24 = cursor.execute("SELECT * FROM shots_yr WHERE season = ?", (yr,))

print(shots_24.fetchall())