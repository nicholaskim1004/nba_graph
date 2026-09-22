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
    
    html.Label('Team',style={"fontFamily": 'sans-serif'}),
    dcc.Dropdown(id='team-dropdown',
                 options=sorted(team_list,reverse=False),
                 value=team_list[0],
                 style={"fontFamily": 'sans-serif','width': '50%'}),
    
    html.Br(),
    
    html.Label('Season',style={"fontFamily": 'sans-serif'}),
    dcc.Slider(id='season-slider',
               min=0,
               max=len(seasons)-1,
               marks={i: seasons[i] for i in range(len(seasons)) },
               value=len(seasons)-1,
               allow_direct_input=False),
    
    html.Br(),
    html.Div(
            id='nav-tabs',
            className='tab-container',
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

if __name__ == "__main__":
    app.run(debug=True)