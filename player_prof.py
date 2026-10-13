import sqlite3
import pandas as pd
import numpy as np

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_page = "SELECT * FROM pageranks_yr"
pageranks = pd.read_sql_query(query_page, con)

query_avd = "SELECT * FROM avdstats_yr"
avdstats = pd.read_sql_query(query_avd, con)

positions = "SELECT * FROM positions"
pos = pd.read_sql_query(positions, con)


shot_types = ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Right Corner 3', 'Above the Break 3', 'Backcourt']


pageranks_players = pageranks[~pageranks['node_name'].isin(shot_types)]

pageranks_players = pageranks_players.merge(pos, how='left', on='player_id')
print(pageranks_players.head())