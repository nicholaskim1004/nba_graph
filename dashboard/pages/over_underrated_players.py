import sqlite3
import pandas as pd

import statsmodels.formula.api as smf
import dash
from dash import html, Input, Output, callback, dash_table, State, dcc, ctx, no_update# type: ignore[import-not-found]

from sklearn.model_selection import train_test_split
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_pos = 'SELECT * FROM positions'
pos = pd.read_sql_query(query_pos, con)

query_page = 'SELECT * FROM pageranks_yr'
pageranks = pd.read_sql_query(query_page, con)

query_avd = 'SELECT * FROM avdstats_yr'
avdstats_yr = pd.read_sql_query(query_avd, con)

seasons = pageranks['season'].unique()
team_df = pd.DataFrame(teams.get_teams())

diff_shots = ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Right Corner 3', 'Above the Break 3', 'Backcourt']

#standarizing naming convention for some 
pos.loc[pos['positions']=='Forward-Guard','positions'] = 'Guard-Forward'
pos.loc[pos['positions']=='Forward-Center','positions'] = 'Center-Forward'

#cleaning up missing player ids before merges
pageranks_players = pageranks[~pageranks['node_name'].isin(diff_shots)]
wrong_ids = pageranks_players[pageranks_players['player_id'].isna()]

player_to_id_df = pageranks_players.loc[~pageranks_players['player_id'].isna(),['node_name','player_id']].drop_duplicates(subset=['node_name'], ignore_index=True)

for _, row in wrong_ids.iterrows():
    index = row.name

    player_name = row['node_name']
    
    pageranks_players.loc[index,'player_id'] = player_to_id_df.loc[player_to_id_df['node_name']==player_name,'player_id'].values


#merging in pos to pagerank
pageranks_players = pd.merge(pageranks_players.loc[:,['season','team_id','node_name','player_id','pagerank']],pos.loc[:,['player_id','positions']], on='player_id', how='left')

#merging avd stats to pos df
pageranks_avd_players = pd.merge(pageranks_players, avdstats_yr.loc[:,['season','team_id','player_id','PIE_SHARE']], on=['player_id','season','team_id'], how='left')

# drop rows with missing target/predictors up front so train/test are clean
model_data = pageranks_avd_players.dropna(subset=['pagerank', 'PIE_SHARE', 'positions']).copy()

train_df, test_df = train_test_split(model_data, test_size=0.2, random_state=42)

# fit on train only
model = smf.ols(
    'pagerank ~ PIE_SHARE + C(positions)',
    data=train_df
).fit()

# predict on test set to evaluate generalization
test_df['expected_pagerank'] = model.predict(test_df)
test_df['pagerank_residual'] = test_df['pagerank'] - test_df['expected_pagerank']

pageranks_avd_players['expected_pagerank'] = model.predict(pageranks_avd_players)
pageranks_avd_players['pagerank_residual'] = pageranks_avd_players['pagerank'] - pageranks_avd_players['expected_pagerank']

dash.register_page(__name__, path='/over_under_players', name='Over/Under Rated Players', order = 2)

layout = html.Div([
    dcc.Dropdown(id='over_or_under_choice',
                    options=['Overrated','Underrated'],
                    value='Overrated',
                    style={"fontFamily": 'sans-serif','width': '10%'}),
    
    html.Br(),
    html.Div("Created a model that predicted the expected pagerank given their Position and PIE_Share. "
             "A measure of their player value (PIE) relative to thier teammates. "
             "The residual between their actual and expected pagerank can highlight players who have more of a role to a team's offense then what their value might suggest "
             "and note players whose offensive role isn't as centeral to a teams offensve as thier value might suggest.",
             style={
                         "fontFamily": 'sans-serif',
                         "fontSize": "20px",
                         "marginTop": "0px"
                     }
             ),
    html.Br(),
    html.Div(
        dash_table.DataTable(
            id = 'expected_pagerank_player_df',
            data = [],
            columns = [
                {'name': i, 'id': i}
                for i in pageranks_avd_players.loc[:,['season','node_name','positions','PIE_SHARE','pagerank','expected_pagerank','pagerank_residual']].columns                 
            ]
        )
    )
])

#change sorted of the table based on the choice of the over under
@callback(
    Output('expected_pagerank_player_df', 'data'),
    Input('over_or_under_choice', 'value'),
    Input('team-dropdown', 'value'),
    Input('season-slider', 'value')
)
def update_player_df(over_under, selected_team, selected_season):
    df = pageranks_avd_players
    df.loc[:,['PIE_SHARE','pagerank','expected_pagerank','pagerank_residual']] = df.loc[:,['PIE_SHARE','pagerank','expected_pagerank','pagerank_residual']].round(4)
    if selected_team != 'All':
        teamid = team_df[team_df['full_name'] == selected_team]['id'].to_numpy()
        df = df[df['team_id'] == teamid[0]]

    if selected_season < len(seasons):
        season = seasons[selected_season]
        df = df[df['season'] == season]
        
    if over_under == 'Overrated':
        return df.sort_values('pagerank_residual').to_dict('records')
    else:
        return df.sort_values('pagerank_residual', ascending=False).to_dict('records')