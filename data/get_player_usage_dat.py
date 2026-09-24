import sqlite3
import pandas as pd # type: ignore[import-not-found]
import numpy as np # type: ignore[import-not-found]
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

#drop table if it exists to avoid duplicates
cursor.execute("DROP TABLE IF EXISTS player_usage_yr")

#set up table for storing cumlative player usage stats for each team 
#an all in one metric that describes how centeralized or spread out the offensive workload is among players
cursor.execute("""
               CREATE TABLE IF NOT EXISTS player_usage_yr
               (
                   season TEXT,
                   team_id INTEGER,
                   gini REAL,
                   entropy REAL,
                   eff_num_players REAL
               )
               """)

#drop table if it exists to avoid duplicates
cursor.execute("DROP TABLE IF EXISTS player_usage_yr_playoff")

#set up table for storing table for playoffs
cursor.execute("""
               CREATE TABLE IF NOT EXISTS player_usage_yr_playoff
               (
                   season TEXT,
                   team_id INTEGER,
                   gini REAL,
                   entropy REAL,
                   eff_num_players REAL
               )
               """)


query_page = "SELECT * FROM pageranks_yr"
pageranks_yr = pd.read_sql_query(query_page, con)

query_page_play = "SELECT * FROM pageranks_playoffs_yr"
pageranks_yr_play = pd.read_sql_query(query_page_play, con)

team_list = teams.get_teams()

years = ['2020-21','2021-22', '2022-23', '2024-25', '2025-26']

diff_shots = ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Right Corner 3', 'Above the Break 3', 'Backcourt']

def gini_coef(x):
    x = np.asarray(x, dtype = np.float64)
    
    if np.any(x < 0):
        raise ValueError("Gini coeff requires non negative values")
    x = np.sort(x)
    n = len(x)
    index = np.arange(1, n + 1)

    return (np.sum((2 * index - n - 1)* x)) / (n * np.sum(x))

def normalized_entropy(p):
    p = np.array(p)
    p = p[p > 0]  
    N = len(p)
    if N <= 1:
        return 0.0
    H = -np.sum(p * np.log(p))
    return H / np.log(N)

##regular season
print(f"starting data pull for Regular Season ✅")

for yr in years:
    print(f'getting data for {yr} season')
    
    for team in team_list:
        print(f'getting player usage inf on {team['full_name']}')
        teamid = team['id']
        
        #only want the player nodes for given year and team
        pageranks_yr_players = pageranks_yr[
                                        (pageranks_yr['season']==yr)&
                                        (pageranks_yr['team_id']==teamid)&
                                        (~pageranks_yr['node_name'].isin(diff_shots))
                                        ]
        
        p = pageranks_yr_players['pagerank'].to_numpy()
        
        #normalize pageranks to just players
        p = p/p.sum()
        
        gini = gini_coef(p)
        entropy = normalized_entropy(p)
        eff_num_players = len(p)/np.sum(p**2)
        
        pd.DataFrame({'season': str(yr), 
                      'team_id': int(teamid),
                      'gini': gini,
                      'entropy': entropy,
                      'eff_num_players': eff_num_players
                      }, index=[0]).to_sql('player_usage_yr', con, if_exists='append', index=False)
        
        print(f'saving data {team['full_name']} in {yr} to database 🕺')
    print(f'finished saving info for season {yr}...')

## Playoffs
print('starting pull for playoffs 🏆')

for yr in years:
    teams_in_play = pageranks_yr_play[pageranks_yr_play['season']==yr].loc[:,'team_id'].to_numpy()
    
    for teamid in teams_in_play:
        pageranks_yr_play_players = pageranks_yr_play[
                                        (pageranks_yr_play['season']==yr)&
                                        (pageranks_yr_play['team_id']==teamid)&
                                        (~pageranks_yr_play['node_name'].isin(diff_shots))
                                    ]
        
        p = pageranks_yr_play_players['pagerank'].to_numpy()
        
        #normalize pageranks to just players
        p = p/p.sum()
        
        gini = gini_coef(p)
        entropy = normalized_entropy(p)
        eff_num_players = len(p)/np.sum(p**2)
        
        pd.DataFrame({'season': str(yr), 
                      'team_id': int(teamid),
                      'gini': gini,
                      'entropy': entropy,
                      'eff_num_players': eff_num_players
                      }, index=[0]).to_sql('player_usage_yr_playoff', con, if_exists='append', index=False)
        print(f'saving data {teamid} in {yr} to database 🕺')
    print(f'finished for {yr} season')

print('finished ')

#close connection and cursor
cursor.close()
con.close()
