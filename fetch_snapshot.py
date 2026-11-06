#!/usr/bin/env python3
"""Fetch Open-Meteo snow data for Western US Ikon resorts and write snapshot.json.
Usage: python3 -I fetch_snapshot.py [out.json]
"""
import json, re, sys, time, urllib.request, urllib.parse, datetime

RESORTS = [
    # name, state, lat, lon, elevation_m (roughly upper mountain), skicentral slug, projected opening (Ikon, tentative 26/27; None = TBA)
    ("Palisades Tahoe", "CA", 39.197, -120.235, 2500, "squawvalley", "2026-11-25"),
    ("Mammoth Mountain", "CA", 37.631, -119.033, 2900, "mammoth", "2026-11-13"),
    ("June Mountain", "CA", 37.767, -119.090, 2800, "junemountain", "2026-12-19"),
    ("Big Bear Mountain", "CA", 34.228, -116.889, 2400, "bigbearmountain", "2026-12-04"),
    ("Jackson Hole", "WY", 43.588, -110.828, 2700, "jacksonhole", "2026-11-27"),
    ("Alta", "UT", 40.588, -111.638, 2900, "alta", "2026-11-20"),
    ("Snowbird", "UT", 40.581, -111.656, 3000, "snowbird", "2026-11-27"),
    ("Solitude", "UT", 40.620, -111.592, 2800, "solitude", "2026-11-20"),
    ("Brighton", "UT", 40.598, -111.583, 2800, "brighton", "2026-12-04"),
    ("Deer Valley", "UT", 40.637, -111.478, 2600, "deervalley", "2026-12-05"),
    ("Snowbasin", "UT", 41.216, -111.857, 2300, "snowbasin", "2026-11-27"),
    ("Aspen Snowmass", "CO", 39.209, -106.949, 3000, "aspen|snowmass", "2026-11-26"),
    ("Steamboat", "CO", 40.457, -106.805, 2800, "steamboat", "2026-11-21"),
    ("Winter Park", "CO", 39.887, -105.763, 3000, "winterpark", None),
    ("Copper Mountain", "CO", 39.501, -106.151, 3300, "copper", "2026-11-06"),
    ("Arapahoe Basin", "CO", 39.642, -105.872, 3500, "arapahoe", "2026-10-30"),
    ("Eldora", "CO", 39.937, -105.583, 3000, "eldora", "2026-11-13"),
    ("Big Sky", "MT", 45.284, -111.401, 2800, "bigsky", "2026-11-25"),
    ("Sun Valley", "ID", 43.676, -114.371, 2500, "sunvalley", "2026-11-26"),
    ("Schweitzer", "ID", 48.368, -116.623, 1700, "schweitzer", "2026-11-27"),
    ("Crystal Mountain", "WA", 46.935, -121.474, 1900, "crystalmountain", "2026-11-27"),
    ("Mt. Bachelor", "OR", 43.979, -121.688, 2200, "mt.bachelor", "2026-12-04"),
    ("Taos Ski Valley", "NM", 36.596, -105.454, 3000, "taos", "2026-11-26"),
]

DAILY = "snowfall_sum,temperature_2m_max,temperature_2m_min,wind_speed_10m_max,weather_code,precipitation_probability_max"

def fetch(url, tries=6):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                d = json.loads(r.read().decode())
            if isinstance(d, dict) and d.get("error"):
                raise RuntimeError(d.get("reason"))
            return d
        except Exception as e:
            last = e
            time.sleep(2 + i * 2)
    raise last

def open_status():
    """Parse SkiCentral's open-areas page: {slug: detail} for every resort currently listed OPEN."""
    url = "https://www.skicentral.com/openareas-skireport.html"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (pow-finder daily refresh)"})
    html = None
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                html = r.read().decode("utf-8", "replace")
            break
        except Exception:
            time.sleep(3)
    if not html:
        return None
    out = {}
    for m in re.finditer(r'class="opendetails inline">\s*<a href="([a-z0-9.\-]+)-skireport\.html">[^<]+</a>.*?<br>\s*(OPEN[^<]*)', html, re.S):
        out[m.group(1)] = re.sub(r"\s+", " ", m.group(2)).strip()
    return out

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "snapshot.json"
    results = []
    opened = open_status()  # None if SkiCentral unreachable -> statuses unknown
    # batch in chunks of 6 to keep URLs short and failures small
    for i in range(0, len(RESORTS), 6):
        chunk = RESORTS[i:i+6]
        q = {
            "latitude": ",".join(str(r[2]) for r in chunk),
            "longitude": ",".join(str(r[3]) for r in chunk),
            "elevation": ",".join(str(r[4]) for r in chunk),
            "daily": DAILY,
            "past_days": 3,
            "forecast_days": 7,
            "timezone": "America/Los_Angeles",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
        }
        url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(q)
        d = fetch(url)
        if isinstance(d, dict):
            d = [d]
        for r, m in zip(chunk, d):
            slugs = r[5].split("|")
            detail = next((opened[sl] for sl in slugs if opened and sl in opened), None)
            status = "unknown" if opened is None else ("open" if detail else "closed")
            results.append({
                "name": r[0], "state": r[1], "lat": r[2], "lon": r[3], "elev_m": r[4],
                "slug": r[5], "opens": r[6], "status": status, "detail": detail,
                "days": m["daily"]["time"],
                "snow": m["daily"]["snowfall_sum"],
                "tmax": m["daily"]["temperature_2m_max"],
                "tmin": m["daily"]["temperature_2m_min"],
                "wind": m["daily"]["wind_speed_10m_max"],
                "wcode": m["daily"]["weather_code"],
                "pop": m["daily"]["precipitation_probability_max"],
            })
        time.sleep(1)
    n_open = sum(1 for r in results if r["status"] == "open")
    snap = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
            "past_days": 3, "resorts": results}
    with open(out, "w") as f:
        json.dump(snap, f)
    print(f"wrote {out}: {len(results)} resorts ({n_open} open), updated {snap['updated']}")

if __name__ == "__main__":
    main()
