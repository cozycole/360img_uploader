"""
This is the entry point for the script.
It handles command line args, and logic for data cleaning/data entry in DB.
See README.md for more information.
"""

import process_imgs as pim
import sql_generator as sg
import argparse
import os
from dotenv import load_dotenv
from datetime import date

def main():
    load_dotenv()
    args = comline_parser()
    if (args.file):
        pass
    else:
        fdata_arr = []
        upload_dir = os.getenv("UPLOAD_DIR")
        FileTable = sg.file_table_gen(args.city, args.month, args.year)
        sg.Base.metadata.create_all(sg.engine)

        # for filename in os.listdir(upload_dir):
        #     img_mdata = pim.extract_metadata(f"{upload_dir}/{filename}")
        #     img_mdata["file_digest"] = pim.file_digest(img_mdata)
        #     fdata_arr.append(img_mdata)
        # sg.add_file_data(fdata_arr, FileTable)
        sg.update_latlon(FileTable)
    sg.session.close()
    # try:
    #     print('Connecting to the PostgreSQL database...')
    #     conn = psycopg2.connect(
    #         host=os.getenv("DB_HOST"),
    #         database=os.getenv("DB_NAME"),
    #         user=os.getenv("DB_USER"),
    #         password=os.getenv("DB_PASSWORD")
    #     )

    #     upload_dir = os.getenv("UPLOAD_DIR")
    #     for filename in os.listdir(upload_dir):
    #         file_data = pi.extractMetadata(f"{upload_dir}/{filename}")
    #         digest, file_path = pi.createFilePath(file_data)
    #         pi.addEntry(conn, digest, file_data["lat"], file_data["lon"], file_data["timestamp"])
    #         # executeKrpano(f"{upload_dir}/{filename}", file_path)
    # except psycopg2.DatabaseError as e:
    #     print(e)
    # finally:
    #     if conn is not None:
    #         conn.close()
    #         print('Database connection closed.')


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
            for c in cities.readlines():
                if args.city.lower() == c.replace('"', "").strip().lower():
                    valid = True
                    break
            if not valid:
                raise Exception("No city matching csv")

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