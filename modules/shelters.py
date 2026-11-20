import math

import requests

from modules.routing import haversine_km


OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def find_nearby_shelters(lat, lon, radius_m=15000):
    query = f"""
    [out:json][timeout:8];
    (
      nwr(around:{radius_m},{lat},{lon})["amenity"="shelter"];
      nwr(around:{radius_m},{lat},{lon})["emergency"="shelter"];
      nwr(around:{radius_m},{lat},{lon})["social_facility"="shelter"];
    );
    out center tags;
    """
    try:
        response = requests.post(
            OVERPASS_URL,
            data=query,
            timeout=9,
            headers={"User-Agent": "Know-Your-Way/1.0 (disaster readiness prototype)"},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
            raise ValueError("Unexpected Overpass response shape")
        elements = payload["elements"]
    except (requests.RequestException, AttributeError, KeyError, TypeError, ValueError):
        elements = _search_nominatim(lat, lon, radius_m)
        if elements is None:
            return None

    shelters = []
    seen = set()
    for element in elements:
        if "extratags" in element:
            shelter = _from_nominatim(element, lat, lon)
        else:
            shelter = _from_overpass(element, lat, lon)
        if shelter is None or not shelter["emergency_designated"]:
            continue
        if shelter["distance_km"] > radius_m / 1000:
            continue
        identity = (
            shelter["name"],
            round(shelter["lat"], 5),
            round(shelter["lon"], 5),
        )
        if identity in seen:
            continue
        seen.add(identity)
        shelters.append(shelter)

    shelters.sort(
        key=lambda shelter: (
            shelter["availability"] in {"Reported closed", "Not public"},
            shelter["distance_km"],
        )
    )
    return shelters


def _search_nominatim(lat, lon, radius_m):
    latitude_delta = radius_m / 111000
    longitude_delta = radius_m / (111000 * max(0.2, abs(math.cos(math.radians(lat)))))
    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "amenity": "shelter",
                "format": "jsonv2",
                "limit": 50,
                "viewbox": (
                    f"{lon - longitude_delta},{lat + latitude_delta},"
                    f"{lon + longitude_delta},{lat - latitude_delta}"
                ),
                "bounded": 1,
                "addressdetails": 1,
                "extratags": 1,
            },
            timeout=8,
            headers={"User-Agent": "Know-Your-Way/1.0 (disaster readiness prototype)"},
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else None
    except (requests.RequestException, KeyError, TypeError, ValueError):
        return None


def _from_overpass(element, lat, lon):
    if not isinstance(element, dict):
        return None
    tags = element.get("tags", {})
    if not isinstance(tags, dict):
        return None
    center = element.get("center", element)
    if "lat" not in center or "lon" not in center:
        return None
    return _make_shelter(
        tags=tags,
        lat=float(center["lat"]),
        lon=float(center["lon"]),
        origin=(lat, lon),
        osm_type=element.get("type"),
        osm_id=element.get("id"),
    )


def _from_nominatim(element, lat, lon):
    if not isinstance(element, dict):
        return None
    try:
        point = (float(element["lat"]), float(element["lon"]))
    except (KeyError, TypeError, ValueError):
        return None
    tags = dict(element.get("extratags") or {})
    if element.get("category") == "amenity" and element.get("type") == "shelter":
        tags["amenity"] = "shelter"
    return _make_shelter(
        tags=tags,
        lat=point[0],
        lon=point[1],
        origin=(lat, lon),
        osm_type=element.get("osm_type"),
        osm_id=element.get("osm_id"),
        fallback_name=element.get("name") or element.get("display_name", "").split(",")[0],
        fallback_address=element.get("display_name", ""),
    )


def _make_shelter(tags, lat, lon, origin, osm_type, osm_id,
                  fallback_name=None, fallback_address=None):
    shelter_type = str(tags.get("shelter_type", "")).lower()
    if shelter_type in {
        "public_transport",
        "bus_stop",
        "sun_shelter",
        "gazebo",
        "weather_shelter",
        "lean_to",
        "parking",
        "animal_shelter",
    }:
        return None
    valid_types = {
        "emergency",
        "basic_hut",
        "field_shelter",
        "picnic_shelter",
        "tornado_shelter",
        "winter_shelter",
        "public_building",
    }
    if shelter_type and shelter_type not in valid_types:
        return None

    name = tags.get("name") or tags.get("operator") or fallback_name or "Unnamed mapped shelter"
    address = " ".join(
        part
        for part in (
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
            tags.get("addr:city"),
        )
        if part
    ) or fallback_address or ""
    availability, availability_note = get_availability(tags)
    if tags.get("emergency") == "shelter" or shelter_type == "emergency":
        designation = "Tagged as an emergency shelter in OpenStreetMap"
    elif tags.get("social_facility") == "shelter":
        designation = "Tagged as a social-service shelter in OpenStreetMap"
    else:
        designation = "Not specifically designated as an emergency shelter"

    return {
        "name": name,
        "kind": shelter_type.replace("_", " ").title() or "Purpose not specified",
        "designation": designation,
        "availability": availability,
        "availability_note": availability_note,
        "opening_hours": tags.get("opening_hours", ""),
        "address": address,
        "lat": lat,
        "lon": lon,
        "distance_km": haversine_km(origin, (lat, lon)),
        "inside_alert": None,
        "emergency_designated": (
            tags.get("emergency") == "shelter"
            or shelter_type == "emergency"
        ),
        "osm_url": _osm_url(osm_type, osm_id),
        "source": "OpenStreetMap",
    }


def get_availability(tags):
    status = (
        str(tags.get("operational_status", tags.get("status", "")))
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )
    access = str(tags.get("access", "")).strip().lower()
    if status in {"closed", "not_operational", "disused", "abandoned", "temporarily_closed"}:
        return "Reported closed", f"OpenStreetMap operational status is {status.replace('_', ' ')}."
    if access in {"no", "private", "customers"}:
        return "Not public", f"OpenStreetMap access is tagged {access}."
    if status in {"open", "operational"}:
        return "Reported open", "OpenStreetMap reports this facility as operational; this is not a live confirmation."
    hours = tags.get("opening_hours")
    if hours:
        if str(hours).strip().lower() in {"off", "closed"}:
            return "Reported closed", f"OpenStreetMap opening hours are tagged {hours}."
        return "Unconfirmed", f"Published hours: {hours}. Current opening status has not been verified."
    return "Unconfirmed", "No current operating or opening status is published in the map data."


def is_routeable_shelter(shelter):
    return (
        shelter.get("emergency_designated") is True
        and shelter.get("availability") not in {"Reported closed", "Not public"}
        and shelter.get("inside_alert") is False
    )


def _osm_url(osm_type, osm_id):
    if not osm_type or not osm_id:
        return ""
    return f"https://www.openstreetmap.org/{osm_type}/{osm_id}"
