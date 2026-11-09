#!/usr/bin/env python3
"""Fetch Open-Meteo snow data for Western US Ikon resorts and write snapshot.json.
Usage: python3 -I fetch_snapshot.py [out.json]
"""
import json, re, sys, time, urllib.request, urllib.parse, datetime

RESORTS = [
    # name, state, lat, lon, elevation_m (roughly upper mountain), skicentral slug, projected opening (Ikon, tentative 26/27; None = TBA), onthesnow path
    ("Palisades Tahoe", "CA", 39.197, -120.235, 2500, "squawvalley", "2026-11-25", "california/palisades-tahoe"),
    ("Mammoth Mountain", "CA", 37.631, -119.033, 2900, "mammoth", "2026-11-13", "california/mammoth-mountain-ski-area"),
    ("June Mountain", "CA", 37.767, -119.090, 2800, "junemountain", "2026-12-19", "california/june-mountain"),
    ("Big Bear Mountain", "CA", 34.228, -116.889, 2400, "bigbearmountain", "2026-12-04", "california/bear-mountain"),
    ("Sierra-at-Tahoe", "CA", 38.799, -120.080, 2200, "sierraattahoe", "2026-12-26", "california/sierra-at-tahoe"),
    ("Jackson Hole", "WY", 43.588, -110.828, 2700, "jacksonhole", "2026-11-27", "wyoming/jackson-hole"),
    ("Alta", "UT", 40.588, -111.638, 2900, "alta", "2026-11-20", "utah/alta-ski-area"),
    ("Snowbird", "UT", 40.581, -111.656, 3000, "snowbird", "2026-11-27", "utah/snowbird"),
    ("Solitude", "UT", 40.620, -111.592, 2800, "solitude", "2026-11-20", "utah/solitude-mountain-resort"),
    ("Brighton", "UT", 40.598, -111.583, 2800, "brighton", "2026-12-04", "utah/brighton-resort"),
    ("Deer Valley", "UT", 40.637, -111.478, 2600, "deervalley", "2026-12-05", "utah/deer-valley-resort"),
    ("Snowbasin", "UT", 41.216, -111.857, 2300, "snowbasin", "2026-11-27", "utah/snowbasin"),
    ("Aspen Snowmass", "CO", 39.209, -106.949, 3000, "aspen|snowmass", "2026-11-26", "colorado/aspen-snowmass"),
    ("Steamboat", "CO", 40.457, -106.805, 2800, "steamboat", "2026-11-21", "colorado/steamboat"),
    ("Winter Park", "CO", 39.887, -105.763, 3000, "winterpark", None, "colorado/winter-park-resort"),
    ("Copper Mountain", "CO", 39.501, -106.151, 3300, "copper", "2026-11-06", "colorado/copper-mountain-resort"),
    ("Arapahoe Basin", "CO", 39.642, -105.872, 3500, "arapahoe", "2026-10-30", "colorado/arapahoe-basin-ski-area"),
    ("Eldora", "CO", 39.937, -105.583, 3000, "eldora", "2026-11-13", "colorado/eldora-mountain-resort"),
    ("Big Sky", "MT", 45.284, -111.401, 2800, "bigsky", "2026-11-25", "montana/big-sky-resort"),
    ("Sun Valley", "ID", 43.676, -114.371, 2500, "sunvalley", "2026-11-26", "idaho/sun-valley"),
    ("Schweitzer", "ID", 48.368, -116.623, 1700, "schweitzer", "2026-11-27", "idaho/schweitzer"),
    ("Crystal Mountain", "WA", 46.935, -121.474, 1900, "crystalmountain", "2026-11-27", "washington/crystal-mountain-wa"),
    ("Summit at Snoqualmie", "WA", 47.424, -121.414, 1200, "snoqualmie", "2026-12-26", "washington/the-summit-at-snoqualmie"),
    ("Mt. Bachelor", "OR", 43.979, -121.688, 2200, "mt.bachelor", "2026-12-04", "oregon/mt-bachelor"),
    ("Taos Ski Valley", "NM", 36.596, -105.454, 3000, "taos", "2026-11-26", "new-mexico/taos-ski-valley"),
    ("Alyeska", "AK", 60.961, -149.098, 1000, "alyeska", "2026-11-28", "alaska/alyeska-resort"),
]

DAILY = "snowfall_sum,temperature_2m_max,temperature_2m_min,wind_speed_10m_max,weather_code,precipitation_probability_max"

def fetch(url, tries=5):
    """Open-Meteo call with backoff. Returns None (instead of raising) if it keeps failing, so the caller can fall back."""
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                d = json.loads(r.read().decode())
            if isinstance(d, dict) and d.get("error"):
                raise RuntimeError(d.get("reason"))
            return d
        except Exception as e:
            print(f"  open-meteo attempt {i+1} failed: {e}", file=sys.stderr)
            time.sleep(5 + i * 10)
    return None

def open_status():
    """Parse SkiCentral's open-areas page: {slug: detail} for every resort currently listed OPEN."""
    url = "https://www.skicentral.com/openareas-skireport.html"
    req = urllib.request.Request(url, headers=UA)
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

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 pow-king daily refresh"}

def resort_report(path):
    """OnTheSnow resort page: the resort's own reported snow (cm), base depth, lifts and open flag. None if unavailable."""
    url = f"https://www.onthesnow.com/{path}/skireport"
    html = None
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                html = r.read().decode("utf-8", "replace")
            break
        except Exception:
            time.sleep(3)
    if not html:
        return None
    u = html.replace('\\"', '"')
    m = re.search(r'\{"base":([\d.]+|null),"middle":([\d.]+|null),"summit":([\d.]+|null),"last24":([\d.]+|null),"last48":([\d.]+|null),"last72":([\d.]+|null)\}', u)
    if not m:
        return None
    cm = lambda v: None if v == "null" else round(float(v) / 2.54, 1)
    rep_ = {"last24": cm(m.group(4)), "last48": cm(m.group(5)), "last72": cm(m.group(6)),
            "base": cm(m.group(1)), "summit": cm(m.group(3))}
    l = re.search(r'\{"open":(\d+),"total":(\d+),"details":', u[m.end():m.end() + 400])
    if l:
        rep_["lifts_open"], rep_["lifts_total"] = int(l.group(1)), int(l.group(2))
    st = re.search(r'\{"openFlag":(\d+),"openingDate":"?([\d-]+|null)"?,"closingDate":', u[m.end():m.end() + 600])
    if st:
        rep_["open_flag"] = int(st.group(1))
        rep_["opening_date"] = None if st.group(2) == "null" else st.group(2)
    up = re.search(r'"updatedAt":"([^"]+)"', u)
    rep_["updated"] = up.group(1) if up else None
    return rep_

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "snapshot.json"
    results = []
    opened = open_status()  # None if SkiCentral unreachable -> statuses unknown
    # Previous snapshot, used as a fallback for the weather arrays if Open-Meteo is unreachable today.
    try:
        prev = {r["name"]: r for r in json.load(open(out))["resorts"]}
    except Exception:
        prev = {}
    WX = ("days", "snow", "tmax", "tmin", "wind", "wcode", "pop")
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
        if d is None:
            print("  using yesterday's weather arrays for this chunk", file=sys.stderr)
        for idx, r in enumerate(chunk):
            if d is not None:
                m = d[idx]
                wx = {"days": m["daily"]["time"], "snow": m["daily"]["snowfall_sum"], "tmax": m["daily"]["temperature_2m_max"],
                      "tmin": m["daily"]["temperature_2m_min"], "wind": m["daily"]["wind_speed_10m_max"],
                      "wcode": m["daily"]["weather_code"], "pop": m["daily"]["precipitation_probability_max"]}
            elif r[0] in prev:
                wx = {k: prev[r[0]][k] for k in WX}
            else:
                # No weather today and nothing to fall back on: ship empty arrays, flagged, so the page shows a dash
                # until the browser's live fetch (or tomorrow's refresh) fills them in.
                print(f"  no weather for {r[0]}; shipping it flagged as missing", file=sys.stderr)
                days = [(datetime.date.today() + datetime.timedelta(days=i - 3)).isoformat() for i in range(10)]
                wx = {"days": days, "snow": [0] * 10, "tmax": [0] * 10, "tmin": [0] * 10, "wind": [0] * 10, "wcode": [3] * 10, "pop": [0] * 10, "wx_missing": True}
            slugs = r[5].split("|")
            detail = next((opened[sl] for sl in slugs if opened and sl in opened), None)
            report = resort_report(r[7]) if len(r) > 7 else None
            # Open if the resort's own report says so (OnTheSnow) or SkiCentral lists it open; closed if either source says closed; else unknown.
            if report and report.get("open_flag") is not None:
                status = "open" if report["open_flag"] == 1 or detail else "closed"
            else:
                status = "unknown" if opened is None else ("open" if detail else "closed")
            if report and report.get("lifts_total") and status == "open":
                detail = f"{report['lifts_open']} of {report['lifts_total']} lifts" + (f" · {report['base']:g}\" base" if report.get("base") else "")
            opens = (report or {}).get("opening_date") or r[6]
            if status == "open" and report and report.get("opening_date"):
                opens = report["opening_date"]
            results.append({
                "name": r[0], "state": r[1], "lat": r[2], "lon": r[3], "elev_m": r[4],
                "slug": r[5], "opens": opens, "status": status, "detail": detail, "report": report, **wx,
            })
        time.sleep(1)
    n_rep = sum(1 for r in results if r["report"])
    n_open = sum(1 for r in results if r["status"] == "open")
    snap = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
            "past_days": 3, "resorts": results}
    with open(out, "w") as f:
        json.dump(snap, f)
    print(f"wrote {out}: {len(results)} resorts ({n_open} open, {n_rep} with resort reports), updated {snap['updated']}")

if __name__ == "__main__":
    main()
