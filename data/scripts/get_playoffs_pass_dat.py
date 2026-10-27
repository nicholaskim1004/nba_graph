import time
import sqlite3
import pandas as pd # type: ignore[import-not-found]
from nba_api.stats.static import teams
from nba_api.stats.endpoints import playerdashptpass

def pull_player(team_id, player_id, season, season_type, tries=4):
    for i in range(tries):
        try:
            return playerdashptpass.PlayerDashPtPass(
                team_id=team_id, player_id=player_id, season=season,
                season_type_all_star=season_type, timeout=60
            ).get_data_frames()[0]
        except Exception as e:
            print(f"  retry {i+1}/{tries} for player {player_id}: {e!r}")
            time.sleep(10 * (i + 1))
    return None

def get_team_pass_df(team_shots, team_id, season, season_type='Playoffs'):
    rows, failed = [], []
    teammate_ids = set(team_shots['player_id'])

    for _, trow in team_shots.iterrows():
        info = pull_player(team_id, int(trow['player_id']), season, season_type)
        time.sleep(1)
        if info is None:
            failed.append(trow['player_name'])
            continue
        info = info[info['PASS_TEAMMATE_PLAYER_ID'].isin(teammate_ids)]
        for _, r in info.iterrows():
            rows.append({'player_id': r['PLAYER_ID'], 'player_name': r['PLAYER_NAME_LAST_FIRST'],
                         'pass_to_id': r['PASS_TEAMMATE_PLAYER_ID'], 'pass_to': r['PASS_TO'],
                         'count': r['PASS'], 'proportion': r['FREQUENCY']})
    return pd.DataFrame(rows), failed

con = sqlite3.connect('data/nba.db')
cursor = con.cursor()

# no DROP TABLE: the script is resumable now
cursor.execute("""
    CREATE TABLE IF NOT EXISTS passes_playoffs_yr (
        player_id INTEGER, player_name TEXT, season TEXT, team_id INTEGER,
        pass_to_id INTEGER, pass_to TEXT, count INTEGER, proportion REAL)
""")
con.commit()

#will store the teams and players that already have info in a given season
done = pd.read_sql_query(
    "SELECT DISTINCT season, team_id, player_id FROM passes_playoffs_yr", con)
done_set = set(zip(done['season'], done['team_id'], done['player_id']))

years = ['2020-21','2021-22','2022-23','2023-24','2024-25','2025-26']
team_list = teams.get_teams()
failed_teams = []

for yr in years:
    shots_full = pd.read_sql_query("SELECT * FROM shots_playoffs_yr WHERE season = ?", con, params=(yr,))
    playoff_ids = set(shots_full['team_id'])
    print(f'🏀 getting passes for {yr}')

    for team in [t for t in team_list if t['id'] in playoff_ids]:
        tid, tname = team['id'], team['full_name']
        if (yr, tid) in done_set:
            print(f"{tname} {yr} already saved, skipping")
            continue

        team_shots = shots_full[shots_full['team_id'] == tid]
        todo = team_shots[~team_shots['player_id'].apply(lambda p: (yr, tid, p) in done_set)]
        pass_df, failed = get_team_pass_df(todo, tid, yr)

        if failed or pass_df.empty:
            print(f"❌ {tname} {yr}: failed players {failed}, not saving so a rerun retries it")
            failed_teams.append((yr, tname))
            continue

        pass_df['team_id'] = int(tid)
        pass_df['season'] = yr
        pass_df.to_sql('passes_playoffs_yr', con, if_exists='append', index=False)
        print(f"💾 {tname} {yr} saved")

print("finished! 🔥")
print("Teams to retry:", failed_teams)
cursor.close()
con.close()