import sqlite3
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.neighbors import NearestNeighbors

from nba_api.stats.static import players

import plotly.graph_objects as go
import plotly.express as px

import dash # type: ignore[import-not-found]
from dash import html, Input, Output, callback, dash_table, State, dcc, ctx, no_update# type: ignore[import-not-found]


con = sqlite3.connect('data/nba.db', timeout=10)
cursor = con.cursor()


query = "SELECT * FROM player_profiles"
prof_df = pd.read_sql_query(query, con)

features = ['positions','pagerank_norm','def_rating_per_rank','AST_PCT','USG','paint_prop','mid_range_prop','left_corner_prop','right_corner_prop','above_break_prop']

preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), features[1:]),
        ('cat', OneHotEncoder(drop='first'), ['positions'])
    ]
)

X = preprocessor.fit_transform(prof_df[features])
nn = NearestNeighbors(n_neighbors=6, metric='euclidean').fit(X)

def similar(player_id, season, n=5):
    i = prof_df.index[(prof_df.player_id == player_id) & (prof_df.season == season)][0]
    pid = prof_df.at[i, 'player_id']

    # distance from the query row to every row
    dist = np.linalg.norm(X - X[i], axis=1)

    # exclude every row belonging to this player (other seasons and the row itself)
    dist[(prof_df['player_id'] == pid).to_numpy()] = np.inf

    idx = np.argsort(dist)[:n]
    return prof_df.iloc[idx].assign(distance=dist[idx])


'''
dash.register_page(__name__, path='/player_profiles', name='Player Profiles', order = 4)

layout = html.Div([
    html.Label('Choice:',style={"fontFamily": 'sans-serif','font-weight': 'bold'}),
    dcc.Dropdown(id='player_profile_choice',
                options=prof_df['player_name'].unique(),
                value=prof_df['player_name'].unique()[0],
                style={"fontFamily": 'sans-serif','width': '10%'}),
    html.Br(),
    html.Div(
        dcc.Graph(id='player_profile_graph', style={'height': '600px'}),
    )
])

@callback(
    Output('player_profile_graph', 'figure'),
    Input('player_profile_choice', 'value')
)
def update_player_profile_graph(player_name):
    
    player_prof = prof_df[(prof_df['player_name'] == player_name)&(prof_df['season'] == '2020-21')]
    
    
    return

'''

similar_players = similar(2544, '2020-21',30)


#sample of player profile rader graph
lebron = prof_df[prof_df['player_id'] == 2544].iloc[0][features]
curry = prof_df[prof_df['player_name']=='Stephen Curry'].iloc[0][features]

#notes
#try shot location proportions to be percentile ranks instead of proportions

print(prof_df[(prof_df['player_name']=='Jalen Johnson')&(prof_df['season']=='2025-26')]['pagerank_norm'])

fig = go.Figure()

fig.add_trace(go.Scatterpolar(
      r=lebron.values[1:],
      theta=features[1:],
      fill='toself',
      name='LeBron James'
))
fig.add_trace(go.Scatterpolar(
      r=curry.values[1:],
      theta=features[1:],
      fill='toself',
      name='Stephen Curry'
))

fig.update_layout(
  polar=dict(
    radialaxis=dict(
      visible=True,
      range=[0, 1]
    )),
  showlegend=False
)
fig.show()