import sqlite3
import pandas as pd # type: ignore[import-not-found]
import dash_cytoscape as cyto  # type: ignore[import-not-found]

from dash import Dash, html, dcc, Input, Output # type: ignore[import-not-found]
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_page = "SELECT * FROM pageranks_yr"
pageranks_yr = pd.read_sql_query(query_page, con)

query_edge = "SELECT * FROM passes_yr"
passes_yr = pd.read_sql_query(query_edge, con)

#ensuring passes_yr only contains the players used as nodes in pagerank
passes_yr_fil = passes_yr[(passes_yr['player_name'].isin(pageranks_yr['node_name']))&(passes_yr['pass_to'].isin(pageranks_yr['node_name']))]

team_df = pd.DataFrame(teams.get_teams())
team_list = team_df['full_name'].to_numpy()

seasons = pageranks_yr['season'].unique()

#convert pagerank data into JSON
nodes = [{
    'data': {
        'id': str(row['node_name']),
        'label': row['node_name'],
        'pagerank': row['pagerank']
    },
    'position': {
        'x': row['x_cord'],
        'y': row['y_cord']
    }
} for _,row in pageranks_yr.iterrows()]

#edge weights to display (proportion of pass)
edges = [{
    'data': {
        'source': row['player_name'],
        'target': row['pass_to'],
        'weight': row['proportion']
    }
} for row in passes_yr_fil.iterrows()]

elements = nodes + edges

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
    dcc.Dropdown(id='team-dropdown',
                 options=sorted(team_list,reverse=False),
                 value=[team_list[0]],
                 multi=True),
    
    html.Br(),
    
    html.Label('Season'),
    dcc.Slider(id='season-slider',
               min=0,
               max=len(seasons)-1,
               marks={i: seasons[i] for i in range(len(seasons)) },
               value=len(seasons)-1),
    
    html.Br(),
    
    cyto.Cytoscape(id='graph_networks',
                   elements=[],
                   layout={'name':'preset'},
                   style={"width": "100%", "height": "700px"})
    
])

@callable(
    Output("graph_networks", "elements"),
    Input("team-dropdown", "value"),
    Input("season-slider", "value")
)
def update_network(selected_teams, selected_season):
    sel_teams_ids = team_df[team_df['full_name'].isin(selected_teams)]['id'].to_numpy()
    selected_pageranks = pageranks_yr[
        (pageranks_yr["team_id"].isin(sel_teams_ids))&(pageranks_yr['season']==selected_season)
    ]

    # Create nodes
    nodes = [
        {
            "data": {
                "id": str(row["node"]),
                "label": row["node"],
                "pagerank": row["pagerank"]
            },
            "position": {
                "x": row["x"],
                "y": row["y"]
            }
        }
        for _, row in selected_pageranks.iterrows()
    ]
    
    selected_passes_yr = passes_yr_fil[(passes_yr_fil['team_id'].isin(sel_teams_ids))&(passes_yr_fil['season']==selected_season)]
    
    edges = [{
        'data': {
            'source': row['player_name'],
            'target': row['pass_to'],
            'weight': row['proportion']
        }
    } for row in selected_passes_yr.iterrows()]

    return nodes + edges

if __name__ == "__main__":
    app.run(debug=True)