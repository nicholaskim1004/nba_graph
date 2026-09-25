import sqlite3
import pandas as pd

import statsmodels.formula.api as smf
import dash

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_pos = 'SELECT * FROM positions'
pos = pd.read_sql_query(query_pos, con)

query_page = 'SELECT * FROM pageranks_yr'
pageranks = pd.read_sql_query(query_page, con)

query_avd = 'SELECT * FROM avdstats_yr'
avdstats_yr = pd.read_sql_query(query_avd, con)

#standarizing naming convention for some 
pos.loc[pos['positions']=='Forward-Guard','positions'] = 'Guard-Forward'
pos.loc[pos['positions']=='Forward-Center','positions'] = 'Center-Forward'


#merging in pos to pagerank
pageranks = pd.merge(pageranks.loc[:,['season','team_id','node_name','player_id']],pos.loc[:,['player_id','positions']], on='player_id', how='left')

#merging avd stats to pos df
pageranks_avd = pd.merge(pageranks, avdstats_yr.loc[:,['season','team_id','player_id','PIE_SHARE']], on=['player_id','season','team_id'], how='left')

print(pageranks_avd.head())
#fitting model
