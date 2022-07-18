"""
This script:
    - Monitors the PANO_UPLOAD directory OR it is called on that directory
    - for file in directory:
        - Extracts timestamp and GPS_lat and GPS_lon using exiftool
        - Converts the GPS coords in degrees/min/sec to decimal
        - Creates string of MD5(GPS coords, timestamp) = filename
        - Adds entry (filename, GPS_lat, GPS_lon, timestamp)
    - Execute an SQL script that orders them based on timestamp, then for ID i,   
    adds the i+1 lat,lon to next_lat, next_lon for i (potentially fill last entry with
    coordinates that would be on the same line as that made by the previous two points)
    - Execute SQL script addrtoFileID to group file ID's per address. 
    - Remove all files and their DB entry that have no references to them
    - for file in directory:
        - Changes krpano config file to create tiles at dir xx/xx/xxxx... (file string)
        - Execute krpano -config file
"""

import subprocess
import os
import json
import logging
import psycopg2
from hashlib import md5
from dotenv import load_dotenv
from dms2dec.dms_convert import dms2dec

load_dotenv()

# "50 deg 27&#39; 21.97&quot; N"

def extractMetadata(file: str):
    """ Requires exiftool installed on system!"""
    try:
        completed_proc = subprocess.run(
            ["exiftool", "-j", file], 
            capture_output=True, 
            encoding='utf-8')
        completed_proc.check_returncode()
        meta_json = json.loads(completed_proc.stdout)[0]
        return {
            'timestamp': meta_json["TimeStamp"], 
            'lat': degreesToDecimalGPS(meta_json["GPSLatitude"] + "N"), 
            'lon' :degreesToDecimalGPS(meta_json["GPSLongitude"] + "W")
            }
    except subprocess.CalledProcessError as e:
        print("exiftool error, file could not be found most likely")
    except FileNotFoundError as e:
        print("exiftool not installed on system")
    except KeyError as e:
        print("File does not contain necessary metadata")

def degreesToDecimalGPS(degrees: str):
    return round(dms2dec(
        degrees
        .replace(" ", "")
        .replace("&#39;","'")
        .replace("&quot;", '"')
        .replace("deg", "°")), 6)

def createFilePath(file_json: dict):
    """ Returns the hash of the string of the metadata and the dirpath"""
    digest = md5((str(file_json["timestamp"]) + str(file_json["lat"]) + str(file_json["lon"])).encode()).hexdigest()
    return digest, f"{digest[:2]}/{digest[2:3]}/{digest[3:]}"

def executeKrpano(file, tile_path):
    """ Requires krpano tool installed on system!"""
    krpano_dir = os.getenv('KRPANO_DIR')
    alterKrpanoConfig(f"{krpano_dir}/maketiles.config", tile_path)
    try:
        completed_proc = subprocess.run(
            [f"{krpano_dir}/krpanotools", "makepano", f"-config={krpano_dir}/maketiles.config", file],  
            encoding='utf-8')
        completed_proc.check_returncode()
    except subprocess.CalledProcessError as e:
        print("krpano error, file could not be found most likely")
    except FileNotFoundError as e:
        print("krpano not installed on system")
    except KeyError as e:
        print("File does not contain necessary metadata")

def alterKrpanoConfig(config_path, file_path):
    """
    Rewrites config lines of krpano tool to print to directory path (derived from hash)
    Be sure line 1 and 2 are:
    tilepath=
    previewpath=
    """
    with open(config_path, 'r') as config:
        lines = config.readlines()
    lines[0] = f"tilepath={os.getenv('TILE_DIR')}/{file_path}/%l/[c]/%v/%h.jpg\n"
    lines[1] = f"previewpath={os.getenv('TILE_DIR')}/{file_path}/preview.jpg\n"

    with open(config_path, 'w') as config:
        config.writelines(lines)

def addEntry(cur, file_str, lat, lon, timestamp):
    """
    Adds entry to PostgreSQL DB
    file_str varchar(32), lat numeric(11,6), lon numeric(11,6), timestamp integer
    """
    cur = conn.cursor()
    query = """ INSERT INTO files (filename, lat, lon, timestamp) VALUES (%s,%s,%s,%s)"""
    record = (file_str, lat, lon, timestamp)
    cur.execute(query, record)
    conn.commit()
 
    pass

if __name__ == "__main__":
    try:
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )

        upload_dir = os.getenv("UPLOAD_DIR")
        for filename in os.listdir(upload_dir):
            file_data = extractMetadata(f"{upload_dir}/{filename}")
            digest, file_path = createFilePath(file_data)
            addEntry(conn, digest, file_data["lat"], file_data["lon"], file_data["timestamp"])
            # executeKrpano(f"{upload_dir}/{filename}", file_path)
    except psycopg2.DatabaseError as e:
        print(e)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')
