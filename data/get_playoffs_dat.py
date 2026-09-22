##script to get the shot attempts and each location for each player
##for traded players will use fraction of minutes played at each team to adjust the shot attempts

import time
import sqlite3
import pandas as pd # type: ignore[import-not-found]

from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguedashplayershotlocations, PlayerCareerStats, playerdashptpass

#function to convert playerdashptpass data to a dataframe of passes between teammates
#stores the count & proportion of passes from each player to each teammate in the dataframe
def get_team_pass_df(team_df, team_id, season, season_type='Playoffs'):
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

#setting up database
#connect to database
con = sqlite3.connect('data/nba.db')
cursor = con.cursor()

#drop shots table if it exists to avoid duplicates
cursor.execute("DROP TABLE IF EXISTS shots_playoffs_yr")

##initalize shots table
cursor.execute("""
               CREATE TABLE IF NOT EXISTS shots_playoffs_yr
               (
                   player_id INTEGER,
                   player_name TEXT,
                   season TEXT,
                   min INTEGER,
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

#drop passes table if it exists to avoid duplicates
cursor.execute("DROP TABLE IF EXISTS passes_playoffs_yr")

#set up table for storing pass proportions between teammates for each team 
cursor.execute("""
               CREATE TABLE IF NOT EXISTS passes_playoffs_yr
               (
                   player_id INTEGER,
                   player_name TEXT,
                   season TEXT,
                   team_id INTEGER,
                   pass_to_id INTEGER,
                   pass_to TEXT,
                   count INTEGER,
                   proportion REAL
               )
               """)

#run on all years once its working for one year
years = ['2020-21','2021-22','2022-23','2023-24','2024-25','2025-26']

attempt_cols = [
    'restricted_area_att',
    'paint_att',
    'mid_range_att',
    'left_corner_att',
    'right_corner_att',
    'above_break_att',
    'backcourt_att'
]

#shots dataset
for yr in years:
    print(f'🏀 getting shots for {yr} ⛹️‍♂️')
    shots_yr = leaguedashplayershotlocations.LeagueDashPlayerShotLocations(season=yr, season_type_all_star='Playoffs').get_data_frames()[0]

    #pulling columns of interest for the shots dataset
    shots_yr = shots_yr.iloc[:,[0,1,2,7,10,13,16,19,22,25]]
    shots_yr['season'] = yr
    shots_yr = shots_yr.iloc[:,[0,1,10,2,3,4,5,6,7,8,9]]
    shots_yr.columns = ['player_id','player_name','season','team_id','restricted_area_att','paint_att','mid_range_att','left_corner_att','right_corner_att','above_break_att','backcourt_att']
    shots_yr['min'] = pd.NA
    
    print("finished getting shots dataset ✅")
    
    #for each traded player, storing the fraction of minutes played for each team
    print(f'finding traded player in {yr} season 🔍')
    
    minutes_dic = {}
    
    for player in shots_yr['player_id'].unique():
        
        try:
            inf = PlayerCareerStats(player).get_data_frames()[2]

            if not inf.empty:
                team_inf = inf[(inf['SEASON_ID']==yr)&(inf['TEAM_ID']!=0)]
                
                if len(team_inf) == 1:
                    shots_yr.loc[shots_yr['player_id'] == player,'min'] = int(team_inf['MIN'].values[0])
                
                else:    
                    #storing the player_id, team_id, and total minutes to later add onto the shots df
                    for _, row in team_inf.iterrows():
                        minutes_dic[(int(player), int(row['TEAM_ID']))] = int(row['MIN'])

                    total = inf[(inf['SEASON_ID']==yr)&(inf['TEAM_ID']==0)]
                    fractions = team_inf.loc[:,'MIN'].values.flatten()/total.loc[:,'MIN'].values
                    teamids = team_inf['TEAM_ID'].values
                
                    team_frac_inf = dict(zip(teamids, fractions))
                    
                    #storing the original row for the player to use for creating new rows for each team
                    player_row = shots_yr[shots_yr['player_id']==player].iloc[0].copy()
                    
                    for team_id, fraction in team_frac_inf.items():
                        #replace the current rows values with adjusted for the team stored in shots_yr
                        
                        adjusted_row = player_row.copy()
                        
                        #safeguard to ensure values are stored in correct format in database
                        adjusted_row['player_id'] = int(player_row['player_id'])
                        adjusted_row['team_id'] = int(team_id)
                        adjusted_row['season'] = str(yr)
                        adjusted_row[attempt_cols] = (adjusted_row[attempt_cols] * fraction).round().astype('Int64')
                        adjusted_row['min'] = int(minutes_dic[(int(player), int(team_id))])
                        
                        if team_id == player_row['team_id']:
                            shots_yr.loc[(shots_yr['player_id'] == player) & (shots_yr['team_id'] == player_row['team_id']), attempt_cols] = adjusted_row[attempt_cols].values
                            shots_yr.loc[(shots_yr['player_id'] == player) & (shots_yr['team_id'] == player_row['team_id']), 'min'] = minutes_dic[(int(player), int(team_id))]
                            
                        #create a new row for the player with the team_id and adjusted shot attempts
                        else:
                            print(f"adding a new row for player {player} for team {team_id}")
                            
                            #adding safeguard so values are stored in correct format in database
                            shots_yr['player_id'] = shots_yr['player_id'].astype('Int64')
                            shots_yr['team_id'] = shots_yr['team_id'].astype('Int64')

                            for col in attempt_cols:
                                shots_yr[col] = shots_yr[col].astype('Int64')
                            shots_yr = pd.concat([shots_yr, adjusted_row.to_frame().T], ignore_index=True)

            time.sleep(1)
        except Exception as e:
            print(f'having issues with {player}: {e}')
    
    #filtering out players without min
    shots_yr = shots_yr[~shots_yr['min'].isna()]
    
    #getting rid of nans in shot
    shots_yr.fillna(0,inplace=True)
    
    #saving to database        
    print(f'saving shots for {yr} to database 🖨️')
    shots_yr.to_sql('shots_playoffs_yr', con, if_exists='append', index=False)

#close connection
print("finished pulling shots data! 🔥")

print("starting passes dataframe pull for playoffs 🏆")
team_list = teams.get_teams()
#filter to teams that appear in playoffs
playoff_ids = shots_yr['team_id'].unique()

team_list = [team for team in team_list if team['id'] in playoff_ids]

for yr in years:
    print(f'🏀 getting passes for {yr} ⛹️‍♂️')
    for team in team_list:
        team_id = team['id']
        team_name = team['full_name']
        print(f"Getting passes for {team_name} ({team_id}) in {yr} season...")
        
        query = f"SELECT * FROM shots_playoffs_yr WHERE season = '{yr}' AND team_id = {team_id}"
        shots_yr = pd.read_sql_query(query, con)
        
        if shots_yr.empty:
            print(f"No shot data found for {team_name} in {yr} season. Skipping...")
            continue
        
        pass_df = get_team_pass_df(shots_yr, team_id, yr)
        #add team_id and season columns to the pass_df
        pass_df['team_id'] = int(team_id)
        pass_df['season'] = str(yr)
        
        if not pass_df.empty:
            pass_df.to_sql('passes__playoffs_yr', con, if_exists='append', index=False)
            print(f"Pass data for {team_name} in {yr} season saved to database 💾")
        else:
            print(f"No pass data found for {team_name} in {yr} season")
print("finished! 🔥")

cursor.close()
con.close()