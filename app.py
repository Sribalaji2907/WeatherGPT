from datetime import date, timedelta
from time import monotonic
from threading import Lock
from pathlib import Path
import calendar
import re
import requests
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="WeatherGPT API", version="1.0.0")
TIMEOUT = 25

# Simple in-memory cache. It reduces duplicate requests while this server process
# is running. Weather is cached for 10 minutes; seasonal outlook for 6 hours.
_CACHE = {}
_CACHE_LOCK = Lock()

def cache_get(key):
    now = monotonic()
    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if item and item["expires_at"] > now:
            return item["value"]
        if item:
            _CACHE.pop(key, None)
    return None

def cache_set(key, value, ttl_seconds):
    with _CACHE_LOCK:
        _CACHE[key] = {"value": value, "expires_at": monotonic() + ttl_seconds}

def city_cache_key(city):
    return re.sub(r"\\s+", " ", city.strip()).casefold()

@app.get("/")
def home():
    return FileResponse(ROOT / "static" / "index.html")

def geocode(city: str):
    key = ("geocode", city_cache_key(city))
    cached = cache_get(key)
    if cached is not None:
        return cached
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 10, "language": "en", "format": "json"},
            timeout=TIMEOUT,
        )
        if r.status_code == 429:
            raise HTTPException(
                503,
                "The location-search service has reached its request limit. Please try again later."
            )
        r.raise_for_status()
        results = r.json().get("results", [])
    except HTTPException:
        raise
    except requests.RequestException as exc:
        raise HTTPException(502, f"Geocoding service error: {exc}")
    if not results:
        raise HTTPException(404, "City not found. Try a city name such as Chennai, Madurai, Delhi or Mumbai.")
    # Prefer an Indian match when available, but permit other cities too.
    match = next((x for x in results if x.get("country_code") == "IN"), results[0])
    cache_set(key, match, 24 * 60 * 60)
    return match

def fetch_json(url, params):
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
        if r.status_code == 429:
            raise HTTPException(
                503,
                "The weather provider's request limit has been reached. Please try again later. "
                "Previously cached results may still be available."
            )
        if not r.ok:
            raise HTTPException(502, f"Weather provider returned HTTP {r.status_code}: {r.text[:250]}")
        return r.json()
    except HTTPException:
        raise
    except requests.RequestException as exc:
        raise HTTPException(502, f"Weather provider connection error: {exc}")

@app.get("/api/health")
def health():
    return {"status": "ok", "message": "WeatherGPT backend is running"}

@app.get("/api/weather")
def weather(city: str = Query(..., min_length=2, max_length=80)):
    key = ("weather", city_cache_key(city))
    cached = cache_get(key)
    if cached is not None:
        return cached

    place = geocode(city)
    params = {
        "latitude": place["latitude"], "longitude": place["longitude"],
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,weather_code,wind_speed_10m_max,uv_index_max",
        "timezone": "auto", "forecast_days": 7, "temperature_unit": "celsius", "wind_speed_unit": "kmh"
    }
    data = fetch_json("https://api.open-meteo.com/v1/forecast", params)
    result = {"city": place.get("name", city), "country": place.get("country", ""), "latitude": place["latitude"], "longitude": place["longitude"], "timezone": data.get("timezone"), "current": data.get("current", {}), "daily": data.get("daily", {}), "source": "Open-Meteo Forecast API", "retrieved_at": data.get("current", {}).get("time")}
    cache_set(key, result, 10 * 60)
    return result

@app.get("/api/outlook")
def outlook(city: str = Query(..., min_length=2, max_length=80)):
    key = ("outlook", city_cache_key(city), date.today().isoformat())
    cached = cache_get(key)
    if cached is not None:
        return cached

    place = geocode(city)
    today = date.today()
    first_next = date(today.year + (today.month == 12), 1 if today.month == 12 else today.month + 1, 1)
    last_next = date(first_next.year, first_next.month, calendar.monthrange(first_next.year, first_next.month)[1])
    params = {
        "latitude": place["latitude"], "longitude": place["longitude"],
        "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum,wind_speed_10m_mean",
        "timezone": "auto", "forecast_days": 92, "temperature_unit": "celsius", "wind_speed_unit": "kmh"
    }
    data = fetch_json("https://seasonal-api.open-meteo.com/v1/seasonal", params)
    daily = data.get("daily", {})
    times = daily.get("time", [])
    indices = [i for i, d in enumerate(times) if first_next.isoformat() <= d <= last_next.isoformat()]
    if not indices:
        raise HTTPException(502, "The seasonal provider did not return daily data for the next calendar month. Try again later; seasonal availability varies by variable and model.")
    sliced = {k: [v[i] for i in indices] for k, v in daily.items() if isinstance(v, list) and len(v) == len(times)}
    def mean(key):
        vals = [x for x in sliced.get(key, []) if isinstance(x, (int, float))]
        return sum(vals) / len(vals) if vals else None
    # Precipitation is a sum, not a mean; preserve missing values.
    precip = [x for x in sliced.get("precipitation_sum", []) if isinstance(x, (int, float))]
    summary = {"temperature_mean": mean("temperature_2m_mean"), "humidity_mean": mean("relative_humidity_2m_mean"), "wind_mean": mean("wind_speed_10m_mean"), "precipitation_sum": sum(precip) if precip else None}
    result = {"city": place.get("name", city), "month": first_next.strftime("%B %Y"), "daily": sliced, "summary": summary, "source": "Open-Meteo Seasonal Forecast API", "note": "Long-range outlook is uncertain and should be interpreted as a broad model estimate, not a guaranteed day-by-day forecast."}
    cache_set(key, result, 6 * 60 * 60)
    return result

@app.get("/api/history")
def history():
    """Summarize a downloaded data.gov.in rainfall CSV after placing it at data/rainfall.csv.

    Dataset schemas vary. This endpoint deliberately reports which columns it detects rather
    than pretending every rainfall file has the same layout.
    """
    path = ROOT / "data" / "rainfall.csv"
    if not path.exists():
        raise HTTPException(404, "Add your downloaded rainfall CSV as data/rainfall.csv. See data/README.txt for instructions.")
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise HTTPException(400, f"Could not read CSV: {exc}")
    if df.empty:
        raise HTTPException(400, "The CSV is empty.")
    cols = {str(c).strip().lower(): c for c in df.columns}
    year_col = next((orig for low, orig in cols.items() if low == "year" or "year" in low), None)
    rain_col = next((orig for low, orig in cols.items() if "rainfall" in low or low in {"rain", "precipitation"}), None)
    if year_col is None or rain_col is None:
        return {"message": "CSV loaded, but automatic summary needs a year column and a rainfall/precipitation column.", "columns": [str(c) for c in df.columns], "rows": int(len(df)), "next_step": "Update app.py's /api/history column detection to match your downloaded dataset's headers."}
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
    df[rain_col] = pd.to_numeric(df[rain_col], errors="coerce")
    clean = df.dropna(subset=[year_col, rain_col])
    if clean.empty:
        return {"message": "Detected columns but found no numeric rainfall rows.", "columns": [str(c) for c in df.columns]}
    grouped = clean.groupby(year_col)[rain_col].mean().reset_index().sort_values(year_col)
    return {"rows": int(len(df)), "year_column": str(year_col), "rainfall_column": str(rain_col), "summary": [{"year": int(row[year_col]), "mean_rainfall": float(row[rain_col])} for _, row in grouped.iterrows()]}
