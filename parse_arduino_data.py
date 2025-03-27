import csv
import os


def parse_adafruit_latlon(coord):
    """Bad black magic to turn the nasty GPS format from the Adafruit module into good numbers"""
    direction = coord[-1]
    coord = coord[:-1]
    coord = float(coord)
    degrees = int(coord / 100)
    minutes = coord - degrees * 100
    coord = degrees + minutes / 60
    if direction in "SW":
        coord *= -1
    return coord


def parse_arduino_dataline(line):
    try:
        [
            boardtime,
            temp,
            humidity,
            timestamp,
            lat,
            lon,
            altitude,
            fixtype,
            satellites,
        ] = line.split(",")
    except:
        print("error parsing", line)
        raise
    boardtime = int(boardtime)
    temp = float(temp)
    humidity = float(humidity)
    lat = parse_adafruit_latlon(lat)
    lon = parse_adafruit_latlon(lon)
    altitude = float(altitude)
    fixtype = ["No Fix", "GPS", "DGPS"][int(fixtype)]
    satellites = int(satellites)
    return [
        boardtime,
        temp,
        humidity,
        timestamp,
        lat,
        lon,
        altitude,
        fixtype,
        satellites,
    ]


def parseupdate(getline):
    status = parse_arduino_dataline(getline())
    savedfiles = {}
    while True:
        filename = getline()
        if filename[0] == "/":
            taking_data = filename[1] == "T"
            corrupted_files = int(filename[2:])
            break
        savedfiles[filename] = int(getline())
    return taking_data, corrupted_files, status, savedfiles


def save_data_to(where, getline):
    saved_files = 0
    while True:
        fname = getline()
        if not fname:
            break
        saved_files += 1
        with open(os.path.join(where, fname), "w", newline="") as f:
            f.write(
                "boardtime,temp,humidity,timestamp,lat,lon,altitude,fixtype,satellites\n"
            )
            writer = csv.writer(f)
            while True:
                line = getline()
                if not line:
                    break
                writer.writerow(parse_arduino_dataline(line))
    return saved_files
