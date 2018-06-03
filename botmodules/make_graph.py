#!/usr/bin/python3.6

import matplotlib
#matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import numpy as np

from sqlalchemy import func, text, cast, Time, and_

from botmodules.sqlconnect import make_connection, Submissions, Comments
from botmodules.upload_image import upload_image
import datetime


def time_graph(author, table, hash, session):
    """creates the time graph for given user
    Uploads the picture and returns the image link"""

    # data for activity per hour in a day


    result_day = session.query(func.date_part('hour', table.datum).label("time"), func.count(table.id).label("count"))\
        .filter(table.autor == author)\
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
        .filter(table.autor == author)\
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



def scatter_graph_total(session, date):



    result = session.query(func.sum(Submissions.num_komments).label("score"), func.date_trunc('week', Submissions.datum).label("datum"), Submissions.flair)\
        .filter(and_(Submissions.datum >= date))\
        .group_by(func.date_trunc('week', Submissions.datum), Submissions.flair)\
        .order_by(func.date_trunc('week', Submissions.datum), func.sum(Submissions.score).desc())\
        .having(func.count(Submissions.id) >= 0)

    flairs = []
    dates = []
    last_date = ""
    old_date = result.first().datum


    for item in result:
        flairs.append(item.flair)
        try:
            if dates[-1] != item.datum:
                dates.append(item.datum)
        except IndexError:
            dates.append(item.datum)

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

    y_list = []
    for keys, values in result_dict.items():
        y_list.append(values)

    #
    # create graph
    #

    ticks = mdates.DateFormatter('%Y-%m')

    cmap = plt.get_cmap('terrain')
    color = cmap(np.linspace(0, 1, (len(result_dict.keys()))))

    #color_patches = []
    # for i in range(0, len(unique_flairs)):
    #     color_patch = mpatches.Patch(color=color[i], label=unique_flairs[i])
    #     color_patches.append(color_patch)

    plt.style.use('ggplot')
    plt.rcParams.update({'figure.autolayout': True})
    plt.figure(figsize=(15,5))

    print(result_dict.keys())


    ax = plt.subplot()
    ax.stackplot(dates, y_list, labels=result_dict.keys(), colors=color)
    ax.legend(loc=2, prop={'size': 7}, ncol=6)

    ax.xaxis.set_major_formatter(ticks)
    ax.xaxis.set_tick_params(labelrotation=55)
    #plt.legend(handles=color_patches)

    plt.show()


