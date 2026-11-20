import math
import requests


def haversine_km(point_a, point_b):
    lat1, lon1 = map(math.radians, point_a)
    lat2, lon2 = map(math.radians, point_b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_local_route(start, destination):
    if haversine_km(start, destination) <= 20:
        route = _get_openstreetmap_route(start, destination)
        if route:
            return route
    return _get_osrm_route(start, destination)


def _get_osrm_route(start, destination):
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{start[1]},{start[0]};{destination[1]},{destination[0]}"
    )
    try:
        response = requests.get(
            url,
            params={"overview": "full", "geometries": "geojson", "steps": "true"},
            timeout=15,
            headers={"User-Agent": "Know-Your-Way/1.0 (disaster readiness prototype)"},
        )
        response.raise_for_status()
        routes = response.json().get("routes", [])
        if not routes:
            return None
        route = routes[0]
        points = [
            (float(lat), float(lon))
            for lon, lat in route["geometry"]["coordinates"]
        ]
        directions = _osrm_directions(route.get("legs", []))
        return {
            "points": points,
            "distance_km": float(route["distance"]) / 1000,
            "directions": directions,
            "method": "OpenStreetMap road routing (OSRM)",
            "closure_status": "Live closures not checked; verify with local emergency management or DOT 511.",
            "note": "This route is not an evacuation order and may not reflect current road conditions.",
        }
    except (requests.RequestException, AttributeError, KeyError, TypeError, ValueError, IndexError):
        return None


def _osrm_directions(legs):
    directions = []
    for leg in legs:
        for step in leg.get("steps", []):
            maneuver = step.get("maneuver", {})
            action = maneuver.get("type", "continue").replace("_", " ")
            modifier = maneuver.get("modifier")
            if modifier:
                action += f" {modifier}"
            if action == "depart":
                instruction = "Start"
            elif action == "arrive":
                instruction = "Arrive at your destination"
            else:
                instruction = action.capitalize()
            name = step.get("name") or step.get("ref")
            if name:
                instruction += f" onto {name}"
            distance_km = float(step.get("distance", 0)) / 1000
            if distance_km > 0.05:
                instruction += f" ({distance_km:.1f} km)"
            directions.append(instruction)
    return directions


def _get_openstreetmap_route(start, destination):
    south = min(start[0], destination[0]) - 0.02
    north = max(start[0], destination[0]) + 0.02
    west = min(start[1], destination[1]) - 0.02
    east = max(start[1], destination[1]) + 0.02

    query = f"""
    [out:json][timeout:8];
    way["highway"]({south},{west},{north},{east});
    out geom tags;
    """
    try:
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            timeout=10,
            headers={"User-Agent": "Know-Your-Way prototype"},
        )
        response.raise_for_status()
        ways = response.json().get("elements", [])
    except (requests.RequestException, KeyError, TypeError, ValueError):
        return None

    if not ways:
        return None

    try:
        import networkx as nx
    except ImportError:
        return None

    graph = nx.DiGraph()
    for way in ways:
        geometry = way.get("geometry", [])
        tags = way.get("tags", {})
        if len(geometry) < 2:
            continue
        if _is_blocked_road(tags):
            continue
        coordinates = [(float(point["lat"]), float(point["lon"])) for point in geometry]
        one_way = str(tags.get("oneway", "")).lower()
        if tags.get("junction") == "roundabout" and not one_way:
            one_way = "yes"
        road_data = {
            "name": tags.get("name") or tags.get("ref") or "",
            "ref": tags.get("ref") or "",
        }
        for index in range(len(coordinates) - 1):
            first = coordinates[index]
            second = coordinates[index + 1]
            edge_data = dict(road_data)
            edge_data["weight"] = haversine_km(first, second)
            if one_way in {"-1", "reverse"}:
                graph.add_edge(second, first, **edge_data)
            else:
                graph.add_edge(first, second, **edge_data)
                if one_way not in {"yes", "1", "true"}:
                    graph.add_edge(second, first, **edge_data)

    if not graph:
        return None

    start_node = min(graph.nodes, key=lambda node: haversine_km(node, start))
    destination_node = min(graph.nodes, key=lambda node: haversine_km(node, destination))
    try:
        path = nx.shortest_path(graph, start_node, destination_node, weight="weight")
    except (nx.NodeNotFound, nx.NetworkXNoPath):
        return None

    route_points = [start] + path + [destination]
    distance = sum(
        haversine_km(route_points[index - 1], route_points[index])
        for index in range(1, len(route_points))
    )
    return {
        "points": route_points,
        "distance_km": distance,
        "directions": _network_directions(path, graph),
        "method": "OpenStreetMap road network (NetworkX)",
        "closure_status": "Mapped construction and access restrictions were excluded; live closures are not included.",
        "note": "Possible route only. Follow official evacuation instructions.",
    }


def _is_blocked_road(tags):
    if tags.get("highway") in {"construction", "proposed", "abandoned", "disused"}:
        return True
    if tags.get("construction") or tags.get("disused") or tags.get("abandoned"):
        return True
    if str(tags.get("status", "")).lower() in {"closed", "construction"}:
        return True
    restricted_values = {"no", "private", "closed"}
    return any(
        str(tags.get(key, "")).lower() in restricted_values
        for key in ("access", "vehicle", "motor_vehicle", "motorcar")
    )


def _network_directions(path, graph):
    instructions = []
    active_name = None
    distance = 0.0
    for first, second in zip(path, path[1:]):
        edge = graph[first][second]
        name = edge.get("name") or edge.get("ref") or "unnamed road"
        distance += float(edge.get("weight", 0))
        if active_name is not None and name != active_name:
            instructions.append(f"Continue for {distance:.1f} km, then follow {name}.")
            distance = 0.0
        active_name = name
    if active_name is not None:
        instructions.append(f"Follow {active_name} for about {distance:.1f} km.")
    return instructions
