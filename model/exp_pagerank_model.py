import sqlite3
import pandas as pd

import statsmodels.formula.api as smf
from sklearn.model_selection import train_test_split
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_pos = 'SELECT * FROM positions'
pos = pd.read_sql_query(query_pos, con)

query_page = 'SELECT * FROM pageranks_yr'
pageranks = pd.read_sql_query(query_page, con)

query_avd = 'SELECT * FROM avdstats_yr'
avdstats_yr = pd.read_sql_query(query_avd, con)

#drop table if it exists to avoid duplicates
cursor.execute("DROP TABLE IF EXISTS expected_pagerank_yr")

#set up table for storing model
cursor.execute("""
               CREATE TABLE IF NOT EXISTS expected_pagerank_yr
               (
                   season TEXT,
                   team_id INTEGER,
                   player_id INTEGER,
                   player_name TEXT,
                   TOTAL_MIN INTEGER,
                   PIE REAL, 
                   PIE_SHARE REAL,
                   TS REAL,
                   USG REAL,
                   AST_PCT REAL,
                   E_OFF_RATING REAL,
                   E_DEF_RATING REAL,
                   E_NET_RATING REAL,
                   expected_pagerank REAL, 
                   pagerank_residual REAL
               )
               """)


seasons = pageranks['season'].unique()
team_df = pd.DataFrame(teams.get_teams())

diff_shots = ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Right Corner 3', 'Above the Break 3', 'Backcourt']

print('standarizing position naming conventions')
#standarizing naming convention for some 
pos.loc[pos['positions']=='Forward-Guard','positions'] = 'Guard-Forward'
pos.loc[pos['positions']=='Forward-Center','positions'] = 'Center-Forward'

print('cleaning up missing player ids')
#cleaning up missing player ids before merges
pageranks_players = pageranks[~pageranks['node_name'].isin(diff_shots)]
wrong_ids = pageranks_players[pageranks_players['player_id'].isna()]

player_to_id_df = pageranks_players.loc[~pageranks_players['player_id'].isna(),['node_name','player_id']].drop_duplicates(subset=['node_name'], ignore_index=True)

for _, row in wrong_ids.iterrows():
    index = row.name

    player_name = row['node_name']
    
    pageranks_players.loc[index,'player_id'] = player_to_id_df.loc[player_to_id_df['node_name']==player_name,'player_id'].values

print('mergining data with advanced stats')
#merging in pos to pagerank
pageranks_players = pd.merge(pageranks_players.loc[:,['season','team_id','node_name','player_id','pagerank']],pos.loc[:,['player_id','positions']], on='player_id', how='left')

#merging avd stats to pos df
pageranks_avd_players = pd.merge(pageranks_players, avdstats_yr.loc[:,['season','team_id','player_id','PIE_SHARE']], on=['player_id','season','team_id'], how='left')

# drop rows with missing target/predictors up front so train/test are clean
model_data = pageranks_avd_players.dropna(subset=['pagerank', 'PIE_SHARE', 'positions']).copy()

train_df, test_df = train_test_split(model_data, test_size=0.2, random_state=42)

print('fitting model')
# fit on train only
model = smf.ols(
    'pagerank ~ PIE_SHARE + C(positions)',
    data=train_df
).fit()

print('making predictions')
# predict on test set to evaluate generalization
test_df['expected_pagerank'] = model.predict(test_df)
test_df['pagerank_residual'] = test_df['pagerank'] - test_df['expected_pagerank']

pageranks_avd_players['expected_pagerank'] = model.predict(pageranks_avd_players)
pageranks_avd_players['pagerank_residual'] = pageranks_avd_players['pagerank'] - pageranks_avd_players['expected_pagerank']

print('saving model predictions to databse')
pageranks_avd_players.to_sql('expected_pagerank_yr', con, if_exists='replace', index=False)
print('finished')

cursor.close()
con.close()