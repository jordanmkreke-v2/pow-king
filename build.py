#!/usr/bin/env python3
"""Inject snapshot.json into page.html -> index.html (standalone site page) and artifact.html (claude.ai page body)."""
import json, pathlib
here = pathlib.Path(__file__).parent
page = (here / "page.html").read_text()
snap = json.dumps(json.load(open(here / "snapshot.json")), separators=(",", ":"))
body = page.replace("/*__SNAPSHOT__*/null", snap, 1)
(here / "artifact.html").write_text(body)

DESC = "Fresh snow, groomer days and storms across every Western Ikon resort. Updated daily."
CROWN_ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 84'%3E"
              "%3Cpath fill='%23f5c542' d='M10 70 L4 24 L34 46 L60 10 L86 46 L116 24 L110 70 Z'/%3E"
              "%3Crect fill='%23f5c542' x='10' y='70' width='100' height='10' rx='3'/%3E%3C/svg%3E")
head, rest = body.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "", 1).split("</style>", 1)
full = (
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    f'<meta name="description" content="{DESC}">\n'
    '<meta property="og:type" content="website">\n<meta property="og:site_name" content="Pow King">\n'
    '<meta property="og:title" content="Who is today\'s pow king?">\n'
    f'<meta property="og:description" content="{DESC}">\n'
    '<meta property="og:url" content="https://powking.io/">\n'
    '<meta property="og:image" content="https://powking.io/og-image.png">\n'
    '<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
    '<meta name="twitter:card" content="summary_large_image">\n'
    '<meta name="twitter:title" content="Who is today\'s pow king?">\n'
    f'<meta name="twitter:description" content="{DESC}">\n'
    '<meta name="twitter:image" content="https://powking.io/og-image.png">\n'
    f'<link rel="icon" href="{CROWN_ICON}">\n'
    + head + "</style>\n</head>\n<body style=\"margin:0\">\n" + rest + "\n</body>\n</html>\n")
(here / "index.html").write_text(full)
print("built index.html and artifact.html")
