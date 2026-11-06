#!/usr/bin/env python3
"""Inject snapshot.json into page.html and write a complete standalone index.html."""
import json, pathlib
here = pathlib.Path(__file__).parent
page = (here / "page.html").read_text()
snap = json.dumps(json.load(open(here / "snapshot.json")), separators=(",", ":"))
body = page.replace("/*__SNAPSHOT__*/null", snap, 1).replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "", 1)
head, rest = body.split("</style>", 1)
full = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="Which Western US Ikon Pass resorts are open, have fresh snow, a groomer day, or a storm on the way.">\n'
        + head + "</style>\n</head>\n<body style=\"margin:0\">\n" + rest + "\n</body>\n</html>\n")
(here / "index.html").write_text(full)
print("built index.html")
