import sqlite3
import pandas as pd
import networkx as nx

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

query = "SELECT * FROM shots_yr"
shots_yr = pd.read_sql_query(query, con)

query = "SELECT * FROM passes_yr"
passes_yr = pd.read_sql_query(query, con)

team_list = teams.get_teams()
team_list = team_list[0:2]

diff_shots = ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Right Corner 3', 'Above the Break 3', 'Backcourt']

#years = ['2020-21','2021-22', '2022-23', '2024-25', '2025-26']
years = ['2024-25']

for yr in years:
    print(f'🏀 getting network information for {yr} ⛹️‍♂️')

    shots_cur = shots_yr[shots_yr['season']==yr]
    for team in team_list:
        print(f"Building network for {team['full_name']} ({team['id']}) in {yr} season...")

        teamid = team['id']
        
        team_shots = shots_cur[shots_cur['team_id']==teamid]
        total_shots = team_shots.iloc[:,4:].sum(axis=1)
        
        #replacing zeros with 1 so won't be NAN when dividing
        total_shots = total_shots.replace(0,1)
        
        proportion_shots = team_shots.iloc[:,4:].div(total_shots, axis=0)
        
        #creating a dataframe that stores the player_id and player_name from passes_yr df to ensure consistent naming
        team_to_id_map = pd.DataFrame({'player_id':passes_yr['pass_to_id'].unique(), 'player_name': passes_yr['pass_to'].unique()})
        
        #merging in the correct player_name after tacking on the player_id
        proportion_shots['player_id'] = shots_yr['player_id']
        proportion_shots = pd.merge(proportion_shots, team_to_id_map, on='player_id', how='left')
        
        #reorganzing df
        proportion_shots = proportion_shots.iloc[:,[8,7,0,1,2,3,4,5,6]]
        
        #filtering passes df to just cur team
        team_passes = passes_yr[passes_yr['team_id']==teamid]
        
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
            
        nx.draw(G, with_labels=True, font_size=10, font_weight='bold')
        
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
        
        pageranks_df = pd.DataFrame(pageranks_df,coord_df, on='node_name', how='left')
        
        pageranks_df.to_sql('pageranks_yr', con, if_exists='append', index=False)
        print(f'saving pagerank info for {team['full_name']} in {yr} to database 💾')
    print(f'finished saving info for season {yr}...')
        
print('finished 🚀')        
#close connection and cursor
con.close()
cursor.close()