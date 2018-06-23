#!/usr/bin/python3.6

import praw, time, sys, hashlib
from datetime import datetime
from botmodules.sqlconnect import make_connection, Submissions, Comments
from sqlalchemy import func, and_, text, exc

from botmodules.make_graph import time_graph, flair_graph, Total_time_graph, total_flair_graph  # custom module to create the graphs
from docs.conf import prawconfig, connection_string, connection_string_bot  # custom module with praw config
from botmodules.sqlconnectbot import make_connection_bot, Calls ,Hashes  # custom module for connection to sql database with replied comments
from botmodules.sqlresults import Sql_Results

reddit = praw.Reddit(client_id=prawconfig['client_id'],
                     client_secret=prawconfig['client_secret'],
                     password=prawconfig['password'],
                     user_agent=prawconfig['user_agent'],
                     username=prawconfig['username'])

rde = reddit.subreddit('rdebottest')

session = make_connection(connection_string)
session_bot = make_connection_bot(connection_string_bot)

footer = "Bugs? Wünsche? Sonstiges Feedback? Schreib eine Nachricht an meinen Meister: [amb_kosh](https://www.reddit.com/message/compose/?to=amb_kosh)"
date = '2015-5-1'
last_update = ''


class Check_Comment:
    """Checks if Comment calls the bot, if Comment was already
    replied to and if comments or submissions are requested"""

    def __init__(self, body, commentid):
        self.body = body.lower().strip()
        self.commentid = commentid

    def check_body(self):

        if self.body[:6] == '!stats':
            print("Found !stats: ", self.body)

            body_splitted = self.body.split(" ")

            scope = body_splitted[1]

            try:
                table = body_splitted[2]
            except IndexError:
                print("Found !stats but comment was malformatted: ", self.body)
                return False

            try:
                date = body_splitted[3]
            except:
                print("date not properly formatted")
                return_date = '2018-1-1'

            if scope == 'de' or scope == 'rde':
                return_scope = 'general'
            elif scope == 'me' or scope == 'ich':
                return_scope = 'user'
            else:
                return False

            if table == 'kommentare' or table == 'comments':
                return_table = Comments
            elif table == 'posts' or table == 'beiträge':
                return_table = Submissions
            else:
                return False

            try:
                return_date = datetime.strptime(date, '%Y-%m-%d')
            except:
                return_date = '2018-1-1'

            return ({'scope': return_scope, 'table': return_table, 'date': return_date})



    def check_author(self, author):
        return (comment.author.name)

    def check_already_replied(self):
        """returns false if comment is not yet in table"""
        query = session_bot.query(Calls.comment_id).filter(Calls.comment_id == self.commentid)
        result = session_bot.query(query.exists()).first()[0]
        print("Comment already in table: ", result)
        return (result)

    def mark_as_replied(self):
        calls_post = Calls(comment_id=self.commentid)
        session_bot.add(calls_post)
        try:
            session_bot.commit()
            return (True)
        except exc.IntegrityError:
            session_bot.rollback()
            print("Already replied to comment ", comment, " This should not happen!")
            return (False)



class Message(object):

    def __init__(self, date, author, table, scope):
        self.date = date
        self.author = author
        self.table = table
        self.scope = scope

    def get_final_answer(self):

        table_data = ''

        if self.scope == 'user':

            message_user = Message_User(self.date, self.author, self.table)
            table_heading = ""
            table_data = message_user.get_table_user()
            image_data = message_user.get_image_text()

        else:
            message_general = Message_General(self.date, self.author, self.table)
            table_heading = message_general.get_table_heading()
            table_data = format_reddit_table(Sql_Results(self.date, self.author, self.table, 'general').get_top_20(session))
            image_data = message_general.get_image_text()


        seperator = "\n\n-------\n\n"
        newline = "\n\n"

        bottom = get_small_text(footer)
        last_update = get_small_text("Daten bis: " + str(Sql_Results('','',Submissions,'').get_update_date(session)))

        return(\
                table_heading\
                + table_data\
                + image_data\
                + newline\
                + seperator\
                + newline\
                + last_update\
                + newline\
                + bottom)

    def check_hash_already_in_table(self, hash):
        """Returns true if hash already in table"""

        query = session_bot.query(Hashes.md5).filter(Hashes.md5 == hash)
        result = session_bot.query(query.exists()).first()[0]
        print("Hash already in table: ", result)
        return (result)

    def mark_hash_as_uploaded(self, hash, session):
        """Mark hash as uploaded after images are uploaded"""
        hash_post = Hashes(md5=hash)
        session_bot.add(hash_post)
        try:
            session_bot.commit()
        except exc.IntegrityError:
            print("Hash was already in table")
        except:
            print("Unexpected error while trying to mark hash as read: ", sys.exc_info()[0])

class Message_User(Message):

    def __init__(self, date, author, table, scope='user'):
        super().__init__(date, author, table, scope)

    def get_table_user(self):
        """Creates the table headings with reddit syntax"""

        sql_results = Sql_Results(self.date, self.author, self.table, self.scope)

        # if not sql_results.get_has_data(session):
        #     return ('No Data')

        score = str(sql_results.get_score_count(session)['score'])
        pos_score = str(sql_results.get_position(session, 'score'))
        count = str(sql_results.get_score_count(session)['count'])
        pos_count= str(sql_results.get_position(session, 'count'))
        top_flair = sql_results.get_top_flairdomain(session, Submissions.flair)['column']
        top_domain = sql_results.get_top_flairdomain(session, Submissions.domain)['column']
        top_post_id = sql_results.get_top_single(session)['postid']
        top_comment_id = sql_results.get_top_single(session)['commentid']

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

        hash = get_hash(self.author, self.date, self.table, self.scope)

        already_in_table = self.check_hash_already_in_table(hash)

        if not already_in_table:
            try:  # if hash is not yet in table
                time_image_path = time_graph(self.author, self.table, hash, session, self.date)
                flair_image_path = flair_graph(self.author, self.table, hash, session)
                self.mark_hash_as_uploaded(hash, session_bot)
            except:
                print("Unexpected error while trying to upload the images: ", sys.exc_info()[0])

        if already_in_table:
            time_image_path = "http://res.cloudinary.com/destats/image/upload/T" + hash  # return the old image path
            flair_image_path = "http://res.cloudinary.com/destats/image/upload/F" + hash  # return the old image path

        time_text = "\n\n" + "[Verteilung nach Aktivität](" + time_image_path + ")"
        flair_text = "\n\n" + "[Verteilung nach Flair](" + flair_image_path + ")"

        return (time_text + flair_text)

class Message_General(Message):

    def __init__(self, date, author, table, scope='general'):
        super().__init__(date, author, table, scope)


    def get_image_text(self):
        """format the link to the images. checks if has the same image was already created
        and if so returns the old link"""

        hash = get_hash(self.author, self.date, self.table, self.scope)

        already_in_table = self.check_hash_already_in_table(hash)

        if not already_in_table:
            try:  # if hash is not yet in table
                time_image_path = Total_time_graph(self.author, self.table, hash, self.date).make_graph(session)
                flair_image_path = total_flair_graph(self.author, self.table, self.date, hash, session)
                self.mark_hash_as_uploaded(hash, session_bot)
            except Exception as e:
                print("Unexpected error while trying to upload the images: ", e)

        if already_in_table:
            time_image_path = "http://res.cloudinary.com/destats/image/upload/T" + hash  # return the old image path
            flair_image_path = "http://res.cloudinary.com/destats/image/upload/F" + hash  # return the old image path

        time_text = "\n\n" + "[Entwicklung von Score und Anzahl Posts, Kommentaren nach Zeit](" + time_image_path + ")"
        try:
            flair_text = "\n\n" + "[Verteilung nach Flair](" + flair_image_path + ")"
        except UnboundLocalError:
            print("Something went wrong while getting flair text, probably someting with interpolation")
            flair_text = ""

        return (time_text+ flair_text)

    def get_table_heading(self):

        if self.table == Submissions:
            heading = "**Top 20 Autoren nach Einreichungen** \n\n"
        elif self.table == Comments:
            heading = "**Top 20 Autoren nach Kommentaren** \n\n"

        return(heading)


def get_small_text(message):
    """formats input string with ^ for small text in reddit"""

    words = message.split()
    words_transformed = list(map(lambda x: " ^^" + x, words))
    words_together = "".join(words_transformed)
    return (words_together)


def get_hash(author, date, table, scope):

    to_string = author + str(table) + str(Sql_Results('','',Submissions,'').get_update_date(session)) + str(date) + scope
    m = hashlib.md5(to_string.encode('utf-8')).hexdigest()
    return(str(m)[:12])

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


###################
###main loop
###################

while True:
    for comment in reddit.subreddit('rdebottest').stream.comments():
        # submission.comments.replace_more(limit=0)
        # comments = submission.comments.list()
        #
        # for comment in comments:

            check = Check_Comment(comment.body, comment.id)
            body_parameters = check.check_body() # checks if comment body calls bot, if so returns Submissions or Comments

            if body_parameters and not check.check_already_replied():  # other checks are only needed if this is true

                scope = body_parameters['scope']
                table = body_parameters['table']
                date = body_parameters['date']

                try:
                    author = check.check_author(comment.author)
                except AttributeError:
                    print("Can't fetch author name. Probably deleted")

                has_data = Sql_Results(date, author, table, scope).check_has_data(session)

                if not has_data:
                    answer = ("No Data")
                    print("Replying to: ", author, " Comment-ID: ", comment.id, " Called by: ", comment.body,
                          " NO DATA")
                    comment.reply(answer)
                    check.mark_as_replied()
                    session.close()
                    sys.stdout.flush()

                if author and has_data:
                    answer = Message(date, author, table, scope).get_final_answer()
                    #print(answer)
                    print("Replying to: ", author, " Comment-ID: ", comment.id, " Called by: ", comment.body)
                    try :
                        comment.reply(answer)
                        check.mark_as_replied()
                    except:
                        print("Unexpected error while trying to answer comment: ", sys.exc_info()[0])
                    # print(answer)
                    session.close()
                    sys.stdout.flush()

    time.sleep(1)