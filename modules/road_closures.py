from datetime import datetime, timezone
import math

import requests


DRIVENC_EVENTS_URL = "https://www.drivenc.gov/api/v2/get/event"
ROWAN_COUNTY = "rowan"


def get_drivenc_events(api_key):
    if not api_key:
        return None

    try:
        response = requests.get(
            DRIVENC_EVENTS_URL,
            params={"key": api_key, "format": "json"},
            timeout=12,
            headers={"User-Agent": "Know-Your-Way/1.0 (disaster readiness prototype)"},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return None
    except (requests.RequestException, AttributeError, TypeError, ValueError):
        return None

    return [event for event in payload if isinstance(event, dict) and _is_current(event)]


def events_for_county(events, county):
    county_name = str(county).strip().casefold()
    return [
        event
        for event in events
        if str(event.get("County", "")).strip().casefold() == county_name
    ]


def events_near_route(events, route_points, threshold_km=0.35):
    if len(route_points) < 2:
        return []

    nearby = []
    for event in events:
        event_points = _event_points(event)
        if (
            event_points
            and _paths_may_be_near(route_points, event_points, threshold_km)
            and _paths_distance_km(route_points, event_points) <= threshold_km
        ):
            nearby.append(event)
    return nearby


def is_full_closure(event):
    value = event.get("IsFullClosure", False)
    is_full = value is True or str(value).strip().casefold() in {"true", "1", "yes"}
    return is_full and str(event.get("EventType", "")).casefold() == "closures"


def _is_current(event):
    now = datetime.now(timezone.utc).timestamp()
    try:
        start_timestamp = float(event.get("StartDate"))
    except (TypeError, ValueError):
        start_timestamp = 0
    try:
        end_timestamp = float(event.get("PlannedEndDate"))
    except (TypeError, ValueError):
        end_timestamp = 0
    return not (
        (start_timestamp > now)
        or (end_timestamp > 0 and end_timestamp < now)
    )


def _event_points(event):
    encoded = event.get("EncodedPolyline")
    if encoded:
        decoded = _decode_polyline(encoded)
        if decoded:
            return decoded

    points = []
    for latitude_key, longitude_key in (
        ("Latitude", "Longitude"),
        ("LatitudeSecondary", "LongitudeSecondary"),
    ):
        try:
            latitude = float(event[latitude_key])
            longitude = float(event[longitude_key])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(latitude) and math.isfinite(longitude):
            if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                points.append((latitude, longitude))
    return points


def _decode_polyline(encoded):
    points = []
    latitude = longitude = index = 0
    try:
        while index < len(encoded):
            latitude_delta, index = _decode_component(encoded, index)
            longitude_delta, index = _decode_component(encoded, index)
            latitude += latitude_delta
            longitude += longitude_delta
            points.append((latitude / 1e5, longitude / 1e5))
    except (IndexError, TypeError, ValueError):
        return []
    return points


def _decode_component(encoded, index):
    result = shift = 0
    while True:
        value = ord(encoded[index]) - 63
        index += 1
        result |= (value & 0x1F) << shift
        shift += 5
        if value < 0x20:
            break
        if shift > 60:
            raise ValueError("Invalid encoded polyline")
    delta = ~(result >> 1) if result & 1 else result >> 1
    return delta, index


def _paths_distance_km(path_a, path_b):
    reference_latitude = sum(point[0] for point in path_a + path_b) / (
        len(path_a) + len(path_b)
    )
    projected_a = [_project(point, reference_latitude) for point in path_a]
    projected_b = [_project(point, reference_latitude) for point in path_b]
    segments_a = list(zip(projected_a, projected_a[1:]))
    segments_b = list(zip(projected_b, projected_b[1:]))

    if not segments_a:
        segments_a = [(projected_a[0], projected_a[0])]
    if not segments_b:
        segments_b = [(projected_b[0], projected_b[0])]

    return min(
        _segment_distance_km(segment_a, segment_b)
        for segment_a in segments_a
        for segment_b in segments_b
    )


def _paths_may_be_near(path_a, path_b, threshold_km):
    reference_latitude = sum(point[0] for point in path_a + path_b) / (
        len(path_a) + len(path_b)
    )
    latitude_margin = threshold_km / 111.32
    longitude_margin = threshold_km / (
        111.32 * max(0.01, math.cos(math.radians(reference_latitude)))
    )
    for axis, margin in ((0, latitude_margin), (1, longitude_margin)):
        range_a = [point[axis] for point in path_a]
        range_b = [point[axis] for point in path_b]
        if (
            max(range_a) + margin < min(range_b)
            or max(range_b) + margin < min(range_a)
        ):
            return False
    return True


def _project(point, reference_latitude):
    latitude, longitude = point
    x = longitude * 111.32 * math.cos(math.radians(reference_latitude))
    y = latitude * 111.32
    return x, y


def _segment_distance_km(segment_a, segment_b):
    a1, a2 = segment_a
    b1, b2 = segment_b
    if _segments_intersect(a1, a2, b1, b2):
        return 0.0
    return min(
        _point_segment_distance(point, segment)
        for point, segment in (
            (a1, segment_b),
            (a2, segment_b),
            (b1, segment_a),
            (b2, segment_a),
        )
    )


def _point_segment_distance(point, segment):
    start, end = segment
    delta_x = end[0] - start[0]
    delta_y = end[1] - start[1]
    length_squared = delta_x * delta_x + delta_y * delta_y
    if length_squared == 0:
        return math.dist(point, start)
    fraction = max(
        0.0,
        min(
            1.0,
            ((point[0] - start[0]) * delta_x + (point[1] - start[1]) * delta_y)
            / length_squared,
        ),
    )
    closest = (start[0] + fraction * delta_x, start[1] + fraction * delta_y)
    return math.dist(point, closest)


def _segments_intersect(a1, a2, b1, b2):
    def orientation(first, second, third):
        return (second[0] - first[0]) * (third[1] - first[1]) - (
            second[1] - first[1]
        ) * (third[0] - first[0])

    def on_segment(first, second, point):
        return (
            min(first[0], second[0]) <= point[0] <= max(first[0], second[0])
            and min(first[1], second[1]) <= point[1] <= max(first[1], second[1])
        )

    orientations = (
        orientation(a1, a2, b1),
        orientation(a1, a2, b2),
        orientation(b1, b2, a1),
        orientation(b1, b2, a2),
    )
    if orientations[0] * orientations[1] < 0 and orientations[2] * orientations[3] < 0:
        return True
    return (
        (orientations[0] == 0 and on_segment(a1, a2, b1))
        or (orientations[1] == 0 and on_segment(a1, a2, b2))
        or (orientations[2] == 0 and on_segment(b1, b2, a1))
        or (orientations[3] == 0 and on_segment(b1, b2, a2))
    )
