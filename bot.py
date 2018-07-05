#!/usr/bin/python3.6

import praw, time, sys, hashlib
from datetime import datetime
import logging
from sqlalchemy import func, and_, text, exc

from botmodules.make_graph import time_graph, flair_graph, Total_time_graph, total_flair_graph  # custom module to create the graphs
from docs.conf import prawconfig, connection_string, connection_string_bot  # custom module with praw config
from botmodules.sqlconnect import make_connection, Submissions, Comments
from botmodules.sqlconnectbot import make_connection_bot, Calls ,Hashes  # custom module for connection to sql database with replied comments
from botmodules.sqldata import Data
from botmodules.log import prepare_logger
from botmodules.upload_image import upload_image


reddit = praw.Reddit(client_id=prawconfig['client_id'],
                     client_secret=prawconfig['client_secret'],
                     password=prawconfig['password'],
                     user_agent=prawconfig['user_agent'],
                     username=prawconfig['username'])

subreddit = prawconfig['subreddit']

rde = reddit.subreddit(subreddit)

session = make_connection(connection_string)
session_bot = make_connection_bot(connection_string_bot)


testmode = False
date = '2015-5-1'
last_update = ''

class Reddit_Comment:
    """Checks if Comment calls the bot, if Comment was already
    replied to and if comments or submissions are requested"""

    prepare_logger('Comment')
    logger = logging.getLogger('Comment')

    def __init__(self, comment):
        try:
            self.body = comment.body.lower().strip()
            self.commentid = comment.id
        except AttributeError:
            self.logger.warn("praw comment did not contain body or commentid")
            self.body = ''
            self.commentid = ''
        try:
            self.author = comment.author.name
        except:
            self.logger.warn("Could not fetch author, probably deleted. Setting author = [deleted]")
            self.author = '[deleted]'

    def check_body(self):

        self.logger.debug("ID: %s - Author: %s - Checking comment body: %s", self.commentid, self.author, self.body[:10])

        if self.body[:6] == '!stats':

            self.logger.info("Found !stats: %s", self.body)

            body_splitted = self.body.split(" ")
            try:
                scope = body_splitted[1]
            except:
                self.logger.debug("ID: %s - Author: %s - Found !stats but comment malformatted: %s", self.commentid, self.author, self.body)
                return False

            try:
                table = body_splitted[2]
            except IndexError:
                self.logger.debug("ID: %s - Author: %s - Found !stats but comment malformatted: %s", self.commentid, self.author, self.body)
                return False

            try:
                date = body_splitted[3]
            except IndexError:
                self.logger.debug("ID: %s - Author: %s - Found !stats but found no date: %s Returning 2018-1-1 as date", self.commentid, self.author, self.body)
                return_date = '2018-1-1'

            if scope in ['de', 'rde']:
                return_scope = 'general'
            elif scope in ['ich', 'me']:
                return_scope = 'user'
            else:
                self.logger.debug("ID: %s - Author: %s - Found !stats but scope malformatted: %s", self.commentid, self.author, self.body)
                return False

            if table == 'kommentare' or table == 'comments':
                return_table = Comments
            elif table == 'posts' or table == 'beiträge' or table == 'submissions':
                return_table = Submissions
            else:
                self.logger.debug("ID: %s - Author: %s - Found !stats but table malformatted: %s", self.commentid, self.author, self.body)
                return False

            try:
                return_date = datetime.strptime(date, '%Y-%m-%d')
            except ValueError as e:
                self.logger.debug("ID: %s - Author: %s - Found !stats but date malformatted: %s Returning 2018-1-1 as date", self.commentid, self.author, self.body)
                return_date = '2018-1-1'
            except:
                self.logger.debug("ID: %s - Author: %s - Found !stats but date malformatted: %s Returning 2018-1-1 as date", self.commentid, self.author, self.body)
                return_date = '2018-1-1'


            r = ({'scope': return_scope, 'table': return_table, 'date': return_date, 'author': self.author})
            self.logger.debug("ID: %s - Author: %s - Returning info for found call: %s", self.commentid, self.author, r)
            return (r)

        else:
            return False

    def check_already_replied(self):
        """returns false if comment is not yet in table"""

        if testmode: return False

        if self.commentid in ['', 0]:
            return True

        try:
            query = session_bot.query(Calls.comment_id).filter(Calls.comment_id == self.commentid)
            result = session_bot.query(query.exists()).first()[0]
        except ValueError:
            self.logger.warn("ID: %s - Author: %s - Commentid malformatted", self.commentid, self.author)
            return True
        except UnboundLocalError:
            self.logger.warn("ID: %s - Author: %s - Commentid malformatted", self.commentid, self.author)
            return True

        if result == None:
            return False

        self.logger.debug("ID: %s - Author: %s - Returning info if comment was already replied to: %s", self.commentid, self.author, result)
        return (result)

    def mark_as_replied(self):

        if testmode: return True

        calls_post = Calls(comment_id=self.commentid)
        session_bot.add(calls_post)
        try:
            session_bot.commit()
            self.logger.debug("ID: %s - Author: %s - Marked comment as replied", self.commentid, self.author)
            return (True)
        except exc.IntegrityError:
            session_bot.rollback()
            self.logger.warn("ID: %s - Author: %s - Already replied to comment", self.commentid, self.author)
            return (False)

class Message(object):
    """Main class for generating the message"""

    prepare_logger('Message')
    logger = logging.getLogger('Message')

    def __init__(self, scope, author, table, date):
        self.scope = scope
        self.author = author
        self.table = table
        self.date = date

        self.d = Data(self.scope, self.author, self.table, self.date)

    def get_message(self):

        seperator = "\n\n-------\n\n"
        newline = "\n\n"

        if not self.d.check_has_data(session):
            return("No Data found for selection (Maybe try an older date).")

        else:
            header = self.get_header()
            table = self.get_table()
            graphs = self.get_graphs()
            footer = self.get_footer()

            message = table + graphs + seperator + footer

        return message

    def get_table(self):

        if self.scope == 'user':

            score           = str(self.d.get_score_count(session)['score'])
            pos_score       = str(self.d.get_position(session)['score'])
            pos_score_2018       = str(self.d.get_position(session)['score2018'])
            count           = str(self.d.get_score_count(session)['count'])
            pos_count       = str(self.d.get_position(session)['count'])
            pos_count_2018       = str(self.d.get_position(session)['count2018'])
            top_flair       = self.d.get_top_flairdomain(session, Submissions.flair)['column']
            top_domain      = self.d.get_top_flairdomain(session, Submissions.domain)['column']
            top_post_id     = self.d.get_top_single(session)['postid']
            top_comment_id  = self.d.get_top_single(session)['commentid']

            if self.table == Submissions:
                heading = "Post"
                heading_plural = "Posts"
                perma_link = "[" + top_post_id + "]" + "(https://reddit.com/r/de/comments/" + top_post_id + ")"

            elif self.table == Comments:
                heading = "Kommentar"
                heading_plural = "Kommentare"
                perma_link = "[" + top_post_id + "]" + "(https://reddit.com/r/de/comments/" + top_post_id + "/topic/" + top_comment_id + ")"

            table_data = "Score | " + heading_plural + " | Top-Flair | Top-Domain | Bester " + heading + " | Pos. Score | Pos. " + heading_plural
            table_data = table_data + "\n---|---|---|---|---|---|---"
            table_data = table_data + "\n" + score + " | " + count + "  | " + top_flair + " | " + top_domain + " | " + perma_link + " | " + pos_score + " (2018: " + pos_score_2018 + ") | " + pos_count + " (2018: " + pos_count_2018 +")"

            self.logger.debug("Author: %s - Returning table data for author", self.author)
            return (table_data)

        if self.scope == 'general':

            if self.table == Submissions:
                heading = "**Top 20 Autoren nach Einreichungen** \n\n"
            elif self.table == Comments:
                heading = "**Top 20 Autoren nach Kommentaren** \n\n"

            table_data = self.d.get_top_20(session)
            table = format_reddit_table(table_data)
            table = heading + table

            self.logger.debug("ID: %s Author: %s - Returning table", comment.id, comment.author.name)
            return(table)

    def get_graphs(self):

        hash = get_hash()
        if not check_hash_already_in_table(hash):

            if self.scope == 'user':

                time_image_path = time_graph(self.author, self.table, self.date, session)
                URL_time_graph = upload_image(time_image_path, "T"+hash)

                flair_image_path = flair_graph(self.author, self.table, self.date, session)
                URL_flair_graph = upload_image(flair_image_path, "F"+hash)

                mark_hash_as_uploaded(hash)

                time_text = "\n\n" + "[Verteilung nach Aktivität](" + URL_time_graph + ")"
                flair_text = "\n\n" + "[Verteilung nach Flair](" + URL_flair_graph + ")"

                return (time_text + flair_text)

            if self.scope == 'general':

                time_image_path = Total_time_graph(self.author, self.table, self.date).make_graph(session)
                URL_time_graph = upload_image(time_image_path, "T"+hash)

                flair_image_path = total_flair_graph(self.author, self.table, self.date, session)
                URL_flair_graph = upload_image(flair_image_path, "F"+hash)
                mark_hash_as_uploaded(hash)

                time_text = "\n\n" + "[Entwicklung von Score und Anzahl Posts, Kommentaren nach Zeit](" + URL_time_graph + ")"
                flair_text = "\n\n" + "[Verteilung nach Flair](" + URL_flair_graph + ")"

                return (time_text + flair_text)

        else: #if hash is already in table

            if self.scope == 'user':

                URL_time_graph = "http://res.cloudinary.com/destats/image/upload/T" + hash  # return the old image path
                URL_flair_graph = "http://res.cloudinary.com/destats/image/upload/T" + hash  # return the old image path

                time_text = "\n\n" + "[Verteilung nach Aktivität](" + URL_time_graph + ")"
                flair_text = "\n\n" + "[Verteilung nach Flair](" + URL_flair_graph + ")"

                return (time_text + flair_text)

            if self.scope == 'general':

                URL_time_graph = "http://res.cloudinary.com/destats/image/upload/T" + hash  # return the old image path
                URL_flair_graph = "http://res.cloudinary.com/destats/image/upload/T" + hash  # return the old image path

                time_text = "\n\n" + "[Entwicklung von Score und Anzahl Posts, Kommentaren nach Zeit](" + URL_time_graph + ")"
                flair_text = "\n\n" + "[Verteilung nach Flair](" + URL_flair_graph + ")"

                return (time_text + flair_text)

    def get_header(self):
            pass

    def get_footer(self):

        last_update = self.d.get_update_date(session)
        last_update = get_small_text("Daten bis: " + str(last_update))
        footer = "Bugs? Wünsche? Sonstiges Feedback? Schreib eine Nachricht an meinen Meister: [amb_kosh](https://www.reddit.com/message/compose/?to=amb_kosh)"
        footer = get_small_text(footer)
        footer = last_update + footer

        mainlog.debug("ID: %s Author: %s - Returning footer", comment.id, comment.author.name)
        return(footer)




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

    mainlog.debug("ID: %s Author: %s - Returning table in reddit format", comment.id, comment.author.name)
    return(table)

def get_hash():

    to_string = comment.body + str(Data('','',Submissions,'').get_update_date(session))
    m = hashlib.md5(to_string.encode('utf-8')).hexdigest()

    mainlog.debug("ID: %s Author: %s - returning hash", comment.id, comment.author.name)
    return(str(m)[:12])

def check_hash_already_in_table(hash):
    """Returns true if hash already in table"""

    if testmode: return False

    query = session_bot.query(Hashes.md5).filter(Hashes.md5 == hash)
    result = session_bot.query(query.exists()).first()[0]

    mainlog.debug("ID: %s Author: %s - Returning check for has already in table: %s", comment.id, comment.author.name, result)
    return (result)

def mark_hash_as_uploaded(hash):
    """Mark hash as uploaded after images are uploaded"""

    hash_post = Hashes(md5=hash)
    session_bot.add(hash_post)
    try:
        session_bot.commit()
        mainlog.debug("ID: %s Author: %s - Marked hash as uploaded", comment.id, comment.author.name)
    except exc.IntegrityError:
        mainlog.warn("ID: %s Author: %s - Hash was already in table", comment.id, comment.author.name)
    except:
        mainlog.warn("ID: %s Author: %s - Unexpected error while trying to mark hash as read: %s", comment.id, comment.author.name, sys.exc_info()[0])

def get_small_text(message):
    """formats input string with ^ for small text in reddit"""

    words = message.split()
    words_transformed = list(map(lambda x: " ^^" + x, words))
    words_together = "".join(words_transformed)
    mainlog.debug("ID: %s - Author: %s - Returning small_text message", comment.id, comment.author.name)
    return(words_together)

if __name__ == "__main__":

    prepare_logger('mainloop')
    mainlog = logging.getLogger('mainloop')

    for comment in reddit.subreddit('rdebottest').stream.comments():

        c = Reddit_Comment(comment)
        body_params = c.check_body()

        if not c.check_already_replied() and body_params:

            scope = body_params['scope']
            author = body_params['author']
            table = body_params['table']
            date = body_params['date']

            mainlog.debug("ID: %s - Author: %s - preparing message", comment.id, comment.author.name)

            m = Message(scope, author, table, date).get_message()
            mainlog.info("ID: %s - Author: %s - replying", comment.id, comment.author.name)
            mainlog.debug("ID: %s - Author: %s - replying with: %s", comment.id, comment.author.name, m)
            if not testmode: comment.reply(m)
            c.mark_as_replied()
            mainlog.debug("ID: %s - Author: %s - marked as replied to", comment.id, comment.author.name)

