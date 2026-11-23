"""Download 26 PDFs: open-access papers (Nature, PMC, RSC gold OA, a repository copy),
6 Wiley papers through the Wiley TDM token, and 7 Springer papers the university subscribes to.

Run on the university network (eduroam / VPN):
    py -3.14 download_open_and_springer.py
Asks only for the Wiley TDM token (Enter to skip the 6 Wiley papers). Saves to ./pdf2/,
skips files that are already there, writes download2_log.csv. One request every 3 s.
"""
import csv, getpass, os, time
from pathlib import Path
from urllib.parse import quote
import requests

OUT = Path("pdf2"); LOG = Path("download2_log.csv"); PAUSE_S = 3.0
UA = {"User-Agent": "Mozilla/5.0 (research text mining, University of Vigo)"}

NATURE = {"P014": "s41467-020-20769-x", "P013": "s41467-025-63274-9", "P273": "s41467-025-62287-8",
          "P041": "s41467-021-26724-8", "P081": "s41467-023-44652-7", "P073": "s41467-019-09626-8",
          "P278": "s41598-025-15079-5"}
PMC = {"P000": "PMC9661489", "P001": "PMC5643516", "P015": "PMC12622441"}
WILEY = {"P206": "10.1002/anie.202521193", "P249": "10.1002/rar2.70362", "P228": "10.1002/anie.202417435",
         "P037": "10.1002/smll.202308767", "P093": "10.1002/adfm.202111446", "P109": "10.1002/anie.202114707"}
SPRINGER = {"P021": "10.1007/s12274-022-4177-x", "P022": "10.1007/s12274-024-6513-9", "P155": "10.1007/s10800-026-02463-w",
            "P046": "10.1007/s40843-024-3168-3", "P189": "10.1007/s12274-023-6079-y", "P198": "10.1007/s40843-023-2793-3",
            "P225": "10.1007/s42864-023-00208-2"}
OTHER = {"P127": "https://pubs.rsc.org/en/content/articlepdf/2022/sc/d2sc04776d",
         "P244": "https://pubs.rsc.org/en/content/articlepdf/2025/ey/d4ey00274a",
         "P177": "https://ualberta.scholaris.ca/bitstreams/f70da5c2-8051-473f-818a-d80c1fbe4350/download"}


def pages(path):
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def fetch(url, path, headers=None):
    r = requests.get(url, headers={**UA, **(headers or {})}, timeout=120, allow_redirects=True)
    if r.status_code != 200:
        return f"HTTP {r.status_code}"
    if not r.content.startswith(b"%PDF"):
        return f"not a PDF ({r.headers.get('content-type')})"
    path.write_bytes(r.content)
    n = pages(path)
    if n is not None and n <= 1:
        path.unlink()
        return "1 page only (no access seen); not saved"
    return f"ok, {n} pages" if n else "ok"


def main():
    token = os.environ.get("WILEY_TDM_TOKEN") or getpass.getpass("Wiley TDM token (Enter to skip Wiley): ").strip()
    jobs = []
    jobs += [(k, "Nature", f"https://www.nature.com/articles/{v}.pdf", None) for k, v in NATURE.items()]
    jobs += [(k, "PMC", f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={v}&blobtype=pdf", None) for k, v in PMC.items()]
    jobs += [(k, "Wiley", "https://api.wiley.com/onlinelibrary/tdm/v1/articles/" + quote(v, safe=""),
              {"Wiley-TDM-Client-Token": token}) for k, v in WILEY.items()]
    jobs += [(k, "Springer", f"https://link.springer.com/content/pdf/{v}.pdf", None) for k, v in SPRINGER.items()]
    jobs += [(k, "other", v, None) for k, v in OTHER.items()]
    OUT.mkdir(exist_ok=True)
    rows = []
    for name, src, url, hdr in jobs:
        path = OUT / f"{name}.pdf"
        if path.exists():
            status = "already there"
        elif src == "Wiley" and not token:
            status = "skipped (no token)"
        else:
            try:
                status = fetch(url, path, hdr)
            except requests.RequestException as e:
                status = f"network error: {e}"
            time.sleep(PAUSE_S)
        print(f"{name}.pdf  {src:9s} {status}")
        rows.append([name, src, url, status])
    with LOG.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["file", "source", "url", "status"]); w.writerows(rows)
    good = sum(s.startswith("ok") or s == "already there" for *_, s in rows)
    print(f"\nDone: {good} of {len(rows)} saved in {OUT}/. Details in {LOG}.")


if __name__ == "__main__":
    main()
