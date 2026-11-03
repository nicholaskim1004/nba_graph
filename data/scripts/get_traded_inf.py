import sqlite3
import time

import pandas as pd

from nba_api.stats.endpoints import playergamelog

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

cursor.execute("DROP TABLE IF EXISTS traded_inf_yr")
cursor.execute("""
               CREATE TABLE IF NOT EXISTS traded_inf_yr
               (
                    season TEXT,
                    player_id INTEGER,
                    player_name TEXT,
                    old_team_abbr TEXT,
                    new_team_abbr TEXT
               )
               """)

prof_df = pd.read_sql_query("SELECT * FROM player_profiles", con)

players = prof_df['player_id'].unique().tolist()
seasons = prof_df['season'].unique().tolist()

for playerid in players:
    player_df = prof_df[prof_df['player_id'] == playerid].reset_index()
    for season in seasons:
        rows = player_df[player_df['season'] == season]
        
        if len(rows) > 1:
            gamelog = playergamelog.PlayerGameLog(player_id=playerid, season=season,timeout=60).get_data_frames()[0]
            if gamelog.empty:
                continue
            # gamelog is newest-first, so tail() is the earliest games.
            # MATCHUP is "LAL vs. BOS" / "LAL @ BOS": the first token is the player's own team
            old_team_abbr = gamelog.tail()['MATCHUP'].str.split(' ').str[0].mode().iloc[0]

            new_team_abbr = gamelog.head()['MATCHUP'].str.split(' ').str[0].mode().iloc[0]
        
            time.sleep(1)

            print(f"Player {playerid} was traded in {season}: {old_team_abbr} -> {new_team_abbr}")
            pd.DataFrame({'season': [season], 'player_id': [playerid], 'player_name': [rows['player_name'].iloc[0]], 'old_team_abbr': [old_team_abbr], 'new_team_abbr': [new_team_abbr]}).to_sql('traded_inf_yr', con, if_exists='append', index=False)
        else:
            continue
    

cursor.close()
con.close()