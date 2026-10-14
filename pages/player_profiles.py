import sqlite3
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.neighbors import NearestNeighbors

from nba_api.stats.static import players

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()


query = "SELECT * FROM player_profiles"
prof_df = pd.read_sql_query(query, con)

features = ['positions','pagerank_norm','E_DEF_RATING','AST_PCT','USG','paint_att','mid_range_att','left_corner_att','right_corner_att','above_break_att']


preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), features[1:]),
        ('cat', OneHotEncoder(drop='first'), ['positions'])
    ]
)

X = preprocessor.fit_transform(prof_df[features])
nn = NearestNeighbors(n_neighbors=6, metric='euclidean').fit(X)

def similar(player_id, season, n=5):
    i = prof_df.index[(prof_df.player_id == player_id) & (prof_df.season == season)][0]
    pid = prof_df.at[i, 'player_id']

    # distance from the query row to every row
    dist = np.linalg.norm(X - X[i], axis=1)

    # exclude every row belonging to this player (other seasons and the row itself)
    dist[(prof_df['player_id'] == pid).to_numpy()] = np.inf

    idx = np.argsort(dist)[:n]
    return prof_df.iloc[idx].assign(distance=dist[idx])


print(players.find_players_by_full_name('LeBron James'))

print(prof_df[(prof_df['player_id'] == 2544)])
similar_players = similar(2544, '2020-21',30)

print(similar_players)