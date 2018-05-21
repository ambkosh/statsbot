# -*- coding: utf-8 -*-
#!/usr/bin/env python


from sqlalchemy import create_engine, Column, String, Sequence, Integer, DateTime, Boolean, func, Date, and_, funcfilter, ForeignKey, TEXT, distinct
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

class Calls(Base):

    __tablename__ = 'calls'

    id          = Column(Integer, primary_key=True)
    comment_id  = Column(String(10))

class Hashes(Base):

    __tablename__ = 'hashes'

    id          = Column(Integer, primary_key=True)
    md5         = Column(String(12))



def make_connection_bot(connection_string):
    """makes the connection to the bot database"""
    engine = create_engine(connection_string)
    connection = engine.connect()
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

