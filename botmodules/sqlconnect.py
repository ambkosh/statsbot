# -*- coding: utf-8 -*-
#!/usr/bin/env python


from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, func, Date, and_, funcfilter, ForeignKey, TEXT, distinct
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Submissions(Base):

    __tablename__ = 'submissionslarge'

    id          = Column(Integer, primary_key=True)
    postid      = Column(String(10))
    datum       = Column(DateTime)
    title       = Column(String(2000))
    flair       = Column(String(250))
    autor       = Column(String(250))
    num_komments= Column(Integer)
    score       = Column(Integer)
    selfpost    = Column(Boolean)
    domain      = Column(String(250))
    datumtag    = Column(DateTime)
    num_crossposts= Column(Integer)
    over18      = Column(Boolean)
    gilded      = Column(Integer)
    ups         = Column(Integer)
    downs       = Column(Integer)
    stickied    = Column(Boolean)



class Comments(Base):

    __tablename__ = 'comments'

    id              = Column(Integer, primary_key=True)
    commentid       = Column(String(10), nullable=False, unique=True)
    postid          = Column(String(10), ForeignKey("submissionslarge.postid"), nullable=False)
    subredditid     = Column(String(10), nullable=False)
    autor           = Column(String(250))
    body            = Column(TEXT(convert_unicode=True))
    score           = Column(Integer)
    subredditname   = Column(String(200))
    datum           = Column(DateTime)
    autorflair      = Column(String(200))
    datumtag        = Column(DateTime)
    gilded          = Column(Integer)
    ups             = Column(Integer)
    downs           = Column(Integer)
    controversiality= Column(Integer)
    depth           = Column(Integer)
    replies         = Column(Integer)
    parentid        = Column(String(10))
    isroot          = Column(Boolean)




def make_connection(connection_string):
    """makes the connection to the postgres-server"""
    engine = create_engine(connection_string)
    connection = engine.connect()
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

