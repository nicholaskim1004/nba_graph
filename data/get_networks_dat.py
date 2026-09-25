import sqlite3
import math
import pandas as pd # type: ignore[import-not-found]
import networkx as nx # type: ignore[import-not-found]

from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

#drop pagerank table if it exists to avoid duplicates
cursor.execute("DROP TABLE IF EXISTS pageranks_yr")

#set up table for storing pageranks for each team and the coordinates to rebuild
cursor.execute("""
               CREATE TABLE IF NOT EXISTS pageranks_yr
               (
                   season TEXT,
                   team_id INTEGER,
                   node_name TEXT,
                   pagerank REAL,
                   x_cord REAL,
                   y_cord REAL
               )
               """)

#tables to store the edge weight information for the networks
cursor.execute("DROP TABLE IF EXISTS network_edges")

cursor.execute("""
               CREATE TABLE IF NOT EXISTS network_edges
               (
                   season TEXT,
                   team_id INTEGER,
                   source TEXT,
                   target TEXT,
                   weight REAL
               )
               """)

#drop pagerank table if it exists to avoid duplicates
cursor.execute("DROP TABLE IF EXISTS pageranks_playoffs_yr")

#set up table for storing pageranks for each team and the coordinates to rebuild
cursor.execute("""
               CREATE TABLE IF NOT EXISTS pageranks_playoffs_yr
               (
                   season TEXT,
                   team_id INTEGER,
                   node_name TEXT,
                   pagerank REAL,
                   x_cord REAL,
                   y_cord REAL
               )
               """)

cursor.execute("DROP TABLE IF EXISTS network_edges_playoffs")

cursor.execute("""
               CREATE TABLE IF NOT EXISTS network_edges_playoffs
               (
                   season TEXT,
                   team_id INTEGER,
                   source TEXT,
                   target TEXT,
                   weight REAL
               )
               """)

###Regular season networks

query_sh = "SELECT * FROM shots_yr"
shots_yr = pd.read_sql_query(query_sh, con)

query_ps = "SELECT * FROM passes_yr"
passes_yr = pd.read_sql_query(query_ps, con)

all_teams = teams.get_teams()

diff_shots = ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Right Corner 3', 'Above the Break 3', 'Backcourt']

years = ['2020-21','2021-22', '2022-23', '2024-25', '2025-26']

for yr in years:
    print(f'🏀 getting network information for {yr} ⛹️‍♂️')

    shots_cur = shots_yr[shots_yr['season']==yr]
    for team in all_teams:
        print(f"Building network for {team['full_name']} ({team['id']}) in {yr} season...")

        teamid = team['id']
        
        team_shots = shots_cur[shots_cur['team_id']==teamid]
        
        #filtering out players who don't play that much
        team_shots = team_shots[team_shots['min']>200]
        
        total_shots = team_shots.iloc[:,5:].sum(axis=1)
        
        #replacing zeros with 1 so won't be NAN when dividing
        total_shots = total_shots.replace(0,1)
        
        proportion_shots = team_shots.iloc[:,5:].div(total_shots, axis=0)
        
        #creating a dataframe that stores the player_id and player_name from passes_yr df to ensure consistent naming
        team_to_id_map = pd.DataFrame({'player_id':passes_yr['pass_to_id'].unique(), 'player_name': passes_yr['pass_to'].unique()})
        
        #merging in the correct player_name after tacking on the player_id
        proportion_shots['player_id'] = shots_yr['player_id']
        proportion_shots = pd.merge(proportion_shots, team_to_id_map, on='player_id', how='left')
        
        #reorganzing df
        proportion_shots = proportion_shots.iloc[:,[8,7,0,1,2,3,4,5,6]]
        
        #filtering passes df to just cur team
        team_passes = passes_yr[(passes_yr['team_id']==teamid)&(passes_yr['season']==yr)]
        
        #making sure the players included in team_passes matches that in shots
        team_passes = team_passes[(team_passes['pass_to_id'].isin(team_shots['player_id']))&(team_passes['player_id'].isin(team_shots['player_id']))]             
             
        #initalizing network
        G = nx.DiGraph()
        
        #creating node between each player and each shot loction type 
        for _,row in proportion_shots.iterrows():
            for i, shot in enumerate(diff_shots):
                #multiply the edge weight by 0.5 in order to ensure that that the sum of value b/t shots and passes doesn't exceed 1
                    G.add_edge(row['player_name'], shot, weight= 0.5 * row.iloc[i+2])

        #creating edge between each player
        for _,row in team_passes.iterrows():
            G.add_edge(row['player_name'],row['pass_to'], weight= 0.5 * row['proportion'])
           
        pageranks = nx.pagerank(G, weight="weight").items()
        
        network_layout = nx.spring_layout(G)
        
        #converting pagerank to dataframe
        pageranks_df = pd.DataFrame(pageranks, columns=['node_name','pagerank'])
        pageranks_df['season'] = str(yr)
        pageranks_df['team_id'] = int(teamid)
        pageranks_df = pageranks_df.iloc[:,[3,2,0,1]]
        
        #getting coordinate columns
        coord = nx.spring_layout(G)
        coord_df = pd.DataFrame(
                        coord.values(),
                        index=coord.keys(),
                        columns=['x_cord', 'y_cord']
                    ).reset_index(names='node_name')
        
        pageranks_df = pd.merge(pageranks_df,coord_df, on='node_name', how='left')        
        
        pageranks_df.to_sql('pageranks_yr', con, if_exists='append', index=False)
        print(f'saving pagerank info for {team['full_name']} in {yr} to database 💾')
        
        edges = nx.to_pandas_edgelist(G, source='source', target='target')
        
        #adding season and team_id columns since it doesn't come with
        edges['season'] = str(yr)
        edges['team_id'] = int(teamid)
        
        edges.to_sql('network_edges', con, if_exists='append', index=False)
        print(f'saving edge weight info for {team['full_name']} in {yr} to database 💽')
        
    print(f'finished saving info for season {yr}...')
        
print('finished 🚀')   

###Playoffs Networks
print('starting to build Playoff networks')

query_sh = "SELECT * FROM shots_playoffs_yr"
shots_yr = pd.read_sql_query(query_sh, con)

query_ps = "SELECT * FROM passes_playoffs_yr"
passes_yr = pd.read_sql_query(query_ps, con)

for yr in years:
    print(f'🏀 getting network information for {yr} ⛹️‍♂️')

    shots_cur = shots_yr[shots_yr['season']==yr]
    
    #filtering team_list to only those in the playoffs for that year
    playoff_ids = passes_yr[passes_yr['season']==yr]['team_id'].unique()
    team_list = [team for team in all_teams if team['id'] in playoff_ids]

    for team in team_list:
        print(f"Building network for {team['full_name']} ({team['id']}) in {yr} season...")

        teamid = team['id']
        
        team_shots = shots_cur[shots_cur['team_id']==teamid]
        
        #filtering out players who don't play that much
        team_shots = team_shots[team_shots['min']>10]
        
        total_shots = team_shots.iloc[:,5:].sum(axis=1)
        
        #replacing zeros with 1 so won't be NAN when dividing
        total_shots = total_shots.replace(0,1)
        
        proportion_shots = team_shots.iloc[:,5:].div(total_shots, axis=0)
        
        #creating a dataframe that stores the player_id and player_name from passes_yr df to ensure consistent naming
        team_to_id_map = pd.DataFrame({'player_id':passes_yr['pass_to_id'].unique(), 'player_name': passes_yr['pass_to'].unique()})
        
        #merging in the correct player_name after tacking on the player_id
        proportion_shots['player_id'] = shots_yr['player_id']
        proportion_shots = pd.merge(proportion_shots, team_to_id_map, on='player_id', how='left')
        
        #reorganzing df
        proportion_shots = proportion_shots.iloc[:,[8,7,0,1,2,3,4,5,6]]
        
        #filtering passes df to just cur team
        team_passes = passes_yr[(passes_yr['team_id']==teamid)&(passes_yr['season']==yr)]
        
        #making sure the players included in team_passes matches that in shots
        team_passes = team_passes[(team_passes['pass_to_id'].isin(team_shots['player_id']))&(team_passes['player_id'].isin(team_shots['player_id']))]             
                        
        #initalizing network
        G = nx.DiGraph()
        
        #creating node between each player and each shot loction type 
        for _,row in proportion_shots.iterrows():
            for i, shot in enumerate(diff_shots):
                #multiply the edge weight by 0.5 in order to ensure that that the sum of value b/t shots and passes doesn't exceed 1
                    G.add_edge(row['player_name'], shot, weight= 0.5 * row.iloc[i+2])

        #creating edge between each player
        for _,row in team_passes.iterrows():
            G.add_edge(row['player_name'],row['pass_to'], weight= 0.5 * row['proportion'])
           
        pageranks = nx.pagerank(G, weight="weight").items()
        
        network_layout = nx.spring_layout(G)
        
        #converting pagerank to dataframe
        pageranks_df = pd.DataFrame(pageranks, columns=['node_name','pagerank'])
        pageranks_df['season'] = str(yr)
        pageranks_df['team_id'] = int(teamid)
        pageranks_df = pageranks_df.iloc[:,[3,2,0,1]]
        
        #getting coordinate columns
        coord = nx.spring_layout(G)
        coord_df = pd.DataFrame(
                        coord.values(),
                        index=coord.keys(),
                        columns=['x_cord', 'y_cord']
                    ).reset_index(names='node_name')
        
        pageranks_df = pd.merge(pageranks_df,coord_df, on='node_name', how='left')        
        
        pageranks_df.to_sql('pageranks_playoffs_yr', con, if_exists='append', index=False)
        print(f'saving pagerank info for {team['full_name']} in {yr} to database 💾')
        
        edges = nx.to_pandas_edgelist(G, source='source', target='target')
        
        #adding season and team_id columns since it doesn't come with
        edges['season'] = str(yr)
        edges['team_id'] = int(teamid)
        
        edges.to_sql('network_edges_playoffs', con, if_exists='append', index=False)
        print(f'saving edge weight info for {team['full_name']} in {yr} to database 💽')
        
    print(f'finished saving info for season {yr}...')
        
print('finished 🚀')
     
#close connection and cursor
cursor.close()
con.close()
