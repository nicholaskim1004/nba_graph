import sqlite3
import pandas as pd

from nba_api.stats.endpoints import LeagueStandings
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db')
cursor = con.cursor()

cursor.execute("DROP TABLE IF EXISTS records_yr")

##initalize records table
cursor.execute("""
               CREATE TABLE IF NOT EXISTS records_yr
               (
                   season TEXT,
                   team_id INTEGER,
                   team_name TEXT,
                   conference TEXT,
                   division TEXT,
                   record STRING,
                   wins INTGER,
                   seed INTEGER,
                   league_rank INTEGER
               )
               """)

cursor.execute("""
               CREATE TABLE IF NOT EXISTS playoff_records_yr
               (
                   season TEXT,
                   conference TEXT,
                   round TEXT,
                   series TEXT,
                   winning_team TEXT,
                   losing_team TEXT
               )
               """)

play_rec = pd.read_csv('data/playoff__bracket_yr.csv')
play_rec.to_sql('playoff_records_yr', con, if_exists='replace')

years = ['2020-21','2021-22','2022-23','2023-24','2024-25','2025-26']

team_df = pd.DataFrame(teams.get_teams())

print('starting data pull')
for yr in years:
    print(f'pulling for {yr} season')
    standings = LeagueStandings(league_id='00',season=yr).get_data_frames()[0]

    standings['season'] = yr
    standings = standings.loc[:,['season','TeamID','TeamName','Conference','Division','Record','PlayoffRank']]

    standings = standings.rename(columns={'TeamID':'team_id',
                                        'TeamName':'team_name',
                                        'Conference':'conference',
                                        'Division':'division',
                                        'Record':'record',
                                        'PlayoffRank':'seed'})
    
    split = standings['record'].str.split('-', expand=True)
    wins = split[0].astype(int).to_numpy()
    
    standings['wins'] = wins
    
    standings['league_rank'] = (
    standings.groupby('season')['wins']
     .rank(method='first', ascending=False)
     .astype(int)
)
    
    print('saving..')
    standings.to_sql('records_yr', con, if_exists='append', index=False, method='multi', chunksize=standings.shape[0])

print('finished')
cursor.close()
con.close()