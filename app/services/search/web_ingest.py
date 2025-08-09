from __future__ import annotations

import time
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class WebDoc:
    url: str
    title: str
    text: str


_last_host_ts: dict[str, float] = {}


def fetch_urls(
    urls: Iterable[str], per_host_delay_s: float = 1.0, timeout_s: float = 15.0
) -> list[WebDoc]:
    docs: list[WebDoc] = []
    client = httpx.Client(timeout=timeout_s, headers={"User-Agent": "auto-gaming/0.1"})
    for url in urls:
        host = urlparse(url).netloc
        now = time.time()
        last_ts = _last_host_ts.get(host, 0.0)
        delta = now - last_ts
        if delta < per_host_delay_s:
            time.sleep(per_host_delay_s - delta)
        resp = client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        title = soup.title.string.strip() if soup.title and soup.title.string else url
        text = " ".join([p.get_text(separator=" ", strip=True) for p in soup.find_all("p")])
        docs.append(WebDoc(url=url, title=title, text=text))
        _last_host_ts[host] = time.time()
    client.close()
    return docs


def summarize(doc: WebDoc, max_chars: int = 500) -> str:
    # Heuristic summarizer: truncate and keep first sentences
    text = doc.text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(".", 1)[0] + "."
