"""
This is the entry point for the script.
It handles command line args, and logic for 
data cleaning/data entry in to postgres DB.
See README.md for more information.
"""
import src.process_imgs as pim
import src.sql_generator as sg
from src.sql_generator import FileData, Addresses, FileAddrMap
import os
from os.path import join
import argparse
from dotenv import load_dotenv
from datetime import date

def main():
    load_dotenv()
    # args = comline_parser()

    fdata_list = []
    img_time_diff = 5 # seconds
    upload_dir = os.getenv("UPLOAD_DIR")
    tile_dir = os.getenv("TILE_DIR")
    krpano_dir = os.getenv("KRPANO_DIR")
    # following specify dirs images will be moved to after
    # processing depending on whether they're tilized or not
    processed_dir = os.getenv("PROCESSED_DIR") # testing
    trash_dir = os.getenv("TRASH_DIR") # testing

    for filename in os.listdir(upload_dir):
        if filename[0] != '.':
            print(f"{upload_dir}/{filename}")
            img_mdata = pim.extract_metadata(f"{upload_dir}/{filename}")
            img_mdata["digest"] = pim.file_digest(img_mdata)
            fdata_list.append(img_mdata)
            os.rename(join(upload_dir, filename), join(upload_dir, img_mdata["digest"] + ".jpg"))
    
    # group photos based on timestamp proximity
    fdata_list.sort(key=lambda x:x["timestamp"])
    fdata_list = pim.group_by_diff(fdata_list, img_time_diff)

    for group in fdata_list:
        sg.insert_file_data(group, FileData)
        sg.update_latlon(FileData)
        sg.update_geo_points(FileData)
        sg.addr_wthin_radius(FileData, Addresses, FileAddrMap)
        sg.session.commit()
        sg.delete_unmapped_files(FileData, FileAddrMap)
        sg.session.commit()
        sg.set_yaw_vals(FileData, Addresses, FileAddrMap)
        sg.session.commit()
    # tilize all mapped files
    sub_query =  (sg.session.query(FileAddrMap.file_id)
                    .distinct())
    query = (sg.session
                    .query(FileData.digest)
                    .filter(FileData.id.in_(sub_query))).all()
    
    tilize_list = [r for (r,) in query]
    print(tilize_list)
    for filename in os.listdir(upload_dir):
        #  to remove [:-4] .jpg extension
        if filename[:-4] in tilize_list:
            filepath = join(upload_dir, filename)
            print(f"filepath: {filepath}\ntile_dir: {tile_dir}\n krpano_dir: {krpano_dir}")
            pim.execute_krpano(filepath,filename[:-4], tile_dir, krpano_dir)
            os.replace(filepath, join(processed_dir,filename))
        else:
            os.replace(join(upload_dir,filename), join(trash_dir,filename))
        
    sg.session.close()


def comline_parser():
    months = [
            "JAN", "FEB", "MAR", 
            "APR", "MAY", "JUN", 
            "JUL", "AUG", "SEP", 
            "OCT", "NOV", "DEC"
            ]

    parser = argparse.ArgumentParser(
        description=
        ("""***Requires exif and krpano commandline exes***\n\n"""
        +"""Tool that:
        - Uploads img timestamp and GPS coords to db 
        - Performs geo operations
        - Filters photos based on proximity to home coordinates
        - Tilizes images with format for marzipano
        - Adds tiles to tile directory\n\n"""
        + """A .env file is needed that specifies the variables:
        - DB_URL= format ex: postgresql://USER:PASS@SERVER_IP:PORT/DB_NAME
        - UPLOAD_DIR= Dir that contains photo files (defaults to current dir)
        - TILE_DIR= Dir to create tiles (defaults to current dir)
        - KRPANO_EXE= Path to execute krpano tool"""),
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("city", 
                    help="city name where route was driven")
    parser.add_argument("month", 
                    help="month in which the photo file/s were captured")
    parser.add_argument("year", type=int, 
                    help="year in which the photo file/s were captured")
    parser.add_argument("-f", "--file", nargs=1, 
                    help="optionally specify a photo file (defaults to all in the current dir)")

    args = parser.parse_args()
    args.month = args.month[:3].upper()
    args.city = args.city.upper()
    if not (args.month in months):
        raise Exception("Not a valid month")
    if not (2011 < args.year <= date.today().year):
        raise Exception("Not a valid year")
    try:
        with open("cities.csv", "r") as cities:
            valid = False
            cities_csv = cities.readlines()
            for c in cities_csv:
                if args.city.lower() == c.replace('"', "").strip().lower():
                    valid = True
                    break
            if not valid:
                raise Exception(f"No city matching csv\n{cities_csv}")

    except FileNotFoundError:
        print(f"cities.csv not found... using {args.city} for table naming")
    except:
        raise Exception(f'city "{args.city}" does not match any city found in cities.csv')
    
    if args.file:
        if not os.path.exists(args.file[0]):
            raise Exception(f"File {args.file[0]} not found")

    return args

if __name__ == '__main__':
    main()