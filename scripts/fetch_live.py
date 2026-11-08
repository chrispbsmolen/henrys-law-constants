"""Fetch the live errata page and the species pages it concerns, politely (one request every 5 s).
Resumes: pages already listed in fetch_log.csv are not fetched again."""
import sys, time, hashlib, csv, datetime, urllib.request, os
OUT = sys.argv[1]
URLS = [
    ("errata.html", "https://www.henrys-law.org/henry/errata.html"),
    ("casrn_3907-98-0.html", "https://www.henrys-law.org/henry/casrn/3907-98-0"),
    ("casrn_14989-30-1.html", "https://www.henrys-law.org/henry/casrn/14989-30-1"),
    ("casrn_96-47-9.html", "https://www.henrys-law.org/henry/casrn/96-47-9"),
    ("casrn_534-22-5.html", "https://www.henrys-law.org/henry/casrn/534-22-5"),
    ("notes.html", "https://www.henrys-law.org/henry/notes.html"),
    ("references.html", "https://www.henrys-law.org/henry/references.html"),
]
UA = "henry-dataset-check/1.0 (contact: chrispbsmolen@gmail.com)"
rows = []
log = os.path.join(OUT, "fetch_log.csv")
if os.path.exists(log):
    rows = list(csv.reader(open(log)))[1:]
done = {r[4] for r in rows}
URLS = [u for u in URLS if u[0] not in done]
for i, (fn, url) in enumerate(URLS):
    if i: time.sleep(5)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read(); code = r.status
            break
        except OSError as e:
            print("retry after", e, flush=True); time.sleep(10)
    else:
        print("FAILED", url); continue
    open(os.path.join(OUT, fn), "wb").write(body)
    rows.append([url, datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), code, len(body), fn, hashlib.sha256(body).hexdigest()])
    print(rows[-1], flush=True)
    with open(log, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["url", "fetched_utc", "http_status", "bytes", "file", "sha256"]); w.writerows(rows)
