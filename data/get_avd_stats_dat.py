import time
import sqlite3
import pandas as pd
import numpy as np

from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguedashplayerstats

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

#drop pagerank table if it exists to avoid duplicates
cursor.execute("DROP TABLE IF EXISTS avdstats_yr")

#set up table for storing position info for each player
cursor.execute("""
               CREATE TABLE IF NOT EXISTS avdstats_yr
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
                   E_NET_RATING REAL
               )
               """)

query = "SELECT * FROM pageranks_yr"
pageranks = pd.read_sql_query(query, con)

years = ['2020-21','2021-22','2023-24','2024-25','2025-26']

team_df = pd.DataFrame(teams.get_teams())

#merge on team full name to pageranks
pageranks = pd.merge(pageranks,team_df.loc[:,['id','full_name']], left_on='team_id', right_on='id', how='left').drop(columns='id')

for yr in years:
    print(f'starting pull for season {yr}')
    
    print('bringing in avd stats table 🤓')
    avdstats = leaguedashplayerstats.LeagueDashPlayerStats(season=yr,measure_type_detailed_defense="Advanced").get_data_frames()[0]
    avdstats['TOTAL_MIN'] = avdstats['GP']*avdstats['MIN']
    
    pageranks_yr = pageranks[pageranks['season']==yr]
    
    pageranks_yr = pd.merge(pageranks_yr,avdstats.loc[:,['PLAYER_ID','TOTAL_MIN','USG_PCT','PIE','AST_PCT','TS_PCT','E_OFF_RATING','E_DEF_RATING','E_NET_RATING']], left_on='player_id', right_on='PLAYER_ID', how='left').drop('PLAYER_ID', axis = 1)
    
    #creating measure to adjust PIE by the total min they played
    confidence = [min(pageranks_yr['TOTAL_MIN'][i] / 1000, 1) for i in range(len(pageranks_yr['TOTAL_MIN']))]

    adj_pie = pageranks_yr['PIE'] * confidence

    pageranks_yr['ADJ_PIE'] = adj_pie

    #filtering out nan
    pageranks_yr = pageranks_yr[~pageranks_yr['ADJ_PIE'].isna()]
    
    pie_shares = []

    print('starting calc pie_share')
    for team in pageranks_yr['full_name'].unique():
        print(f'pie share adjust for team {team}')
        t_pie = np.sum(pageranks_yr[pageranks_yr['full_name']==team]['ADJ_PIE'])
        pie_shares.extend(pageranks_yr[pageranks_yr['full_name']==team]['ADJ_PIE']/t_pie)
        
    pageranks_yr['PIE_SHARE'] = pie_shares
    pageranks_yr = pageranks_yr.rename(columns={
                                            'TS_PCT': 'TS',
                                            'USG_PCT': 'USG',
                                            'PIE_SHARES': 'PIE_SHARE',
                                            'node_name': 'player_name'
                                        })
    
    chunksize = pageranks_yr.shape[0]
    print(f'saving season {yr} to database...')
    pageranks_yr.loc[:,['season','team_id','player_id','player_name','TOTAL_MIN','PIE','PIE_SHARE','TS','USG','AST_PCT','E_OFF_RATING','E_DEF_RATING','E_NET_RATING']].to_sql('avdstats_yr', con, if_exists='append', index=False, chunksize=chunksize)

print('finished')

cursor.close()
con.close()