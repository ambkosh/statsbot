#!/usr/bin/python3.6

import praw, time, sys, hashlib
from botmodules.sqlconnect import make_connection, Submissions, Comments
from sqlalchemy import func, and_, text, exc

from botmodules.make_graph import time_graph, flair_graph  # custom module to create the graphs
from docs.conf import prawconfig, connection_string, connection_string_bot  # custom module with praw config
from botmodules.sqlconnectbot import make_connection_bot, Calls, \
    Hashes  # custom module for connection to sql database with replied comments

reddit = praw.Reddit(client_id=prawconfig['client_id'],
                     client_secret=prawconfig['client_secret'],
                     password=prawconfig['password'],
                     user_agent=prawconfig['user_agent'],
                     username=prawconfig['username'])

rde = reddit.subreddit('rdebottest')

session = make_connection(connection_string)
session_bot = make_connection_bot(connection_string_bot)

header = "Daten bis: "
footer = "Bugs? Wünsche? Sonstiges Feedback? Schreib eine Nachricht an meinen Meister: [amb_kosh](https://www.reddit.com/message/compose/?to=amb_kosh)"
date = '2015-5-1'


class Sql_Results(object):
    """Basic Class for SQL results"""

    def __init__(self, author, date):
        self.author = author
        self.date = date

    def get_author(self):
        return self.author

    def get_table(self):
        return self.table

    def set_author(self, author):
        self.author = author

    def set_table(self, table):
        self.table = table


class Sql_User(Sql_Results):
    """Basic Class for SQL results"""

    def __init__(self, author, date, table):

        super().__init__(author, date)
        self.table = table

        if self.table == Submissions:
            self.table_text = 'submissionslarge'
        else:
            self.table_text = 'comments'

    def get_has_data(self, session):
        """returns true if user has rows in time frame"""

        query = session.query(self.table.id).filter(
            and_(self.table.autor == self.author, self.table.datum >= self.date))
        result = session.query(query.exists()).first()[0]

        if result == True:
            return (True)

    def get_hash(self):

        to_string = self.author + str(self.table) + str(self.get_update_date(session))
        m = hashlib.md5(to_string.encode('utf-8')).hexdigest()

        return (str(m)[:12])

    def get_score_count(self, session):
        """Returns total number of comments and sum of score
        {'score': score, 'comments': number_of_comments"""

        score_comments_total = session.query(func.sum(self.table.score).label("score"), \
                                             func.count(self.table.id).label("comments")) \
            .filter(and_(self.table.autor == self.author, self.table.datum >= self.date)).first()

        return ({'score': score_comments_total.score, 'count': score_comments_total.comments})

    def get_update_date(self, session):
        """Returns the last datetime the database was updates"""

        last_update = session.query(Submissions.datum).order_by(Submissions.datum.desc()).limit(1).first()

        return (last_update.datum)

    def get_top_flair(self, session):
        """Returns the flair with the most submissions and its score
        {'flair': flair, 'count': count}"""

        if self.table == Submissions:
            top_flair = session.query(func.count(Submissions.id).label("count"), Submissions.flair) \
                .filter(and_(Submissions.autor == self.author, Submissions.datum >= self.date)) \
                .group_by(Submissions.flair) \
                .order_by(func.count(Submissions.id).desc()).first()
        else:
            top_flair = session.query(func.count(Comments.id).label("count"), Submissions.flair) \
                .join(Submissions, Submissions.postid == Comments.postid) \
                .filter(and_(Comments.autor == self.author, Comments.datum >= self.date)) \
                .group_by(Submissions.flair) \
                .order_by(func.count(Comments.id).desc()).first()

        return ({'flair': top_flair.flair, 'count': top_flair.count})

    def get_top_domain(self, session):
        """Returns the domain with the most submissions and its score
        {'domain': domain, 'count': count}"""

        if self.table == Submissions:
            top_domain = session.query(func.count(Submissions.id).label("count"), Submissions.domain) \
                .filter(and_(Submissions.autor == self.author, Submissions.datum >= self.date)) \
                .group_by(Submissions.domain) \
                .order_by(func.count(Submissions.id).desc()).first()
        else:
            top_domain = session.query(func.count(Comments.id).label("count"), Submissions.domain) \
                .join(Submissions, Submissions.postid == Comments.postid) \
                .filter(and_(Comments.autor == self.author, Comments.datum >= self.date)) \
                .group_by(Submissions.domain) \
                .order_by(func.count(Comments.id).desc()).first()

        return ({'domain': top_domain.domain, 'count': top_domain.count})

    def get_top_post(self, session):
        """Returns the postid and title of the top scoring post.
        Need to later construct the permalink
        {'postid': postid, 'title': title}"""

        top_post = session.query(Submissions.postid, Submissions.title, Comments.commentid) \
            .join(Comments, Submissions.postid == Comments.postid) \
            .filter(and_(self.table.autor == self.author, self.table.datum >= self.date)) \
            .order_by(self.table.score.desc()) \
            .limit(1).first()

        return ({'postid': top_post.postid, 'title': top_post.title, 'commentid': top_post.commentid})

    def get_position_count(self, session):
        """returns position compared to all for number of posts/comments"""

        position_count = text("select row_number from \
            	    (select autor, count(id), row_number () over(order by count(id) desc) \
            	    from " + self.table_text + " \
                    where datum >='" + self.date + "' \
                    group by autor \
            	    order by count(id) desc ) row \
                    where autor = '" + self.author + "'")

        return (session.execute(position_count).first()['row_number'])

    def get_position_score(self, session):
        """returns position compared to all for score of posts/comments"""

        position_score = text("select row_number from \
            	    (select autor, count(id), row_number () over(order by sum(score) desc) \
            	    from " + self.table_text + " \
                    where datum >='" + self.date + "' \
                    group by autor \
            	    order by sum(score) desc ) row \
                    where autor = '" + self.author + "'")

        return (session.execute(position_score).first()['row_number'])

    # for some reason this was super slow

    # def get_position_score(self):
    #     """Returns the position compared to all other authors score wise"""
    #     position_score_subqery = session.query(self.table.autor.label("autor"), func.sum(self.table.score), \
    #                                                 func.row_number().over(order_by=(func.sum(self.table.score))).label(
    #                                                     "row_number")) \
    #         .group_by(self.table.autor) \
    #         .order_by(func.sum(self.table.score).desc()) \
    #         .subquery('position_score_subqery')
    #     position_score = session.query(position_score_subqery.c.row_number) \
    #         .filter(position_score_subqery.c.autor == self.author) \
    #         .first()
    #     return (position_score[0])


# Subclass just for comments not needed for now

# class Sql_Comments(Sql_Results):
#     """Returns results for table Comments when joins are required"""
#
#     session = make_connection()
#
#     def __init__(self, author, date):
#         super().__init__(author, date, table=Comments)


class Message_Data(object):
    """Creates the final Message"""

    def __init__(self, author, date, table):
        self.author = author
        self.date = date
        self.table = table

    def get_table(self):
        """Creates the table headings with reddit syntax"""

        sql_results = Sql_User(self.author, self.date, self.table)

        if not sql_results.get_has_data(session):
            return ('No Data')

        score = str(sql_results.get_score_count(session)['score'])
        pos_score = str(sql_results.get_position_score(session))
        count = str(sql_results.get_score_count(session)['count'])
        pos_count = str(sql_results.get_position_count(session))
        top_flair = sql_results.get_top_flair(session)['flair']
        top_domain = sql_results.get_top_domain(session)['domain']
        top_post_id = sql_results.get_top_post(session)['postid']
        top_comment_id = sql_results.get_top_post(session)['commentid']

        if self.table == Submissions:
            heading = "Post"
            heading_plural = "Posts"
            perma_link = "[" + top_post_id + "]" + "(https://reddit.com/r/de/comments/" + top_post_id + ")"

        else:
            heading = "Kommentar"
            heading_plural = "Kommentare"
            perma_link = "[" + top_post_id + "]" + "(https://reddit.com/r/de/comments/" + top_post_id + "/topic/" + top_comment_id + ")"

        table_data = "Score | " + heading_plural + " | Top-Flair | Top-Domain | Bester " + heading
        table_data = table_data + "\n---|---|---|---|---"
        table_data = table_data + "\n" + score + " (Pos.: " + pos_score + ")  | " + count + " (Pos.: " + pos_count + ")  | " + top_flair + " | " + top_domain + " | " + perma_link

        return (table_data)

    def get_image_text(self):
        """format the link to the images. checks if has the same image was already created
        and if so returns the old link"""

        hash = Sql_User(self.author, self.date, self.table).get_hash()

        hash_post = Hashes(md5=hash)
        session_bot.add(hash_post)  # tries to write has to table
        try:  # if hash is not yet in table
            session_bot.commit()
            time_image_path = time_graph(self.author, self.table, hash, session)
            flair_image_path = flair_graph(self.author, self.table, hash, session)

        except exc.IntegrityError:  # fails because of unique constraint
            session_bot.rollback()
            print("Hash already in table")
            time_image_path = "http://res.cloudinary.com/destats/image/upload/T" + hash  # return the old image path
            flair_image_path = "http://res.cloudinary.com/destats/image/upload/F" + hash  # return the old image path

        time_text = "\n\n" + "[Verteilung nach Aktivität](" + time_image_path + ")"
        flair_text = "\n\n" + "[Verteilung nach Flair](" + flair_image_path + ")"

        return (time_text + flair_text)

        return ("bla")

    def get_small_text(self, message):
        """formats input string with ^ for small text in reddit"""

        words = message.split()
        words_transformed = list(map(lambda x: " ^^" + x, words))
        words_together = "".join(words_transformed)
        return (words_together)

    def get_final_answer(self):
        """Puts all the shit together"""

        last_update = self.get_small_text(header) + " " + self.get_small_text(
            str(Sql_User(self.author, self.table, self.date).get_update_date(session).date()))
        table_data = self.get_table()
        images_data = self.get_image_text()
        seperator = "\n\n-------\n\n"
        newline = "\n\n"
        bottom = self.get_small_text(footer)

        return (table_data + images_data + newline + seperator + newline + last_update + newline + bottom)


class Check_Comment:
    """Checks if Comment calls the bot, if Comment was already
    replied to and if comments or submissions are requested"""

    def __init__(self, body, commentid):
        self.body = body
        self.commentid = commentid

    def check_body(self):
        if self.body.strip().lower() in ['!stats kommentare']:
            return (Comments)
        elif comment.body.strip().lower() in ['!stats posts']:
            return (Submissions)

    def check_author(self, author):
        return (comment.author.name)

    def check_already_replied(self):
        calls_post = Calls(comment_id=self.commentid)
        session_bot.add(calls_post)
        try:
            session_bot.commit()
            return (True)
        except exc.IntegrityError:
            session_bot.rollback()
            # print("Already replied to comment ", comment)
            return (False)


###################
###main loop
###################

while True:
    for submission in reddit.subreddit('rdebottest').hot(limit=25):
        submission.comments.replace_more(limit=0)
        comments = submission.comments.list()

        for comment in comments:

            check = Check_Comment(comment.body, comment.id)
            table = check.check_body()  # checks if comment body calls bot, if so returns Submissions or Comments

            if table and check.check_already_replied():  # other checks are only needed if this is true

                try:
                    author = check.check_author(comment.author)
                except AttributeError:
                    print("Can't fetch author name. Probably deleted")

                has_data = Sql_User(author, date, table).get_has_data(session)

                if not has_data:
                    answer = ("No Data")
                    print("Replying to: ", author, " Comment-ID: ", comment.id, " Called by: ", comment.body,
                          " NO DATA")
                    comment.reply(answer)
                    session.close()
                    sys.stdout.flush()

                if author and has_data:
                    answer = Message_Data(author, date, table).get_final_answer()
                    print("Replying to: ", author, " Comment-ID: ", comment.id, " Called by: ", comment.body)
                    comment.reply(answer)
                    # print(answer)
                    session.close()
                    sys.stdout.flush()

    time.sleep(1)