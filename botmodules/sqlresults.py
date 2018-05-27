#!/usr/bin/python3.6

from sqlalchemy import func, and_, text, exc
from docs.conf import prawconfig, connection_string, connection_string_bot  # custom module with praw config
from botmodules.sqlconnect import make_connection, Submissions, Comments


session = make_connection(connection_string)


class Sql_Results(object):
    """Basic Class for SQL results"""

    def __init__(self, date, author, table, scope):
        self.scope = scope
        self.author = author
        self.table = table
        self.date = date

        self.query_filter = (and_(self.table.autor == self.author, self.table.datum >= self. date))

    def get_author(self):
        return self.author

    def get_table(self):
        return self.table

    def set_author(self, author):
        self.author = author

    def set_table(self, table):
        self.table = table

    def check_has_data(self, session):
        """checks if requested data returns anything"""

        query = session.query(self.table.id).filter(self.query_filter)
        result = session.query(query.exists()).first()[0]

        return(result)

    def get_update_date(self, session):
        """Returns the last datetime the database was updates"""

        last_update = session.query(Submissions.datum).order_by(Submissions.datum.desc()).limit(1).first()

        return (last_update.datum)


    def get_score_count(self, session):
        """Returns total number of comments and sum of score
        {'score': score, 'comments': number_of_comments"""

        score_comments_total = session.query(func.sum(self.table.score).label("score"), func.count(self.table.id).label("comments")) \
            .filter(self.query_filter)\
            .first()

        return ({'score': score_comments_total.score, 'count': score_comments_total.comments})

    def get_top_flairdomain(self, session, column):
        """Returns the flair with the most submissions and its score
        {'flair': flair, 'count': count}"""

        if self.table == Submissions:
            t1 = Submissions
            t2 = Submissions
        else:
            t1 = Comments
            t2 = Submissions

        top_column = session.query(func.count(t1.id).label("count"), column.label("column"))

        if self.table == Comments:
            top_column = top_column.join(t2, t2.postid == t1.postid)

        top_column = top_column.filter(and_(t1.autor == self.author, t1.datum >= self.date)) \
            .group_by(column) \
            .order_by(func.count(t1.id).desc()) \
            .first()

        return ({'column': top_column.column, 'count': top_column.count})

    def get_position(self, session, column):
        """returns the position for score or number of comments"""

        if self.table == Submissions:
            table_text = 'submissionslarge' #need to make it string for execution it as text
        else:
            table_text = 'comments'

        if column == 'score':
            window_query = "(select autor, count(id), row_number () over(order by sum(score) desc) \
            	    from " + table_text + " \
                    where datum >='" + self.date + "' \
                    group by autor \
            	    order by sum(score) desc ) row " #that space at the end is important
        else:
            window_query = "(select autor, count(id), row_number () over(order by count(id) desc) \
            	    from " + table_text + " \
                    where datum >='" + self.date + "' \
                    group by autor \
            	    order by count(id) desc ) row " #that space at the end is important

        query = text("select row_number from \
                      "+window_query+\
                      "where autor = '" + self.author + "'")

        return (session.execute(query).first()['row_number'])


    def get_top_single(self, session):
        """Returns the postid and title of the top scoring post.
        Need to later construct the permalink
        {'postid': postid, 'title': title}"""

        top_post = session.query(Submissions.postid, Submissions.title, Comments.commentid) \
            .join(Comments, Submissions.postid == Comments.postid) \
            .filter(and_(self.table.autor == self.author, self.table.datum >= self.date)) \
            .order_by(self.table.score.desc()) \
            .limit(1).first()

        return ({'postid': top_post.postid, 'title': top_post.title, 'commentid': top_post.commentid})

    def get_top_20(self, session):
        result =session.query(self.table.autor, func.sum(self.table.score).label("score"), func.count(self.table.id).label("count")).\
                filter(and_(self.table.datum >=  self.date, self.table.autor != '[deleted]')).\
                group_by(self.table.autor).\
                order_by(func.sum(self.table.score).desc()).\
                limit(20)

        result_list = []

        for item in result:
            result_list.append({'author': item.autor, 'score': item.score, 'count':item.count})

        return(result_list)



def format_reddit_table(table_data):
    """Formats data in reddit table format"""

    num_columns = len(table_data[0].keys())
    num_rows = len(table_data)

    headings = list(table_data[0].keys())
    headings_formated = []
    table_align = []
    table_row = []

    for i in range (0, num_columns):
        if i != num_columns-1:
            (lambda x: headings_formated.append(x + " | "))(headings[i])
        else:
            headings_formated.append(" " + headings[i] + "\n")

    table = ''.join(headings_formated)

    for i in range (0, num_columns):
        if i != num_columns-1:
            table_align.append("--|")
        else:
            table_align.append("--" + "\n")

    table += ''.join(table_align)

    for i in range (0, num_rows):
        table_row = []
        for j in range(0, num_columns):
            if j != num_columns-1:
                table_row.append(str(table_data[i][headings[j]]) + " | ")
            else:
                table_row.append(str(table_data[i][headings[j]]) + "\n")
        table += ''.join(table_row)

    return(table)

# table_data = Sql_Results('2018-1-1', 'amb_kosh', Submissions, 'general').get_top_20(session)
# print(format_reddit_table(table_data))