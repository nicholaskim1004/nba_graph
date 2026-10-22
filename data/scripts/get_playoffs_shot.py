##script to get the shot attempts and each location for each player
##for traded players will use fraction of minutes played at each team to adjust the shot attempts

import time
import sqlite3
import pandas as pd # type: ignore[import-not-found]

from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguedashplayershotlocations, leaguestandings, PlayerCareerStats

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

#run on all years once its working for one year
years = ['2020-21','2021-22','2022-23','2023-24','2024-25','2025-26']

team_df = pd.DataFrame(teams.get_teams())


#shots dataset
for yr in years:
    print(f'🏀 getting shots for {yr} ⛹️‍♂️')
    
    standings_yr = leaguestandings.LeagueStandings(season=yr).get_data_frames()[0]
    playoff_teams = standings_yr.loc[standings_yr['PlayoffRank']<=8,['TeamID','TeamName']]
    
    for team_id in playoff_teams['TeamID']:
        
        team = playoff_teams.loc[playoff_teams['TeamID']==team_id,'TeamName'].item()
        
        print(f'pulling for team {team}')
        
        shots_yr_team = leaguedashplayershotlocations.LeagueDashPlayerShotLocations(season=yr, season_type_all_star='Playoffs',team_id_nullable=team_id).get_data_frames()[0]

        #pulling columns of interest for the shots dataset
        shots_yr_team = shots_yr_team.iloc[:,[0,1,2,7,10,13,16,19,22,25]]
        shots_yr_team['season'] = yr
        shots_yr_team = shots_yr_team.iloc[:,[0,1,10,2,3,4,5,6,7,8,9]]
        shots_yr_team.columns = ['player_id','player_name','season','team_id','restricted_area_att','paint_att','mid_range_att','left_corner_att','right_corner_att','above_break_att','backcourt_att']
    
        #getting rid of nans in shot
        shots_yr_team.fillna(0,inplace=True)
        
        minuets = []
        
        #going through and pulling minutes played on each team in current season
        for player in shots_yr_team['player_id'].unique():
            print(player)
            play_post_tot = PlayerCareerStats(player_id=player).season_totals_post_season.get_data_frame()
            minuets.append(play_post_tot.loc[(play_post_tot['SEASON_ID']==yr)&(play_post_tot['TEAM_ID']==team_id),'MIN'])
            time.sleep(1)
            
        shots_yr_team['min'] = minuets
        
        #saving to database        
        print(f'saving shots for {yr} {team} to database 🖨️')
        shots_yr_team.to_sql('shots_playoffs_yr', con, if_exists='append', index=False)
        time.sleep(1)
        
#close connection
print("finished pulling shots data! 🔥")

cursor.close()
con.close()