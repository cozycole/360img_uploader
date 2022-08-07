"""
This script:
    - Called on PANO_UPLOAD directory
    - for file in directory:
        - Extracts timestamp and GPS_lat and GPS_lon using exiftool (PYTHON)
        - Converts the GPS coords in degrees/min/sec to decimal (PYTHON)
        - Creates string of MD5(GPS coords, timestamp) = filename (PYTHON)
        - Adds entry (filename, GPS_lat, GPS_lon, timestamp) (PYTHON)
    - Execute an SQL script that orders them based on timestamp, then for ID i,   
    adds the i+1 lat,lon to next_lat, next_lon for i (potentially fill last entry with
    coordinates that would be on the same line as that made by the previous two points)
    - Execute SQL script addrtoFileID to group file ID's per address. 
    - Remove all files and their DB entry that have no references to them
    - for file in directory:
        - Changes krpano config file to create tiles at dir xx/x/xxxxx... (file string)
        - Execute krpano -config file
"""

import subprocess
import os
import json
import logging
import psycopg2
from hashlib import md5
from dms2dec.dms_convert import dms2dec

def extract_metadata(file: str):
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
            'lat': deg_to_dec(meta_json["GPSLatitude"] + "N"), 
            'lon' :deg_to_dec(meta_json["GPSLongitude"] + "W")
            }
    except subprocess.CalledProcessError as e:
        print("exiftool error, file could not be found")
    except FileNotFoundError as e:
        print("exiftool not installed on system")
    except KeyError as e:
        print("File does not contain necessary metadata")

def deg_to_dec(degrees: str):
    # "50 deg 27&#39; 21.97&quot; N" is 
    # an example lat/lon metadata for Insta360 photos
    return round(dms2dec(
        degrees
        .replace(" ", "")
        .replace("&#39;","'")
        .replace("&quot;", '"')
        .replace("deg", "°")), 6)

def digest_filepath(digest):
    """ Returns the hash of the string of the metadata for the dirpath"""
    return f"{digest[:2]}/{digest[2:3]}/{digest[3:]}"

def file_digest(file_json):
    data = "".join(str(i) for i in [file_json["timestamp"],file_json["lat"],file_json["lon"]])
    return md5(data.encode()).hexdigest()

def execute_krpano(file, tile_path):
    """ Requires krpano tool installed on system!"""
    krpano_dir = os.getenv('KRPANO_EXE')
    alter_krpano_config(f"{krpano_dir}/maketiles.config", tile_path)
    try:
        completed_proc = subprocess.run(
            [f"{krpano_dir}/krpanotools", "makepano", f"-config={krpano_dir}/maketiles.config", file],  
            encoding='utf-8')
        completed_proc.check_returncode()
    except subprocess.CalledProcessError as e:
        print("krpano error, file could not be found\n", e)
    except FileNotFoundError as e:
        print("krpano tool not found\n", e)
    except KeyError as e:
        print("File does not contain necessary metadata\n", e)

def alter_krpano_config(config_path, file_path):
    """
    Rewrites config lines of krpano tool to print to directory path (derived from hash)
    Be sure line 1 and 2 start with "tilepath=" and "previewpath=" respectively.
    """

    with open(config_path, 'r') as config:
        lines = config.readlines()
    # We are modifying the config file for krpano such that it creates the
    # tile photos in the directory dictated by the file path hash
    lines[0] = f"tilepath={os.getenv('TILE_DIR')}/{file_path}/%l/[c]/%v/%h.jpg\n"
    lines[1] = f"previewpath={os.getenv('TILE_DIR')}/{file_path}/preview.jpg\n"

    with open(config_path, 'w') as config:
        config.writelines(lines)
