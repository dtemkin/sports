import os
from stats.utils import fullpath
import requests
from bs4 import BeautifulSoup as bsoup
from time import time
import datetime
import re
from pandas import DataFrame, read_csv, concat


class Data(object):

    def __init__(self, league):
        self.attendance_data = None
        self.games_data = None

        if league.lower() in ["nhl", "nba"]:
            self.league = league.lower()
        else:
            print("Error: League %s not supported. Must be 'nhl' or 'nba'")
        self.posthead = {
            "Host": "www.shrpsports.com",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
            }

        self.postdata = {
            "team1": "", "div1": "", "team2": "", "div2": "", "begdate": "all",
            "begmonth": "all", "begyear": "all", "enddate": "all", "endmonth": "all",
            "endyear": "all", "seastype": "reg", "location": "", "gametype": "", "serstand": "", "specmonth": "all",
            "specdate": "all", "month": "", "day": "", "last": "", "B1": "Submit"
            }

    def _abbreviations(self, team_name, src, year):
        file = fullpath("../info/%s_abbreviations_%s.csv" % (self.league, src))
        if os.path.isfile(file):

            df = read_csv(file)
            for i in range(len(df.index)):

                df_daterng = range(int(df.loc[i]["startdate"]), int(df.loc[i]["enddate"])+1)
                if int(year) in df_daterng and df.loc[i]["team_name"] == team_name:
                    return df.loc[i]
                elif int(year) in df_daterng and df.loc[i]["short_name"] == team_name:
                    return df.loc[i]
                elif int(year) in df_daterng and df.loc[i]["full_name"] == team_name:
                    return df.loc[i]
                else:
                    pass
        else:
            raise OSError("File %s_abbreviations_%s.csv is invalid. check league name parameter" % (self.league, src))
        
    @staticmethod
    def _get_existing(file):
        if os.path.isfile(file):
            df = read_csv(file)
            return df
        else:
            return None

    def games(self, start, end, **kwargs):
        save = kwargs.get("save", True)

        datafile = fullpath("../data/%s_anyVSany_games.csv" % self.league)
        df = self._get_existing(file=datafile)
        dfx, df0 = None, None
        if df is not None:
            if start in df["year"]:
                df0 = df[df["year"] >= start]
                if end in df0["year"]:
                    dfx = df0[df0["year"] <= end]
                    self.games_data = dfx
                else:
                    st, ed = df0["year"].loc[len(df["year"])], end

            else:
                if end in df["year"]:
                    df0 = df[df["year"] <= end]
                    st, ed = start, df0["year"].loc[0]
                else:
                    st, ed = start, end

        else:
            st, ed = start, end

        if self.games_data is None:
            self.posthead.update({"Referer": "http://www.shrpsports.com/%s/result.htm" % self.league})
            self.postdata.update({"begseas": st, "endseas": ed})
            url = "http://www.shrpsports.com/%s/result.php" % self.league

            postreq = requests.post(url=url, data=self.postdata, headers=self.posthead)
            soup = bsoup(postreq.text, "lxml")

            htmltable = soup.find("table", {"cellpadding": "5", "cellspacing": "0"})
            rows = htmltable.findAll("tr")
            datatable = []
            starttime = time()
            for r in range(len(rows)):

                cols = rows[r].findAll("td")
                season = cols[0].string.replace(" season:", "").strip()
                date = datetime.datetime.strptime(cols[1].string, "%a %b %d %Y")
                loca = cols[2].string.split(" ")[1]

                teams_scores = [c.strip().split(" ") for c in cols[3].get_text().split(", ")]

                if len(teams_scores) < 2:
                    pass
                else:
                    print("%s%% done. \r" % round((float(r/len(rows))*100), 4))
                    row = {}

                    team1 = teams_scores[0]
                    team2 = teams_scores[1]
                    team2s = team2[len(team2) - 1].split("\xa0")

                    team1_name = " ".join(team1[:len(team1) - 1])
                    team1_props = self._abbreviations(team_name=team1_name.strip(), src="shrpsports", year=date.year)

                    team2_name = " ".join(team2[:len(team2) - 1])
                    team2_props = self._abbreviations(team_name=team2_name.strip(), src="shrpsports", year=date.year)

                    if loca.strip() == team1_props["abbrev"]:
                        home_team = team1_name
                        home_score = int(team1[len(team1) - 1])
                        home_abbr = team1_props["abbrev"]
                        home_team_name = team1_props["team_name"]
                        home_city = team1_props["city"]
                        home_state = team1_props["state_iso"]
                        home_country = team1_props["country_iso"]

                        away_team = team2_name
                        away_score = int(team2s[0])
                        away_abbr = team2_props["abbrev"]
                        away_team_name = team2_props["team_name"]
                        away_city = team2_props["city"]
                        away_state = team2_props["state_iso"]
                        away_country = team2_props["country_iso"]

                        identinfo = {
                            "id": r, "home_shortname": home_team,
                            "away_shortname": away_team, "home_abbr": home_abbr,
                            "away_abbr": away_abbr, "home_teamname": home_team_name,
                            "away_teamname": away_team_name,
                            "home_city": home_city, "home_state": home_state,
                            "home_country": home_country, "away_city": away_city,
                            "away_state": away_state, "away_country": away_country,
                            "game_location": " ".join(team1[:len(team1) - 1]),
                            "season": season
                        }
                        gameinfo = {
                            "game_location": " ".join(team1[:len(team1) - 1]),
                            "season": season, "game_date": date.strftime("%Y-%m-%d"),
                            "year": date.year, "month": date.month, "day": date.day,
                            "dayofweek": date.strftime("%A")
                        }
                        scoreinfo = {
                            "home_score": home_score, "away_score": away_score,
                            "diff": home_score - away_score, "margin": abs(home_score - away_score),
                            "home_startelo": 1000, "away_startelo": 1000,
                            "home_endelo": 1000, "away_endelo": 1000,
                            "home_prob": .5, "away_prob": .5
                        }
                        row.update(identinfo)
                        if away_score == home_score:
                            row.update({"winner": "tie"})
                        else:
                            row.update({"winner": "home"})

                        row.update(gameinfo)
                        row.update(scoreinfo)

                    elif loca.strip() == team2_props["abbrev"]:
                        home_team = team2_name
                        home_score = int(team2s[0])
                        home_abbr = team2_props["abbrev"]
                        home_team_name = team2_props["team_name"]
                        home_city = team2_props["city"]
                        home_state = team2_props["state_iso"]
                        home_country = team2_props["country_iso"]

                        away_team = team1_name
                        away_score = int(team1[len(team1) - 1])
                        away_abbr = team1_props["abbrev"]
                        away_team_name = team1_props["team_name"]
                        away_city = team1_props["city"]
                        away_state = team1_props["state_iso"]
                        away_country = team1_props["country_iso"]

                        identinfo = {"id": r, "home_shortname": home_team,
                                     "away_shortname": away_team, "home_abbr": home_abbr,
                                     "away_abbr": away_abbr, "home_teamname": home_team_name,
                                     "away_teamname": away_team_name, "home_city": home_city,
                                     "home_state": home_state, "home_country": home_country,
                                     "away_city": away_city, "away_state": away_state,
                                     "away_country": away_country}
                        gameinfo = {"game_location": " ".join(team1[:len(team1) - 1]),
                                    "season": season, "game_date": date.strftime("%Y-%m-%d"),
                                    "year": date.year, "month": date.month, "day": date.day,
                                    "dayofweek": date.strftime("%A")}
                        scoreinfo = {"home_score": home_score, "away_score": away_score,
                                     "diff": home_score - away_score, "margin": abs(home_score - away_score),
                                     "home_startelo": 1000, "away_startelo": 1000,
                                     "home_endelo": 1000, "away_endelo": 1000,
                                     "home_prob": .5, "away_prob": .5}
                        row.update(identinfo)
                        if away_score == home_score:
                            row.update({"winner": "tie"})
                        else:
                            row.update({"winner": "away"})
                        row.update(gameinfo)
                        row.update(scoreinfo)
                    else:
                        print("Invalid abbreviation: %s. " % loca.strip())
                    if len(team2s) > 1:
                        numots = 0
                        n = re.search('([0-9])', team2s[1])
                        if n is None:
                            numots += 1
                        else:
                            numots += int(n.group(0))
                        row.update({"overtime": True, "overtime_count": numots})
                    else:
                        row.update({"overtime": False, "overtime_count": 0})
                    datatable.append(row)

            df1 = DataFrame(datatable)
            print("runtime %s seconds" % round(time() - starttime, 2))
            if df0 is None:
                dfx = df1
                if save is True:
                    with open(datafile, mode="w") as f:
                        df1.to_csv(f, header=df1.columns)
                        f.close()
                        print("Saved New File.")
            else:
                dfx = DataFrame(concat([df0, df1]))
                if save is True:
                    with open(datafile, mode="a") as f:
                        dfx.index = [i for i in range(0, len(dfx["year"]))]
                        dfx.to_csv(f, header=dfx.columns)
                        f.close()
                        print("Saved new data to file")
            self.games_data = dfx

    @staticmethod
    def _retype(row):
        newrow = []
        for x in row:

            if x.find(".", 0, len(x)) > -1:
                newrow.append(float(x)/100)
            elif x.find(",", 0, len(x)) > -1:
                i = x.replace(",", "")
                newrow.append(int(i))
            elif any([s.isalpha() for s in x]) is True:
                newrow.append(str(x))
            elif x == "--" or x == "-":
                newrow.append(0)
            else:
                newrow.append(int(x))
        return newrow

    def attendance(self, start, end):

        baseurl = "http://www.espn.com/%s/attendance/_/year" % self.league.lower()
        if int(start) <= 1993 and self.league.lower() in ["nhl", "nba"]:
            print("Warning: 1994 is earliest available year resetting start to 1994.")
            start = 1994

        elif int(start) < 2000 and self.league.lower() == "mlb":
            print("Warning: 2000 is earliest available year resetting start to 2000.")
            start = 2000
        elif int(start) < 2006 and self.league.lower() == "nfl":
            print("Warning: Data before 2006 is woefully incomplete, setting start_year to 2006")
            start = 2006

        data = []
        for i in range(int(start), int(end) + 1):
            url = "/".join([baseurl, str(i)])
            req = requests.get(url)
            soup = bsoup(req.content, "html5lib")

            table = soup.find("table", {"cellpadding": "3", "cellspacing": "1", "class": "tablehead"})
            rows = table.findAll("tr")
            for row in rows[2:]:
                # In the home column, the average represents an estimate
                # of the capacity the stadium can hold.
                # The percentage is how full the stadium was
                # during a specific teams games.
                # The same is applied to the Road
                # column when that team is traveling.
                # The last column is the overall average of
                # the previous two columns combined.

                itemlst = [item.string for item in row.findAll("td")]
                itemdict = dict(map(lambda z, y: (z, y),
                                    ["rank", "team_name", "home_games", "total_home_attend",
                                     "avg_home_attend", "pctcap_home_attend", "total_away_attend",
                                     "avg_away_attend", "pctcap_away_attend", "total_overall_attend",
                                     "avg_overall_attend", "pctcap_overall_attend"],
                                    self._retype(itemlst)))
                itemdict.update({"year": i})
                data.append(itemdict)

        df = DataFrame(data=data)
        cap = []
        for x in df.index:
            est = df["avg_home_attend"].loc[x]/df["pctcap_home_attend"].loc[x]
            cap.append(est)

        df.insert(len(df.columns), "est_cap_home", cap)
        self.attendance_data = df

