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
        __tablename__ = f'files_{city}_{month}{year}'

        id = Column(Integer, primary_key=True, nullable=False)
        digest = Column(String,nullable=False)
        lat = Column(Float, nullable=False)
        lon = Column(Float, nullable=False)
        timestamp = Column(Integer, nullable=False)
        next_lat = Column(Float)
        next_lon = Column(Float)
        geom = Column(Geography('POINT'))

        def __repr__(self):
            return f"<FileData(address={self.digest}, lat={self.lat}, lon={self.lon}, timestamp={self.timestamp})>"
    return FileData

def add_file_data(data_arr, table_class):
    obj_arr = []
    for data in data_arr:
        obj_arr.append(table_class(
            digest=data["file_digest"], 
            timestamp=data["timestamp"], 
            lat=data["lat"], 
            lon=data["lon"]))
    
    session.add_all(obj_arr)

def update_latlon(file_table):
    # The purpose of this function is to create
    # a heading value for each file in order to
    # create yaw values
    latlon_list = session.\
                    query(file_table).\
                    order_by(file_table.timestamp).\
                    all()
    for curr, next in zip(latlon_list, latlon_list[1:]):
        curr.next_lat = next.lat
        curr.next_lon = next.lon
    # generate the next lat/lon for the last record
    # by extending the line formed by the previous two points
    if len(latlon_list) > 2:
        next_lat, next_lon = est_latlon_list(latlon_list[-1], latlon_list[-2])
        latlon_list[-1].next_lat = next_lat
        latlon_list[-1].next_lon = next_lon
        print('EXECUTED!',next_lat,next_lon)

def update_geo_points(table):
    session.execute(
        """UPDATE "%s" SET
        geom=ST_SetSRID(ST_MakePoint(lon, lat), 4326);""" % table.__tablename__)
    

def est_latlon_list(curr, last):
    # estimates the next latlon from previous two points
    next_lat = curr.lat + curr.lat - last.lat
    next_lon = curr.lon + curr.lon - last.lon
    return (next_lat, next_lon)


    
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
