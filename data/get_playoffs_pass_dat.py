import time
import sqlite3
import pandas as pd # type: ignore[import-not-found]
from nba_api.stats.static import teams
from nba_api.stats.endpoints import playerdashptpass

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

print("starting passes dataframe pull for playoffs 🏆")

team_list = teams.get_teams()

for yr in years:
    query = f"SELECT * FROM shots_playoffs_yr WHERE season = '{yr}'"
    shots_yr_full = pd.read_sql_query(query, con)
    
    #filtering to only playoff teams for that year
    playoff_ids = shots_yr_full['team_id'].unique()
    
    team_list_playoffs_yr = [team for team in team_list if team['id'] in playoff_ids]
    
    print(f'🏀 getting passes for {yr} ⛹️‍♂️')
    for team in team_list_playoffs_yr:
        team_id = team['id']
        team_name = team['full_name']
        print(f"Getting passes for {team_name} ({team_id}) in {yr} season...")
        
        shots_yr = shots_yr_full[shots_yr_full['team_id']==team_id]
            
        if shots_yr.empty:
            print(f"No shot data found for {team_name} in {yr} season. Skipping...")
            continue
        
        pass_df = get_team_pass_df(shots_yr, team_id, yr)
        #add team_id and season columns to the pass_df
        pass_df['team_id'] = int(team_id)
        pass_df['season'] = str(yr)
        
        if not pass_df.empty:
            pass_df.to_sql('passes_playoffs_yr', con, if_exists='append', index=False)
            print(f"Pass data for {team_name} in {yr} season saved to database 💾")
        else:
            print(f"No pass data found for {team_name} in {yr} season")
print("finished! 🔥")

cursor.close()
con.close()