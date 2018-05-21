import matplotlib
matplotlib.use('Agg')

from os import path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

from sqlalchemy import func, text, cast, Time

from botmodules.sqlconnect import make_connection, Submissions, Comments
from botmodules.upload_image import upload_image
import datetime

directory = path.dirname(__file__)

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


    plt.savefig(directory + '/output/time_graph.png') 

    return(upload_image(directory + '/output/time_graph.png', "T"+hash)[0])



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

    plt.savefig(directory + '/output/flair_graph.png')

    return(upload_image(directory + '/output/flair_graph.png', "F"+hash)[0])

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



#session = make_connection()
#total_distribution_graph(Comments, '123', session)
