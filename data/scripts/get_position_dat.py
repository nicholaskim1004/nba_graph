import time
import sqlite3
import pandas as pd
from nba_api.stats.endpoints import CommonPlayerInfo

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

cursor.execute("DROP TABLE IF EXISTS positions")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions
    (
        player_id INTEGER, 
        player_name TEXT,
        positions TEXT
        )
""")

con.commit()

unique_players = pd.read_sql_query(
    "SELECT DISTINCT player_id, player_name FROM shots_yr", con
)
N = len(unique_players)

MAX_RETRIES = 5
failed = []

for i, row in unique_players.iterrows():
    playerid = int(row['player_id'])
    name = str(row['player_name'])
    print(f'progress: {(i+1)/N*100:.1f}% ({name})')

    for attempt in range(MAX_RETRIES):
        try:
            info = CommonPlayerInfo(player_id=playerid, timeout=60).get_data_frames()[0]
            pos = str(info['POSITION'].iloc[0])
            pd.DataFrame(
                {'player_id': [playerid], 'player_name': [name], 'positions': [pos]}
            ).to_sql('positions', con, if_exists='append', index=False)
            break
        except Exception as e:
            wait = min(10 * 2 ** attempt, 120)  # 10, 20, 40, 80, 120
            print(f'  attempt {attempt+1}/{MAX_RETRIES} failed: {e}')
            time.sleep(wait)
    else:
        print(f'  giving up on {name}')
        failed.append((playerid, name))

    time.sleep(1)

print('finished. failed players:', failed)
cursor.close()
con.close()