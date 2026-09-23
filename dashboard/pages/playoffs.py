import sqlite3
import pandas as pd # type: ignore[import-not-found]
import dash_cytoscape as cyto  # type: ignore[import-not-found]
import numpy as np # type: ignore[import-not-found]

import dash # type: ignore[import-not-found]
from dash import html, Input, Output, callback, dash_table, State, ctx, no_update# type: ignore[import-not-found]
from nba_api.stats.static import teams

con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()

query_page = "SELECT * FROM pageranks_playoffs_yr"
pageranks_yr = pd.read_sql_query(query_page, con)

query_edge = "SELECT * FROM network_edges_playoffs"
edges_yr = pd.read_sql_query(query_edge, con)

team_df = pd.DataFrame(teams.get_teams())
team_list = team_df['full_name'].to_numpy()

seasons = pageranks_yr['season'].unique()

diff_shots = ['Restricted Area', 'In The Paint (Non-RA)', 'Mid-Range', 'Left Corner 3', 'Right Corner 3', 'Above the Break 3', 'Backcourt']

dash.register_page(__name__, path='/playoffs', name='Playoffs', order = 1)

layout = html.Div([
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
                id='graph_networks_playoffs',
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
                id='pagerank_table_playoffs',
                data=[],
                columns=[
                    {'name': i, 'id': i}
                    for i in pageranks_yr.loc[:, ['season','node_name','pagerank']].columns
                ],
                style_data_conditional = [
                    {
                    'if': {'state': 'active'},
                    'backgroundColor': '#FF0000',
                    'color': 'white'
                    }
                ]
            ),
            style={
                'width': '30%'
            }
        )
    ]
    ),
    html.Div(
    id='passes_weight_container_play',
    children=[
        html.H2('Edge Weights',style={"fontFamily": 'sans-serif',"fontWeight": 'bold'}),
        dash_table.DataTable(
            id='passes_weight_table_play',
            data=[],
            columns=[{'name': i, 'id': i}
                    for i in ['season','node_name','edge_to','weight']]
        )
    ],
    style={'display': 'none'}  # hidden until something is selected
    )
])


@callback(
    Output("graph_networks_playoffs", "elements"),
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
                "pagerank": float(row["pagerank"]) * 1000,
                "selected": False
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

@callback(
    Output('pagerank_table_playoffs', 'data'),
    Input("team-dropdown", "value"),
    Input("season-slider", "value")
)
def update_pagerank_table(selected_team, selected_season):
    sel_teams_ids = team_df[team_df['full_name']==selected_team]['id'].to_numpy()
    season = seasons[selected_season]
    
    selected_pageranks = pageranks_yr[
        (pageranks_yr["team_id"].isin(sel_teams_ids))&(pageranks_yr['season']==season)
    ]
    
    selected_pageranks['pagerank'] = selected_pageranks['pagerank'].round(4)
    
    return selected_pageranks.loc[:,['season','node_name','pagerank']].sort_values('pagerank',ascending=False).to_dict('records')

BASE_STYLESHEET = [
    {'selector': 'node',
     'style': {'label': 'data(label)',
               'width': 'data(pagerank)',
               'height': 'data(pagerank)'}},
    {'selector': '.shot',
     'style': {'background-color': '#FF2C2C', 'opacity': 0.95}},
    {'selector': '.player',
     'style': {'background-color': '#B6E3FF', 'opacity': 0.95}},
    {'selector': 'edge',
     'style': {'source-arrow-shape': 'triangle'}},
]


def with_highlight(node_name):
    return BASE_STYLESHEET + [{
        'selector': f'node[id = "{node_name}"]',
        'style': {
            'border-width': '12px',
            'border-color': '#172B3C',
            'background-color': '#172B3C',
            'opacity': 1,
        }
    }]

#highlights the correct node or element based on clicked node or element
@callback(
    Output('graph_networks_playoffs', 'stylesheet'),
    Output('pagerank_table_playoffs', 'active_cell'),
    Output('pagerank_table_playoffs', 'selected_cells'),
    Output('graph_networks_playoffs', 'tapNodeData'),
    Input('graph_networks_playoffs', 'tapNodeData'),
    Input('pagerank_table_playoffs', 'active_cell'),
    State('pagerank_table_playoffs', 'data'),
    prevent_initial_call=True,
)
def sync_selection(tap_node, active_cell, table_data):
    table_data = table_data or []

    if ctx.triggered_id == 'graph_networks_playoffs':
        if tap_node is None:
            # this is the reset pass firing back into us — ignore it
            return no_update, no_update, no_update, no_update

        name = tap_node['id']
        row = next((i for i, r in enumerate(table_data)
                    if r['node_name'] == name), None)
        if row is None:
            return BASE_STYLESHEET, None, [], None

        cell = {'row': row, 'column': 1, 'column_id': 'node_name'}
        return with_highlight(name), cell, [cell], None

    # table was clicked
    if active_cell is None or active_cell['row'] >= len(table_data):
        return BASE_STYLESHEET, no_update, no_update, None

    name = table_data[active_cell['row']]['node_name']
    return with_highlight(name), no_update, no_update, None

#show datatable with edge weights from node ordered from highest to lowest
@callback(
    Output('passes_weight_table_play', 'data'),
    Output('passes_weight_container_play', 'style'),
    Input("team-dropdown", "value"),
    Input("season-slider", "value"),
    Input('pagerank_table_playoffs', 'active_cell'),
    State('pagerank_table_playoffs', 'data')
)
def update_pass_table(selected_team, selected_season, active_cell, table_data):
    sel_teams_ids = team_df[team_df['full_name']==selected_team]['id'].to_numpy()

    if active_cell is None or not table_data:
        return [], {'display': 'none'}

    season = seasons[selected_season]
    name = table_data[active_cell['row']]['node_name']

    if name in diff_shots:
        weights = edges_yr[
            (edges_yr['season'] == season) &
            (edges_yr['team_id'].isin(sel_teams_ids)) &
            (edges_yr['target'] == name)
        ].sort_values('weight', ascending=False)
        weights = weights.rename(columns={'source': 'node_name', 'target': 'edge_to'})
        
        weights['weight'] = weights['weight'].round(4)
    else:
        weights = edges_yr[
            (edges_yr['season'] == season) &
            (edges_yr['team_id'].isin(sel_teams_ids)) &
            (edges_yr['source'] == name)
        ].sort_values('weight', ascending=False)
        weights = weights.rename(columns={'source': 'node_name', 'target': 'edge_to'})
        
        weights['weight'] = weights['weight'].round(4)
    if weights.empty:
        return [], {'display': 'none'}

    return weights[['season', 'node_name', 'edge_to', 'weight']].to_dict('records'), {'display': 'block'}

    