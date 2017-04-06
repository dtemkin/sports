from stats.score import ELO


ratings = ELO(league="nhl")
ratings.matchup(home="Blackhawks", away="Jets", winner="home")

