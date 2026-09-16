import sqlite3
import pandas as pd # type: ignore[import-not-found]
import dash_cytoscape as cyto  # type: ignore[import-not-found]

from dash import Dash, html, dcc # type: ignore[import-not-found]
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_sh = "SELECT * FROM pageranks_yr"
pageranks_yr = pd.read_sql_query(query_sh, con)

team_df = pd.DataFrame(teams.get_teams())
team_list = team_df['full_name'].to_numpy()

seasons = pageranks_yr['season'].unique()

#convert pagerank data into JSON


app = Dash()

app.layout = html.Div([
    html.H1("NBA GRAPH NETWORKS"),
    html.Div(
        "How are NBA Offenses different? Do teams follow a similar pattern? "
        "Do strategies change in the Playoffs? All these questions can be "
        "answered using network structure! This dashboard will display the "
        "results from a network for a given season and team.",
        style={
            "fontSize": "20px",
            "marginTop": "0px"
        }
    ),
    
    html.Br(),
    
    html.Label('Team'),
    dcc.Dropdown(options=sorted(team_list,reverse=False),value=[team_list[0]],multi=True),
    
    html.Br(),
    
    html.Label('Season'),
    dcc.Slider(min=0,
               max=len(seasons)-1,
               marks={i: seasons[i] for i in range(len(seasons)) },
               value=len(seasons)-1),
    
    html.Br(),
    
    cyto.Cytoscape()
    
])

if __name__ == "__main__":
    app.run(debug=True)