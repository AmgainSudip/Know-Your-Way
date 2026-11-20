from urllib.parse import urlencode

import folium
from folium.plugins import Fullscreen, LocateControl
import requests
import streamlit as st
from streamlit_folium import st_folium


def geocode_location(query):
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            timeout=8,
            headers={"User-Agent": "Know-Your-Way prototype"},
        )
        response.raise_for_status()
        results = response.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except (requests.RequestException, KeyError, TypeError, ValueError):
        pass
    return None


def google_maps_directions_url(destination, origin=None):
    params = {
        "api": 1,
        "destination": f'{destination["lat"]},{destination["lon"]}',
        "travelmode": "driving",
    }
    if origin is not None:
        params["origin"] = f'{origin["lat"]},{origin["lon"]}'
    return "https://www.google.com/maps/dir/?" + urlencode(params)


def create_disaster_map(origin, destination, alerts, shelters, route=None):
    center = [origin["lat"], origin["lon"]]
    if destination:
        center = [
            (origin["lat"] + destination["lat"]) / 2,
            (origin["lon"] + destination["lon"]) / 2,
        ]
    map_object = folium.Map(location=center, zoom_start=11, tiles="OpenStreetMap")
    LocateControl(
        auto_start=False,
        strings={"title": "Show my current location"},
        locateOptions={"enableHighAccuracy": True, "maxZoom": 16},
    ).add_to(map_object)
    Fullscreen(
        position="topright",
        title="Expand map",
        title_cancel="Exit full screen",
    ).add_to(map_object)

    folium.Marker(
        location=[origin["lat"], origin["lon"]],
        tooltip=f'Start: {origin["name"]}',
        icon=folium.Icon(color="blue", icon="play", prefix="fa"),
    ).add_to(map_object)
    visible_points = [
        [origin["lat"], origin["lon"]],
    ]
    if destination:
        folium.Marker(
            location=[destination["lat"], destination["lon"]],
            tooltip=f'Destination: {destination["name"]}',
            icon=folium.Icon(color="purple", icon="flag", prefix="fa"),
        ).add_to(map_object)
        visible_points.append([destination["lat"], destination["lon"]])
    for shelter in shelters[:10]:
        point = [shelter["lat"], shelter["lon"]]
        visible_points.append(point)
        folium.Marker(
            location=point,
            tooltip=shelter["name"],
            icon=folium.Icon(color="green", icon="plus-sign", prefix="glyphicon"),
        ).add_to(map_object)

    for alert in alerts:
        geometry = alert.get("polygon")
        if not geometry:
            continue
        if geometry["type"] == "Polygon":
            coordinates = [[point[1], point[0]] for point in geometry["coordinates"][0]]
            folium.Polygon(
                locations=coordinates,
                color="#b42318",
                weight=2,
                fill=True,
                fill_opacity=0.18,
                tooltip=alert["title"],
            ).add_to(map_object)

    if route:
        visible_points.extend([[lat, lon] for lat, lon in route["points"]])
        folium.PolyLine(
            locations=[[lat, lon] for lat, lon in route["points"]],
            color="#2457c5",
            weight=5,
            opacity=0.9,
            tooltip=f"{route['distance_km']:.1f} km possible route",
        ).add_to(map_object)

    map_object.fit_bounds(visible_points, padding=(24, 24))
    st_folium(map_object, width=None, height=520, returned_objects=[])
