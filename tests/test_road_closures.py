from datetime import datetime, timedelta, timezone

from modules import road_closures


def test_drive_nc_fetch_uses_developer_key_and_returns_current_events(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            now = datetime.now(timezone.utc).timestamp()
            return [
                {"ID": 1, "County": "Rowan", "PlannedEndDate": None},
                {
                    "ID": 2,
                    "County": "Rowan",
                    "PlannedEndDate": now - 3600,
                },
                {
                    "ID": 3,
                    "County": "Rowan",
                    "StartDate": now + 3600,
                },
            ]

    def fake_get(url, **kwargs):
        assert url == road_closures.DRIVENC_EVENTS_URL
        assert kwargs["params"] == {"key": "test-key", "format": "json"}
        return MockResponse()

    monkeypatch.setattr(road_closures.requests, "get", fake_get)

    assert road_closures.get_drivenc_events("test-key") == [
        {"ID": 1, "County": "Rowan", "PlannedEndDate": None}
    ]


def test_drive_nc_fetch_without_key_is_unverified(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("The feed should not be requested without a key")

    monkeypatch.setattr(road_closures.requests, "get", fail_if_called)

    assert road_closures.get_drivenc_events("") is None


def test_events_are_filtered_by_county_case_insensitively():
    events = [
        {"County": "Rowan"},
        {"County": "Iredell"},
        {"County": " ROWAN "},
    ]

    assert road_closures.events_for_county(events, "rowan") == [
        {"County": "Rowan"},
        {"County": " ROWAN "},
    ]


def test_route_match_detects_nearby_event_and_ignores_distant_event():
    route = [(35.67, -80.48), (35.67, -80.46)]
    events = [
        {
            "ID": 1,
            "Latitude": 35.6701,
            "Longitude": -80.47,
        },
        {
            "ID": 2,
            "Latitude": 35.68,
            "Longitude": -80.47,
        },
    ]

    assert road_closures.events_near_route(events, route) == [events[0]]


def test_route_match_detects_intersecting_event_polyline():
    event = {
        "EncodedPolyline": "_p~iF~ps|U_ulLnnqC_mqNvxq`@",
    }

    decoded = road_closures._decode_polyline(event["EncodedPolyline"])
    assert decoded == [
        (38.5, -120.2),
        (40.7, -120.95),
        (43.252, -126.453),
    ]
    assert road_closures.events_near_route([event], decoded) == [event]


def test_only_full_closure_events_block_route():
    assert road_closures.is_full_closure(
        {"EventType": "closures", "IsFullClosure": True}
    )
    assert road_closures.is_full_closure(
        {"EventType": "closures", "IsFullClosure": "true"}
    )
    assert not road_closures.is_full_closure(
        {"EventType": "roadwork", "IsFullClosure": True}
    )
    assert not road_closures.is_full_closure(
        {"EventType": "closures", "IsFullClosure": False}
    )
