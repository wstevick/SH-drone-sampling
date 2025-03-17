import sys

import pandas as pd

data = pd.read_csv(
    sys.argv[1],
    names=[
        "boardtime",
        "temp",
        "humidity",
        "timestamp",
        "lat",
        "lon",
        "altitude",
        "fixtype",
        "satellites",
    ],
)


def to_hms(total_seconds):
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    assert ((hours * 60) + minutes) * 60 + seconds == total_seconds
    return f"{hours}:{minutes}:{seconds}"


period = data["boardtime"].iloc[-1]
period /= 1000
period = round(period)
print(to_hms(period), "of data")

seconds_of_data = len(data) * 3
seconds_taken = round(
    (data["boardtime"].iloc[-1] - data["boardtime"].iloc[0]) / 1000 + 3
)
if seconds_of_data != seconds_taken:
    print(seconds_taken - seconds_of_data, "seconds missing")

isna = data["temp"].isna() | data["humidity"].isna()
print(to_hms((~isna).sum() * 3), "of useful data")

if isna.sum() != 0:
    first_nan_row = data[isna].iloc[0]
    print(
        "first nan row was at",
        to_hms(round(first_nan_row["boardtime"] / 1000)),
    )
    last_nonnan_row = data[~isna].iloc[-1]
    print(
        "last non-nan row was at",
        to_hms(round(last_nonnan_row["boardtime"] / 1000)),
    )
