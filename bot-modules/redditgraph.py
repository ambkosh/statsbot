from sqlalchemy import func
from sqlconnect import make_connection, Submissions, Comments, and_


def make_graph_submissions(autor, date):
    """Takes a dictoinary of data and creates graphs"""

    session = make_connection()

    graph = ""

    result = session.query(Submissions.flair, func.count(Submissions.id).label("count"))\
        .filter(and_(Submissions.autor == autor,Submissions.datum >= date))\
        .group_by(Submissions.flair)\
        .order_by(func.count(Submissions.id).desc())

    dataGraph = {}
    longestFlair = 0

    for item in result:

        flair = ""

        try:
            len(item.flair)
            flair = item.flair
        except TypeError:
            flair = 'Kein Flair'

        if len(flair) > longestFlair:
            longestFlair = len(flair)

        dataGraph[flair] = item.count

    total = sum(dataGraph.values())


    for key, value in dataGraph.items():
        percent = (round(value/total*100))
        line = "    "+key + ": "
        spaces = longestFlair - len((key))
        for x in range(0, spaces):
            line = line + " "
        if percent == 0: line = line + "| " + str(value)
        for x in range(0, percent):
            line = line + '|'
            if x == percent-1:
                line = line + " " + str(value)

        graph = graph + line + "\n"

    return(graph)

def make_graph_comments(autor, date):
    """Takes a dictoinary of data and creates graphs"""

    session = make_connection()

    graph = ""

    result = session.query(Submissions.flair, func.count(Submissions.id).label("count"))\
        .join(Comments, Submissions.postid == Comments.postid)\
        .filter(and_(Comments.autor == autor,Comments.datum >= date))\
        .group_by(Submissions.flair)\
        .order_by(func.count(Submissions.id).desc())

    dataGraph = {}
    longestFlair = 0

    for item in result:

        flair = ""

        try:
            len(item.flair)
            flair = item.flair
        except TypeError:
            flair = 'Kein Flair'

        if len(flair) > longestFlair:
            longestFlair = len(flair)

        dataGraph[flair] = item.count

    total = sum(dataGraph.values())


    for key, value in dataGraph.items():
        percent = (round(value/total*100))
        line = "    "+key + ": "
        spaces = longestFlair - len((key))
        for x in range(0, spaces):
            line = line + " "
        if percent == 0: line = line + "| " + str(value)
        for x in range(0, percent):
            line = line + '|'
            if x == percent-1:
                line = line + " " + str(value)

        graph = graph + line + "\n"

    return(graph)