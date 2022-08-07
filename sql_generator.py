from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Float, Sequence
from geoalchemy2 import Geography
from dotenv import load_dotenv
import os

load_dotenv()

# echo flag to log SQL statements to standard out
# future flag for future API 2.0 formatting
# The Engine, when first returned by create_engine(), has not actually tried 
# to connect to the database yet; that happens only the first time it is asked to perform a task against the database.
engine = create_engine(os.getenv("DB_URL"), echo=True, future=True)

# base class which maintains a catalog of classes and tables relative to that base
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# Describe the database tables we'll be dealing with,
# then define our own classes which will be mapped to those tables
def file_table_gen(city, month, year):
    class FileData(Base):
        # Table metadata
        __tablename__ = f'files_{city}/{month}{year}'

        id = Column(Integer, Sequence('file_id_seq'), primary_key=True)
        digest = Column(String)
        lat = Column(Float)
        lon = Column(Float)
        timestamp = Column(Integer)
        next_lat = Column(Float)
        next_lon = Column(Float)
        geom = Column(Geography('POINT'))

        def __repr__(self):
            return f"<FileData(address={self.file_digest}, lat={self.lat}, lon={self.lon}, geom={self.geom})>"
    return FileData

def add_file_data(data_arr, table_class):
    obj_arr = []
    for data in data_arr:
        obj_arr.append(table_class(
            digest=data["file_digest"], 
            timestamp=data['timestamp'], 
            lat=data["lat"], 
            lon=data["lon"]))
    
    session.add_all(obj_arr)
    session.commit()
    
# home = Addresses(address="2370 Park Ridge Lane", lat=44.0212259, lon=-123.1217560)
# nullAddress = Addresses(address="null address", lat=00.00000, lon=-00.00000)

# The MetaData is a registry of the data for all created sub classes of the base class
# We can use this metadata, for instance, to create all tables that do not exist yet as follows:
# FileData = file_table_gen("Eugene", "Aug", 2022)
# Base.metadata.create_all(engine)

# the instance is pending i.e. no SQL has been issued
# session.add(home) # use add_all and list of objects to do multiple at once
# session.commit()

# print(session.query(Addresses).filter(Addresses.address.in_(['2370 Park Ridge Ln.', 'null address'])))
