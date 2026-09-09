import time
import sqlite3
import numpy as np
import pandas as pd

from nba_api.stats.static import teams
from nba_api.stats.endpoints import playerdashptpass

#function to convert playerdashptpass data to a dataframe of passes between teammates
#stores the count & proportion of passes from each player to each teammate in the dataframe
def get_team_pass_df(team_df, team_id, season, season_type='Regular Season'):
    pass_row_inf = []
    
    pulled = {}
    for _, trow in team_df.iterrows():
        while True:
            try:
                if trow['player_id'] in pulled.keys():
                    print(f"Already pulled data for player {trow['player_name']}, skipping...")
                    break
                else:
                    player_info = playerdashptpass.PlayerDashPtPass(team_id=team_id, player_id=int(trow['player_id']), season=season, season_type_all_star=season_type).get_data_frames()[0]
                    #ensure the pass to player is teammate in dataframe
                    player_info = player_info[player_info['PASS_TEAMMATE_PLAYER_ID'].isin(team_df['player_id'])]
                    pulled[trow['player_id']] = True
                    for _, row in player_info.iterrows():
                        pass_row_inf.append({'player_id': row['PLAYER_ID'], 'player_name': row['PLAYER_NAME_LAST_FIRST'], 'pass_to_id': row['PASS_TEAMMATE_PLAYER_ID'], 'pass_to': row['PASS_TO'], 'count': row['PASS'], 'proportion': row['FREQUENCY']})
                    break
            except Exception as e:
                print(f"Error occurred: {trow['player_name']}: {e}")
                print("Retrying after 30 seconds...")
                time.sleep(30)  # Sleep for 30 seconds to avoid rate limiting
                get_team_pass_df(team_df, team_id, season)  # Retry the function
                break
        time.sleep(1)
            
    return pd.DataFrame(pass_row_inf)

#setting up & connecting to database
con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

#set up table for storing pass proportions between teammates for each team 
#cursor.execute("""
#               CREATE TABLE IF NOT EXISTS team_passes
#               (
#                   player_id INTEGER,
#                   player_name TEXT,
#                   season TEXT,
#                   team_id INTEGER,
#                   pass_to_id INTEGER,
#                   pass_to TEXT,
#                   count INTEGER,
#                   proportion REAL
#               )
#               """)

#years = ['2020-21','2021-22','2022-23','2023-24','2024-25','2025-26']
yr = '2024-25'

team_list = teams.get_teams()
#print(team_list)

query = f"SELECT * FROM shots_yr WHERE season = '{yr}'"
shots_24 = pd.read_sql_query(query, con)

print(get_team_pass_df(shots_24.loc[shots_24['team_id'] == 1610612737], 1610612737, yr))