import sqlite3
import pandas as pd

from nba_api.stats.endpoints import LeagueStandings
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db')
cursor = con.cursor()

cursor.execute("DROP TABLE IF EXISTS records_yr")

##initalize shots table
cursor.execute("""
               CREATE TABLE IF NOT EXISTS records_yr
               (
                   season TEXT,
                   team_id INTEGER,
                   team_name TEXT,
                   conference TEXT,
                   division TEXT,
                   record STRING,
                   seed INTEGER
               )
               """)

years = ['2020-21','2021-22','2022-23','2023-24','2024-25','2025-26']

team_df = pd.DataFrame(teams.get_teams())

for yr in years:
    standings = LeagueStandings(league_id='00',season=yr).get_data_frames()[0]

    standings['season'] = yr
    standings = standings.loc[:,['season','TeamID','TeamName','Conference','Division','Record','PlayoffRank']]

    standings = standings.rename(columns={'TeamID':'team_id',
                                        'TeamName':'team_name',
                                        'Conference':'conference',
                                        'Division':'division',
                                        'Record':'record',
                                        'PlayoffRank':'seed'})
    
    standings.to_sql('record_yr', con, if_exists='append', chunksize=standings.shape[0])

cursor.close()
con.close()