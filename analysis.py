import pandas as pd
import os
import numpy as np
from geopy.distance import geodesic


def check_date_transect(df, date, transect):
    """Check that a dataset is from the day and transect we think it is"""
    if "date" in df.columns:
        assert np.all(df.eval(f"date == '{date}'"))
    if "transect" in df.columns:
        assert np.all(df.eval(f"transect == {transect}"))

    df["date"] = date
    df["transect"] = transect


def load_ground(date, transect):
    """Get a set of soil data"""
    ground = pd.read_excel(f"data/{date}_{transect}_ground.xlsx")

    # rename columns
    ground.rename(columns=str.lower, inplace=True)
    ground["soil_temperature"] = ground["soil temperature"]
    del ground["soil temperature"]

    # numerify soil moisture readings
    ground["soil_moisture"] = ground["soil moisture"].apply(
        lambda m: (
            float("nan")
            if pd.isnull(m)
            else (
                "DNW".index(m[0]) * 3
                + (1 if m[-1] in "-_" else (2 if m[-1] != "+" else 3))
            )
        )
    )
    del ground["soil moisture"]

    # Convert time data to workable variables
    for col in ["lap (out)", "lap (in)"]:
        ground[col] = pd.to_timedelta(
            ground[col].map(
                lambda time: (
                    int(time.split(" ")[0]) * 60 + float(time.split(" ")[1])
                    if " " in str(time)
                    else float(time or "nan")
                )
            ),
            unit="seconds",
        )

    ground["direction"] = "out"
    check_date_transect(ground, date, transect)

    return ground


def load_MATH_data(date, transect, layer):
    """Helper function to load data taken by MATH"""
    fname = f"data/{date}_{transect}_{layer}.csv"
    if os.path.isfile(fname):
        df = pd.read_csv(fname)
    else:
        print("Couldn't find", fname)
        df = pd.DataFrame(
            columns=[
                "boardtime",
                "temp",
                "humidity",
                "timestamp",
                "lat",
                "lon",
                "altitude",
                "fixtype",
                "satellites",
            ]
        )

    # format time data
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%H:%M:%S")
    df["boardtime"] = pd.to_timedelta(df["boardtime"], unit="milliseconds")

    check_date_transect(df, date, transect)
    return df


def add_directions(df):
    """Add `direction` column to a dataset based on the `distance` column"""
    df["direction"] = "out"
    if df.shape[0] < 2:
        return

    furthest = df["distance"].idxmax()
    df.loc[furthest:, "direction"] = "in"


def below_distances(below, ground):
    """Calculate distances and directions for below canopy based on ground laps"""
    below_samples = []
    for tcol in ["lap (out)", "lap (in)"]:
        for lap, distance in ground[[tcol, "distance"]].values:
            if pd.isnull(lap):
                continue
            sample = below.query(f"boardtime.values >= {lap.value + 1}").iloc[
                0
            ]
            below_samples.append({**sample, "distance": distance})
    below_samples = pd.DataFrame(
        below_samples, columns=[*below.columns, "distance"]
    )
    below_samples.sort_values("boardtime", inplace=True)
    add_directions(below_samples)
    return below_samples


def above_distances(above, calibrate_time=None, laps=None, turnarounds=None):
    """Calculate distances and directions for above the canopy either based on GPS information, laps taken while flying, or an approximate constant speed"""
    above = above.copy()
    if calibrate_time is not None:
        print(
            above.loc[
                above["boardtime"] <= above["boardtime"] + calibrate_time,
                ["lat", "lon"],
            ].shape
        )
        start_position = above.loc[
            above["boardtime"] <= above["boardtime"] + calibrate_time,
            ["lat", "lon"],
        ].mean(axis=0)
        print(start_position)
        above["distance"] = above[["lat", "lon"]].apply(
            lambda other: geodesic(start_position, other).meters
        )
    elif laps is not None:
        assert len(laps) == 29
        laps = pd.Series(
            [above["boardtime"][0], *laps, above["boardtime"].values[-1]]
        )
        distances = pd.Series([*range(0, 15), *range(15, -1)])
        above["distance"] = above["boardtime"].apply(
            lambda t: distances[(laps - t).abs().argmin()]
        )
    else:
        [stop_out, start_in] = turnarounds
        speed_out = 150 / (stop_out - above["boardtime"][0])
        speed_in = 150 / (above["boardtime"].values[-1] - start_in)
        print(speed_out, speed_in)
        above["distance"] = 150
        above[above["boardtime"] < stop_out, "distance"] = speed_out * (
            above["boardtime"] - above["boardtime"][0]
        )
        above[above["boardtime"] > start_in, "distance"] = 150 - speed_in * (
            above["boardtime"] - start_in
        )
    add_directions(above)
    return above
