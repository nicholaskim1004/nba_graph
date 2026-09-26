import sqlite3
import pandas as pd
import dash

from dash import html, Input, Output, callback, dash_table, State, dcc, ctx, no_update# type: ignore[import-not-found]
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query = "SELECT * FROM expected_pagerank_yr"
pageranks_avd_players = pd.read_sql_query(query, con)

team_df = pd.DataFrame(teams.get_teams())
seasons = pageranks_avd_players['season'].unique()

dash.register_page(__name__, path='/over_under_players', name='Over/Under Rated Players', order = 2)

layout = html.Div([
    html.Label('Choice',style={"fontFamily": 'sans-serif','font-weight': 'bold'}),
    html.Br(),
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