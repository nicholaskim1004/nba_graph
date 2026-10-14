import sqlite3
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.neighbors import NearestNeighbors

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

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
prof_df = prof_df.merge(avdstats.loc[:,['player_id','season','E_DEF_RATING','AST_PCT','USG']], how='left', on=['season', 'player_id'])
prof_df = prof_df.merge(pos.loc[:,['player_id','positions']], how='left', on='player_id')

print(prof_df.duplicated(['season','team_id','player_id']).sum())

features = ['positions','pagerank_norm','E_DEF_RATING','AST_PCT','USG','paint_att','mid_range_att','left_corner_att','right_corner_att','above_break_att']


preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), features[1:]),
        ('cat', OneHotEncoder(drop='first'), ['positions'])
    ]
)

X = preprocessor.fit_transform(prof_df[features])
nn = NearestNeighbors(n_neighbors=6, metric='euclidean').fit(X)

def similar(player_name, season, n=5):
    i = prof_df.index[(prof_df.player_name == player_name) & (prof_df.season == season)][0]
    pid = prof_df.at[i, 'player_id']

    # distance from the query row to every row
    dist = np.linalg.norm(X - X[i], axis=1)

    # exclude every row belonging to this player (other seasons and the row itself)
    dist[(prof_df['player_id'] == pid).to_numpy()] = np.inf

    idx = np.argsort(dist)[:n]
    return prof_df.iloc[idx].assign(distance=dist[idx])

print(prof_df[prof_df['player_id'] == 201942])

print(prof_df['season'].unique())

similar_players = similar('DeMar DeRozan', '2020-21',30)

print(similar_players)