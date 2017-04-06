from stats.utils import fullpath
from pandas import read_csv, DataFrame, concat
import os
import math
from stats.base import Data
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
        self.datafile = fullpath("../data/%s_%sVS%s_games.csv" % (self.league, self.team1, self.team2))
        self.df = self._data()
        self.ratings_data = []

    def _data(self):
        if os.path.isfile(self.datafile):
            df = read_csv(self.datafile, header=0)
            df = df.loc[self.startyear<=df["year"]]
            dfx = df.loc[df["year"]<=self.endyear]
            dfx.index = [i for i in range(len(dfx.index))]

        else:
            data = Data(league=self.league)
            data.games(start=self.startyear, end=self.endyear,
                       team1=self.team1, team2=self.team2)
            dfx = data.games_data
            self.update()

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

        if len(self.df.index) < pds:
            print("Insufficient number of past ratings to calculate the rsi with pd window %s" % str(pds))
        else:
            firstpd_gains = stats.mean(self.df.loc[0:pds+1][self.df["diff"] > 0])
            firstpd_losses = stats.mean(self.df.loc[0:pds+1][self.df["diff"] < 0])
            data = {"idx":[], "avggain":[], "avgloss":[], "rs":[], "rsi":[]}
            data["idx"].append(pds+1)
            data["avggain"].append(firstpd_gains)
            data["avgloss"].append(firstpd_losses)
            if firstpd_losses == 0:
                data["rs"].append(0.)
            else:
                data["rs"].append(float(firstpd_gains/firstpd_losses))

            x=1
            while x+pds+1 <=len(self.df.index):
                gain = (stats.mean(self.df.loc[x:x+pds-1][self.df["margin"]>0]) * pds)+data["avggain"][x-1]
                loss = (stats.mean(self.df.loc[x:x+pds-1][self.df["margin"]<0]) * pds)+data["avgloss"][x-1]
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
        home = self.df.loc[self.df["home_teamname"]==team]
        away = self.df.loc[self.df["away_teamname"]==team]


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


    def update(self):

        games = self.df.to_dict("index")
        for i in range(len(games)):
            new_game = self.adjust_ratings(ID=i, gameinfo=games[i])
            self.ratings_data.append(new_game)
            print("%s %% Completed." % round((i / len(games) * 100), 4))
        dfx = DataFrame(self.ratings_data)
        dfx.to_csv(self.datafile)
        print("Ratings Updated.")


