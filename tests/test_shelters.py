from modules import shelters


class MockResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {
            "elements": [
                {
                    "type": "node",
                    "lat": 42.37,
                    "lon": -71.06,
                    "tags": {
                        "amenity": "shelter",
                        "emergency": "shelter",
                        "name": "Community Center",
                        "addr:city": "Exampletown",
                    },
                },
                {
                    "type": "way",
                    "center": {"lat": 42.36, "lon": -71.06},
                    "tags": {"emergency": "shelter"},
                },
                {
                    "type": "node",
                    "lat": 42.365,
                    "lon": -71.06,
                    "tags": {
                        "amenity": "shelter",
                        "name": "Park shelter",
                    },
                }
            ]
        }


def test_shelters_are_real_records_sorted_by_distance_and_filtered(monkeypatch):
    monkeypatch.setattr(shelters.requests, "post", lambda *args, **kwargs: MockResponse())

    result = shelters.find_nearby_shelters(42.36, -71.06)

    assert len(result) == 2
    assert result[0]["name"] == "Unnamed mapped shelter"
    assert result[0]["emergency_designated"]
    assert result[1]["name"] == "Community Center"
    assert result[1]["address"] == "Exampletown"


def test_shelter_api_failure_is_not_reported_as_no_results(monkeypatch):
    def fail(*args, **kwargs):
        raise shelters.requests.RequestException("offline")

    monkeypatch.setattr(shelters.requests, "post", fail)
    monkeypatch.setattr(shelters.requests, "get", fail)

    assert shelters.find_nearby_shelters(42.36, -71.06) is None


def test_shelter_availability_is_not_assumed_from_missing_status():
    assert shelters.get_availability({}) == (
        "Unconfirmed",
        "No current operating or opening status is published in the map data.",
    )


def test_shelter_availability_respects_published_closed_and_private_tags():
    assert shelters.get_availability({"operational_status": "closed"})[0] == "Reported closed"
    assert shelters.get_availability({"access": "private"})[0] == "Not public"


def test_nominatim_fallback_filters_non_shelter_amenity_values():
    result = shelters._from_nominatim(
        {
            "lat": "42.36",
            "lon": "-71.06",
            "category": "amenity",
            "type": "shelter",
            "extratags": {"shelter_type": "Fuel Station"},
        },
        42.36,
        -71.06,
    )

    assert result is None


def test_shelter_route_requires_emergency_designation_and_clear_alert_check():
    candidate = {
        "emergency_designated": True,
        "availability": "Unconfirmed",
        "inside_alert": False,
    }
    assert shelters.is_routeable_shelter(candidate)

    candidate["inside_alert"] = None
    assert not shelters.is_routeable_shelter(candidate)
    candidate["inside_alert"] = True
    assert not shelters.is_routeable_shelter(candidate)
    candidate["inside_alert"] = False
    candidate["availability"] = "Reported closed"
    assert not shelters.is_routeable_shelter(candidate)
    candidate["availability"] = "Unconfirmed"
    candidate["emergency_designated"] = False
    assert not shelters.is_routeable_shelter(candidate)
