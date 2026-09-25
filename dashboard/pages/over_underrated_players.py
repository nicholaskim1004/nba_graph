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

#standarizing naming convention for some 
pos.loc[pos['positions']=='Forward-Guard','positions'] = 'Guard-Forward'
pos.loc[pos['positions']=='Forward-Center','positions'] = 'Center-Forward'


#merging in pos to pagerank
pos = pd.merge(pageranks.loc[:,['season','team_id','node_name','player_id']],pos.loc[:,['player_id','positions']], on='player_id', how='left')

#fitting model
model = smf.ols(
    'pagerank ~ pie_shares + C(POS)',
    data=pos
).fit()

pos['expected_pagerank'] = model.predict(pos)

pos['pagerank_residual'] = (
    pos['pagerank'] - pos['expected_pagerank']
)

print(pos.sort_values('pagerank_residual',ascending=False))