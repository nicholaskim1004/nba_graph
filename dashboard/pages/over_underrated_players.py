import sqlite3
import pandas as pd

import dash

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_pos = 'SELECT * FROM positions'
pos = pd.read_sql_query(query_pos, con)

query_page = 'SELECT * FROM pageranks_yr'
pageranks = pd.read_sql_query(query_page, con)

query_id = 'SELECT DISTINCT player_id, player_name FROM shots_yr'
player_ids = pd.read_sql_query(query_id, con)

#standarizing naming convention for some 
pos.loc[pos['positions']=='Forward-Guard','positions'] = 'Guard-Forward'
pos.loc[pos['positions']=='Forward-Center','positions'] = 'Center-Forward'

#mergining on player id to pagerank
pageranks = pd.merge(pageranks.loc[:,['season','team_id','node_name','pagerank']], player_ids, left_on='node_name', right_on='player_name', how='left' )
print(pageranks.head())

#merging in pos to pagerank
#pos = pd.merge(pageranks,pos.loc[:,['player_name','positions']], left_on='node_name', right_on='player_name', how='left')
#print(pos.head())