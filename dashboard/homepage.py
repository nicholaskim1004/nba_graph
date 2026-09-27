# app.py
import dash # type: ignore[import-not-found]
import sqlite3
import pandas as pd # type: ignore[import-not-found]
from dash import Dash, html, dcc, Output, Input, ctx, State, no_update # type: ignore[import-not-found]
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
    html.Div(
        style = {'display': 'flex', 'flexDirection': 'row'},
        children=[
            html.Img(src='/assets/logos/nba_logo.png', style={'width': '5%', 'height': 'auto'}),

            html.H1("NBA GRAPH NETWORKS",
                    style={
                        "fontFamily": 'sans-serif',
                        "fontWeight": 'bold'})
            ]
    ),

    html.Div(
        style={
            'display': 'grid',
            'gridTemplateColumns': '1fr 280px',
            'gridTemplateRows': 'auto auto',
            'gridTemplateAreas': '"desc logo" "dropdown logo"',
            'columnGap': '24px',
            'alignItems': 'stretch'
        },
        children=[
            html.Div(
                "How are NBA Offenses different? Do teams follow a similar pattern? "
                "Do strategies change in the Playoffs? All these questions can be "
                "answered using network structure! This dashboard will display the "
                "results from a network for a given season and team.",
                style={
                    "fontFamily": 'sans-serif',
                    "fontSize": "20px",
                    "gridArea": "desc"
                }
            ),
            html.Div(
                style={'gridArea': 'dropdown'},
                children=[
                    html.Label('Team', style={"fontFamily": 'sans-serif', 'font-weight': 'bold'}),
                    dcc.Dropdown(
                        id='team-dropdown',
                        options=sorted(team_list, reverse=False),
                        value=team_list[0],
                        style={"fontFamily": 'sans-serif', 'width': '60%'}
                    )
                ]
            ),
            html.Img(
                id='team-logo',
                src='',
                style={
                    'gridArea': 'logo',
                    'width': '50%',
                    'height': 'auto',
                    'objectFit': 'contain'
                }
            )
        ]
    ),

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
    Input("_pages_location", "pathname"),
    State("team-dropdown", "value")
)
def update_team_list(selected_season, pathname, current_team_value):
    triggered = ctx.triggered_id

    # Slider moved on a non-playoffs page: nothing should change
    if triggered == "season-slider" and pathname != "/playoffs":
        return no_update, no_update

    if pathname == '/playoffs':
        df = pageranks_play
        season = seasons[selected_season]
        season_team_ids = df[df['season'] == season]['team_id'].unique()
        team_options = sorted(team_df[team_df['id'].isin(season_team_ids)]['full_name'].to_numpy())
    else:
        df = pageranks_yr
        team_options = sorted(team_df['full_name'].to_numpy())

    if pathname == '/over_under_players':
        team_options = ['All'] + team_options

    # If we're recomputing (page changed, or playoffs season changed),
    # keep the user's current team if it's still valid for the new option set;
    # otherwise fall back to a sensible default.
    if pathname == '/over_under_players':
        default_value = 'All'
    elif current_team_value in team_options:
        default_value = current_team_value
    else:
        default_value = team_options[0] if len(team_options) else None

    return team_options, default_value

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

#to display correct team
@app.callback(
    Output('team-logo', 'src'),
    Input('team-dropdown', 'value')
)
def show_correct_logo(selected_team):
    team_split = selected_team.split(" ")
    
    if len(team_split) == 3:
        team = team_split[2]
    elif selected_team == 'All':
        return None
    else:
        team = team_split[1]
    
    src = f'/assets/logos/{team.lower()}.png'

    return src


if __name__ == "__main__":
    app.run(debug=True)