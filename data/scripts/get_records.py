import sqlite3
import pandas as pd

from nba_api.stats.endpoints import TeamGameLog
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
                   conference TEXT,
                   division TEXT,
                   record STRING,
                   seed INTEGER
               )
               """)

years = ['2020-21','2021-22','2022-23','2023-24','2024-25','2025-26']

team_df = pd.DataFrame(teams.get_teams())

print(TeamGameLog(team_id=team_df['id'][0],season='2024-25',season_type_all_star='Regular Season'))