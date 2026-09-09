import time
import sqlite3
import pandas as pd


con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

yr = '2024-25'

query = f"SELECT * FROM shots_yr WHERE season = '{yr}'"
shots_24 = pd.read_sql_query(query, con)
print(shots_24)