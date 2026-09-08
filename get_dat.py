import time
import sqlite3
import numpy as np 
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

from nba_api.stats.static import teams, players
from nba_api.stats.endpoints import commonteamroster, leaguedashplayershotlocations, PlayerCareerStats, TeamPlayerDashboard, playerdashptpass


#functions

#setting up database
#connect to database
con = sqlite3.connect('data/nba.db')
cursor = con.cursor()

def db_connect():
    con = sqlite3.connect('data/nba.db')
    return con

def db_init():
    con = db_connect()
    cursor = con.cursor()
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS shot_proportions """)

#run on all years once its working for one year
#years = ['2020-21','2021-22','2022-23','2023-24','2024-25','2025-26']

yr = '2024-25'

#shots dataset
shots_yr = leaguedashplayershotlocations.LeagueDashPlayerShotLocations(season=yr, season_type_all_star='Regular Season').get_data_frames()[0]

traded_players_min = {}

for player in shots_yr[('', 'PLAYER_ID')].unique():
    
    try:
        inf = PlayerCareerStats(player).get_data_frames()[0]

        if not inf.empty:
            team_inf = inf[(inf['SEASON_ID']==yr)&(inf['TEAM_ID']!=0)]
            
            if len(team_inf) > 1:
                total = inf[(inf['SEASON_ID']==yr)&(inf['TEAM_ID']==0)]
                fractions = team_inf.loc[:,'MIN'].values.flatten()/total.loc[:,'MIN'].values
                teamids = team_inf['TEAM_ID'].values
            
                team_frac_inf = dict(zip(teamids, fractions))

                traded_players_min[player] = team_frac_inf
        time.sleep(1)
    except Exception as e:
        print(f'having issues with {player}: {e}')
            
#nba data functions
def get_team_df(team_id,season,season_type='Regular Season',filtered=False):
    df_values = np.array([])
    
    teamplayerinf = TeamPlayerDashboard(team_id=team_id,season=season,season_type_all_star=season_type).get_data_frames()[1]
    teamplayerinf = teamplayerinf.loc[:,['PLAYER_ID','PLAYER_NAME','MIN']]
    
    if filtered and season_type == 'Regular Season':
        teamplayerinf = teamplayerinf[teamplayerinf['MIN']>=700]
    elif filtered and season_type != 'Regular Season':
        teamplayerinf = teamplayerinf[teamplayerinf['MIN']>=100]
    else:
        teamplayerinf
    
    unique_player_count = 0
    
    #get dictionary of all traded players that year
    #estimate traded players stats respective to their minutes played on the team
    
    traded_shot_df = shots_yr[(shots_yr[('', 'PLAYER_ID')].isin(traded_players_min.keys()))&(shots_yr[('','PLAYER_ID')].isin(teamplayerinf['PLAYER_ID'].tolist()))].copy()
    #filling in nan with zero
    traded_shot_df.fillna(0,inplace=True)
    
    attempt_cols = [7, 10, 13, 16, 19, 22, 25]

    fractions = traded_shot_df[('', 'PLAYER_ID')].map(lambda pid: traded_players_min[pid][team_id])

    traded_shot_df.iloc[:, attempt_cols] = (traded_shot_df.iloc[:, attempt_cols].mul(fractions, axis=0)).astype(int)
    
    temp = shots_yr[shots_yr[('', 'PLAYER_ID')].isin(teamplayerinf['PLAYER_ID'])].copy()

    # overwrite traded players with adjusted values
    temp.update(traded_shot_df)
    
    for _, row in temp.iterrows():

        player_id = row.iloc[0]
        
        unique_player_count += 1
        df_values = np.append(df_values, int(player_id))
        df_values = np.append(df_values, row.iloc[[1,7,8,10,11,13,14,16,17,19,20,22,23,25,26]])
        
    
    df = pd.DataFrame(df_values.reshape(unique_player_count, -1), 
                        columns = ['player_id','player_name','restricited_area_att','restricited_area_pct',
                                    'in_the_paint_att','in_the_paint_pct','mid_range_att','mid_range_pct',
                                    'left_corner_att','left_corner_pct','right_corner_att','right_corner_pct',
                                    'above_break3_att','above_break3_pct','backcourt_att','backcourt_pct'])
    return df

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


