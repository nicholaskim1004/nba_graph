# app.py
import dash # type: ignore[import-not-found]
import sqlite3
import pandas as pd # type: ignore[import-not-found]
from dash import Dash, html, dcc, Output, Input # type: ignore[import-not-found]
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_page = "SELECT * FROM pageranks_yr"
pageranks_yr = pd.read_sql_query(query_page, con)

query_play = "SELECT * FROM pageranks_playoffs_yr"
pageranks_play = pd.read_sql_query(query_play, con)

team_df = pd.DataFrame(teams.get_teams())
team_list = team_df['full_name'].to_numpy()

seasons = pageranks_yr['season'].unique()

app = Dash(__name__, use_pages=True,suppress_callback_exceptions=True)

app.layout = html.Div([
    html.H1("NBA GRAPH NETWORKS",
            style={
                "fontFamily": 'sans-serif',
                "fontWeight": 'bold'}),
    html.Div(
        "How are NBA Offenses different? Do teams follow a similar pattern? "
        "Do strategies change in the Playoffs? All these questions can be "
        "answered using network structure! This dashboard will display the "
        "results from a network for a given season and team.",
        style={
            "fontFamily": 'sans-serif',
            "fontSize": "20px",
            "marginTop": "0px"
        }
    ),
    html.Br(),    
    
    html.Label('Team',style={"fontFamily": 'sans-serif','font-weight': 'bold'}),
    dcc.Dropdown(id='team-dropdown',
                 options=sorted(team_list,reverse=False),
                 value=team_list[0],
                 style={"fontFamily": 'sans-serif','width': '50%'}),
    
    html.Br(),
    
    html.Label('Season',style={"fontFamily": 'sans-serif','font-weight': 'bold'}),
    html.Div(
        dcc.Slider(id='season-slider',
               min=0,
               max=len(seasons)-1,
               marks={i: seasons[i] for i in range(len(seasons)) },
               value=len(seasons)-1,
               allow_direct_input=False),
        style={'width': '96%',
               'padding': '0 30px',
               'margin': '0 auto'
               }
            ),
    
    html.Br(),
    html.Div(
            id='nav-tabs',
            className='tab-container',
            style = {'display': 'flex', 'flexDirection': 'row', 'gap': '16px'},
            children=[
                dcc.Link(
                    page['name'],
                    href=page['relative_path'],
                    className='tab-link'
                )
                for page in dash.page_registry.values()
            ]
    ),
    dash.page_container  # Dash swaps content here based on URL
])

@app.callback(
    Output('nav-tabs', 'children'),
    Input('_pages_location', 'pathname')  # Dash Pages' built-in Location component
)
def update_active_tab(pathname):
    return [
        dcc.Link(
            page['name'],
            href=page['relative_path'],
            className='tab-link active' if page['relative_path'] == pathname else 'tab-link'
        )
        for page in dash.page_registry.values()
    ]

#dynamically change list of team to teams in playoffs for selected season 
@app.callback(
    Output("team-dropdown", "options"),
    Output("team-dropdown", "value"),
    Input("season-slider", "value"),
    Input("_pages_location", "pathname")
)
def update_team_list(selected_season, pathname):
    if pathname == '/playoffs':
        df = pageranks_play
    else:
        df = pageranks_yr

    if selected_season < len(seasons):
        season = seasons[selected_season]
        season_team_ids = df[df['season'] == season]['team_id'].unique()
    else:
        # "All" selected on the season slider
        season_team_ids = df['team_id'].unique()

    season_teams = sorted(team_df[team_df['id'].isin(season_team_ids)]['full_name'].to_numpy())

    if pathname == '/over_under_players':
        season_teams = ['All'] + season_teams
        default_value = 'All'
    else:
        default_value = season_teams[0] if len(season_teams) else None

    return season_teams, default_value

@app.callback(
    Output('season-slider','value'),
    Output('season-slider', 'marks'),
    Output('season-slider', 'max'),
    Input("_pages_location", "pathname")
)
def update_season_slider_options(pathname):
    marks = {i: seasons[i] for i in range(len(seasons)) }
    max = len(seasons)-1
    value = max
    if pathname == '/over_under_players':
        max += 1
        marks[max] = 'All'
        value += 1
    
    return value, marks, max

if __name__ == "__main__":
    app.run(debug=True)