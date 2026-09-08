##script to get the shot attempts and each location for each player
##for traded players will use fraction of minutes played at each team to adjust the shot attempts

import time
import sqlite3
import pandas as pd

from nba_api.stats.endpoints import leaguedashplayershotlocations, PlayerCareerStats

#setting up database
#connect to database
con = sqlite3.connect('data/nba.db')
cursor = con.cursor()

##initalize tables
#traded players table
cursor.execute("""
               CREATE TABLE IF NOT EXISTS traded_players
               (
                   player_id INTEGER,
                   season TEXT, 
                   team_id INTEGER,
                   fraction REAL,
                   PRIMARY KEY (player_id, season, team_id)
                )""")

#shots table
cursor.execute("""
               CREATE TABLE IF NOT EXISTS shots_yr
               (
                   player_id INTEGER,
                   player_name TEXT,
                   season TEXT,
                   team_id INTEGER,
                   restricted_area_att INTEGER,
                   paint_att INTEGER,
                   mid_range_att INTEGER,
                   left_corner_att INTEGER,
                   right_corner_att INTEGER,
                   above_break_att INTEGER,
                   backcourt_att INTEGER
               )
               """)

#run on all years once its working for one year
years = ['2020-21','2021-22','2022-23','2023-24','2024-25','2025-26']

#shots dataset
for yr in years:
    shots_yr = leaguedashplayershotlocations.LeagueDashPlayerShotLocations(season=yr, season_type_all_star='Regular Season').get_data_frames()[0]

    #pulling columns of interest for the shots dataset
    shots_yr = shots_yr.iloc[:,[0,1,2,7,10,13,16,19,22,25]]
    shots_yr['season'] = yr
    shots_yr = shots_yr.iloc[:,[0,1,10,2,3,4,5,6,7,8,9]]
    shots_yr.columns = ['player_id','player_name','season','team_id','restricted_area_att','paint_att','mid_range_att','left_corner_att','right_corner_att','above_break_att','backcourt_att']
    
    #saving to database
    shots_yr.to_sql('shots_yr', con, if_exists='append', index=False)
    
#for each traded player, storing the fraction of minutes played for each team

    traded_players_min = []

    for player in shots_yr['player_id'].unique():
        
        try:
            inf = PlayerCareerStats(player).get_data_frames()[0]

            if not inf.empty:
                team_inf = inf[(inf['SEASON_ID']==yr)&(inf['TEAM_ID']!=0)]
                
                if len(team_inf) > 1:
                    total = inf[(inf['SEASON_ID']==yr)&(inf['TEAM_ID']==0)]
                    fractions = team_inf.loc[:,'MIN'].values.flatten()/total.loc[:,'MIN'].values
                    teamids = team_inf['TEAM_ID'].values
                
                    team_frac_inf = dict(zip(teamids, fractions))

                    for team_id, fraction in team_frac_inf.items():
                        traded_players_min.append({'player_id': player, 'team_id': team_id, 'fraction': fraction})
            time.sleep(1)
        except Exception as e:
            print(f'having issues with {player}: {e}')
    
    traded = pd.DataFrame(traded_players_min).to_sql('traded_players', con, if_exists='append', index=False)
    
    #use the fraction of minutes to adjust the number of shot attempts
    


