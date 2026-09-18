import sqlite3
import pandas as pd # type: ignore[import-not-found]
import dash_cytoscape as cyto  # type: ignore[import-not-found]

from dash import Dash, html, dcc, Input, Output, callback, dash_table # type: ignore[import-not-found]
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

diff_shots = ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Right Corner 3', 'Above the Break 3', 'Backcourt']

app = Dash()

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
    
    html.Label('Team'),
    dcc.Dropdown(id='team-dropdown',
                 options=sorted(team_list,reverse=False),
                 value=team_list[0],
                 style={'width': '50%'}),
    
    html.Br(),
    
    html.Label('Season'),
    dcc.Slider(id='season-slider',
               min=0,
               max=len(seasons)-1,
               marks={i: seasons[i] for i in range(len(seasons)) },
               value=len(seasons)-1),
    
    html.Br(),
    
    html.Div(
    style={
        'display': 'flex',
        'flexDirection': 'row',
        'gap': '20px',
        'width': '100%'
    },
    children=[
        # LEFT: Cytoscape
        html.Div(
            cyto.Cytoscape(
                id='graph_networks',
                elements=[],
                layout={'name': 'preset'},
                stylesheet=[
                    {
                        'selector': 'node',
                        'style': {
                            'label': 'data(label)',
                            'width': 'data(pagerank)',
                            'height': 'data(pagerank)'
                        }
                    },
                    {
                        'selector': '.shot',
                        'style': {
                            'background-color': '#FF2C2C',
                            'opacity': 0.95
                        }
                    },
                    {
                        'selector': '.player',
                        'style': {
                            'background-color': '#B6E3FF',
                            'opacity': 0.95
                        }
                    },
                    {
                        'selector': 'edge',
                        'style': {
                            'source-arrow-shape': 'triangle'
                        }
                    }
                ],
                style={
                    'width': '100%',
                    'height': '700px'
                }
            ),
            style={
                'width': '70%'
            }
        ),

        # RIGHT: PageRank table
        html.Div(
            dash_table.DataTable(
                id='pagerank_table',
                data=[],
                columns=[
                    {'name': i, 'id': i}
                    for i in pageranks_yr.loc[:, ['season','node_name','pagerank']].columns
                ],
                row_selectable='single'
            ),
            style={
                'width': '30%'
            }
        )
    ]
)
])


@app.callback(
    Output("graph_networks", "elements"),
    Input("team-dropdown", "value"),
    Input("season-slider", "value")
)
def update_network(selected_teams, selected_season):
    sel_teams_ids = team_df[team_df['full_name']==selected_teams]['id'].to_numpy()
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
                "pagerank": float(row["pagerank"]) * 1000
            },
            "classes": "shot" if row["node_name"] in diff_shots else "player",
            "position": {
                "x": float(row["x_cord"]) * 800,
                "y": float(row["y_cord"]) * 800
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

@app.callback(
    Output('pagerank_table', 'data'),
    Input("team-dropdown", "value"),
    Input("season-slider", "value")
)
def update_pagerank_table(selected_team, selected_season):
    sel_teams_ids = team_df[team_df['full_name']==selected_team]['id'].to_numpy()
    season = seasons[selected_season]
    
    selected_pageranks = pageranks_yr[
        (pageranks_yr["team_id"].isin(sel_teams_ids))&(pageranks_yr['season']==season)
    ]
    
    return selected_pageranks.loc[:,['season','node_name','pagerank']].sort_values('pagerank',ascending=False).to_dict('records')

if __name__ == "__main__":
    app.run(debug=True)
    