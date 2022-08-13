from sqlalchemy import create_engine, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Numeric
from geoalchemy2 import Geography
from dotenv import load_dotenv
import os

load_dotenv()

engine = create_engine(os.getenv("DB_URL"), echo=True, future=True)

# base class which maintains a catalog of classes and tables relative to that base
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

class FileAddrMap(Base):
    __tablename__ = "file_address_map"
    addr_id = Column(Integer, ForeignKey("lane_addrs.id"), primary_key=True, nullable=False)
    file_id = Column(Integer, ForeignKey("image_metadata.id"), primary_key=True, nullable=False)
    yaw = Column(Float)
    
    def __repr__(self):
        return f"<FileAddrMap(id={self.id}, addr_id={self.addr_id}, img_id={self.img_id})>"


class Addresses(Base):
    __tablename__ = "lane_addrs"
    id = Column(Integer, primary_key=True, unique=True, nullable=False)
    addr = Column(String(100), nullable=False)
    city = Column(String(30))
    lat = Column(Numeric(11,6), nullable=False)
    lon = Column(Numeric(11,6), nullable=False)
    geom = Column(Geography('POINT'))


class FileData(Base):
    __tablename__ = "image_metadata"

    id = Column(Integer, primary_key=True, nullable=False)
    digest = Column(String,unique=True, nullable=False)
    lat = Column(Numeric(11,6), nullable=False)
    lon = Column(Numeric(11,6), nullable=False)
    timestamp = Column(Integer, nullable=False)
    next_lat = Column(Numeric(11,6))
    next_lon = Column(Numeric(11,6))
    geom = Column(Geography('POINT'))

    def __repr__(self):
        return f"<FileData(address={self.digest}, lat={self.lat}, lon={self.lon}, timestamp={self.timestamp})>"


def insert_file_data(data_arr, table_class):
    for data in data_arr:
        try:
            session.execute(
                insert(table_class).\
                    values(**data).\
                        on_conflict_do_nothing(
                    index_elements=['digest']
                )
            )
        except:
            print("issue adding to db")

def update_latlon(file_table):
    # The purpose of this function is to create
    # a heading value for each file in order to
    # create yaw values for the pano viewer
    latlon_list = session.\
                    query(file_table).\
                    where(or_(file_table.next_lat == None, 
                            file_table.next_lon == None)).\
                    order_by(file_table.timestamp).\
                    all()
    if len(latlon_list) < 2:
        return

    for curr, next in zip(latlon_list, latlon_list[1:]):
        curr.next_lat = next.lat
        curr.next_lon = next.lon
    # generate the next lat/lon for the last record
    # by extending the line formed by the previous two points
    if len(latlon_list) > 2:
        next_lat, next_lon = est_latlon_list(latlon_list[-1], latlon_list[-2])
        latlon_list[-1].next_lat = next_lat
        latlon_list[-1].next_lon = next_lon

def est_latlon_list(curr, last):
    # estimates the next latlon from previous two points
    next_lat = curr.lat + curr.lat - last.lat
    next_lon = curr.lon + curr.lon - last.lon
    return (next_lat, next_lon)

def update_geo_points(table):
    session.execute(
        """UPDATE "%s" SET
        geom=ST_SetSRID(ST_MakePoint(lon, lat), 4326);""" % (table.__tablename__))
    
def addr_wthin_radius(file_table, addr_table_name, fa_map_table):
    session.execute(
        """INSERT INTO "%s" (addr_id, file_id)
        SELECT la.id, f.id
        FROM "%s" as la
        JOIN "%s" as f
        ON ST_DWithin(
            ST_Transform(la.geom::geometry, 3857),
            ST_Transform(f.geom::geometry, 3857),
            50
        ) ON CONFLICT DO NOTHING
        """ % (fa_map_table.__tablename__,
                addr_table_name.__tablename__,
                file_table.__tablename__)
    )

def delete_unmapped_files(file_table, fa_map_table):
    # delete all images with no house within 50 meters
    # which was previously found with addr_wthin_radius(..)
    session.execute("""DELETE FROM "%s" as im
        WHERE im.id NOT IN 
        (SELECT DISTINCT file_id FROM "%s");
        """ % (file_table.__tablename__,
                fa_map_table.__tablename__))

def set_yaw_vals(file_table, addr_table, fa_map_table):
    session.execute("""UPDATE "%s" as fa
        SET yaw=(SELECT (2*PI() - (ATAN2((a.lat - f.lat),(a.lon - f.lon))) - (PI() - (ATAN2((f.lat - f.next_lat), (f.lon - f.next_lon)))))
                FROM "%s" as f
                JOIN "%s" as a
                ON a.id = fa.addr_id
                WHERE a.id=fa.addr_id AND f.id=fa.file_id);
        """ % (fa_map_table.__tablename__,
                file_table.__tablename__,
                addr_table.__tablename__))

Base.metadata.create_all(engine)
