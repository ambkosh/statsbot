#!/usr/bin/python3.6

import matplotlib #
matplotlib.use('Agg') #turn this off if you want to show the plot

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

from sqlalchemy import func, text, cast, Time, and_

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


def total_flair_graph(author, table, date, hash, session):

    column = Submissions.score
    title = "Flairs by number of submissions"
    label = "Numer of submissions"
    timeframe = 'week'

    group1 = ['Humor/MaiMai', 'Humor', 'MaiMai', 'Humor/MaiMai ']
    group2 = ['Interessant', 'Medien', 'Boulevard', 'Gesellschaft']
    group3 = ['Frage/Diskussion', 'Dienstmeldung', 'TIRADE', 'Meta/Reddit']
    group4 = ['Politik', 'Nachrichten', 'Nachrichten DE', 'Kriminalität', 'Flüchtlinge', 'US-Politik', 'Nachrichten Europa', 'Terrorismus', 'Nachrichten Welt', 'Nachrichten A', 'Nachrichten CH']
    group5 = ['Geschichte', 'Wissenschaft&Technik', 'Bildung', 'Umwelt', 'Feuilleton/Kultur', 'Musik', 'Wirtschaft']
    group6 = ['Essen&Trinken', 'Sport', 'Zocken']
    group7 = [] #all other flairs

    groups = [group1, group2, group3, group4, group5, group6]


    result = session.query(func.count(column).label("score"), func.date_trunc(timeframe, Submissions.datum).label("datum"), Submissions.flair)\
        .filter(and_(Submissions.datum >= date, Submissions.datum <= '2018-5-13'))\
        .group_by(func.date_trunc(timeframe, Submissions.datum), Submissions.flair)\
        .order_by(func.date_trunc(timeframe, Submissions.datum), func.sum(Submissions.score).desc())\
        .having(func.count(Submissions.id) >= 10)

    flairs = []
    dates = []
    last_date = ""
    old_date = result.first().datum


    for item in result:

        flairs.append(item.flair)
        try:
            if dates[-1] != item.datum.timestamp():
                dates.append(item.datum.timestamp())
        except IndexError:
            dates.append(item.datum.timestamp())


    unique_flairs = list(set(flairs))

    last = result[-1]

    for item in result:

        flair_list = Flair_lists(item.flair, item.score, item.datum, unique_flairs)

        flair_list.mark() # mark flair for that date
        flair_list.add_value(item.score, item.flair) #add value for flair

        if item == last:
            flair_list.check_mark(old_date, "last")
        else:
            flair_list.check_mark(old_date, "")

        old_date = item.datum

    result_dict = Flair_lists("","","","").result_dict
    flair_legend = []


    date_new = np.linspace(dates[0], dates[-1], len(dates)*50) #new x for interpolation
    dates_new = [datetime.datetime.fromtimestamp(i) for i in date_new] #convert back to datedtime

    y_list = []
    i = 0
    d= []
    for member in groups:
        i += 1
        for keys, values in result_dict.items():
            if keys in member:
                f = interp1d(dates, values, kind='quadratic')
                new_y = f(date_new)
                y_list.append(new_y)
                flair_legend.append(keys)

        if i == len(groups):
            for keys, values in result_dict.items():
                if keys not in [item for sublist in groups for item in sublist]:
                    group7.append(keys)
                    f = interp1d(dates, values, kind='quadratic')
                    new_y = f(date_new)
                    y_list.append(new_y)
                    flair_legend.append(keys)


    ticks = mdates.DateFormatter('%Y-%m-%d')


    start_color_range = 0.5
    stop_color_range = 0.96

    cmap_blue =     plt.get_cmap('Blues')(np.linspace(start_color_range, stop_color_range, (len(group1))))
    cmap_green =    plt.get_cmap('Greens')(np.linspace(start_color_range, stop_color_range, (len(group2))))
    cmap_red =      plt.get_cmap('Reds')(np.linspace(start_color_range, stop_color_range, (len(group3))))
    cmap_purple =   plt.get_cmap('Purples')(np.linspace(start_color_range, stop_color_range, (len(group4))))
    cmap_orange =   plt.get_cmap('Oranges')(np.linspace(start_color_range, stop_color_range, (len(group5))))
    cmap_grey =     plt.get_cmap('Greys')(np.linspace(start_color_range, stop_color_range, (len(group6))))
    cmap_grey2 =     plt.get_cmap('Wistia')(np.linspace(start_color_range, stop_color_range, (len(group7))))


    colormap = []
    bluei = greeni = redi = purplei = orangei = greyi = greyi2 = 0
    for flair in flair_legend:
        if flair in group1:
            colormap.append(cmap_blue[bluei])
            bluei += 1
        elif flair in group2:
            colormap.append(cmap_green[greeni])
            greeni += 1
        elif flair in group3:
            colormap.append(cmap_red[redi])
            redi += 1
        elif flair in group4:
            colormap.append(cmap_purple[purplei])
            purplei += 1
        elif flair in group5:
            colormap.append(cmap_orange[orangei])
            orangei += 1
        elif flair in group6:
            colormap.append(cmap_grey[greyi])
            greyi += 1
        elif flair in group7:
            colormap.append(cmap_grey2[greyi2])
            greyi2 += 1

    #color_patches = []
    # for i in range(0, len(unique_flairs)):
    #     color_patch = mpatches.Patch(color=color[i], label=unique_flairs[i])
    #     color_patches.append(color_patch)

    plt.style.use('Solarize_Light2')
    plt.rcParams.update({'figure.autolayout': True})
    plt.figure(figsize=(25,7))

    days = mdates.MonthLocator()


    ax = plt.subplot()

    ax.stackplot(dates_new, y_list, labels=flair_legend, colors=colormap)
    ax.legend(loc=2, prop={'size': 10}, ncol=6)

    ax.xaxis.set_major_formatter(ticks)
    ax.xaxis.set_minor_locator(days)
    ax.xaxis.set_tick_params(labelrotation=0)
    ax.set_ylim(0)

    plt.title(title)
    plt.ylabel(label)
    plt.show()

    plt.savefig("output/total_flair_graph.png")
    return (upload_image("output/total_flair_graph.png", "F" + hash))


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
        return (upload_image("output/total_time_graph.png", "T" + self.hash))


