import math

from modules import routing
from modules.routing import haversine_km


def test_haversine_same_point():
    assert haversine_km((42.3601, -71.0589), (42.3601, -71.0589)) == 0


def test_haversine_known_distance():
    distance = haversine_km((40.7128, -74.0060), (40.73061, -73.935242))
    assert 5 < distance < 7


def test_haversine_is_symmetric():
    point_a = (42.3601, -71.0589)
    point_b = (42.3650, -71.0600)
    assert math.isclose(haversine_km(point_a, point_b), haversine_km(point_b, point_a))


def test_route_returns_no_fabricated_line_when_services_fail(monkeypatch):
    monkeypatch.setattr(routing, "_get_openstreetmap_route", lambda start, end: None)
    monkeypatch.setattr(routing, "_get_osrm_route", lambda start, end: None)

    assert routing.build_local_route((42.36, -71.06), (42.37, -71.06)) is None


def test_closed_or_restricted_roads_are_excluded():
    assert routing._is_blocked_road({"highway": "construction"})
    assert routing._is_blocked_road({"highway": "residential", "access": "no"})
    assert not routing._is_blocked_road({"highway": "residential", "access": "yes"})


def test_osrm_steps_become_readable_directions():
    steps = routing._osrm_directions(
        [
            {
                "steps": [
                    {
                        "maneuver": {"type": "depart"},
                        "name": "Main Street",
                        "distance": 600,
                    },
                    {
                        "maneuver": {"type": "turn", "modifier": "left"},
                        "name": "First Avenue",
                        "distance": 1200,
                    },
                    {
                        "maneuver": {"type": "arrive"},
                        "name": "",
                        "distance": 0,
                    },
                ]
            }
        ]
    )

    assert steps == [
        "Start onto Main Street (0.6 km)",
        "Turn left onto First Avenue (1.2 km)",
        "Arrive at your destination",
    ]


def test_osrm_route_requests_step_data(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "routes": [
                    {
                        "distance": 1200,
                        "geometry": {
                            "coordinates": [[-71.0, 42.0], [-71.01, 42.01]]
                        },
                        "legs": [
                            {
                                "steps": [
                                    {
                                        "maneuver": {"type": "depart"},
                                        "name": "Main Street",
                                        "distance": 1200,
                                    }
                                ]
                            }
                        ],
                    }
                ]
            }

    def fake_get(*args, **kwargs):
        assert kwargs["params"]["steps"] == "true"
        return MockResponse()

    monkeypatch.setattr(routing.requests, "get", fake_get)

    result = routing._get_osrm_route((42.0, -71.0), (42.01, -71.01))

    assert result["distance_km"] == 1.2
    assert result["directions"] == ["Start onto Main Street (1.2 km)"]


def test_local_route_avoids_mapped_closed_road(monkeypatch):
    start = (42.0, -71.0)
    midpoint = (42.005, -71.01)
    end = (42.01, -71.0)

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "elements": [
                    {
                        "geometry": [
                            {"lat": start[0], "lon": start[1]},
                            {"lat": end[0], "lon": end[1]},
                        ],
                        "tags": {"highway": "primary", "status": "closed"},
                    },
                    {
                        "geometry": [
                            {"lat": start[0], "lon": start[1]},
                            {"lat": midpoint[0], "lon": midpoint[1]},
                            {"lat": end[0], "lon": end[1]},
                        ],
                        "tags": {"highway": "residential", "name": "Open Road"},
                    },
                ]
            }

    monkeypatch.setattr(routing.requests, "post", lambda *args, **kwargs: MockResponse())
    route = routing.build_local_route(start, end)

    assert route["method"] == "OpenStreetMap road network (NetworkX)"
    assert route["closure_status"].startswith("Mapped construction")
    assert midpoint in route["points"]
