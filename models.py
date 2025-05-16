from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, ARRAY

Base = declarative_base()


class Candle(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    notes = Column(String, nullable=False)
    description = Column(Text)
    tags = Column(ARRAY(String))
