import sys
from pandas import read_csv
import os


def pyversion():
    return sys.version_info


def abbreviations(league, src):
    file = fullpath("../info/%s_abbreviations_%s.csv" % (league.lower(), src))

    rows = read_csv(file, index_col="abbrev", header=0)

    return rows

def fullpath(file):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), file))


