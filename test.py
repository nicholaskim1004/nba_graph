#ordered list [primary, secondary, tertiary]
team_colors = {'Miami Heat':['#98002e','#f9a01b','#000000'],
               'Los Angeles Lakers':['#552583','#f9a01b','#000000'],
               'Boston Celtics':['#007a33','#ba9653','#963821'],
               'Los Angeles Clippers':['#c8102e','#1d428a','#bec0c2'],
               'Brooklyn Nets':['#002a60','#cd1041','#777d84'],
               'Charlotte Hornets':['#1d1160','#00788c','#a1a1a4'],
               'Chicago Bulls':['#ce1141',"#E8E8E8FF",'#000000'],
               'Atlanta Hawks':['#e03a3e','#c1d32f','#26282a'],
               'Phoenix Suns':['#1d1160','#e56020','#000000'],
               'Dallas Mavericks':['#00538c','#002b5e','#b8c4ca'],
               'Denver Nuggets':['#0e2240','#fec524','#8b2131'],
               'Detroit Pistons':['#c8102e','#1d42ba','#bec0c2'],
               'Golden State Warriors':['#1d428a','#ffc72c','#000000'],
               'Houston Rockets':['#ce1141','#c4ced4','#000000'],
               'Indiana Pacers':['#002d62','#fdbb30','#bec0c2'],
               'Memphis Grizzlies':['#5d76a9','#12173f','#f5b112'],
               'Milwaukee Bucks':['#00471b','#eee1c6','#0077c0'],
               'Minnesota Timberwolves':['#0c2340','#236192','#9ea2a2'],
               'New Orleans Pelicans':['#0c2340','#c8102e','#85714d'],
               'New York Knicks':['#006bb6','#f58426','#bec0c2'],
               'Oklahoma City Thunder':['#007ac1','#ef3b24','#002d62'],
               'Orlando Magic':['#0077c0','#c4ced4','#000000'],
               'Philadelphia 76ers':['#006bb6','#ed174c','#002b5c'],
               'Portland Trail Blazers':['#e03a3e','#E8E8E8FF','#000000'],
               'Sacramento Kings':['#5a2d81','#63727a','#000000'],
               'San Antonio Spurs':['#c4ced4','#E8E8E8FF','#000000'],
               'Toronto Raptors':['#ce1141','#a1a1a4','#000000'],
               'Utah Jazz':['#002b5c','#00471b','#f9a01b'],
               'Cleveland Cavaliers':['#860038','#041e42','#fdbb30'],
               'Washington Wizards':['#002b5c','#e31837','#c4ced4']}


print("Info for NBA offensive networks")

print("Enter the following information to get the desired data")

try: 
    season = input("Enter desired season (ex. 2024-25): ")
    start_year, end_year = map(int, season.split('-'))
    if end_year != (start_year + 1) % 100:
        raise ValueError
except ValueError:
    print("Invalid season. Please enter the season in the format 'YYYY-YY' (e.g., '2024-25').")
    season = input("Enter desired season (ex. 2024-25): ")

print("\nNote: Do you want to get data for the playoffs or regular season?")

try:
    playoffs = input("Playoffs (Y/N): ")
    if playoffs not in ['Y', 'N']:
        raise ValueError
except ValueError:
    print("Invalid input. Please enter 'Y' for playoffs or 'N' for regular season.")
    playoffs = input("Playoffs (Y/N): ")

print("\nNote: If you want to get data for all teams, leave the team field blank")

try:
    team = input("Team: ")
    if team and team not in team_colors:
        raise ValueError
except ValueError:
    print("Invalid team name. Likely mispelled.")
    team = input("Team: ")

print("\nNote: Do you want to filter the data to only include players who played a minimum number of minutes?")
try:
    filtered = input("Filtered (Y/N): ")
    if filtered not in ['Y', 'N']:
        raise ValueError
except ValueError:
    print("Invalid input. Please enter 'Y' for filtered or 'N' for unfiltered.")
    filtered = input("Filtered (Y/N): ")
