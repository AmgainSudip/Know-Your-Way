from urllib.parse import parse_qs, urlsplit

from modules import maps


def test_google_maps_url_uses_selected_origin_when_provided():
    url = maps.google_maps_directions_url(
        {"lat": 35.67, "lon": -80.47},
        {"lat": 35.68, "lon": -80.48},
    )

    assert parse_qs(urlsplit(url).query) == {
        "api": ["1"],
        "destination": ["35.67,-80.47"],
        "origin": ["35.68,-80.48"],
        "travelmode": ["driving"],
    }


def test_google_maps_url_omits_origin_to_allow_device_location():
    url = maps.google_maps_directions_url({"lat": 35.67, "lon": -80.47})

    assert parse_qs(urlsplit(url).query) == {
        "api": ["1"],
        "destination": ["35.67,-80.47"],
        "travelmode": ["driving"],
    }


def test_route_map_includes_device_location_and_fullscreen_controls(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        maps,
        "st_folium",
        lambda map_object, **kwargs: captured.update(map=map_object, options=kwargs),
    )

    maps.create_disaster_map(
        {"name": "Start", "lat": 35.67, "lon": -80.48},
        {"name": "Shelter", "lat": 35.68, "lon": -80.47},
        [],
        [],
        {
            "points": [(35.67, -80.48), (35.675, -80.475), (35.68, -80.47)],
            "distance_km": 2.1,
        },
    )

    child_types = {type(child).__name__ for child in captured["map"]._children.values()}
    assert "LocateControl" in child_types
    assert "Fullscreen" in child_types
    assert captured["options"]["height"] == 520
