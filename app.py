import os

import streamlit as st

from modules.alerts import get_nws_alerts
from modules.maps import (
    create_disaster_map,
    geocode_location,
    google_maps_directions_url,
)
from modules.road_closures import (
    ROWAN_COUNTY,
    events_for_county,
    events_near_route,
    get_drivenc_events,
    is_full_closure,
)
from modules.routing import build_local_route
from modules.shelters import find_nearby_shelters, is_routeable_shelter
from modules.weather import get_weather


SHELTER_RESULTS_VERSION = 3
LOCATION_DEFAULTS_VERSION = 2
SALISBURY = {"name": "Salisbury, NC", "lat": 35.6709727, "lon": -80.4742261}


st.set_page_config(
    page_title="Know Your Way",
    page_icon="🧭",
    layout="centered",
)

st.markdown(
    """
    <style>
      .stApp { background: #f3f6fa; color: #172b4d; }
      [data-testid="stAppViewContainer"] { background: #f3f6fa; }
      [data-testid="stHeader"] { background: rgba(243, 246, 250, 0.96); }
      .block-container { max-width: 820px; padding-top: 2rem; padding-bottom: 3rem; }
      h1, h2, h3, p, label, li, [data-testid="stMarkdownContainer"] {
        color: #172b4d !important;
      }
      [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
        color: #46566b !important;
      }
      [data-testid="stForm"] {
        background: #ffffff !important;
        border: 1px solid #d8e1eb !important;
        border-radius: 14px;
        padding: 20px;
      }
      [data-testid="stForm"] label,
      [data-testid="stForm"] p,
      [data-testid="stForm"] span {
        color: #172b4d !important;
      }
      input::placeholder,
      textarea::placeholder {
        color: #65758a !important;
        opacity: 1;
      }
      div[data-testid="stAlert"],
      div[data-testid="stAlert"] > div {
        background-color: #edf4f8 !important;
        border: 1px solid #cbd9e6 !important;
        border-radius: 10px;
      }
      div[data-testid="stAlert"] > div > div,
      div[data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
        background-color: transparent !important;
      }
      div[data-testid="stAlert"] p,
      div[data-testid="stAlert"] div,
      div[data-testid="stAlert"] span {
        color: #172b4d !important;
      }
      [data-testid="stExpander"] {
        background: #edf4f8 !important;
        border: 1px solid #cbd9e6 !important;
        border-radius: 10px;
      }
      [data-testid="stExpander"] summary,
      [data-testid="stExpander"] summary p,
      [data-testid="stExpander"] p,
      [data-testid="stExpander"] li {
        color: #172b4d !important;
      }
      [data-testid="stExpander"] details,
      [data-testid="stExpander"] details > summary,
      [data-testid="stExpander"] details > div {
        background: #edf4f8 !important;
      }
      [data-testid="stExpander"] details > summary:hover,
      [data-testid="stExpander"] details > summary:active,
      [data-testid="stExpander"] details > summary:focus,
      [data-testid="stExpander"] details > summary:focus-visible {
        background: #dceaf2 !important;
        color: #172b4d !important;
      }
      [data-testid="stExpander"] details > summary:focus-visible {
        outline: 2px solid #83a9bf;
        outline-offset: -2px;
      }
      [data-testid="stVerticalBlock"],
      [data-testid="stHorizontalBlock"] {
        color: #172b4d;
      }
      [data-testid="stMarkdownContainer"] strong,
      [data-testid="stMarkdownContainer"] code {
        color: #172b4d !important;
      }
      [data-testid="stMetric"] {
        background: #ffffff !important;
        border: 1px solid #d8e1eb;
        border-radius: 14px;
        padding: 18px 20px;
      }
      [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {
        color: #52647a !important;
      }
      [data-testid="stMetricValue"], [data-testid="stMetricValue"] div {
        color: #12355b !important;
      }
      .st-key-weather_metrics [data-testid="stHorizontalBlock"] {
        display: grid !important;
        grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
        gap: 0.6rem !important;
      }
      .st-key-weather_metrics [data-testid="stColumn"] {
        width: auto !important;
        min-width: 0 !important;
        flex: initial !important;
      }
      .st-key-weather_metrics [data-testid="stMetric"] {
        padding: 12px 10px;
      }
      input, textarea, [data-baseweb="select"] > div {
        background: #ffffff !important;
        color: #172b4d !important;
      }
      input, textarea { -webkit-text-fill-color: #172b4d !important; }
      [data-baseweb="select"] * { color: #172b4d !important; }
      div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        border-radius: 10px;
        min-height: 2.8rem;
        font-weight: 650;
        color: #176849 !important;
        border-color: #9dc9b7 !important;
        background: #ffffff !important;
      }
      div.stButton > button[kind="primary"],
      div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
        color: #ffffff !important;
        border-color: #176849 !important;
        background: #176849 !important;
      }
      div.stButton > button[kind="primary"] *,
      div[data-testid="stFormSubmitButton"] > button[kind="primary"] * {
        color: #ffffff !important;
      }
      .st-key-shelter_211_link [data-testid="stLinkButton"] a {
        background: #d9f3e5 !important;
        border: 1px solid #83c7a2 !important;
        color: #176849 !important;
        font-weight: 650;
      }
      .st-key-shelter_211_link [data-testid="stLinkButton"] a * {
        color: #176849 !important;
      }
      .st-key-shelter_211_link [data-testid="stLinkButton"] a:hover {
        background: #c8ecd8 !important;
        border-color: #65b88b !important;
        color: #14583e !important;
      }
      .st-key-shelter_211_link [data-testid="stLinkButton"] a:hover * {
        color: #14583e !important;
      }
      .st-key-current_location_navigation [data-testid="stLinkButton"] a,
      .st-key-selected_start_navigation [data-testid="stLinkButton"] a {
        background: #d9f3e5 !important;
        border: 1px solid #83c7a2 !important;
        color: #176849 !important;
        font-weight: 650;
      }
      .st-key-current_location_navigation [data-testid="stLinkButton"] a *,
      .st-key-selected_start_navigation [data-testid="stLinkButton"] a * {
        color: #176849 !important;
      }
      .st-key-selected_start_navigation [data-testid="stLinkButton"] a {
        background: #ffffff !important;
      }
      .st-key-current_location_navigation [data-testid="stLinkButton"] a:hover,
      .st-key-current_location_navigation [data-testid="stLinkButton"] a:active,
      .st-key-current_location_navigation [data-testid="stLinkButton"] a:focus-visible,
      .st-key-selected_start_navigation [data-testid="stLinkButton"] a:hover,
      .st-key-selected_start_navigation [data-testid="stLinkButton"] a:active,
      .st-key-selected_start_navigation [data-testid="stLinkButton"] a:focus-visible {
        background: #c8ecd8 !important;
        border-color: #65b88b !important;
        color: #14583e !important;
        box-shadow: 0 0 0 0.2rem rgba(101, 184, 139, 0.25);
      }
      .st-key-current_location_navigation [data-testid="stLinkButton"] a:hover *,
      .st-key-current_location_navigation [data-testid="stLinkButton"] a:active *,
      .st-key-current_location_navigation [data-testid="stLinkButton"] a:focus-visible *,
      .st-key-selected_start_navigation [data-testid="stLinkButton"] a:hover *,
      .st-key-selected_start_navigation [data-testid="stLinkButton"] a:active *,
      .st-key-selected_start_navigation [data-testid="stLinkButton"] a:focus-visible * {
        color: #14583e !important;
      }
      [data-testid="stExpander"] [data-testid="stLinkButton"] a {
        background: #d9f3e5 !important;
        border: 1px solid #83c7a2 !important;
        color: #176849 !important;
        font-weight: 650;
      }
      [data-testid="stExpander"] [data-testid="stLinkButton"] a *,
      [data-testid="stExpander"] [data-testid="stLinkButton"] a:hover *,
      [data-testid="stExpander"] [data-testid="stLinkButton"] a:active *,
      [data-testid="stExpander"] [data-testid="stLinkButton"] a:focus *,
      [data-testid="stExpander"] [data-testid="stLinkButton"] a:focus-visible * {
        color: #176849 !important;
      }
      [data-testid="stExpander"] [data-testid="stLinkButton"] a:hover,
      [data-testid="stExpander"] [data-testid="stLinkButton"] a:active,
      [data-testid="stExpander"] [data-testid="stLinkButton"] a:focus,
      [data-testid="stExpander"] [data-testid="stLinkButton"] a:focus-visible {
        background: #c8ecd8 !important;
        border-color: #65b88b !important;
        color: #14583e !important;
        box-shadow: 0 0 0 0.2rem rgba(101, 184, 139, 0.25);
      }
      [data-testid="stExpander"] [data-testid="stLinkButton"] a:hover *,
      [data-testid="stExpander"] [data-testid="stLinkButton"] a:active *,
      [data-testid="stExpander"] [data-testid="stLinkButton"] a:focus *,
      [data-testid="stExpander"] [data-testid="stLinkButton"] a:focus-visible * {
        color: #14583e !important;
      }
      .risk-card {
        border-radius: 16px;
        padding: 20px 22px;
        color: #ffffff !important;
        margin: 12px 0 18px;
      }
      .risk-card h2, .risk-card p { color: #ffffff !important; margin: 0; }
      .risk-card p { margin-top: 6px; opacity: 0.96; }
      .risk-extreme { background: #8f1d1d; }
      .risk-high { background: #b93825; }
      .risk-elevated { background: #8a5a08; }
      .risk-low { background: #176849; }
      .risk-unknown { background: #46566b; }
      .source-note { color: #46566b !important; font-size: 0.86rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Know Your Way")
st.caption("Understand local risk, find mapped shelters, and plan a possible route.")

if st.session_state.get("location_defaults_version") != LOCATION_DEFAULTS_VERSION:
    st.session_state.origin = SALISBURY.copy()
    st.session_state.destination = None
    st.session_state.origin_input = SALISBURY["name"]
    st.session_state.destination_input = ""
    st.session_state.location_defaults_version = LOCATION_DEFAULTS_VERSION
else:
    if "origin_input" not in st.session_state:
        st.session_state.origin_input = SALISBURY["name"]
    if "destination_input" not in st.session_state:
        st.session_state.destination_input = ""

with st.form("location_form"):
    st.subheader("Where are you going?")
    origin_text = st.text_input(
        "From",
        key="origin_input",
        placeholder="Starting address, city, or ZIP",
    )
    destination_text = st.text_input(
        "To",
        key="destination_input",
        placeholder="Destination address, city, or ZIP",
    )
    submitted = st.form_submit_button("Check locations", type="primary", use_container_width=True)

if submitted:
    if not origin_text.strip():
        st.error("Enter a starting location.")
    else:
        with st.spinner("Finding your locations..."):
            origin_coords = geocode_location(origin_text.strip())
            destination_coords = (
                geocode_location(destination_text.strip())
                if destination_text.strip()
                else None
            )
        if origin_coords is None:
            st.error(f"Could not find the starting location: {origin_text}")
        elif destination_text.strip() and destination_coords is None:
            st.error(f"Could not find the destination: {destination_text}")
        else:
            st.session_state.origin = {
                "name": origin_text.strip(),
                "lat": origin_coords[0],
                "lon": origin_coords[1],
            }
            st.session_state.destination = (
                {
                    "name": destination_text.strip(),
                    "lat": destination_coords[0],
                    "lon": destination_coords[1],
                }
                if destination_coords
                else None
            )
            st.session_state.pop("route", None)
            st.session_state.pop("route_target", None)
            st.session_state.pop("route_destination", None)
            st.session_state.pop("shelters_origin", None)
            st.session_state.pop("shelters", None)

origin = st.session_state.origin
destination = st.session_state.get("destination")


@st.cache_data(ttl=300)
def cached_alerts(lat, lon):
    return get_nws_alerts(lat, lon)


@st.cache_data(ttl=300)
def cached_weather(lat, lon):
    return get_weather(lat, lon)


@st.cache_data(ttl=600)
def cached_shelters(lat, lon):
    shelters = find_nearby_shelters(lat, lon)
    if shelters is None:
        return None
    return [shelter for shelter in shelters if shelter["emergency_designated"]]


@st.cache_data(ttl=120)
def cached_drivenc_events(api_key):
    return get_drivenc_events(api_key)


drivenc_api_key = os.getenv("DRIVENC_API_KEY", "").strip()
drivenc_events = cached_drivenc_events(drivenc_api_key) if drivenc_api_key else None


with st.spinner("Checking conditions near your starting point..."):
    alerts = cached_alerts(origin["lat"], origin["lon"])
    weather = cached_weather(origin["lat"], origin["lon"])

alert_signature = None if alerts is None else tuple(
    (alert["title"], alert["severity"], alert["effective"], alert["url"])
    for alert in alerts
)


def severity_for(current_alerts):
    if current_alerts is None:
        return "ALERT STATUS UNKNOWN", "unknown", "Official alerts could not be retrieved"
    if not current_alerts:
        return "NO ACTIVE ALERTS", "low", "No active NWS alerts were returned for this point"
    labels = " ".join(
        alert["title"] + " " + str(alert["severity"]) for alert in current_alerts
    ).lower()
    if any(word in labels for word in ("tornado", "extreme", "flash flood", "hurricane")):
        return "EXTREME RISK", "extreme", "Treat official instructions as urgent"
    if any(word in labels for word in ("warning", "major", "severe")):
        return "HIGH RISK", "high", "An active warning requires prompt action"
    return "ELEVATED RISK", "elevated", "Stay informed and review the official guidance"


level, css_level, guidance = severity_for(alerts)
st.markdown(
    f'<div class="risk-card risk-{css_level}"><h2>{level}</h2>'
    f'<p>{guidance} · Near {origin["name"]}</p></div>',
    unsafe_allow_html=True,
)

st.subheader("Current conditions near your starting point")
if weather is None:
    st.warning("Live weather is currently unavailable. No sample readings are shown.")
else:
    with st.container(key="weather_metrics"):
        temperature, precipitation, wind = st.columns(3)
        temperature.metric("Temperature", f'{weather["temperature"]:.1f}°F')
        precipitation.metric("Precipitation", f'{weather["precipitation"]:.2f} in')
        wind.metric("Wind", f'{weather["wind"]:.1f} mph')
    st.caption(weather["condition"])

alert_count = len(alerts) if alerts is not None else "unavailable"
with st.expander(f"Official alerts · {alert_count}", expanded=False):
    if alerts is None:
        st.warning("Could not retrieve NWS alerts. Check the National Weather Service directly.")
    elif alerts:
        for alert in alerts[:5]:
            with st.container(border=True):
                st.markdown(f'**{alert["title"]}**')
                st.caption(f'{str(alert["severity"]).upper()} · {alert["effective"]}')
                st.write(alert["description"][:700])
                if alert["instruction"]:
                    st.info(alert["instruction"][:500])
                if alert["url"]:
                    st.link_button("Open official NWS alert", alert["url"])
    else:
        st.info("No active NWS alerts were returned for the starting point. This does not guarantee conditions are safe.")

st.subheader("Find a shelter")
st.caption(
    "Search mapped shelter facilities near your starting point. Only locations explicitly tagged as emergency shelters can be selected as route targets; confirm that a shelter is open with local officials before traveling."
)
if st.button("Find mapped shelters nearby", use_container_width=True):
    with st.spinner("Searching OpenStreetMap for nearby shelter listings..."):
        found_shelters = cached_shelters(
            origin["lat"],
            origin["lon"],
        )
        if found_shelters is not None:
            found_shelters = sorted(
                found_shelters,
                key=lambda shelter: (
                    shelter["availability"] in {"Reported closed", "Not public"},
                    not shelter["emergency_designated"],
                    shelter["distance_km"],
                ),
            )[:5]
        for shelter in found_shelters or []:
            shelter_alerts = cached_alerts(shelter["lat"], shelter["lon"])
            shelter["active_alerts"] = shelter_alerts
            shelter["inside_alert"] = (
                None if shelter_alerts is None else bool(shelter_alerts)
            )
        if found_shelters is not None:
            found_shelters = sorted(
                found_shelters,
                key=lambda shelter: (
                    shelter["inside_alert"] is True,
                    shelter["availability"] in {"Reported closed", "Not public"},
                    not shelter["emergency_designated"],
                    shelter["distance_km"],
                ),
            )
        st.session_state.shelters = found_shelters
    st.session_state.shelters_origin = (origin["lat"], origin["lon"])
    st.session_state.shelters_alert_signature = alert_signature
    st.session_state.shelters_version = SHELTER_RESULTS_VERSION

if (
    st.session_state.get("shelters_version") != SHELTER_RESULTS_VERSION
    or st.session_state.get("shelters_origin") != (origin["lat"], origin["lon"])
    or st.session_state.get("shelters_alert_signature") != alert_signature
):
    shelters = "not-searched"
else:
    shelters = st.session_state.get("shelters")

if shelters == "not-searched":
    st.info("Search OpenStreetMap to see shelter locations mapped near your starting point.")
elif shelters is None:
    st.warning("OpenStreetMap shelter data could not be retrieved. Try again later.")
elif not shelters:
    st.info(
        "No nearby facility explicitly tagged as an emergency shelter was found in the map data. Check 211 or local emergency management for an official open shelter."
    )
else:
    st.caption("The nearest results are checked individually against current NWS alerts at each location.")
    for shelter_index, shelter in enumerate(shelters[:8]):
        with st.container(border=True):
            st.markdown(f'**{shelter["name"]}** · {shelter["distance_km"]:.1f} km')
            st.caption(
                f'{shelter["kind"]} · {shelter["designation"]}'
                + (f'\n\n{shelter["address"]}' if shelter["address"] else "")
            )
            if shelter["availability"] == "Reported closed":
                st.error(f'{shelter["availability"]}: {shelter["availability_note"]}')
            elif shelter["availability"] == "Not public":
                st.warning(f'{shelter["availability"]}: {shelter["availability_note"]}')
            else:
                st.warning(
                    f'{shelter["availability"]}: {shelter["availability_note"]}'
                )
            if shelter["opening_hours"]:
                st.caption(f'Published hours: {shelter["opening_hours"]}')
            if shelter["inside_alert"] is True:
                st.error("This facility is inside an active NWS alert area; it is not suggested as a safer destination.")
            elif shelter["inside_alert"] is None:
                st.warning("Could not retrieve official alert status at this facility.")
            else:
                st.info("No active NWS alerts were returned for this location. This does not guarantee safety.")
            if shelter.get("active_alerts"):
                st.error(
                    "Active NWS alerts here: "
                    + ", ".join(alert["title"] for alert in shelter["active_alerts"][:3])
                )
            if shelter["osm_url"]:
                st.link_button("View source and facility details", shelter["osm_url"])
            if not shelter["emergency_designated"]:
                st.info("This mapped location is not designated as an emergency shelter and will not be offered as an evacuation route target.")

with st.container(key="shelter_211_link"):
    nc211_column, local_211_column = st.columns(2)
    nc211_column.link_button(
        "Search NC 211 resources",
        "https://nc211.org/",
        use_container_width=True,
    )
    local_211_column.link_button(
        "Find your local 211",
        "https://www.211.org/about-us/your-local-211",
        use_container_width=True,
    )
st.caption(
    f'Enter "{origin["name"]}" in the 211 site’s location field to search nearby resources. '
    "NC 2-1-1 is available 24/7; call 2-1-1 for local referrals. "
    "Confirm shelter availability with local emergency officials before traveling."
)

st.subheader("Plan a possible route")
if destination:
    st.write(f'**From:** {origin["name"]}  \n**To:** {destination["name"]}')
else:
    st.info("Enter a destination above, or choose an eligible shelter from the search results.")

route_target = None
if destination and st.button(
    "Route to entered destination", type="primary", use_container_width=True
):
    destination_alerts = cached_alerts(destination["lat"], destination["lon"])
    if destination_alerts:
        st.session_state.pop("route", None)
        st.session_state.pop("route_target", None)
        st.session_state.pop("route_destination", None)
        st.error("NWS reports active alerts at the entered destination. Review these alerts before deciding whether to travel.")
        for alert in destination_alerts[:3]:
            st.warning(f'{alert["title"]} — {alert["instruction"] or alert["description"][:300]}')
    else:
        if destination_alerts is None:
            st.warning("Could not check NWS alerts at the destination. Verify local conditions before traveling.")
        route_target = destination

if isinstance(shelters, list):
    routeable_shelters = [
        shelter
        for shelter in shelters
        if is_routeable_shelter(shelter)
    ]
    if shelters and not routeable_shelters:
        st.warning(
            "Could not confirm an emergency-designated shelter outside active NWS alerts. Check 211 or local emergency management for an open shelter."
        )
    for shelter_index, shelter in enumerate(routeable_shelters[:5]):
        if st.button(
            f'Route to {shelter["name"]}',
            key=f"route_shelter_{shelter_index}_{shelter['lat']}_{shelter['lon']}",
            use_container_width=True,
        ):
            route_target = shelter

with st.expander("Salisbury / Rowan County official resources", expanded=False):
    st.markdown(
        "- **Shelter availability:** NC 2-1-1 is available 24/7 at "
        "[nc211.org](https://nc211.org/) or [call 2-1-1](tel:211). "
        "The referral service can confirm local resources; map data cannot confirm a shelter is open.\n"
        "- **County emergency notices:** [Rowan County Alert Center]"
        "(https://www.rowancountync.gov/AlertCenter.aspx)\n"
        "- **Road conditions and closures:** [NCDOT DriveNC]"
        "(https://drivenc.gov/) or call **511** in North Carolina "
        "(877-511-4662 outside the state)."
    )
    if not drivenc_api_key:
        st.warning(
            "Live DriveNC event checks are not configured in this app. "
            "Set the DRIVENC_API_KEY environment variable to enable automated checks."
        )
    elif drivenc_events is None:
        st.warning(
            "The DriveNC feed could not be retrieved. Road closures are not verified; "
            "check DriveNC directly before traveling."
        )
    else:
        rowan_events = events_for_county(drivenc_events, ROWAN_COUNTY)
        if rowan_events:
            st.caption(
                f"DriveNC currently reports {len(rowan_events)} traffic event(s) "
                "in Rowan County:"
            )
            for event in rowan_events[:8]:
                st.markdown(
                    f'- **{event.get("RoadwayName") or "Roadway"}** · '
                    f'{event.get("EventType", "event")}: '
                    f'{event.get("Description") or "See DriveNC for details"}'
                )
        else:
            st.success("DriveNC returned no current traffic events for Rowan County.")
        st.caption(
            "DriveNC events are checked from the NCDOT feed and cached for up to two minutes. "
            "The feed may be delayed or incomplete."
        )

if route_target is not None:
    with st.spinner("Looking for a road route..."):
        route = build_local_route(
            (origin["lat"], origin["lon"]),
            (route_target["lat"], route_target["lon"]),
        )
    if route is None:
        st.session_state.pop("route", None)
        st.session_state.pop("route_destination", None)
        st.error("No road route could be found. Try a closer destination or consult a navigation service.")
    else:
        route_events = (
            events_near_route(drivenc_events, route["points"])
            if drivenc_events is not None
            else None
        )
        full_closures = (
            [event for event in route_events if is_full_closure(event)]
            if route_events is not None
            else []
        )
        if full_closures:
            st.session_state.pop("route", None)
            st.session_state.pop("route_target", None)
            st.session_state.pop("route_destination", None)
            closure = full_closures[0]
            st.error(
                "DriveNC reports a full closure near this possible route: "
                f'{closure.get("RoadwayName") or "roadway"}. '
                "This route is not shown as usable. Check the official DriveNC detour "
                "and follow local emergency instructions."
            )
        else:
            if route_events is None:
                route["closure_status"] = (
                    "Live NCDOT closures were not checked; verify with DriveNC or call 511."
                )
            elif route_events:
                route["closure_status"] = (
                    f"DriveNC reports {len(route_events)} event(s) near this route; "
                    "review them before traveling."
                )
            else:
                route["closure_status"] = (
                    "DriveNC reports no full closures near this route; "
                    "conditions may change."
                )
            st.session_state.route = route
            st.session_state.route_target = route_target["name"]
            st.session_state.route_destination = route_target

route = st.session_state.get("route")
if route:
    st.success(f'Possible route to {st.session_state.route_target}')
    st.metric("Estimated road distance", f'{route["distance_km"]:.1f} km')
    st.caption(f'{route["method"]}. {route["closure_status"]} {route["note"]}')
    if route.get("directions"):
        with st.expander(
            f'Route directions · {len(route["directions"])} steps',
            expanded=False,
        ):
            for instruction in route["directions"]:
                st.write(f"- {instruction}")
    navigation_destination = st.session_state.route_destination
    selected_start_url = google_maps_directions_url(
        navigation_destination,
        origin,
    )
    current_location_url = google_maps_directions_url(
        navigation_destination,
    )
    current_navigation, selected_navigation = st.columns(2)
    with current_navigation.container(key="current_location_navigation"):
        st.link_button(
            "Navigate from my current location",
            current_location_url,
            type="primary",
            use_container_width=True,
        )
    with selected_navigation.container(key="selected_start_navigation"):
        st.link_button(
            "Navigate from selected start",
            selected_start_url,
            use_container_width=True,
        )
    st.caption(
        "Current-location navigation uses Google Maps' device location; the map's location button "
        "asks your browser for permission. Google Maps may choose a different route than the one "
        "screened here, so recheck current closures. "
        "Routes are not evacuation orders; follow official instructions."
    )

st.subheader("Location overview")
st.caption(
    "Blue pin: selected start · Purple pin: destination · Green pins: mapped shelters · "
    "Blue line: possible route. Use the map's location control to show your device location."
)
map_shelters = shelters if isinstance(shelters, list) else []
create_disaster_map(origin, destination, alerts or [], map_shelters, route)

st.markdown(
    '<p class="source-note">Sources: National Weather Service, Open-Meteo, OpenStreetMap, '
    'and (when configured) North Carolina DOT DriveNC. '
    "Shelter operating status is reported only when available in map data; otherwise it is unconfirmed. "
    "NC 2-1-1 or local officials must confirm which shelters are open. "
    "DriveNC may be delayed or incomplete; follow official evacuation instructions.</p>",
    unsafe_allow_html=True,
)
