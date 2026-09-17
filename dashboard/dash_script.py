import sqlite3
import pandas as pd # type: ignore[import-not-found]
import dash_cytoscape as cyto  # type: ignore[import-not-found]

from dash import Dash, html, dcc, Input, Output, callback # type: ignore[import-not-found]
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_page = "SELECT * FROM pageranks_yr"
pageranks_yr = pd.read_sql_query(query_page, con)

query_edge = "SELECT * FROM network_edges"
edges_yr = pd.read_sql_query(query_edge, con)

team_df = pd.DataFrame(teams.get_teams())
team_list = team_df['full_name'].to_numpy()

seasons = pageranks_yr['season'].unique()

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

@app.callback(
    Output("graph_networks", "elements"),
    Input("team-dropdown", "value"),
    Input("season-slider", "value")
)
def update_network(selected_teams, selected_season):
    sel_teams_ids = team_df[team_df['full_name'].isin(selected_teams)]['id'].to_numpy()
    season = seasons[selected_season]
    
    selected_pageranks = pageranks_yr[
        (pageranks_yr["team_id"].isin(sel_teams_ids))&(pageranks_yr['season']==season)
    ]

    # Create nodes
    nodes = [
        {
            "data": {
                "id": str(row["node_name"]),
                "label": row["node_name"],
                "pagerank": row["pagerank"]
            },
            "position": {
                "x": float(row["x_cord"]) * 100,
                "y": float(row["y_cord"]) * 100
            }
        }
        for _, row in selected_pageranks.iterrows()
    ]
    
    selected_edges = edges_yr[
        (edges_yr['team_id'].isin(sel_teams_ids))&(edges_yr['season']==season)
    ]
    
    edges = [{
        'data': {
            'source': row['source'],
            'target': row['target'],
            'weight': row['weight']
        }
    } for _, row in selected_edges.iterrows()]

    return nodes + edges

if __name__ == "__main__":
    app.run(debug=True)