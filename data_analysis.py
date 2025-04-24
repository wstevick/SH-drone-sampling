import pandas as pd
from geopy.distance import geodesic
import geopandas as gpd


def load_data(transect, date):
    ground = pd.read_excel(f"data/{date}_{transect}_ground.xlsx")
    ground.rename(columns=str.lower, inplace=True)
    ground['soil_temperature'] = ground['soil temperature']
    del ground['soil temperature']
    for col in ["lap (out)", "lap (in)"]:
        ground[col] = pd.to_timedelta(
            ground[col].map(
                lambda time: (
                    int(time.split(" ")[0]) * 60 + float(time.split(" ")[1])
                    if " " in str(time)
                    else float(time)
                )
            ),
            unit="seconds",
        )

    ground["transect"] = transect
    ground["date"] = date

    below = pd.read_csv(f"data/{date}_{transect}_below.csv")
    below = gpd.GeoDataFrame(
        below,
        geometry=gpd.points_from_xy(
            below["lon"], below["lat"], below["altitude"]
        ),
        crs="EPSG:4326",
    )
    below["timestamp"] = pd.to_datetime(below["timestamp"], format="%H:%M:%S")
    below["boardtime"] = pd.to_timedelta(
        below["boardtime"], unit="milliseconds"
    )

    below["transect"] = transect
    below["date"] = date

    try:
        above = pd.read_csv(f"data/{date}_{transect}_above.csv")
    except FileNotFoundError:
        above = gpd.GeoDataFrame(
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
                "date",
                "transect",
            ]
        )
    else:
        above = gpd.GeoDataFrame(
            above,
            geometry=gpd.points_from_xy(
                above["lon"], above["lat"], above["altitude"]
            ),
            crs="EPSG:4326",
        )
        above.query("lat != 0 and lon != 0", inplace=True)
        above["timestamp"] = pd.to_datetime(
            above["timestamp"], format="%H:%M:%S"
        )
        above["boardtime"] = pd.to_timedelta(
            above["boardtime"], unit="milliseconds"
        )

        above["transect"] = transect
        above["date"] = date

    below_samples = []
    for out, in_, distance in ground[
        ["lap (out)", "lap (in)", "distance"]
    ].values:
        if pd.isnull(out):
            continue
        out_sample = below.query(f"boardtime.values >= {out.value}").iloc[0]
        below_samples.append(
            {**out_sample, "distance": distance, "direction": "out"}
        )
        if not pd.isnull(in_):
            in_sample = below.query(f"boardtime.values >= {in_.value}").iloc[0]
            below_samples.append(
                {**in_sample, "distance": distance, "direction": "in"}
            )
    below_samples = gpd.GeoDataFrame(
        below_samples,
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
            "distance",
            "direction",
            "date",
            "transect",
        ],
    )
    below_samples.sort_values("boardtime", inplace=True)

    above_distances = []
    for above_lat, above_lon in above[["lat", "lon"]].values:
        closest_points_road_distance = float("nan")
        distance_to_closest = float("inf")
        for below_lat, below_lon, below_road_distance in below_samples[
            ["lat", "lon", "distance"]
        ].values:
            distance_to_this = geodesic(
                (above_lat, above_lon), (below_lat, below_lon)
            ).meters
            if distance_to_this < distance_to_closest:
                distance_to_closest = distance_to_this
                closest_points_road_distance = below_road_distance
        above_distances.append(closest_points_road_distance)
    above["distance"] = above_distances

    return ground, below_samples, above


def combine_data(data):
    return data.groupby(['date', 'transect', 'distance'])[['temp', 'humidity']].mean()


def merge(df1, df2, suffixes):
    return df1.merge(df2, on=['date', 'transect', 'distance'], how='outer', suffixes=suffixes)


dates = ['04-03', '04-04']
