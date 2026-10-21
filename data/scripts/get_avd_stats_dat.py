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

years = ['2020-21','2021-22','2022-23','2023-24','2024-25','2025-26']

team_df = pd.DataFrame(teams.get_teams())

#merge on team full name to pageranks
pageranks = pd.merge(pageranks,team_df.loc[:,['id','full_name']], left_on='team_id', right_on='id', how='left').drop(columns='id')

for yr in years:
    print(f'starting pull for season {yr}')

    for team_id in team_df['id']:
        team = team_df.loc[team_df['id'] == team_id, 'full_name'].item()
        print(f'pulling stats for team: {team}')

        avdstats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=yr,
            measure_type_detailed_defense="Advanced",
            team_id_nullable=team_id,
        ).get_data_frames()[0]

        pageranks_yr_team = pageranks[(pageranks['season'] == yr) & (pageranks['team_id'] == team_id)]

        pageranks_yr_team = pd.merge(
            pageranks_yr_team,
            avdstats.loc[:, ['PLAYER_ID','USG_PCT','PIE','AST_PCT','TS_PCT',
                             'E_OFF_RATING','E_DEF_RATING','E_NET_RATING']],
            left_on='player_id', right_on='PLAYER_ID', how='left'
        ).drop('PLAYER_ID', axis=1)

        pageranks_yr_team = pageranks_yr_team[~pageranks_yr_team['PIE'].isna()].copy()

        pageranks_yr_team['PIE_SHARE'] = pageranks_yr_team['PIE'] / pageranks_yr_team['PIE'].sum()
        pageranks_yr_team = pageranks_yr_team.rename(columns={
            'TS_PCT': 'TS',
            'USG_PCT': 'USG',
            'node_name': 'player_name',
        })

        pageranks_yr_team[['season','team_id','player_id','player_name','PIE','PIE_SHARE',
                           'TS','USG','AST_PCT','E_OFF_RATING','E_DEF_RATING','E_NET_RATING']] \
            .to_sql('avdstats_yr', con, if_exists='append', index=False)
        time.sleep(1)

    print(f'finished season {yr}...')
    
print('finished')

cursor.close()
con.close()