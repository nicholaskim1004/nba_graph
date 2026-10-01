## ALL TABLES

# shots_yr: 

stores the shots proportions at 7 distict shot locations (Restricted Area, In the Pain, Mid-Range, Above the Break 3, Left Corner, Right Corner)

| Column | Descirption |
| -------- | -------- |
| player_id | unique id for player |
| player_name | player's full name (last, first) |
| season | string of season ex. '2020-21' |
| min | total minutes played | 
| team_id | unique id for team (one that player ended year at) | 
| restricted_area_att | proportion of attempts at restricted area | 
| paint_att | proportion of attempts in paint |
| mid_range_att | proportion of attempts in mid-range | 
| left_corner_att | proportion of attempts in left corner three | 
| right_corner_att | proportion of attempts in right corner three | 
| above_break_att | proportion of attempts at above the break three | 
| backcourt_att | proportion of attempts in backcourt (behind opposing teams half court line) | 

# passes_yr 

stores the proportion of pass attempts to from one player to each of its teammates in a season. 

| Column | Description | 
| -------- | -------- |
| player_id | unique id for player (one where passes originate from) |
| player_name | player's full name (last, first) |
| season | string of season ex. '2020-21' |
| team_id | unique id for team (one that player ended year at) | 
| pass_to_id | unique id for player who recieves the pass | 
| pass_to | full name of player who get's the ball |
| count | raw total number of passes to each teammate | 
| proportion | converted count into proporiton of passes to each teammate | 

# positions 

stores the positions for each player. one of 5 groups (Guard, Guard-Forward, Forward, Center, Center-Forward)

| Column | Description | 
| -------- | -------- |
| player_id | unique id for player (one where passes originate from) |
| player_name | player's full name (last, first) |
| positions | player position, 1 of 5 label | 

# avdstats_yr

stores avdanced metrics for each player in a given season

| Column | Description | 
| -------- | -------- |
| season | string of season ex. '2020-21' |
| team_id | unique id for team (one that player ended year at) | 
| player_id | unique id for player (one where passes originate from) |
| player_name | player's full name (last, first) |
| TOTAL_MIN | total minutes played in a season | 
| PIE | Player Impact Estimate, metric to capture how valuable a player is | 
| PIE_SHARE | proportion of PIE a player takes up in their team |
| TS | True Shooting, metric to capture a player's efficeny in all 3 shots in the game (2, 3, free-throw) |
| USG | Usage Rate, metric to capture how many possessions end with the player |
| AST_PCT | Assist Percentage, metric to estimate how many percentage of a team's field goals a player assists on |
| E_OFF_RATING | Expected Offensive Rating, how many points an offense should have scored based on shot quality | 
| E_DEF_RATING | Expected Defensive Rating, metric to estimate how many points a player allows when on the court | 
| E_NET_RATING | Expected Net Rating, estimated impact of a player (diff in off and def rating) |

# shots_playoffs_yr 

stores the shots proportions at 7 distict shot locations (Restricted Area, In the Pain, Mid-Range, Above the Break 3, Left Corner, Right Corner) during the playoff

| Column | Descirption |
| -------- | -------- |
| player_id | unique id for player |
| player_name | player's full name (last, first) |
| season | string of season ex. '2020-21' |
| min | total minutes played | 
| team_id | unique id for team (one that player ended year at) | 
| restricted_area_att | proportion of attempts at restricted area | 
| paint_att | proportion of attempts in paint |
| mid_range_att | proportion of attempts in mid-range | 
| left_corner_att | proportion of attempts in left corner three | 
| right_corner_att | proportion of attempts in right corner three | 
| above_break_att | proportion of attempts at above the break three | 
| backcourt_att | proportion of attempts in backcourt (behind opposing teams half court line) | 

# passes_playoffs_yr 

stores the proportion of pass attempts to from one player to each of its teammates during the playoffs for a given season. 

| Column | Description | 
| -------- | -------- |
| player_id | unique id for player (one where passes originate from) |
| player_name | player's full name (last, first) |
| season | string of season ex. '2020-21' |
| team_id | unique id for team (one that player ended year at) | 
| pass_to_id | unique id for player who recieves the pass | 
| pass_to | full name of player who get's the ball |
| count | raw total number of passes to each teammate | 
| proportion | converted count into proporiton of passes to each teammate | 

# records_yr

stores the teams record the regular season 

| Column | Description | 
| -------- | -------- |
| season | string of season ex. '2020-21' |
| team_id | unique id for team (one that player ended year at) | 
| team_name | the full name of the team | 
| conference | West or East |
| division | what division team is in | 
| record | regular season record, stored as string (W-L)|
| wins | integer storing how many wins | 
| seed | the teams ranking in their respective conference (1-15) |
| league_rank | overall team seeding (1-30) |

# playoff_records_yr

stores the results of the playoffs for a given season 

| Column | Description | 
| -------- | -------- |
| season | string of season ex. '2020-21' |
| conference | West or East | 
| round | what round the matchup was at (first_round, conference_semi, conference_final, final) |
| series | the result of the series as a string (ex. 4-3) | 
| winning_team | winning team of series |
| seed_win | the seed of the winning team |
| losing_team | losing team of series |
| seed_lose | seed of losing team | 

# pageranks_yr 

stores the pageranks from built out graph netowrk for a given team in a given season 

| Column | Description | 
| -------- | -------- |
| season | string of season ex. '2020-21' |
| team_id | unique id for team (one that player ended year at) | 
| node_name | name of the node | 
| player_id | unique id for player (for shot location nodes id is teamid+[0-7]) where 0 is for restricted area, 1 paint, and so on|
| pagerank | pagerank (how central a player is to the network) of node |
| x_cord | the x-cordinate of node in plot to use when rebuilding graph |
| y_cord | the y-cordinate of node in plot to use when rebuilding graph |

# network_edges

stores the edge weights of node to other node for a given season 

| Column | Description | 
| -------- | -------- |
| season | string of season ex. '2020-21' |
| team_id | unique id for team (one that player ended year at) | 
| source | name of node that edge starts from | 
| target | name of node that edge connects to |
| weight | the proporiton value from node to target | 

# pageranks_playoffs_yr 

stores the pageranks from built out graph netowrk for a given team during the playoffs for a given season 

| Column | Description | 
| -------- | -------- |
| season | string of season ex. '2020-21' |
| team_id | unique id for team (one that player ended year at) | 
| node_name | name of the node | 
| player_id | unique id for player (for shot location nodes id is teamid+[0-7]) where 0 is for restricted area, 1 paint, and so on|
| pagerank | pagerank (how central a player is to the network) of node |
| x_cord | the x-cordinate of node in plot to use when rebuilding graph |
| y_cord | the y-cordinate of node in plot to use when rebuilding graph |

# network_edges_playoffs

stores the edge weights of node to other node during the playoffs for a given season 

| Column | Description | 
| -------- | -------- |
| season | string of season ex. '2020-21' |
| team_id | unique id for team (one that player ended year at) | 
| source | name of node that edge starts from | 
| target | name of node that edge connects to |
| weight | the proporiton value from node to target | 

# player_usage_yr

stores metrics on how diverse or concentrated the pagerank is split amounst player nodes for a given season 

| Column | Description | 
| -------- | -------- |
| season | string of season ex. '2020-21' |
| team_id | unique id for team (one that player ended year at) | 
| gini | how unequal pagerank is (smaller more unequal) |
| entropy | how predicitable is pagerank between nodes (higher means more unpredictable or evenly spread out) |
| eff_num_players | how many nodes have a siginficant pagerank value |

# player_usage_yr_playoff

stores metrics on how diverse or concentrated the pagerank is split amounst player nodes during the playoffs for a given season 

| Column | Description | 
| -------- | -------- |
| season | string of season ex. '2020-21' |
| team_id | unique id for team (one that player ended year at) | 
| gini | how unequal pagerank is (smaller more unequal) |
| entropy | how predicitable is pagerank between nodes (higher means more unpredictable or evenly spread out) |
| eff_num_players | how many nodes have a siginficant pagerank value |

# expected_pagerank_yr

stores the expected pagerank and residual for a player given their PIE and position

| Column | Description | 
| -------- | -------- |
| season | string of season ex. '2020-21' |
| team_id | unique id for team (one that player ended year at) | 
| player_id | unique id for player (one where passes originate from) |
| player_name | player's full name (last, first) |
| TOTAL_MIN | total minutes played in a season | 
| PIE | Player Impact Estimate, metric to capture how valuable a player is | 
| PIE_SHARE | proportion of PIE a player takes up in their team |
| TS | True Shooting, metric to capture a player's efficeny in all 3 shots in the game (2, 3, free-throw) |
| USG | Usage Rate, metric to capture how many possessions end with the player |
| AST_PCT | Assist Percentage, metric to estimate how many percentage of a team's field goals a player assists on |
| E_OFF_RATING | Expected Offensive Rating, how many points an offense should have scored based on shot quality | 
| E_DEF_RATING | Expected Defensive Rating, metric to estimate how many points a player allows when on the court | 
| E_NET_RATING | Expected Net Rating, estimated impact of a player (diff in off and def rating) |
| expected_pagerank | the expected imporatance to a teams offense based on position and PIE_SHARE |
| pagerank_residual | the difference between actual and expected pagerank, to find underrated or overrated players | 
