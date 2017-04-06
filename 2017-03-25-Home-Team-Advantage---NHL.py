
# coding: utf-8

# ### Home Team Advantage - How does your NBA team do when your there?
# 
# 
# 
# Often credit for "Home Team Advantage" in sports is, in large part, given to the fervor of the fans. But whether it is the roar of the crowd, the familiarity of the location, the jet-lag of the away team, or blind luck I attempt to find out which teams in the National Basketball Association have the best record at home as well as which teams have fewer "weather fans" or in other words, the teams that retain their at home win percentage after adjusting for the number of years in the league.
# 
# 

# In[8]:

import requests
from bs4 import BeautifulSoup as bsoup
import datetime
import re
from pandas import DataFrame, read_csv
from time import sleep, time
import statistics as stats
from csv import DictReader
import os
from urllib import request

from plotly import tools as plttools
from plotly.offline import plot, iplot, init_notebook_mode
import plotly.graph_objs as graph

global graph, plttools, nba_table, start_year, end_year, stats, os,sleep, \
       time, re, datetime, league, bsoup, requests, DataFrame, read_csv, \
       DictReader, baseurl,posthead, postdata, _data, group, urllib

leagues = ["nhl","mlb","nfl","collbask","cfl","worldcup","arena","collfoot","aba","wha","misc"]
league = "nhl"


baseurl = "http://www.shrpsports.com/%s/result.php" % league
start_year = 1980
end_year  = 2017


posthead = {"Host": "www.shrpsports.com",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Referer": "http://www.shrpsports.com/%s/result.htm" % league,
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"}

postdata = {"team1":"", "div1":"","team2":"", "div2":"", "begseas":str(start_year),"begdate":"all",
            "begmonth":"all","begyear":"all","endseas":str(end_year),"enddate":"all","endmonth":"all",
            "endyear":"all","seastype":"reg","location":"","gametype":"","serstand":"","specmonth":"all",
            "specdate":"all","month":"","day":"","last":"","B1":"Submit"}



# In[9]:

abbrev_file_header = ["short_name","abbrev","full_name","startdate","enddate"]
abbrfile = request.urlopen("https://cdn.rawgit.com/dtemkin/blog/66b12f0d/data/nba_abbreviations.csv")

# outfile = "https://cdn.rawgit.com/dtemkin/blog/66b12f0d/data/nba_data.csv"
abbrev_readr = DictReader(abbrfile, fieldnames=abbrev_file_header)


resp = request.urlopen(outfile)
_data = read_csv(resp)



def get_table():
    postreq = requests.post(url=url, data=postdata, headers=posthead)
    soup = bsoup(postreq.text, "lxml")
    
    htmltable = soup.find("table",{"cellpadding":"5", "cellspacing":"0"})
    rows = html.findAll("tr")
    datatable = []
    starttime = time()
    abbrevs = dict([(r["abbrev"].strip(), r["short_name"].strip()), ("city", r["city"]),
                    ("state",r["state_ISO3166"]), ("country",r["country_ISO3166"]) for r in readr])
    
    for r in range(len(rows)):
        
        cols = rows[r].findAll("td")
        season = cols[0].string.replace(" season:", "").strip()
        date = datetime.datetime.strptime(cols[1].string, "%a %b %d %Y")
        loc = cols[2].string.split(" ")[1]
        # abbr = re.search("(?<=;team=).*?&", str(cols[3]))
 
        teams_scores = [c.strip().split(" ") for c in cols[3].get_text().split(", ")]
        
        if len(teams_scores) < 2:
            pass
        else:
            # print("%s%% done. \r" % round((float(r/len(rows))*100), 4))
            
            name = abbrevs[loc.strip()]

            team1 = teams_scores[0]
            team2 = teams_scores[1]
            team2s = team2[len(team2)-1].split("\xa0")
            

            team1_name = " ".join(team1[:len(team1)-1])
            team2_name = " ".join(team2[:len(team2)-1])

            if team1_name.strip() == name:
                home_team = team1_name
                home_score = int(team1[len(team1)-1])
                
                away_team = team2_name
                away_score = int(team2s[0])
                winner = "home"
                diff = home_score - away_score
                
                if away_score == home_score:
                    winner = "tie"
                    diff = 0
                else:
                    pass

            elif team2_name == name:
                home_team = team2_name
                home_score = int(team2s[0])
                
                away_team = team1_name
                away_score = int(team1[len(team1)-1])
                winner = "away"
                diff = away_score - home_score
                if away_score == home_score:
                    winner = "tie"
                    diff = 0
                else:
                    pass

            if len(team2s) > 1:
                ot = True
                numots = 0
                n = re.search('([0-9])', team2s[1])
                if n is None:
                    numots += 1
                else:
                    numots += int(n.group(0))
            else:
                ot = False
                numots = 0
                 
            row = {"season":season, "game_date":date.strftime("%Y-%m-%d"),
                   "year":date.year, "month":date.month, "day":date.day,
                   "dayofweek": date.strftime("%A"), "loc_abbr":loc,
                   "location":" ".join(team1[:len(team1)-1]), 
                   "winner":winner, "home_score":home_score,
                   "home_team":home_team, "away_team":away_team,
                   "away_score":away_score, "overtime":ot,
                   "overtime_count":numots,"margin":diff}
            datatable.append(row)

    df = DataFrame(datatable)
    print("runtime %s seconds" % round(time()-starttime, 2))
    df.to_csv(outfile, header=df.columns)
    
    return df


# In[12]:
##
##outfile = "https://cdn.rawgit.com/dtemkin/blog/66b12f0d/data/nba_data.csv"
##resp = request.urlopen(outfile)
##_data = read_csv(resp)

_data = get_table()


# In[13]:

trace = graph.Scattergl(x=_data["home_score"], y=_data["away_score"], mode="markers",
                        marker=dict(size="6", color=_data["margin"], colorscale='Viridis',
                                    showscale=True),
                        text=_data["year"])

layout= graph.Layout(
    title= 'NBA Game Scores %s - Present' % start_year,
    hovermode= 'closest',
    xaxis= dict(
        title= 'Home Team Score',
    ),
    yaxis=dict(
        title= 'Away Team Score',
    ),
)
fig = graph.Figure(data=[trace], layout=layout)
iplot(fig, filename='NBA Game Scores %s - Present' % start_year)


# 
# The chart above shows every NBA game for the past 37 years and is colored depending on the difference in score with the dark blue (purple) indicating a close score and the more yellow/greenish dots indicating games where one team blew out the other. It is interesting to note that the games with the largest margin occured when the home team won. Also we can even see the highest scoring game in the sample which was 171 to 166 from a game in 1982.
# 
# 
# It should be noted that due to the limited number of potential variations in score there were likely points duplicated or that are being covered by more recent occurences.
# 
# 

# In[159]:

group = _data.groupby(["year"])

group_means = [stats.harmonic_mean(g[1]["margin"]) for g in list(group)]
group_median = [stats.median(g[1]["margin"]) for g in list(group)]


trace = graph.Scatter(x=[g[0] for g in list(group)], y=group_means,
                      mode="line", name="Harm. Mean")
trace2 = graph.Scatter(x=[g[0] for g in list(group)], y=group_median,
                       mode="line", name="Median", marker=dict(color="#454a6d"))

layout = graph.Layout(title="Average Winning Margin YoY", xaxis=dict(title="Year"), yaxis=dict(title="Win Margin"))
fig = graph.Figure(data=[trace, trace2], layout=layout)
iplot(fig)



# 
# 
# This line chart is interesting because as we can see there despite the introduction of new teams, better players, equipment and so on that the average game is won by the same amount of points today as it was 37 years ago which is fascinating. What I would have expected is that the increase in the number of games per year which is simply due to the number of teams increasing, would have caused the score differential to trend towards a more normal distribution. But apparently it is as normal as it is going to get.
# 
# 

# In[155]:

wins = [(g[0], sum(g[1]["winner"]=="home"), sum(g[1]["winner"]=="away"), len(g[1]["winner"]))  for g in list(group)]

trace = graph.Bar(x=[i[0] for i in wins], y=[i[1] for i in wins], 
                  name="# Win @ Home", hoverinfo="x+y", text="Home", 
                  marker=dict(color="#a0bca5"))
trace2 = graph.Bar(x=[i[0] for i in wins], y=[i[2] for i in wins], 
                   name="# Lose @ Home", hoverinfo="x+y", text="Away", 
                   marker=dict(color="#a0addb"))

trace_pct = graph.Scatter(x=[i[0] for i in wins], y=[round(float(i[1]/i[3]), 2) for i in wins], 
                          text=[" ".join([str(round(float(i[1]/i[3])*100, 2)), "%"]) for i in wins],
                          name="% Win @ Home", yaxis="y2", hoverinfo="text", mode="lines", 
                          line=dict(color="#3d684e"))
trace2_pct = graph.Scatter(x=[i[0] for i in wins], y=[round(float(i[2]/i[3]), 2) for i in wins], 
                           text=[" ".join([str(round(float(i[2]/i[3])*100, 2)), "%"]) for i in wins],
                           name="% Lose @ Home", yaxis="y2", hoverinfo="text", mode="lines", 
                           line=dict(color="#2c3a68"))


layout = graph.Layout(
    title='Home Court Advantage',
    yaxis=dict(
        title='# of Games Won'
    ),
    yaxis2=dict(
        title='% of Total Games Won',
        overlaying='y',
        side='right'
    )
)

data = [trace, trace2, trace_pct, trace2_pct]
fig = graph.Figure(data=data, layout=layout)
iplot(fig)


# 
# Now, on to the home court advantage. As you can see home teams do have a greater win percentage over away teams and though the difference is shrinking slightly there is still about a 60% percent chance that any team when at home will win the game. This pattern is consistent over time even when the number of games increased by a couple hundred from the 1980s to now. 
# 

# In[236]:

homegroup = _data.groupby(["home_team"])

homewins = [(g[0], g[1]["year"].unique(), sum(g[1]["winner"]=="home"), sum(g[1]["winner"]=="away"), 
             len(g[1]["winner"]), len(g[1]["year"].unique()),
             float(sum(g[1]["winner"]=="home")/len(g[1]["winner"])), 
             float(sum(g[1]["winner"]=="away")/len(g[1]["winner"])),
             float(sum(g[1]["winner"]=="home")/len(g[1]["winner"]))/len(g[1]["year"].unique()), 
             float(sum(g[1]["winner"]=="away")/len(g[1]["winner"]))/len(g[1]["year"].unique()))  for g in list(homegroup)]

homedf = DataFrame(homewins, columns=["Home_Team","Years","Num_Wins_Home","Num_Losses_Home",
                                      "Num_Games", "NumYears", "Pct_Home_Losses",
                                      "Pct_Home_Wins","AdjPct_Home_Wins", "AdjPct_Home_Losses"])
homedf = homedf.sort_values(by=["Pct_Home_Wins"], ascending=False)
homedf.index = [x for x in range(len(homedf.index))]
print(homedf.head())

trace1 = graph.Scattergl(x=[i for i in homedf["Num_Wins_Home"].head(10)], 
                         y=[j for j in homedf["Pct_Home_Wins"].head(10)], name="Top 10",
                         mode="markers", text=[g for g in homedf["Home_Team"].head(10)], hoverinfo="x+text",
                         marker=dict(size=[h for h in homedf["NumYears"].head(10)]))
trace2 = graph.Scattergl(x=[i for i in homedf["Num_Wins_Home"].tail(10)], 
                         y=[j for j in homedf["Pct_Home_Wins"].tail(10)],  name="Bottom 10",
                         mode="markers", text=[g for g in homedf["Home_Team"].tail(10)], hoverinfo="x+text",
                         marker=dict(size=[h for h in homedf["NumYears"].tail(10)], color="#fc8c7b"))

homedf = homedf.sort_values(by=["AdjPct_Home_Wins"], ascending=False)
homedf.index = [x for x in range(len(homedf.index))]

trace3 = graph.Scattergl(x=[i for i in homedf["Num_Wins_Home"].head(10)], 
                         y=[j for j in homedf["AdjPct_Home_Wins"].head(10)], name="Top 10",
                         mode="markers", text=[g for g in homedf["Home_Team"].head(10)], hoverinfo="x+text",
                         marker=dict(size=[h for h in homedf["NumYears"].head(10)]))

trace4 = graph.Scattergl(x=[i for i in homedf["Num_Wins_Home"].tail(10)], 
                         y=[j for j in homedf["AdjPct_Home_Wins"].tail(10)], name="Bottom 10",
                         mode="markers", text=[g for g in homedf["Home_Team"].tail(10)], hoverinfo="x+text",
                         marker=dict(size=[h for h in homedf["NumYears"].tail(10)], color="#fc8c7b"))

layout1= graph.Layout(
    title= 'UnAdjusted Win Percent - Top 10 Winners & Losers',
    hovermode= 'closest',
    xaxis= dict(
        title= 'Number of Wins @ Home',
    ),
    yaxis=dict(
        title= 'Percent of Wins @ Home',
    ),
)

layout2= graph.Layout(
    title= 'Adjusted Win Percent - Top 10 Winners & Losers',
    hovermode= 'closest',
    xaxis= dict(
        title= 'Number of Wins @ Home',
    ),
    yaxis=dict(
        title= 'Adjusted Win Percent of Wins @ Home',
    ),
)


fig1 = graph.Figure(data=[trace1, trace2], layout=layout1)
fig2 = graph.Figure(data=[trace3, trace4], layout=layout2)
iplot(fig1, filename)
iplot(fig2)


# In the above graphs the size of each point corresponds to the number of years each team has been active in the league. In the "UnAdjusted Win Percent - Top 10 Winners & Losers" plot, the win percentage is taken regardless of the number of years the team has been around. As such, I would argue the teams within the center are the ones with the most consistent win percentage at home and subsequently are the ones wiht the best fans. For the first plot these are Sacramento, LA Clippers and New Jersey.
# 
# The adjusted plot containes the top 10 and bottom 10 teams by win percentage after controlling for number of years in the league. This control had a very polarizing effect. There were very few in the middle and those with the lowest "adjusted win percent" have been around for longer. Though this is to be expected, the more years a team plays the greater variance we expect in their, though in this case we could use it to see which teams have a greater number of "fair weather fans" who don't stick around for more than a year or so. Ironically, the LA Clippers which were among the best performing on the unadjusted plot are now among the bottom 10. 
# 
# So, check it out and see if the team whose colors you bleed season after season is better or "worse" when you are at the games.
