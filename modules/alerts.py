import requests


def get_nws_alerts(lat, lon):
    try:
        response = requests.get(
            f"https://api.weather.gov/alerts/active?point={lat},{lon}",
            timeout=8,
            headers={"User-Agent": "Know-Your-Way/1.0 (disaster readiness prototype)"},
        )
        response.raise_for_status()
        features = response.json().get("features", [])
    except (requests.RequestException, KeyError, TypeError, ValueError):
        return None

    alerts = []
    for feature in features:
        properties = feature.get("properties", {})
        alerts.append(
            {
                "title": properties.get("event", "Weather alert"),
                "severity": properties.get("severity", "Unknown"),
                "description": properties.get("description", "No description provided."),
                "instruction": properties.get("instruction", ""),
                "effective": _format_time(properties.get("effective")),
                "polygon": feature.get("geometry"),
                "url": feature.get("id", ""),
            }
        )
    severity_rank = {"extreme": 4, "severe": 3, "moderate": 2, "minor": 1, "unknown": 0}
    alerts.sort(
        key=lambda item: severity_rank.get(str(item["severity"]).lower(), 0),
        reverse=True,
    )
    return alerts


def _format_time(value):
    if not value:
        return "Now"
    return str(value).replace("T", " ").replace("Z", " UTC")[:16]
