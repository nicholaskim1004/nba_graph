import sqlite3
import pandas as pd
import numpy as np

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_page = "SELECT * FROM pageranks_yr"
pageranks = pd.read_sql_query(query_page, con)

query_avd = "SELECT * FROM avdstats_yr"
avdstats = pd.read_sql_query(query_avd, con)

query_shots = "SELECT * FROM shots_yr"
shots = pd.read_sql_query(query_shots, con)

positions = "SELECT * FROM positions"
pos = pd.read_sql_query(positions, con)


shot_types = ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Right Corner 3', 'Above the Break 3', 'Backcourt']


pageranks_players = pageranks[~pageranks['node_name'].isin(shot_types)]

shots = shots.loc[:,['player_id','player_name','season', 'min','team_id', 'paint_att','mid_range_att','left_corner_att','right_corner_att','above_break_att']]
all_teams = shots['team_id'].drop_duplicates()
for team in all_teams:

   
    
    team_shots = shots[shots['team_id']==team]
    
    #filtering out players who don't play that much
    team_shots = team_shots[team_shots['min']>200]
    
    
    print(team_shots.head())
    total_shots = team_shots.iloc[:,5:].sum(axis=1)
    
    #replacing zeros with 1 so won't be NAN when dividing
    total_shots = total_shots.replace(0,1)
    
    proportion_shots = team_shots.iloc[:,5:].div(total_shots, axis=0)
        
    #merging in the correct player_name after tacking on the player_id
    proportion_shots['player_id'] = shots['player_id']
    proportion_shots['player_name'] = shots['player_name']
    proportion_shots['season'] = shots['season']
    proportion_shots['team_id'] = shots['team_id']
    
    
proportion_shots = proportion_shots.loc[:,['season','team_id','player_id','player_name','paint_att','mid_range_att','left_corner_att','right_corner_att','above_break_att']]
print(proportion_shots.head())
#pageranks_players = pageranks_players.merge(pos, how='left', on='player_id')
#pageranks_players = pageranks_players.merge(avdstats.loc[:,['']], how='left', on=['player_id', 'season'])

#features in player profile:
#pagerank, position, Def rating, prop at 6 shot locations, ast_pct, usg_pct

page_norm = pageranks_players.groupby(['season','team_id']).apply(lambda x: x['pagerank']/x['pagerank'].sum())
pageranks_players['pagerank_norm'] = page_norm.reset_index(level=[0,1], drop=True)

prof_df = proportion_shots.merge(pageranks_players[['player_id', 'pagerank_norm']], how='left', on='player_id')
#prof_df = prof_df.merge(avdstats.loc[:,['player_id','season','E_DEF_RATING','AST_PCT','USG']], how='left', on=['player_id', 'season'])
#prof_df = prof_df.merge(pos, how='left', on='player_id')

print(prof_df.head())