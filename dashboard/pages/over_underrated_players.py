import sqlite3
import pandas as pd

import statsmodels.formula.api as smf
import dash

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_pos = 'SELECT * FROM positions'
pos = pd.read_sql_query(query_pos, con)

query_page = 'SELECT * FROM pageranks_yr'
pageranks = pd.read_sql_query(query_page, con)

query_avd = 'SELECT * FROM avdstats_yr'
avdstats_yr = pd.read_sql_query(query_avd, con)

diff_shots = ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Right Corner 3', 'Above the Break 3', 'Backcourt']

#standarizing naming convention for some 
pos.loc[pos['positions']=='Forward-Guard','positions'] = 'Guard-Forward'
pos.loc[pos['positions']=='Forward-Center','positions'] = 'Center-Forward'


#merging in pos to pagerank
pageranks = pd.merge(pageranks.loc[:,['season','team_id','node_name','player_id','pagerank']],pos.loc[:,['player_id','positions']], on='player_id', how='left')

#merging avd stats to pos df
pageranks_avd = pd.merge(pageranks, avdstats_yr.loc[:,['season','team_id','player_id','PIE_SHARE']], on=['player_id','season','team_id'], how='left')

#subset to only players
pageranks_avd_players = pageranks_avd[~pageranks_avd['node_name'].isin(diff_shots)]

# drop rows with missing target/predictors up front so train/test are clean
model_data = pageranks_avd_players.dropna(subset=['pagerank', 'PIE_SHARE', 'positions']).copy()

train_df, test_df = train_test_split(model_data, test_size=0.2, random_state=42)

# fit on train only
model = smf.ols(
    'pagerank ~ PIE_SHARE + C(positions)',
    data=train_df
).fit()

print(model.summary())

# predict on test set to evaluate generalization
test_df['expected_pagerank'] = model.predict(test_df)
test_df['pagerank_residual'] = test_df['pagerank'] - test_df['expected_pagerank']

print('Test R2:', r2_score(test_df['pagerank'], test_df['expected_pagerank']))
print('Test RMSE:', mean_squared_error(test_df['pagerank'], test_df['expected_pagerank']))

# once you're happy with performance, apply the model to the FULL dataset
# (train+test+anything else) to get expected_pagerank/residual for every row
pageranks_avd_players['expected_pagerank'] = model.predict(pageranks_avd)
pageranks_avd_players['pagerank_residual'] = pageranks_avd_players['pagerank'] - pageranks_avd_players['expected_pagerank']
print(pageranks_avd_players.loc[pageranks_avd_players['PIE_SHARE'].isna(),['season','team_id','node_name','player_id']])
print(pageranks_avd_players[pageranks_avd_players['PIE_SHARE'].isna()&(pageranks_avd_players['node_name']=='Horford, Al')])