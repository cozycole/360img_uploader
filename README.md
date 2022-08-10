# 360img_uploader

Command line tool that loads the time and location metadata of 360 photos into a postgres database.
It then tileizes them if they meet spatial requirements (the coordinates are within a certain distance
of a house in the address db table).
