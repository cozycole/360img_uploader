import subprocess
import os
from os import path
import json
from hashlib import md5
from dms2dec.dms_convert import dms2dec

def group_by_diff(stamp_arr, time_diff):
    """ Groups list of dictionary elements based on timestamp difference"""
    grouped_arr = []
    if type(time_diff) != int:
        raise Exception("group_by_diff: time difference not an int")
    if not stamp_arr or type(stamp_arr) != list:
        raise Exception("group_by_diff: Empty array/not an array")
    if len(stamp_arr) == 1:
        grouped_arr.append(stamp_arr)

    curr_arr = [stamp_arr[0]]
    for curr, next in zip(stamp_arr, stamp_arr[1:]):
        if next["timestamp"] - curr["timestamp"] > time_diff:
            grouped_arr.append(curr_arr)
            curr_arr = [next]
        else:
            curr_arr.append(next)
        #append the last grouping
        if next == stamp_arr[-1]:
            grouped_arr.append(curr_arr)
    return grouped_arr

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
            "timestamp": meta_json["TimeStamp"], 
            "lat": deg_to_dec(meta_json["GPSLatitude"] + "N"), 
            "lon" :deg_to_dec(meta_json["GPSLongitude"] + "W")
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
    print(file_json)
    data = "".join(str(i) for i in [file_json["timestamp"],file_json["lat"],file_json["lon"]])
    return md5(data.encode()).hexdigest()

def execute_krpano(file_path,filename,  tile_path, krpano_dir):
    """ Requires krpano tool installed on system!"""
    config_file = path.join(krpano_dir, "maketiles.config")
    krpano_tool = path.join(krpano_dir, "krpanotools")
    alter_krpano_config(config_file, tile_path, digest_filepath(filename)) # filename is a hash
    try:
        completed_proc = subprocess.run(
            [krpano_tool, "makepano", f"-config={krpano_dir}/maketiles.config", file_path],  
            encoding='utf-8')
        completed_proc.check_returncode()
    except subprocess.CalledProcessError as e:
        print("krpano error, file could not be found\n", e)
    except FileNotFoundError as e:
        print("krpano tool not found\n", e)
    except KeyError as e:
        print("File does not contain necessary metadata\n", e)

def alter_krpano_config(config_path, tile_path, file_path):
    """
    Rewrites config lines of krpano tool to print to directory path (derived from hash)
    Be sure line 1 and 2 start with "tilepath=" and "previewpath=" respectively.
    It will overwrite those lines; whatever they may be.
    """
    print(f"configpath: {config_path}\ntile_path: {tile_path}\nfilepath: {file_path}")
    with open(config_path, "r") as config:
        lines = config.readlines()
    # We are modifying the config file for krpano such that it creates the
    # tile photos in the directory dictated by the file path hash
    full_tpath = path.join(tile_path, file_path, "%l","[c]","%v","%h.jpg")
    full_ppath = path.join(tile_path, file_path, "preview.jpg")
    lines[0] = f"tilepath={full_tpath}\n"
    lines[1] = f"previewpath={full_ppath}\n"
    print("TILEPATH: ", lines[0])
    print("PREVIEWPATH: ", lines[1])

    with open(config_path, "w") as config:
        config.writelines(lines)
