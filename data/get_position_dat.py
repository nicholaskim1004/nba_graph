import time
import sqlite3
import pandas as pd

from nba_api.stats.static import teams
from nba_api.stats.endpoints import CommonPlayerInfo

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

#drop pagerank table if it exists to avoid duplicates
cursor.execute("DROP TABLE IF EXISTS positions")

#set up table for storing position info for each player
cursor.execute("""
               CREATE TABLE IF NOT EXISTS positions
               (
                   player_id INTEGER,
                   player_name TEXT,
                   positions TEXT
               )
               """)

query = "SELECT DISTINCT player_id, player_name FROM shots_yr"
unique_players = pd.read_sql_query(query, con)

N = len(unique_players)

print('starting data pull')

for i, row in unique_players.iterrows():

    print(f'progress: {(i+1)/N * 100}')
    try:
        playerid = row['player_id']
        name = row['player_name']
        
        pos = player_inf['POSITION'].iloc[0]
        
        player_inf = CommonPlayerInfo(player_id=playerid).get_data_frames()[0]
            
        pd.DataFrame({'player_id': int(playerid), 'player_name': str(name), 'positions': str(pos)}, index=[0]).to_sql('positions', con, if_exists='append', index=False)

    except Exception as e:
        print(f'having issues with {name}: {e}') 
    
    #avoid rate limit
    time.sleep(1)
    
print('finished')