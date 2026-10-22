##script to get the shot attempts and each location for each player
##for traded players will use fraction of minutes played at each team to adjust the shot attempts

import time
import sqlite3
import pandas as pd # type: ignore[import-not-found]

from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguedashplayershotlocations, leaguestandings, leaguedashplayerstats

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


def with_retry(fn, tries=4, wait=3):
    """Retry NBA API calls with backoff since NBA.com is flaky."""
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            print(f'  retry {i+1}/{tries} after error: {e!r}')
            time.sleep(wait * (i + 1))
    raise RuntimeError('API call failed after retries')


#shots dataset
for yr in years:
    print(f'🏀 getting shots for {yr}')
    standings = with_retry(lambda: leaguestandings.LeagueStandings(season=yr, timeout=60).get_data_frames()[0])
    playoff_teams = standings.loc[standings['PlayoffRank'] <= 8, ['TeamID', 'TeamName']]

    for team_id, team in zip(playoff_teams['TeamID'], playoff_teams['TeamName']):
        print(f'pulling for team {team}')

        shots = with_retry(lambda: leaguedashplayershotlocations.LeagueDashPlayerShotLocations(
            season=yr, season_type_all_star='Playoffs',
            team_id_nullable=team_id, timeout=60).get_data_frames()[0])
        time.sleep(1)

        shots = shots.iloc[:, [0, 1, 2, 7, 10, 13, 16, 19, 22, 25]].copy()
        shots['season'] = yr
        shots = shots.iloc[:, [0, 1, 10, 2, 3, 4, 5, 6, 7, 8, 9]]
        shots.columns = ['player_id','player_name','season','team_id','restricted_area_att',
                         'paint_att','mid_range_att','left_corner_att','right_corner_att',
                         'above_break_att','backcourt_att']
        shots = shots.fillna(0)

        # one call gets playoff minutes for every player on this team
        stats = with_retry(lambda: leaguedashplayerstats.LeagueDashPlayerStats(
            season=yr, season_type_all_star='Playoffs',
            team_id_nullable=team_id, timeout=60).get_data_frames()[0])
        time.sleep(1)

        mins = stats[['PLAYER_ID', 'MIN']].rename(columns={'PLAYER_ID': 'player_id', 'MIN': 'min'})
        shots = shots.merge(mins, on='player_id', how='left')

        shots.to_sql('shots_playoffs_yr', con, if_exists='append', index=False)

con.commit()
cursor.close()
con.close()
print('finished pulling shots data! 🔥')