import random
import time
import sqlite3
import pandas as pd
from nba_api.stats.endpoints import CommonPlayerInfo

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions
    (player_id INTEGER, player_name TEXT, positions TEXT)
""")
con.commit()

unique_players = pd.read_sql_query("SELECT DISTINCT player_id, player_name FROM shots_yr", con)
done = set(pd.read_sql_query("SELECT player_id FROM positions", con)['player_id'])
unique_players = unique_players[~unique_players['player_id'].isin(done)].reset_index(drop=True)

N = len(unique_players)
MAX_RETRIES = 5
failed = []

for i, row in unique_players.iterrows():
    playerid = int(row['player_id'])
    name = str(row['player_name'])
    print(f'progress: {(i+1)/N*100:.1f}% ({name})')

    for attempt in range(MAX_RETRIES):
        try:
            info = CommonPlayerInfo(
                player_id=playerid,
                timeout=60,
            ).get_data_frames()[0]
            pos = str(info['POSITION'].iloc[0])
            pd.DataFrame(
                {'player_id': [playerid], 'player_name': [name], 'positions': [pos]}
            ).to_sql('positions', con, if_exists='append', index=False)
            break
        except Exception as e:
            wait = min(10 * 2 ** attempt, 120)
            print(f'  attempt {attempt+1} failed ({e}); switching agent, waiting {wait}s')
            time.sleep(wait)
    else:
        failed.append((playerid, name))

    time.sleep(random.uniform(1, 2.5))  # jitter looks less bot-like than a fixed 1s

print('failed:', failed)
cursor.close()
con.close()