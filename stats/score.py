
from pandas import read_csv, DataFrame, read_json, merge
import os
import math
import numpy as np
import plotly.graph_objs as graph
from plotly.offline import plot
import datetime
from sklearn.metrics import accuracy_score
from sklearn.linear_model import LogisticRegression
from collections import Counter
import json

try:
    from stats.utils import fullpath
    from stats.base import Data
except ImportError:
    from utils import fullpath
    from base import Data
try:
    import statistics as stats
except ImportError:
    import scipy.stats as stats


class ELO(object):

    def __init__(self, league, **kwargs):

        self.league = league.lower()

        self.team1 = kwargs.get("team1", "any")
        self.team2 = kwargs.get("team2", "any")
        self.startyear = kwargs.get("start", 1994)
        self.endyear = kwargs.get("end", 2017)

        self.games_datafile = fullpath("../data/%s_%sVS%s_games.csv" % (self.league, self.team1, self.team2))
        self.attends_datafile = fullpath("../data/%s_attendance.csv" % self.league)
        self.ratings_data=[]

        self.attendance_df = self.attendance_data()
        self.games_df = self.games_data()
        
    def games_data(self):
        if os.path.isfile(".".join([self.games_datafile,"csv"])):
            dfx = read_csv(".".join([self.games_datafile,"csv"]))
            dfx = dfx.loc[self.startyear <= dfx["year"]]
            dfx = dfx.loc[dfx["year"] <= self.endyear]
            dfx.index = [i for i in range(len(dfx.index))]
            return dfx

        else:
            data = Data(league=self.league)
            data.games(start=self.startyear, end=self.endyear,
                       team1=self.team1, team2=self.team2)
            dfx = data.games_data
            dfx.index = [i for i in range(len(dfx.index))]
            return self.update_games(d=dfx)


    def attendance_data(self):
        if os.path.isfile(self.attends_datafile):
            dfx = read_csv(self.attends_datafile)
            dfx = dfx.loc[(self.startyear <= dfx["year"]) & (dfx["year"] <= self.endyear)]
            dfx.index = [i for i in range(len(dfx.index))]
        else:
            data = Data(league=self.league)
            data.attendance(start=self.startyear, end=self.endyear, save=True)
            dfx = data.attendance_data

        return dfx

    def get_last_rating(self, team, gameid):

        if len(self.ratings_data) == 0:
            lastelo = 1000
        else:

            home_list = list(filter(lambda x: self.ratings_data[x]["home_teamname"] == team, [i for i in range(0, int(gameid)-1)]))
            away_list = list(filter(lambda x: self.ratings_data[x]["away_teamname"] == team, [i for i in range(0, int(gameid)-1)]))
            try:
                lasthome, lastaway = home_list[len(home_list)-1], away_list[len(away_list)-1]
            except IndexError:
                lastelo = 1000
            else:
                if lasthome > lastaway:
                    lastelo = self.ratings_data[lasthome]["home_endelo"]
                elif lastaway > lasthome:
                    lastelo = self.ratings_data[lastaway]["away_endelo"]
                else:
                    lastelo = 1000

        return lastelo


    def _calc_elo(self, home_elo, away_elo, winner="home", k=20):
        home_expected, away_expected = self.expected_ratings(team1_rating=home_elo,
                                                             team2_rating=away_elo)

        home_mult, away_mult = 0, 0
        if winner.lower() == "home":
            home_mult += 1
            away_prob = self.log_prob(winner_elo=home_elo, loser_elo=away_elo)
            home_prob = 1 - away_prob
        elif winner.lower() == "away":
            away_mult += 1
            home_prob = self.log_prob(winner_elo=away_elo, loser_elo=home_elo)
            away_prob = 1 - home_prob
        elif winner.lower() == "tie":
            home_mult += .5
            away_mult += .5
            home_prob, away_prob = .5, .5
        else:
            raise AttributeError("winner %s invalid must be in ['home','away','tie']" % winner.lower())


        home_new_elo = home_elo + float(k) * (home_mult - home_expected)
        away_new_elo = away_elo + float(k) * (away_mult - away_expected)

        return {"home_startelo": home_elo, "home_endelo": home_new_elo, "home_prob": home_prob,
                "away_startelo": away_elo, "away_endelo": away_new_elo, "away_prob": away_prob}



    def adjust_ratings(self, ID, gameinfo, **kwargs):
        kfactor = kwargs.get("k", 20)
        winner = kwargs.get("winner", gameinfo["winner"])
        if ID == 0:
            home_beg_elo = 1000
            away_beg_elo = 1000
            elo_ratings = self._calc_elo(home_elo=home_beg_elo, away_elo=away_beg_elo, k=kfactor, winner=winner)
            gameinfo.update(elo_ratings)
        else:

            try:
                home_beg_elo = self.get_last_rating(team=gameinfo["home_teamname"], gameid=ID)
                away_beg_elo = self.get_last_rating(team=gameinfo["away_teamname"], gameid=ID)
            except KeyError as err:
                print(err)
            else:
                elo_ratings = self._calc_elo(home_elo=home_beg_elo, away_elo=away_beg_elo, k=kfactor, winner=winner)
                gameinfo.update(elo_ratings)

        return gameinfo

    def log_prob(self, winner_elo, loser_elo):
        # based on the model developed by Boltzmann
        # source: goo.gl/gNMNSi

        diff = float(winner_elo) - float(loser_elo)
        a = 1 + math.exp((0.00583*float(diff)) - 0.0505)
        prob = float(1/a)
        return prob

    def rsiK(self, team, pds=14):

        if len(self.games_df.index) < pds:
            print("Insufficient number of past ratings to calculate the rsi with pd window %s" % str(pds))
        else:
            firstpd_gains = stats.mean(self.games_df.loc[0:pds+1][self.games_df["diff"] > 0])
            firstpd_losses = stats.mean(self.games_df.loc[0:pds+1][self.games_df["diff"] < 0])
            data = {"idx":[], "avggain":[], "avgloss":[], "rs":[], "rsi":[]}
            data["idx"].append(pds+1)
            data["avggain"].append(firstpd_gains)
            data["avgloss"].append(firstpd_losses)
            if firstpd_losses == 0:
                data["rs"].append(0.)
            else:
                data["rs"].append(float(firstpd_gains/firstpd_losses))

            x=1
            while x+pds+1 <=len(self.games_df.index):
                gain = (stats.mean(self.games_df.loc[x:x+pds-1][self.games_df["margin"]>0]) * pds)+data["avggain"][x-1]
                loss = (stats.mean(self.games_df.loc[x:x+pds-1][self.games_df["margin"]<0]) * pds)+data["avgloss"][x-1]
                rs = float(gain/loss)
                rsi = 100 - (100/1+float(rs))



                data["idx"].append(x+pds+1)
                data["avggain"].append(gain)
                data["avgloss"].append(loss)
                data["rs"].append(rs)
                data["rsi"].append(rsi)

            return data



    def expected_ratings(self, team1_rating, team2_rating):
        a = 10**(float(team1_rating)/200)
        b = 10**(float(team2_rating)/200)
        expected_a = float(a/(a+b))
        expected_b = float(b/(a+b))
        return expected_a, expected_b

    def get_last_local(self, team):
        home = self.games_df.loc[self.games_df["home_teamname"]==team]
        away = self.games_df.loc[self.games_df["away_teamname"]==team]


        lasthome = [i for i in home.index]
        lasthome_id = lasthome[len(home)-1]
        lastaway = [i for i in away.index]
        lastaway_id = lastaway[len(away)-1]

        if lasthome_id > lastaway_id:
            team_elo = home.loc[lasthome_id]["home_endelo"]

        elif lasthome_id < lastaway_id:
            team_elo = away.loc[lastaway_id]["away_endelo"]
        else:
            team_elo = 1000

        return team_elo

    def matchup(self, home, away, **kwargs):
        winner = kwargs.get("winner", "home")
        kfactor = kwargs.get("k", 20)

        team1_elo = self.get_last_local(team=home.lower())
        team2_elo = self.get_last_local(team=away.lower())
        matchup_dict = self._calc_elo(home_elo=team1_elo, away_elo=team2_elo, winner=winner, k=kfactor)

        print("Game Results",
        "\n--------------------\n")
        print("Home: %s  Starting ELO Rank: %s  Ending ELO Rank:  %s  Log-Prob: %s\n" % (home.upper(), matchup_dict["home_startelo"],
                                                                                         matchup_dict["home_endelo"], matchup_dict["home_prob"]))
        print("Away: %s  Starting ELO Rank: %s  Ending ELO Rank:  %s  Log-Prob: %s\n" % (away.upper(), matchup_dict["away_startelo"],
                                                                                         matchup_dict["away_endelo"], matchup_dict["away_prob"]))


    def update_games(self, d):
        games = d.to_dict("index")
        for i in range(len(games)):
            new_game = self.adjust_ratings(ID=i, gameinfo=games[i])
            self.ratings_data.append(new_game)

            print("%s %% Completed." % round((i / len(games) * 100), 4))
        dfx = DataFrame(self.ratings_data)
        
        dfx.index.name = "index"
        dfx.to_csv(".".join([self.games_datafile,"csv"]))
        dfx.to_json(".".join([self.games_datafile, "json"]), orient="index", date_format="iso")
        return dfx

        print("Ratings Updated.")
    
    def get_teams_by_year(self, year=2017):
        teams = [i for i in np.unique(self.games_df["home_teamname"][self.games_df["year"]==year])]
        return teams

    def get_team_elos(self, team, years=None):
        teamx = self.games_df[(self.games_df["home_teamname"]==team) | (self.games_df["away_teamname"]==team)].dropna()
        team_elos = []
        for i in teamx.index:
            if teamx.loc[i]["home_teamname"]==team:
                if years is not None:
                    if type(years) is list:
                        if teamx.loc[i]["year"] in range(years[0], years[len(years)-1]):

                            team_elos.append((teamx.loc[i]["year"], teamx.loc[i]["game_date"], teamx.loc[i]["home_endelo"]))
                        else:
                            pass
                    elif type(years) is int:
                        if teamx.loc[i]["year"] in range(1993, years):
                            team_elos.append((teamx.loc[i]["year"], teamx.loc[i]["game_date"], teamx.loc[i]["home_endelo"]))
                        else:
                            pass
                    else:
                        print("years must be list, nonetype, or int")
                else:
                    team_elos.append((teamx.loc[i]["year"], teamx.loc[i]["game_date"], teamx.loc[i]["home_endelo"]))
            elif teamx.loc[i]["away_teamname"]==team:
                team_elos.append((teamx.loc[i]["year"], teamx.loc[i]["game_date"], teamx.loc[i]["away_endelo"]))
            
        return team_elos

    def get_team_colors(self, team):
        grayscale_alts = ["#cccccc","#b7b7b7","#939393", "#666666"]
        colormap = {}
        file = fullpath("../conf/%s_team_colormap.json" % self.league)
        
        if os.path.isfile(file):
            with open(file, mode='r') as f:
                js = json.load(f)
                for j in range(len(js)):
                    if js[j]["team"] == team:
                        colormap.update({"marker":js[j]["colors"][1], "line":js[j]["colors"][0]})
                    else:
                        pass
                f.close()
        else:
            colors = Data(league=self.league).team_colors()
            for c in range(len(colors)):
                if colors[c]["team"] == team:
                    try:
                        linecolor = colors[c]["colors"][1]
                        markercolor = colors[c]["colors"][0]
                    except IndexError:
                        markercolor = colors[c]["colors"][1]
                        linecolor = np.random.choice(grayscale_alts, size=1)
                    
                    colormap.update({"line":linecolor, "marker":markercolor})
        return colormap


    

    def plot(self, year):
        print("Plotting...")
        years = range(1994, 2017+1)
        teams_by_year_dict = {}
        
        teams = self.get_teams_by_year(year=year)

        traces = []
        btns1 = [dict(args=["visible", [False]*len(teams)], label="Select Team:", method="restyle")]
        # btns2 = [dict(args=["visible", [False]*len(teams)], label="Select Team 2:", method="restyle")]
        base = datetime.datetime(year, 12, 31)
        dates = [base - datetime.timedelta(days=x) for x in range(0, 365)]
        menu = [dict(x=-.05, y=1.0, yanchor="top", buttons=btns1)]
        for team in teams:

            teamcolors = self.get_team_colors(team=team)

            elo_scores = self.get_team_elos(team=team, years=[year-1, year])
            scores = [elo_scores[x][2] for x in range(len(elo_scores))]
            teamidx = list(filter(lambda x: teams[x]==team, [t for t in range(len(teams))]))
            vis = [False]*len(teams)
            vis[teamidx[0]]=True
            trace = graph.Scatter(x=dates, y=scores,
                mode="lines+markers",
                line=dict(width=1.5, color=teamcolors["line"]),
                marker=dict(color=teamcolors["marker"], size=4.0),
                name=team.capitalize())
            btnlabels = dict(args=["visible", vis],
                             label=team.capitalize(),
                             method="restyle")
            btns1.append(btnlabels)
            # btns2.append(btnlabels)
            traces.append(trace)


        data =graph.Data(traces)
        layout = graph.Layout(title="%s Team ELO Ratings" % self.league.upper(),
                              updatemenus=list(menu))
        fig = graph.Figure(data=data, layout=layout)
        return fig

    def setup_predict(self, classifier, df, **kwargs):

        training_size = kwargs.get("training_size", .70)
        selection_method = kwargs.get("selection_method", "random")


        if selection_method == "random":
            ids = np.random.choice(df.index, size=int(training_size*len(df.index)))
            testing_ids = list(filter(lambda x: x not in ids, self.games_df.index))

        elif selection_method == "inline":
            ids = df.loc[0:int(len(df.index)*training_size)]
            start = int(len(self.games_df.index)*training_size)
            testing_ids = [i for i in range(start+1, len(self.games_df.index))]
        
        training_df = df.loc[[i for i in ids] ,:]
        testing_df = df.loc[[j for j in testing_ids] ,:]
        return training_df, testing_df

    def predict(self, classifier, **kwargs):


        training_size = kwargs.get("training_size", .70)
        selection_method = kwargs.get("selection_method", "random")


        if selection_method == "random":
            ids = np.random.choice(self.games_df.index, size=int(training_size*len(self.games_df.index)))
            testing_ids = list(filter(lambda x: x not in ids, self.games_df.index))

        elif selection_method == "inline":
            ids = self.games_df.loc[0:int(len(self.games_df.index)*training_size)]
            start = int(len(self.games_df.index)*training_size)
            testing_ids = [i for i in range(start+1, len(self.games_df.index))]
        
        training_df = self.games_df.loc[[i for i in ids] ,:]
        testing_df = self.games_df.loc[[j for j in testing_ids] ,:]

        
        trainx = training_df.loc[:, ["home_startelo","away_startelo","home_prob","away_prob"]]
        trainy = training_df["winner"]

        testx = testing_df.loc[:, ["home_startelo","away_startelo","home_prob","away_prob"]]
        actualy = testing_df["winner"]


        classifier.fit(X=trainx, y=trainy)
        predicted = classifier.predict(testx)
        accuracy = accuracy_score(actualy, predicted)
        print(accuracy)

