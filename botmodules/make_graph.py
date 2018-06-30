#!/usr/bin/python3.6

import matplotlib #
matplotlib.use('Agg') #turn this off if you want to show the plot

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

from sqlalchemy import func, text, cast, Time, and_, distinct, case, select

from botmodules.sqlconnect import make_connection, Submissions, Comments
from botmodules.upload_image import upload_image
import datetime


def time_graph(author, table, hash, session, date):
    """creates the time graph for given user
    Uploads the picture and returns the image link"""

    # data for activity per hour in a day


    result_day = session.query(func.date_part('hour', table.datum).label("time"), func.count(table.id).label("count"))\
        .filter(and_(table.autor == author, table.datum >= date))\
        .group_by(func.date_part('hour', table.datum))

    times_day = []
    counts_day = []

    for item in result_day:

        times_day.append(datetime.datetime.combine(datetime.date(2000, 1, 1), datetime.time(int(item.time), 0, 0))) #200,1,1 is a random day. won't be show in the end
        counts_day.append(item.count)

    # data for activity graph all time


    times_all = []
    counts_all = []

    result_all_time = session.query(func.date_trunc('week', table.datum).label("time"), func.count(table.id).label("count"))\
        .filter(and_(table.autor == author, table.datum >= date))\
        .group_by(func.date_trunc('week', table.datum))

    for item in result_all_time:

        times_all.append(item.time)
        counts_all.append(item.count)


    # Matplotlib part

    plt.style.use('ggplot')
    plt.rcParams.update({'figure.autolayout': True})

    dates = mdates.DateFormatter('%H:%M')
    weeks = mdates.MonthLocator()


    plt1 = plt.subplot(2, 1, 1)
    plt1.set_title("Average daily activity")
    plt1.bar(times_day, counts_day, 0.03)
    plt1.xaxis.set_tick_params(labelrotation=55)
    plt1.xaxis.set_major_formatter(dates)
    plt1.set_xticks(times_day)
    plt1.set_ylabel('Number of comments\n per hour')

    plt2 = plt.subplot(2,1,2)
    plt2.set_title("Activity progress")
    plt2.plot(times_all, counts_all)
    plt2.xaxis.set_tick_params(labelrotation=55)
    plt2.xaxis.set_minor_locator(weeks)
    plt2.set_ylabel('Number of comments\n per week')


    plt.savefig("output/time_graph.png")
    return(upload_image("output/time_graph.png", "T"+hash))


def flair_graph(author, table, hash, session):
    """creates the flair graph for given user
    Uploads the picture and returns the image link"""

    if table == Comments:
        result = session.query(func.count(Comments.id).label("count"), Submissions.flair)\
            .join(Submissions, Submissions.postid == Comments.postid)\
            .group_by(Submissions.flair)\
            .filter(Comments.autor == author)\
            .order_by(func.count(Comments.id).desc())

        title = 'Number of comments'

    if table == Submissions:
        result = session.query(func.count(Submissions.id).label("count"), Submissions.flair)\
            .group_by(Submissions.flair)\
            .filter(Submissions.autor == author)\
            .order_by(func.count(Submissions.id).desc())

        title = 'Number of Submissions'


    flairs = []
    counts = []

    for item in result:
        if item.flair == None:
            flair = 'None'
        else:
            flair = item.flair
        flairs.append(flair)
        counts.append(item.count)

    width = 0.8

    plt.style.use('ggplot')
    plt.rcParams.update({'figure.autolayout': True})
    plt.figure(figsize=(10, 6))

    ax = plt.subplot()

    ax.set_ylabel('Number of comments')
    ax.set_title(title)
    ax.bar(flairs, counts, width)
    ax.xaxis.set_tick_params(rotation=40, labelsize=9)
    ax.set_xticklabels(flairs, ha='right')

    #plt.show()

    plt.savefig("output/flair_graph.png")
    return(upload_image("output/flair_graph.png", "F"+hash))


def total_distribution_graph(table, time, session):

    result = session.query(table.autor.label("author"), func.count(table.id).label("count"), func.sum(table.score).label("score"))\
        .filter(table.autor != '[deleted]')\
        .group_by(table.autor)\
        .order_by(func.sum(table.score).desc())\
        .having(func.count(table.id) >= 100)\
        .limit(10000)

    authors = []
    counts  = []
    scores  = []

    for item in result:
        authors.append(item.author)
        counts.append(item.count)
        scores.append(item.score/item.count)


    plt.figure(figsize=(10, 6))
    plt.scatter(counts,scores, s=1, alpha=0.7, c='red')
    plt.xlabel('Number of comments')
    plt.ylabel('Sum o score')
    plt.xscale('log')
    #plt.yscale('log')
    plt.show()
    return(plt)

class Flair_lists(object):
    """creates the score lists for each flair"""

    result_dict = {}
    marked = {}

    def __init__(self, flair, score, datum, unique_flairs):
        self.flair = flair
        self.score = score
        self.date = datum
        self.uniques = unique_flairs

    def add_value(self, value, flair):
        """adds values to dictionary"""

        try:
            current_list = self.result_dict[flair]
            current_list.append(value)
            self.result_dict.update({flair: current_list})
        except KeyError:
            current_list = [value]
            self.result_dict.update({flair: current_list})

        return(self.result_dict)


    def mark(self):
        """mark value as added for that day"""

        try:
            current_list = self.marked[self.date]
            current_list.append(self.flair)
            self.marked.update({self.date:current_list})
        except KeyError:
            current_list = [self.flair]
            self.marked.update({self.date:current_list})


    def check_mark(self, old_date, last_date):
        """check if flair is marked for that day, if not add zero to list"""

        if old_date != self.date: #new date, check which flairs are not yet marked
            for flair in self.uniques:
                if not flair in self.marked[old_date]: #if true flair is not in marked flairs for time in old_date
                    self.add_value(0, flair)

        if last_date == "last":
            for flair in self.uniques:
                if not flair in self.marked[self.date]: #if true flair is not in marked flairs for time in old_date
                    self.add_value(0, flair)


class Total_time_graph(object):

    color1 = 'red'
    color2 = 'blue'

    def __init__(self, author, table, hash, date):
        self.author = author
        self.table = table
        self.hash = hash
        self.date = date
    
    '''The graph for the multiple overview stats called by stats de general'''

    def format_plot(self, plot, data, data2, title):

        plot.plot(data, color=self.color1)
        plot.set_title(title)
        plot.set_ylabel(data.name, color=self.color1)
        plot.tick_params('y', colors=self.color1)
        plot.xaxis.set_tick_params(labelrotation=45)

        ax2 = plot.twinx()  # for second y axis on same plot
        ax2.plot(data2, color=self.color2)
        ax2.tick_params(axis='y', colors=self.color2)
        ax2.set_ylabel(data2.name, color=self.color2)


    def make_graph(self, session):

        subs_query = session.query(func.count(Submissions.score).label("Posts count"), func.sum(Submissions.score).label("Posts score"),\
                                   func.date_trunc('week', Submissions.datum).label("date")) \
            .group_by(func.date_trunc('week', Submissions.datum)) \
            .having(func.date_trunc('week', Submissions.datum) > self.date)\
            .statement

        comments_query = session.query(func.count(Comments.score).label("Comments count"), func.sum(Comments.score).label("Comments score"),\
                                   func.date_trunc('week', Comments.datum).label("date")) \
            .group_by(func.date_trunc('week', Comments.datum)) \
            .having(func.date_trunc('week', Comments.datum) > self.date)\
            .statement

        df1 = pd.read_sql(comments_query, session.bind, index_col=['date'])
        df2 = pd.read_sql(subs_query, session.bind, index_col=['date'])

        df = pd.concat([df1,df2], axis=1) #axis = 1 because of same index
        df = df.resample('3T')
        df = df.interpolate(method='cubic', limit_direction='both')

        plt.style.use('ggplot')
        plt.rcParams.update({'font.size': 8})
        fig, (axes) = plt.subplots(2, 1) #creates for plots, i.e. one plot is axes[0, 0}

        self.format_plot(axes[0], df["Posts count"], df["Posts score"], "Posts")
        self.format_plot(axes[1], df["Comments count"], df["Comments score"], "Comments")


        fig.tight_layout()
        #plt.show()

        plt.savefig("output/total_time_graph.png")
        plt.close()
        return (upload_image("output/total_time_graph.png", "T" + self.hash))

def total_flair_graph(author, table, date, hash, session):

    scope = 'week'
    if table == Submissions:
        metric = 1
        ylabel = "Number of submissions"
    else:
        metric = Submissions.num_komments
        ylabel = "Number of comments"

    group1 = ['Humor/MaiMai', 'Humor', 'MaiMai', 'Humor/MaiMai ']
    group2 = ['Interessant', 'Medien', 'Boulevard', 'Gesellschaft']
    group3 = ['Frage/Diskussion', 'Dienstmeldung', 'TIRADE', 'Meta/Reddit']
    group4 = ['Politik', 'Nachrichten', 'Nachrichten DE', 'Kriminalität', 'Flüchtlinge', 'US-Politik',
              'Nachrichten Europa',
              'Terrorismus', 'Nachrichten Welt', 'Nachrichten A', 'Nachrichten CH', 'Nachrichten Deutschland',
              'Nachrichten Österreich']
    group5 = ['Geschichte', 'Wissenschaft&Technik', 'Bildung', 'Umwelt', 'Feuilleton/Kultur', 'Musik', 'Wirtschaft']
    group6 = ['Essen&Trinken', 'Sport', 'Zocken']
    group7 = []  # all other flairs

    start_color_range = 0.6
    stop_color_range = 0.96

    cmap_blue = plt.get_cmap('Blues')(np.linspace(start_color_range, stop_color_range, (len(group1))))
    cmap_green = plt.get_cmap('Greens')(np.linspace(start_color_range, stop_color_range, (len(group2))))
    cmap_red = plt.get_cmap('Reds')(np.linspace(start_color_range, stop_color_range, (len(group3))))
    cmap_purple = plt.get_cmap('Purples')(np.linspace(start_color_range, stop_color_range, (len(group4))))
    cmap_orange = plt.get_cmap('Oranges')(np.linspace(start_color_range, stop_color_range, (len(group5))))
    cmap_grey = plt.get_cmap('Greys')(np.linspace(start_color_range, stop_color_range, (len(group6))))

    group1 = {'members': group1, 'color': cmap_blue}
    group2 = {'members': group2, 'color': cmap_green}
    group3 = {'members': group3, 'color': cmap_red}
    group4 = {'members': group4, 'color': cmap_purple}
    group5 = {'members': group5, 'color': cmap_orange}
    group6 = {'members': group6, 'color': cmap_grey}
    groups = [group1, group2, group3, group4, group5, group6]
    allgroups = []
    for group in groups:
        allgroups = allgroups + group['members']

    flairs = result = session.query(distinct(Submissions.flair).label("flair"), func.count(Submissions.id)) \
        .filter(Submissions.flair != None) \
        .group_by(Submissions.flair) \
        .order_by(func.count(Submissions.id).desc()) \
        .limit(35).all()

    q = [func.date_trunc(scope, Submissions.datum).label("date")]
    for flair in flairs:
        flair_modified = str(flair.flair)
        q.append(func.sum(case([(Submissions.flair == flair_modified, metric)], else_=0)).label(flair_modified))

    s = select(q)
    s = s.where(and_(Submissions.datum >= date, Submissions.flair != None))
    s = s.group_by(func.date_trunc(scope, Submissions.datum))
    s = s.order_by(func.date_trunc(scope, Submissions.datum))

    df = pd.read_sql(s, session.bind, index_col=['date'])

    colormaps = {}
    cols = []
    i = 0
    for group in groups:
        for column in list(df.columns.values):
            if column in group['members']:
                cols.append(column)
                try:
                    length = len(colormaps[i])
                except:
                    length = 0
                try:
                    current = colormaps[i]
                except:
                    current = []

                current.append(group['color'][length])
                colormaps.update({i: current})
            if column not in allgroups:
                group7.append(column)

        i += 1

    group7 = list(set(group7))
    cols += group7
    colormap = []
    for keys, value in colormaps.items():
        colormap = colormap + value

    cmap_grey2 = plt.get_cmap('cool')(np.linspace(start_color_range, stop_color_range, (len(group7))))
    i = 0
    for i in range(i, len(group7)):
        colormap.append(cmap_grey2[i])

    df = df.reindex(columns=cols)
    df = df.resample('12H')
    df = df.interpolate(method='cubic', limit_direction='both')

    plt.style.use('ggplot')
    plt.figure(figsize=(15, 8))
    plt.stackplot(df.index, df.values.T, labels=df.columns,
                  colors=colormap)  # .T transposes the values from rows to for each to columns see https://stackoverflow.com/questions/51076766/pandas-and-matplotlib-cant-get-the-stackplot-to-work-with-using-matplotlib-on/51077068#51077068
    plt.legend(loc=2, prop={'size': 10}, ncol=6)
    plt.title('Progression of flairs')
    plt.ylabel(ylabel)
    plt.ylim(0)
    plt.tight_layout()


    plt.savefig("output/total_flair_graph.png")
    return (upload_image("output/total_flair_graph.png", "F" + hash))