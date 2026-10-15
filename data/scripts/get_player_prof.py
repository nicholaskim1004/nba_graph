import sqlite3
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.neighbors import NearestNeighbors

from nba_api.stats.static import players

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

cursor.execute("DROP TABLE IF EXISTS player_profiles")
cursor.execute("""
               CREATE TABLE IF NOT EXISTS player_profiles
               (
                    season TEXT,
                    team_id INTEGER,
                    player_id INTEGER,
                    player_name TEXT,
                    positions TEXT,
                    pagerank_norm REAL,
                    E_DEF_RATING REAL,
                    AST_PCT REAL,
                    USG REAL,
                    paint_att REAL,
                    mid_range_att REAL,
                    left_corner_att REAL,
                    right_corner_att REAL,
                    above_break_att REAL
               )
               """)

query_page = "SELECT * FROM pageranks_yr"
pageranks = pd.read_sql_query(query_page, con)

query_avd = "SELECT * FROM avdstats_yr"
avdstats = pd.read_sql_query(query_avd, con)

query_shots = "SELECT * FROM shots_yr"
shots = pd.read_sql_query(query_shots, con)

positions = "SELECT * FROM positions"
pos = pd.read_sql_query(positions, con)


shot_types = ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Right Corner 3', 'Above the Break 3', 'Backcourt']


pageranks_players = pageranks[~pageranks['node_name'].isin(shot_types)]

shots = shots.loc[:,['player_id','player_name','season', 'min','team_id', 'paint_att','mid_range_att','left_corner_att','right_corner_att','above_break_att']]

zones = ['paint_att','mid_range_att','left_corner_att','right_corner_att','above_break_att']

shots_f = shots[shots['min'] > 200].copy()
total = shots_f[zones].sum(axis=1).replace(0, 1)
shots_f[zones] = shots_f[zones].div(total, axis=0)

proportion_shots = shots_f[['season','team_id','player_id','player_name'] + zones]
    
#features in player profile:
#pagerank, position, Def rating, prop at 6 shot locations, ast_pct, usg_pct

page_norm = pageranks_players.groupby(['season','team_id']).apply(lambda x: x['pagerank']/x['pagerank'].sum())
pageranks_players['pagerank_norm'] = page_norm.reset_index(level=[0,1], drop=True)

prof_df = proportion_shots.merge(pageranks_players[['player_id', 'season','team_id','pagerank_norm']], how='left', on=['season','team_id','player_id'])
prof_df = prof_df.merge(avdstats.loc[:,['player_id','season','team_id','E_DEF_RATING','AST_PCT','USG']], how='left', on=['season', 'team_id','player_id'])

pos_clean = pos.drop_duplicates(['player_id', 'positions'])

assert pos_clean['player_id'].is_unique
prof_df = prof_df.merge(pos_clean[['player_id', 'positions']],
                        how='left', on='player_id', validate='many_to_one')


prof_df.loc[:,['season','team_id','player_id','player_name','positions','pagerank_norm','E_DEF_RATING','AST_PCT','USG','paint_att','mid_range_att','left_corner_att','right_corner_att','above_break_att']].to_sql('player_profiles', con, if_exists='replace', index=False)

cursor.close()
con.close()

