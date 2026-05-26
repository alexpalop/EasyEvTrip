import math
import os
from math import asin, cos, radians, sin, sqrt

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, store_feedback
from i18n import _t, normalize_lang
from models import FeedbackRequest, PlanRequest, PlanResponse, PlanStop

load_dotenv()

app = FastAPI(title="EasyEvTrip API", version="0.5.0")

@app.on_event("startup")
async def _startup() -> None:
    init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ORS_KEY    = os.getenv("ORS_API_KEY")
OCM_KEY    = os.getenv("OCM_API_KEY")
PLACES_KEY = os.getenv("GOOGLE_PLACES_KEY")

ORS_BASE    = "https://api.openrouteservice.org"
OCM_BASE    = "https://api.openchargemap.io/v3/poi/"
PLACES_BASE = "https://places.googleapis.com/v1/places:searchNearby"

# ── Constants ─────────────────────────────────────────────────────────────────

CAR = {
    "compact": {"range_km": 220, "capacity_kwh": 38, "peak_kw": 55,  "sustained_kw": 40},
    "medium":  {"range_km": 320, "capacity_kwh": 55, "peak_kw": 110, "sustained_kw": 80},
    "large":   {"range_km": 400, "capacity_kwh": 72, "peak_kw": 175, "sustained_kw": 130},
    "premium": {"range_km": 470, "capacity_kwh": 90, "peak_kw": 230, "sustained_kw": 170},
}

DEPARTURE_HOUR  = {"morning_early": 8.0, "morning_late": 10.0, "afternoon": 16.0}
LUNCH_MID       = {"13_14": 13.5, "13_30_15": 14.0, "14_15_30": 14.25, "none": None}

DEFAULT_CHARGER_KW = 120   # kW reals (150 kW anunciats × 80 %)
EUR_PER_KWH_DC     = 0.55
EUR_PER_KWH_AC     = 0.22
START_SOC          = 95
RESERVE_SOC        = 10
MAX_HOUR           = 20.5
MAX_KM_PER_DAY     = 700   # límit de km per jornada (independentment de l'hora)
MAX_WALK_MINUTES      = 10  # màxim temps de caminada acceptable (carregador → restaurant/hotel)
MIN_LUNCH_CHARGE_MIN  = 12  # càrrega <12 min al dinar no val la pena — dinar simple

# ── Helpers ORS ───────────────────────────────────────────────────────────────

def _geocode(city: str) -> tuple[float, float]:
    r = httpx.get(
        f"{ORS_BASE}/geocode/search",
        params={"api_key": ORS_KEY, "text": city, "size": 1, "layers": "locality,region"},
        timeout=10,
    )
    r.raise_for_status()
    feats = r.json().get("features", [])
    if not feats:
        raise ValueError(f"No s'ha trobat la localitat «{city}»")
    lon, lat = feats[0]["geometry"]["coordinates"]
    return lon, lat


def _route(a: tuple[float, float], b: tuple[float, float]) -> tuple[int, int, list]:
    """Retorna (distance_km, driving_minutes, route_coords [[lon,lat], ...])."""
    r = httpx.get(
        f"{ORS_BASE}/v2/directions/driving-car",
        params={"api_key": ORS_KEY, "start": f"{a[0]},{a[1]}", "end": f"{b[0]},{b[1]}"},
        timeout=15,
    )
    r.raise_for_status()
    feat   = r.json()["features"][0]
    s      = feat["properties"]["summary"]
    coords = feat["geometry"]["coordinates"]
    return round(s["distance"] / 1000), round(s["duration"] / 60), coords


# ── Helpers geometria ─────────────────────────────────────────────────────────

def _hav_km(p1: list, p2: list) -> float:
    lon1, lat1, lon2, lat2 = map(radians, [p1[0], p1[1], p2[0], p2[1]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(a))


def _coords_at_km(coords: list, target_km: float) -> tuple[float, float]:
    cum = 0.0
    for i in range(len(coords) - 1):
        seg = _hav_km(coords[i], coords[i + 1])
        if cum + seg >= target_km:
            frac = (target_km - cum) / seg if seg > 0 else 0.0
            lon  = coords[i][0] + frac * (coords[i + 1][0] - coords[i][0])
            lat  = coords[i][1] + frac * (coords[i + 1][1] - coords[i][1])
            return lon, lat
        cum += seg
    return coords[-1][0], coords[-1][1]


# ── Helpers OCM ───────────────────────────────────────────────────────────────

def _find_charger(lat: float, lon: float, min_kw: int = 50) -> dict | None:
    if not OCM_KEY:
        return None
    try:
        r = httpx.get(
            OCM_BASE,
            params={
                "key": OCM_KEY,
                "latitude": lat, "longitude": lon,
                "distance": 15, "distanceunit": "KM",
                "maxresults": 8, "minpowerkw": min_kw,
                "compact": "true", "verbose": "false",
            },
            timeout=10,
        )
        r.raise_for_status()
        pois = r.json()
    except Exception:
        return None

    best, best_score = None, -1.0
    for poi in pois:
        connections = poi.get("Connections") or []
        power_kw = max(
            (c.get("PowerKW") or 0 for c in connections if c.get("PowerKW")),
            default=0,
        )
        if power_kw < min_kw:
            continue
        addr     = poi.get("AddressInfo") or {}
        dist_km  = addr.get("Distance") or 999
        operator = (poi.get("OperatorInfo") or {}).get("Title") or ""
        score    = power_kw / (1 + dist_km)
        if score > best_score:
            best_score = score
            best = {
                "name":     addr.get("Title") or "Carregador DC",
                "operator": operator,
                "town":     addr.get("Town") or addr.get("StateOrProvince") or "",
                "power_kw": int(power_kw),
                "lat":      addr.get("Latitude"),
                "lon":      addr.get("Longitude"),
            }
    return best


# ── Walking time via Google Routes API ───────────────────────────────────────

ROUTES_BASE = "https://routes.googleapis.com/directions/v2:computeRoutes"

def _walking_minutes(lat1: float, lon1: float, lat2: float, lon2: float) -> float | None:
    """Temps real caminant entre dos punts (Google Routes API). Retorna None si falla."""
    if not PLACES_KEY:
        return None
    try:
        r = httpx.post(
            ROUTES_BASE,
            headers={
                "X-Goog-Api-Key": PLACES_KEY,
                "X-Goog-FieldMask": "routes.duration",
            },
            json={
                "origin":      {"location": {"latLng": {"latitude": lat1, "longitude": lon1}}},
                "destination": {"location": {"latLng": {"latitude": lat2, "longitude": lon2}}},
                "travelMode": "WALK",
                "computeAlternativeRoutes": False,
            },
            timeout=8,
        )
        r.raise_for_status()
        routes = r.json().get("routes", [])
        if not routes:
            return None
        dur_str = routes[0].get("duration", "0s")
        return round(int(dur_str.rstrip("s")) / 60, 1)
    except Exception:
        return None


# ── Helpers Google Places ─────────────────────────────────────────────────────

def _places_nearby(place_type: str, lat: float, lon: float, radius: float, fields: str) -> list:
    try:
        r = httpx.post(
            PLACES_BASE,
            headers={"X-Goog-Api-Key": PLACES_KEY, "X-Goog-FieldMask": fields},
            json={
                "includedTypes": [place_type],
                "maxResultCount": 10,
                "locationRestriction": {
                    "circle": {"center": {"latitude": lat, "longitude": lon}, "radius": radius}
                },
            },
            timeout=10,
        )
        r.raise_for_status()
        return r.json().get("places", [])
    except Exception:
        return []


def _find_restaurant(lat: float, lon: float) -> dict | None:
    if not PLACES_KEY:
        return None
    fields = "places.displayName,places.rating,places.location"
    for radius in [300, 600]:
        results = _places_nearby("restaurant", lat, lon, float(radius), fields)

        # Filtra per rating mínim i extreu coords
        candidates = []
        for p in results:
            if p.get("rating", 0) < 3.5:
                continue
            loc  = (p.get("location") or {})
            plat = loc.get("latitude")
            plon = loc.get("longitude")
            if plat is None or plon is None:
                continue
            candidates.append({
                "name":   (p.get("displayName") or {}).get("text", ""),
                "rating": p.get("rating"),
                "lat":    plat,
                "lon":    plon,
            })

        if not candidates:
            continue

        # Ordena per rating i comprova temps de caminada (màx 5 candidats per limitar crides API)
        candidates.sort(key=lambda x: -(x.get("rating") or 0))
        walkable = []
        for c in candidates[:5]:
            walk_min = _walking_minutes(lat, lon, c["lat"], c["lon"])
            if walk_min is not None and walk_min > MAX_WALK_MINUTES:
                continue  # massa lluny caminant — descarta
            c["walk_min"] = walk_min
            walkable.append(c)

        if walkable:
            # Prioritza menys temps a peu; desempat per rating
            walkable.sort(key=lambda x: (x["walk_min"] if x["walk_min"] is not None else 5.0, -(x.get("rating") or 0)))
            return walkable[0]

    return None


# ── Helpers model ─────────────────────────────────────────────────────────────

def _charging(from_soc: int, to_soc: int, car: dict, charger_kw: float = DEFAULT_CHARGER_KW) -> tuple[int, float]:
    cap   = car["capacity_kwh"]
    zones = [
        (10, 50, min(car["peak_kw"],      charger_kw)),
        (50, 80, min(car["sustained_kw"], charger_kw) * 0.7),
        (80, 100, 30 * 0.5),
    ]
    mins, kwh = 0.0, 0.0
    for z0, z1, pw in zones:
        a = max(from_soc, z0)
        b = min(to_soc,   z1)
        if a >= b:
            continue
        chunk = (b - a) / 100 * cap
        mins += chunk / pw * 60
        kwh  += chunk
    return math.ceil(mins), round(kwh, 1)


def _soc_after(soc: int, km: float, car: dict) -> int:
    return round(soc - km / (car["range_km"] / 85))


def _fmt(h: float) -> str:
    h = h % 24
    return f"{int(h):02d}:{round((h % 1) * 60):02d}"


def _resolve_charger(route_coords: list | None, km_pos: float) -> tuple[dict | None, float]:
    if not route_coords:
        return None, DEFAULT_CHARGER_KW
    lon, lat    = _coords_at_km(route_coords, km_pos)
    charger     = _find_charger(lat, lon)
    kw_real     = (charger["power_kw"] * 0.80) if charger else DEFAULT_CHARGER_KW
    return charger, kw_real


def _make_lunch_stop(
    charger: dict | None,
    kw_real: float,
    soc_from: int,
    arrival_hour: float,
    car: dict,
    km_pos: float | None = None,
    lang: str = "ca",
) -> tuple[PlanStop, float, float]:
    """
    Construeix una parada de dinar amb càrrega.
    Retorna (PlanStop, kWh_carregats, hora_sortida).
    """
    c_min, c_kwh = _charging(soc_from, 80, car, kw_real)

    # Si la càrrega seria massa curta (bateria ja alta), fem dinar simple sense carregador
    if c_min < MIN_LUNCH_CHARGE_MIN:
        dep_hour = arrival_hour + 0.75
        return PlanStop(
            type="lunch",
            name=_t(lang, "lunch_name"),
            description=_t(lang, "lunch_high_soc_desc", soc=soc_from),
            arrival_time=_fmt(arrival_hour),
            departure_time=_fmt(dep_hour),
            battery_arrival=soc_from,
            battery_departure=soc_from,
            lat=charger.get("lat") if charger else None,
            lon=charger.get("lon") if charger else None,
            km_pos=km_pos,
        ), 0.0, dep_hour

    lunch_dur    = max(60, c_min)
    dep_hour     = arrival_hour + lunch_dur / 60

    # Restaurant proper al carregador (Fase 5)
    restaurant = None
    if charger and charger.get("lat") and charger.get("lon"):
        restaurant = _find_restaurant(charger["lat"], charger["lon"])

    op = (charger or {}).get("operator") or (charger or {}).get("name") or _t(lang, "charger_fallback")
    kw_str = f"{charger['power_kw']} kW" if charger else "DC"
    walk_label = _t(lang, "walk_min_label")

    if restaurant:
        name     = restaurant["name"]
        rat      = f"Valoració {restaurant['rating']} · " if restaurant.get("rating") else ""
        walk_str = f"{int(restaurant['walk_min'])} {walk_label} · " if restaurant.get("walk_min") else ""
        desc     = f"{rat}{walk_str}{op} {kw_str} · {c_min} min ({soc_from}% → 80%)"
    else:
        name = _t(lang, "lunch_charge_name")
        desc = f"{op} {kw_str} · {c_min} min ({soc_from}% → 80%)"

    stop = PlanStop(
        type="lunch",
        name=name,
        description=desc,
        location=(charger or {}).get("town") or None,
        arrival_time=_fmt(arrival_hour),
        departure_time=_fmt(dep_hour),
        battery_arrival=soc_from,
        battery_departure=80,
        lat=charger.get("lat") if charger else None,
        lon=charger.get("lon") if charger else None,
        km_pos=km_pos,
        walk_to_lat=restaurant.get("lat") if restaurant else None,
        walk_to_lon=restaurant.get("lon") if restaurant else None,
    )
    return stop, c_kwh, dep_hour


def _find_hotels(lat: float, lon: float, max_results: int = 6) -> list[dict]:
    """Retorna fins a max_results hotels propers, ordenats per rating."""
    if not PLACES_KEY:
        return []
    fields  = "places.displayName,places.rating,places.location,places.formattedAddress"
    results = _places_nearby("lodging", lat, lon, 8000.0, fields)
    if not results:
        return []
    rated = sorted(
        [h for h in results if h.get("rating", 0) >= 3.5],
        key=lambda x: x.get("rating", 0),
        reverse=True,
    ) or results
    hotels = []
    for h in rated[:max_results]:
        loc = h.get("location") or {}
        hlat = loc.get("latitude")
        hlon = loc.get("longitude")
        if hlat is None or hlon is None:
            continue
        hotels.append({
            "name":     (h.get("displayName") or {}).get("text", ""),
            "rating":   h.get("rating"),
            "lat":      hlat,
            "lon":      hlon,
            "vicinity": h.get("formattedAddress", ""),
        })
    return hotels


def _make_hotel_stop(
    route_coords: list | None,
    km_pos: float,
    soc_arrival: int,
    arrival_hour: float,
    lang: str = "ca",
) -> PlanStop | None:
    """
    Cerca hotel + carregador accessible a peu. Retorna None si no en troba cap combo vàlid.
    Itera pels millors hotels fins trobar un amb carregador a ≤MAX_WALK_MINUTES a peu.
    """
    if not route_coords:
        return None

    lon, lat = _coords_at_km(route_coords, km_pos)
    hotels   = _find_hotels(lat, lon)

    for hotel in hotels:
        hlat = hotel["lat"]
        hlon = hotel["lon"]

        charger_near = _find_charger(hlat, hlon, min_kw=3)
        if not charger_near:
            continue

        clat = charger_near.get("lat")
        clon = charger_near.get("lon")
        if not clat or not clon:
            continue

        walk_min = _walking_minutes(clat, clon, hlat, hlon)
        if walk_min is not None and walk_min > MAX_WALK_MINUTES:
            continue  # carregador massa lluny caminant per a aquest hotel

        # Combo vàlid — construïm la parada
        rat_str  = f" · {hotel['rating']}/5" if hotel.get("rating") else ""
        name     = f"{hotel['name']}{rat_str}"
        parts    = (hotel.get("vicinity") or "").split(",")
        location = (parts[-2].strip() if len(parts) >= 2 else parts[0].strip()) or None
        kw       = charger_near["power_kw"]
        op       = charger_near.get("operator") or charger_near["name"]
        wm       = int(walk_min) if walk_min else "?"
        desc     = _t(lang, "hotel_desc", hotel=hotel["name"], walk_min=wm, charger=f"{op} {kw} kW")

        return PlanStop(
            type="hotel",
            name=name,
            description=desc,
            location=location,
            arrival_time=_fmt(arrival_hour),
            departure_time="09:00",
            battery_arrival=soc_arrival,
            battery_departure=95,
            lat=clat,
            lon=clon,
            km_pos=km_pos,
            walk_to_lat=hlat,
            walk_to_lon=hlon,
        )

    return None  # cap hotel proper té carregador accessible a peu


def _charger_desc(charger: dict | None, c_min: int, from_soc: int, to_soc: int, lang: str = "ca") -> tuple[str, str | None]:
    if charger:
        op   = charger["operator"] or charger["name"]
        desc = f"{op} · {charger['power_kw']} kW · {c_min} min ({from_soc}% → {to_soc}%)"
        loc  = charger["town"] or None
    else:
        fb   = _t(lang, "charger_fallback")
        desc = f"{fb} · {c_min} min ({from_soc}% → {to_soc}%)"
        loc  = None
    return desc, loc


# ── Simplificació de ruta ─────────────────────────────────────────────────────

def _simplify_route(coords: list, n: int = 60) -> list[list[float]]:
    """Retorna n punts equidistants de la ruta com a [[lat, lon], ...]."""
    if not coords:
        return []
    if len(coords) <= n:
        return [[c[1], c[0]] for c in coords]
    step = (len(coords) - 1) / (n - 1)
    return [[coords[round(i * step)][1], coords[round(i * step)][0]] for i in range(n)]


# ── Funció de conducció amb càrregues DC ──────────────────────────────────────

def _drive_segment(
    stops_out: list,
    start_km: float,
    start_soc: int,
    start_hour: float,
    dist_km: int,
    car: dict,
    avg_speed: float,
    route_coords: list | None = None,
    max_charges: int = 4,
    lang: str = "ca",
    target_km: float | None = None,     # atura't aquí en lloc de dist_km (per dinar com a waypoint)
    max_daily_km: float = float("inf"), # km màxims d'aquesta jornada (des de start_km)
) -> tuple[bool, float, int, float, float]:
    eff_target = target_km if target_km is not None else float(dist_km)
    km_per_pct = car["range_km"] / 85
    cur_km, cur_soc, cur_hour = start_km, start_soc, start_hour
    dc_kwh = 0.0

    for _ in range(max_charges + 1):
        km_left     = eff_target - cur_km
        soc_at_dest = _soc_after(cur_soc, km_left, car)

        if soc_at_dest >= RESERVE_SOC:
            return True, cur_hour + km_left / avg_speed, soc_at_dest, eff_target, dc_kwh

        km_to_20    = max(0.5, (cur_soc - 20) * km_per_pct)
        charge_hour = cur_hour + km_to_20 / avg_speed

        if charge_hour >= MAX_HOUR:
            km_drive   = min(km_to_20, (MAX_HOUR - cur_hour) * avg_speed)
            hotel_hour = cur_hour + km_drive / avg_speed
            hotel_soc  = max(15, _soc_after(cur_soc, km_drive, car))
            return False, hotel_hour, hotel_soc, cur_km + km_drive, dc_kwh

        charger, kw_real = _resolve_charger(route_coords, cur_km + km_to_20)
        c_min, c_kwh     = _charging(20, 80, car, kw_real)
        dc_kwh          += c_kwh
        charge_end       = charge_hour + c_min / 60

        if charger and charger.get("lat") and charger.get("lon"):
            stop_lat, stop_lon = charger["lat"], charger["lon"]
        elif route_coords:
            stop_lon, stop_lat = _coords_at_km(route_coords, cur_km + km_to_20)
        else:
            stop_lat, stop_lon = None, None

        desc, loc = _charger_desc(charger, c_min, 20, 80, lang)
        stops_out.append(PlanStop(
            type="charge",
            name=_t(lang, "charge_name"),
            description=desc,
            location=loc,
            arrival_time=_fmt(charge_hour),
            departure_time=_fmt(charge_end),
            battery_arrival=20,
            battery_departure=80,
            lat=stop_lat,
            lon=stop_lon,
            km_pos=round(cur_km + km_to_20, 1),
        ))

        cur_km  += km_to_20
        cur_soc  = 80
        cur_hour = charge_end

        # Límit de km/dia: para aquí si hem superat el màxim de la jornada
        if cur_km - start_km >= max_daily_km:
            return False, cur_hour, cur_soc, cur_km, dc_kwh

    return False, cur_hour, cur_soc, cur_km, dc_kwh


# ── Endpoint ──────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "ev-trip-planner", "version": "0.4.0"}


@app.post("/plan", response_model=PlanResponse)
def create_plan(req: PlanRequest) -> PlanResponse:
    if not ORS_KEY:
        raise HTTPException(503, "ORS_API_KEY no configurada al servidor.")

    try:
        origin_ll              = _geocode(req.origin)
        dest_ll                = _geocode(req.destination)
        dist_km, drive_min, rc = _route(origin_ll, dest_ll)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"Error de l'API de rutes (HTTP {e.response.status_code})")
    except httpx.RequestError:
        raise HTTPException(502, "No s'ha pogut connectar amb l'API de rutes")

    lang       = normalize_lang(req.lang)
    car        = CAR[req.car_category]
    dep_hour   = DEPARTURE_HOUR[req.departure_window]
    lunch_mid  = LUNCH_MID.get(req.lunch_window)
    km_per_pct = car["range_km"] / 85
    avg_speed  = dist_km / (drive_min / 60)

    stops: list[PlanStop] = []
    total_dc_kwh = 0.0

    stops.append(PlanStop(
        type="start",
        name=_t(lang, "start_name", origin=req.origin),
        description=_t(lang, "start_desc"),
        arrival_time=_fmt(dep_hour),
        departure_time=_fmt(dep_hour),
        battery_departure=START_SOC,
        lat=origin_ll[1],
        lon=origin_ll[0],
        km_pos=0.0,
    ))

    # ── Cas A: arriba sense carregar ──────────────────────────────────────────
    if _soc_after(START_SOC, dist_km, car) >= RESERVE_SOC:
        arr_hour  = dep_hour + drive_min / 60
        total_min = drive_min

        if lunch_mid:
            km_lunch = (lunch_mid - dep_hour) * avg_speed
            if 0 < km_lunch < dist_km:
                soc_l = _soc_after(START_SOC, km_lunch, car)
                _llon, _llat = _coords_at_km(rc, km_lunch) if rc else (None, None)
                stops.append(PlanStop(
                    type="lunch",
                    name=_t(lang, "lunch_name"),
                    description=_t(lang, "lunch_no_charge_desc"),
                    arrival_time=_fmt(lunch_mid - 0.375),
                    departure_time=_fmt(lunch_mid + 0.375),
                    battery_arrival=soc_l,
                    battery_departure=soc_l,
                    lat=_llat,
                    lon=_llon,
                    km_pos=round(km_lunch, 1),
                ))
                total_min += 45
                arr_hour  += 0.75

        soc_dest = max(10, _soc_after(START_SOC, dist_km, car))
        stops.append(PlanStop(
            type="destination",
            name=_t(lang, "destination_name", dest=req.destination),
            description=_t(lang, "destination_desc"),
            arrival_time=_fmt(arr_hour),
            battery_arrival=soc_dest,
            lat=dest_ll[1],
            lon=dest_ll[0],
            km_pos=float(dist_km),
        ))
        return PlanResponse(
            total_distance_km=dist_km,
            total_duration_minutes=total_min,
            estimated_charge_cost_eur=0.0,
            stops=stops,
            notes=_t(lang, "note_no_charge", dest=req.destination, soc=soc_dest),
            route_polyline=_simplify_route(rc) if rc else None,
        )

    # ── Cas B: cal carregar ───────────────────────────────────────────────────
    cur_km, cur_soc, cur_hour = 0.0, START_SOC, dep_hour

    if lunch_mid:
        km_to_lunch  = (lunch_mid - dep_hour) * avg_speed
        soc_at_lunch = _soc_after(cur_soc, km_to_lunch, car)

        if soc_at_lunch >= 10:
            # B-a: arriba al dinar amb bateria → dinar = parada de càrrega + restaurant
            charger, kw_real = _resolve_charger(rc, km_to_lunch)
            lunch_stop, c_kwh, lunch_end = _make_lunch_stop(
                charger, kw_real, soc_at_lunch, lunch_mid - 0.5, car, km_pos=round(km_to_lunch, 1), lang=lang
            )
            total_dc_kwh += c_kwh
            stops.append(lunch_stop)
            cur_km, cur_soc, cur_hour = km_to_lunch, 80, lunch_end

        else:
            # B-b: no arriba al dinar → càrrega mínima pre-dinar per arribar ~20% al restaurant
            km_to_20     = (cur_soc - 20) * km_per_pct
            stop_hour    = cur_hour + km_to_20 / avg_speed
            charger, kw_real = _resolve_charger(rc, km_to_20)

            # Carrega just el necessari per arribar al dinar amb ~20% (+ 5% marge)
            km_precharge_to_lunch = km_to_lunch - km_to_20
            soc_needed_to_lunch   = km_precharge_to_lunch / km_per_pct
            target_precharge      = min(80, max(22, int(20 + soc_needed_to_lunch) + 5))

            c_min, c_kwh = _charging(20, target_precharge, car, kw_real)
            total_dc_kwh += c_kwh
            charge_end    = stop_hour + c_min / 60

            if charger and charger.get("lat") and charger.get("lon"):
                _slat, _slon = charger["lat"], charger["lon"]
            elif rc:
                _slon, _slat = _coords_at_km(rc, km_to_20)
            else:
                _slat, _slon = None, None

            desc, loc = _charger_desc(charger, c_min, 20, target_precharge, lang)
            stops.append(PlanStop(
                type="charge",
                name=_t(lang, "pre_lunch_charge_name"),
                description=desc + _t(lang, "pre_lunch_charge_suffix"),
                location=loc,
                arrival_time=_fmt(stop_hour),
                departure_time=_fmt(charge_end),
                battery_arrival=20,
                battery_departure=target_precharge,
                lat=_slat,
                lon=_slon,
                km_pos=round(km_to_20, 1),
            ))
            cur_km, cur_soc, cur_hour = km_to_20, target_precharge, charge_end

            # Re-avalua estat a la finestra de dinar
            km_to_lunch_now  = max(0.0, (lunch_mid - cur_hour) * avg_speed)
            lunch_arrival    = cur_hour + km_to_lunch_now / avg_speed
            soc_at_lunch_now = _soc_after(cur_soc, km_to_lunch_now, car)

            if cur_km + km_to_lunch_now >= dist_km:
                # Destí arriba abans de la finestra de dinar → no s'afegeix parada
                pass

            elif soc_at_lunch_now >= 15 and lunch_arrival <= lunch_mid + 0.75:
                # Fusiona dinar + càrrega + restaurant
                charger2, kw_real2 = _resolve_charger(rc, cur_km + km_to_lunch_now)
                lunch_stop, c_kwh2, lunch_end = _make_lunch_stop(
                    charger2, kw_real2, max(10, soc_at_lunch_now), lunch_arrival, car,
                    km_pos=round(cur_km + km_to_lunch_now, 1), lang=lang,
                )
                total_dc_kwh += c_kwh2
                stops.append(lunch_stop)
                cur_km  += km_to_lunch_now
                cur_soc  = 80
                cur_hour = lunch_end

            elif soc_at_lunch_now >= RESERVE_SOC:
                lunch_end = lunch_arrival + 0.75
                _llon2, _llat2 = _coords_at_km(rc, cur_km + km_to_lunch_now) if rc else (None, None)
                stops.append(PlanStop(
                    type="lunch",
                    name=_t(lang, "lunch_name"),
                    description=_t(lang, "lunch_simple_desc"),
                    arrival_time=_fmt(lunch_arrival),
                    departure_time=_fmt(lunch_end),
                    battery_arrival=soc_at_lunch_now,
                    battery_departure=soc_at_lunch_now,
                    lat=_llat2,
                    lon=_llon2,
                    km_pos=round(cur_km + km_to_lunch_now, 1),
                ))
                cur_km  += km_to_lunch_now
                cur_soc  = soc_at_lunch_now
                cur_hour = lunch_end

    # ── Bucle multi-dia: condueix fins al destí amb les pernoctacions necessàries
    hotel_kwh_total  = 0.0
    nights           = 0
    active_min       = round((cur_hour - dep_hour) * 60)  # temps acumulat fins aquí
    day_start        = cur_hour

    while nights <= 5:  # límit de seguretat: màxim 5 pernoctacions
        day_km_start = cur_km  # km al inici d'aquesta jornada (per calcular pressupost post-dinar)

        # ── Dinar del dia (tots els dies, no només el primer) ─────────────────
        if lunch_mid:
            km_to_lunch_today = (lunch_mid - cur_hour) * avg_speed
            lunch_km_abs      = cur_km + km_to_lunch_today

            if km_to_lunch_today > 0 and lunch_km_abs < dist_km:
                # Condueix fins a la zona de dinar (amb càrregues DC si cal)
                pre_arrived, pre_fh, pre_fs, pre_fkm, pre_dc = _drive_segment(
                    stops, cur_km, cur_soc, cur_hour, dist_km, car, avg_speed, rc,
                    lang=lang, target_km=lunch_km_abs, max_daily_km=MAX_KM_PER_DAY,
                )
                total_dc_kwh += pre_dc

                if pre_arrived:
                    charger_l, kw_real_l = _resolve_charger(rc, pre_fkm)
                    lunch_obj, c_kwh_l, lunch_end = _make_lunch_stop(
                        charger_l, kw_real_l, max(10, pre_fs), lunch_mid - 0.5, car,
                        km_pos=round(pre_fkm, 1), lang=lang,
                    )
                    total_dc_kwh += c_kwh_l
                    stops.append(lunch_obj)

                    km_used_pre_lunch = pre_fkm - day_km_start
                    arrived, fh, fs, fkm, extra_dc = _drive_segment(
                        stops, pre_fkm, 80, lunch_end, dist_km, car, avg_speed, rc,
                        lang=lang, max_daily_km=MAX_KM_PER_DAY - km_used_pre_lunch,
                    )
                    total_dc_kwh += extra_dc
                else:
                    # No ha pogut arribar al dinar (km o hora hotel assolida abans)
                    arrived, fh, fs, fkm = pre_arrived, pre_fh, pre_fs, pre_fkm
            else:
                arrived, fh, fs, fkm, extra_dc = _drive_segment(
                    stops, cur_km, cur_soc, cur_hour, dist_km, car, avg_speed, rc,
                    lang=lang, max_daily_km=MAX_KM_PER_DAY,
                )
                total_dc_kwh += extra_dc
        else:
            arrived, fh, fs, fkm, extra_dc = _drive_segment(
                stops, cur_km, cur_soc, cur_hour, dist_km, car, avg_speed, rc,
                lang=lang, max_daily_km=MAX_KM_PER_DAY,
            )
            total_dc_kwh += extra_dc

        active_min += round((fh - day_start) * 60)

        if arrived:
            stops.append(PlanStop(
                type="destination",
                name=_t(lang, "destination_name", dest=req.destination),
                description=_t(lang, "destination_desc"),
                arrival_time=_fmt(fh),
                battery_arrival=max(10, fs),
                lat=dest_ll[1],
                lon=dest_ll[0],
                km_pos=float(dist_km),
            ))
            break

        # Cal pernoctar — busca hotel+carregador, provant fins a 3 posicions anteriors
        hotel_stop = None
        for km_offset in [0, -40, -80]:
            alt_km   = max(0.0, min(float(dist_km) - 1.0, fkm + km_offset))
            alt_hour = fh - km_offset / avg_speed
            alt_soc  = min(95, max(RESERVE_SOC, round(fs + km_offset / (car["range_km"] / 85))))
            hotel_stop = _make_hotel_stop(rc, alt_km, alt_soc, alt_hour, lang=lang)
            if hotel_stop:
                fkm = alt_km
                break

        if hotel_stop is None:
            raise HTTPException(
                503,
                "No s'ha trobat cap hotel amb carregador accessible a peu a la zona de pernoctació. "
                "Prova una data diferent o un cotxe amb més autonomia per evitar pernoctar en aquest tram.",
            )

        nights        += 1
        hotel_kwh      = (95 - fs) / 100 * car["capacity_kwh"]
        hotel_kwh_total += hotel_kwh
        stops.append(hotel_stop)
        cur_km   = fkm
        cur_soc  = 95
        cur_hour = 9.0
        day_start = 9.0

    cost = round(total_dc_kwh * EUR_PER_KWH_DC + hotel_kwh_total * EUR_PER_KWH_AC, 1)

    if nights == 0:
        notes = None
    elif nights == 1:
        notes = _t(lang, "note_1night")
    else:
        notes = _t(lang, "note_multinight", days=nights + 1)

    return PlanResponse(
        total_distance_km=dist_km,
        total_duration_minutes=active_min,
        estimated_charge_cost_eur=cost,
        stops=stops,
        notes=notes,
        route_polyline=_simplify_route(rc) if rc else None,
    )



@app.post("/feedback")
async def post_feedback(req: FeedbackRequest) -> dict:
    store_feedback(req.rating, req.comment, req.origin, req.destination, req.car_category)
    return {"ok": True}
