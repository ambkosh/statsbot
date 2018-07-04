#!/usr/bin/python3.6

import pytest
import praw
from datetime import datetime
from hypothesis import given, example, assume
from hypothesis.strategies import text

from docs.conf import prawconfig
from bot import Reddit_Comment
from botmodules.sqlconnect import Comments, Submissions, make_connection
from botmodules.sqlconnectbot import Calls, make_connection_bot
from botmodules.sqldata import Data
from botmodules.make_graph import total_flair_graph
from docs.conf import connection_string, connection_string_bot



reddit = praw.Reddit(client_id=prawconfig['client_id'],
                     client_secret=prawconfig['client_secret'],
                     password=prawconfig['password'],
                     user_agent=prawconfig['user_agent'],
                     username=prawconfig['username'])

session = make_connection(connection_string)
session_bot = make_connection_bot(connection_string_bot)


def test_check_body():
    c = Reddit_Comment(reddit.comment('e1nhqob'))
    r = c.check_body()
    assert r['scope'] == 'general'
    assert r['table'] == Comments
    assert r['date'] == datetime(2018,5,7,0,0)

@given(s=text())
def test_check_body_hyp(s):
    c = Reddit_Comment(s)
    r = c.check_body()
    assert r == False

@pytest.mark.parametrize("test_input, expected",[
    (reddit.comment('e1nfmp2'), False),
    (reddit.comment('dz8tcht'), True),
    ("", True),
    (0, True),
    ('', True),
])
def test_check_already_replied(test_input, expected):
    c = Reddit_Comment(test_input)
    r = c.check_already_replied()
    assert r == expected

@pytest.mark.parametrize("date, author, table, scope, expected",[
    ('general', 'amb_kosh',     Comments,       '2018-1-1', True),
    ('general', 'amb_kosh123',  Comments,       '2018-1-1', False),
    ('general', 'amb_kosh',     Submissions,    '2018-1-1', True),
    ('general', 'amb_kosh',     Comments,       '2050-1-1', False),
    ('user',    'amb_kosh',     Comments,       '2018-1-1', True),
])
def test_check_has_data(date, author, table, scope, expected):
    d = Data(date, author, table, scope)
    r = d.check_has_data(session)
    assert  r == expected

@pytest.mark.parametrize("test_input, expected",[
    (reddit.comment('dyr42uu'), False),
    (reddit.comment('e1na4j5'), True),
    ("", True),
    (0, True),
    ('', True),
])
def test_mark_as_replied(test_input, expected):
    c = Reddit_Comment(test_input)
    r = c.mark_as_replied()
    session_bot.query(Calls.comment_id).filter(Calls.comment_id == 'e1na4j5').delete()  #delete inserted records for next tests
    session_bot.query(Calls.comment_id).filter(Calls.comment_id == '').delete()         #delete inserted records for next tests
    session_bot.query(Calls.comment_id).filter(Calls.comment_id == '0').delete()        #delete inserted records for next tests
    session_bot.commit()
    assert r == expected

@pytest.mark.parametrize("date, author, table, scope, expected_score, expected_count",[
    ('general', 'amb_kosh',     Comments,       '2018-1-1', 824, 85),
    ('general', 'amb_kosh123',  Comments,       '2018-1-1', None, 0),
    ('general', 'amb_kosh',     Submissions,    '2040-1-1', None, 0),
    ('user',    'harzach',      Comments,       '2018-1-1', 12470, 3622),
])
def test_get_score_count(date, author, table, scope, expected_score, expected_count):
    d = Data(date, author, table, scope)
    r = d.get_score_count(session)
    assert r['score'] == expected_score
    assert r['count'] == expected_count

@pytest.mark.parametrize("author, table, date, session, expected",[
    ('amb_kosh', Comments,  '2017-1-1', session, 'output/total_flair_graph.png')
])
def test_total_flair_graph(author, table, date, session, expected):
    g = total_flair_graph(author, table, date, session)
    assert g == expected

# @given(s1=text(), s2=text())
# def test_check_body_isdict(s1, s2):
#     # assume(s1 is not None and s1 is not '')
#     # assume(s2 is not None and s2 is not '')
#     s1 = "!stats de comments " + s1
#     c = Comment(s1, s2)
#     r = c.check_body()
#     assert type(r) == dict