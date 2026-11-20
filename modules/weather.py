import requests


def get_weather(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,wind_speed_10m,weather_code",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "auto",
    }
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params=params,
            timeout=8,
            headers={"User-Agent": "Know-Your-Way prototype"},
        )
        response.raise_for_status()
        current = response.json()["current"]
        return {
            "temperature": float(current.get("temperature_2m", 0)),
            "precipitation": float(current.get("precipitation", 0)),
            "wind": float(current.get("wind_speed_10m", 0)),
            "condition": _weather_condition(current.get("weather_code")),
        }
    except (requests.RequestException, KeyError, TypeError, ValueError):
        return None


def _weather_condition(code):
    code = int(code or 0)
    if code == 0:
        return "Clear"
    if code in (1, 2):
        return "Mostly clear"
    if code == 3:
        return "Overcast"
    if code in (45, 48):
        return "Fog"
    if code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        return "Rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow"
    if code in (95, 96, 99):
        return "Thunderstorm"
    return "Cloudy"
