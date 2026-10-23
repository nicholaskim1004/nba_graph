import random
import time
import sqlite3
import pandas as pd
from nba_api.stats.endpoints import CommonPlayerInfo

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

def make_headers(ua):
    return {
        "User-Agent": ua,
        "Referer": "https://www.nba.com/",
        "Origin": "https://www.nba.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "x-nba-stats-origin": "stats",
        "x-nba-stats-token": "true",
        "Connection": "keep-alive",
    }

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
        ua = USER_AGENTS[attempt % len(USER_AGENTS)]  # new agent each retry
        try:
            info = CommonPlayerInfo(
                player_id=playerid,
                headers=make_headers(ua),
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