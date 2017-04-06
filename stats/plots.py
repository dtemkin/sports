import seaborn as sns
import matplotlib.pyplot as mplt

from plotly import tools as plttools
from plotly.offline import plot as plotlyplt
import plotly.figure_factory as figbuild
import plotly.graph_objs as graph

from stats import shrpsports
from stats import espn

from stats.utils import fullpath

try:
    from statistics import harmonic_mean as hmean
    from statistics import mean, median
except ImportError:
    from scipy.stats import hmean, mean, median


# NBA Game Scores
league = "nba"
start, end = 1994, 2017

scores = shrpsports.Data(league=league, start_year=start, end_year=end)
func = scores.gamestats()
scores.main(functype="gamestats", fn=str(func))
scores_df = scores.dataframe

attends = espn.Data(league=league, start_year=start, end_year=end)

func = attends.attendance()
attends.main(functype="attendance", fn=str(func))
attends_df = attends.dataframe

class ScorePlots(object):

    def __init__(self, dataframe):
        self.df = dataframe
        self.group = dataframe.groupby(["year"])

    def ScoresScatter(self, filename=fullpath("../plots/ScoresScatter.html")):
        trace = graph.Scattergl(x=self.df["home_score"], y=self.df["away_score"], mode="markers",
                                marker=dict(size="6", color=[abs(m) for m in self.df["margin"]], colorscale='Viridis',
                                            showscale=True),
                                text=self.df["year"])
        layout= graph.Layout(
            title= '%s Game Scores %s - Present' % (league.upper(), start),
            hovermode= 'closest',
            xaxis= dict(
                title= 'Home Team Score',
            ),
            yaxis=dict(
                title= 'Away Team Score',
            ),
        )
        fig = graph.Figure(data=[trace], layout=layout)
        plotlyplt(fig, filename=filename)

    def HistPlotGrid(self, filename=fullpath("../plots/HistPlotGrid.png"), show=False):

        sns.set(style="darkgrid")
        grid = sns.FacetGrid(self.df, col="year", col_wrap=4)
        grid.map(mplt.hist, "margin", color=".3")
        sns.plt.savefig(filename)
        if show is True:
            sns.plt.show()
        else:
            pass

    def AvgMargin(self, filename=fullpath("../plots/AvgScoresMargin.html")):
        group_means = [(mean(g[1]["margin"]), hmean(g[1]["margin"]),
                        mean(g[1]["margin"]) - hmean(g[1]["margin"])) for g in list(self.group)]
        n = 0
        for i in group_means:
            if abs(i[2]) > .5:
                n += 1
            else:
                pass

        if float(n) > .30 * len([g[0] for g in list(self.group)]):
            trace = graph.Scatter(x=[g[0] for g in list(self.group)], y=[m[1] for m in group_means],
                                  mode="line", name="Harm. Mean")
        else:

            trace = graph.Scatter(x=[g[0] for g in list(self.group)], y=[m[0] for m in group_means],
                                  mode="line", name="Mean", marker=dict(color="#454a6d"))

        layout = graph.Layout(title="Average Winning Margin YoY", xaxis=dict(title="Year"),
                              yaxis=dict(title="Win Margin"))
        fig = graph.Figure(data=[trace], layout=layout)
        plotlyplt(fig, filename=filename)

    def HomeCourtAdv(self, filename=fullpath("../plots/")):
        wins = [(g[0], sum(g[1]["winner"] == "home"), sum(g[1]["winner"] == "away"), len(g[1]["winner"])) for g in list(self.group)]

        trace = graph.Bar(x=[i[0] for i in wins], y=[i[1] for i in wins],
                          name="# Win @ Home", hoverinfo="x+y", text="Home",
                          marker=dict(color="#667292"))
        trace2 = graph.Bar(x=[i[0] for i in wins], y=[i[2] for i in wins],
                           name="# Lose @ Home", hoverinfo="x+y", text="Away",
                           marker=dict(color="#e06377"))

        trace_pct = graph.Scatter(x=[i[0] for i in wins], y=[round(float(i[1] / i[3]), 2) for i in wins],
                                  text=[" ".join([str(round(float(i[1] / i[3]) * 100, 2)), "%"]) for i in wins],
                                  name="% Win @ Home", hoverinfo="text", mode="lines",
                                  line=dict(color="#213C86", shape="spline", smoothing=".7"))
        trace2_pct = graph.Scatter(x=[i[0] for i in wins], y=[round(float(i[2] / i[3]), 2) for i in wins],
                                   text=[" ".join([str(round(float(i[2] / i[3]) * 100, 2)), "%"]) for i in wins],
                                   name="% Lose @ Home", hoverinfo="text", mode="lines",
                                   fill="tonexty", line=dict(color="#213C86", shape="spline", smoothing="0.7"))

        layout = graph.Layout(
                title='Home Court Advantage',
                yaxis=dict(
                        title='# of Games Won'
                )
        )
        layout0 = graph.Layout(
                yaxis=dict(
                        title='% of Total Games Won',
                        overlaying='y',
                        side='right'),
        )

        data = [trace, trace2]
        data0 = [trace_pct, trace2_pct]
        fig0 = graph.Figure(data=data0, layout=layout0)
        fig = graph.Figure(data=data, layout=layout)
        plotlyplt(fig, filename=filename+"HomeTeam-UnAdjusted.html")
        plotlyplt(fig0, filename=filename+"HomeTeam-Adjusted.html")


    def All(self):
        self.ScoresScatter()
        self.HistPlotGrid()
        self.AvgMargin()
        self.HomeCourtAdv()

plot = ScorePlots(dataframe=scores.dataframe)
plot.All()