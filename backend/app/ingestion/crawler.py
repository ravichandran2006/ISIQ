import time
import requests
import os
import hashlib
import re
import json
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

from backend.app.ingestion.parser import BISPreviewParser
from backend.app.recommendation.classifier import BISDomainClassifier
from backend.app.core.config import settings

class BISCrawler:
    """
    High-performance, cached crawler for BIS standard search results, preview pages,
    and amendment documents.
    """

    BASE_SEARCH_URL = "https://standardsbis.bsbedge.com/BIS_searchstandard.aspx"
    BASE_PREVIEW_URL = "https://standardsbis.bsbedge.com/BIS_Preview.aspx"
    BASE_AMENDMENTS_URL = "https://standardsbis.bsbedge.com/BIS_Amendments.aspx"
    AUTOCOMPLETE_URL = "https://standardsbis.bsbedge.com/popupextender.aspx/GetStdNo_Bis"

    def __init__(self, cache_dir: str = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.cache_dir = cache_dir or settings.CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, url: str) -> str:
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.html")

    def fetch_url(self, url: str, use_cache: bool = True) -> Optional[str]:
        cache_file = self._get_cache_path(url)
        if use_cache and os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass

        try:
            resp = self.session.get(url, timeout=8)
            if resp.status_code == 200:
                html = resp.text
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(html)
                return html
        except Exception as e:
            print(f"[CRAWLER ERROR] Fetch failed for {url}: {e}")
        return None

    def search_standard_number_autocomplete(self, prefix: str) -> List[str]:
        try:
            headers = {
                'Content-Type': 'application/json; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest'
            }
            payload = {"prefixText": prefix.replace("IS", "").strip(), "count": 10, "contextKey": ""}
            resp = self.session.post(self.AUTOCOMPLETE_URL, json=payload, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                raw_items = data.get("d", [])
                links = []
                for item_str in raw_items:
                    import json
                    try:
                        item = json.loads(item_str)
                        sec = item.get("Second", "")
                        if sec:
                            links.append(f"{self.BASE_SEARCH_URL}?{sec}")
                    except Exception:
                        pass
                return links
        except Exception as e:
            print(f"[AUTOCOMPLETE ERROR] {e}")
        return []

    BASE_FREE_AMENDMENTS_URL = "https://standardsbis.bsbedge.com/BIS_FreeAmendments.aspx?id=0"

    def fetch_free_amendments(self, standard_number: str) -> List[Dict[str, Any]]:
        """
        Directly queries BIS_FreeAmendments.aspx via POST to retrieve official free amendments,
        publication dates, technical committees, and status.
        """
        try:
            # 1. Acquire initial ASP.NET ViewState tokens
            res = self.session.get(self.BASE_FREE_AMENDMENTS_URL, timeout=8)
            if res.status_code != 200:
                return []

            soup = BeautifulSoup(res.text, "html.parser")
            viewstate = soup.find("input", {"name": "__VIEWSTATE"})
            viewstate_val = viewstate["value"] if viewstate else ""
            vgen = soup.find("input", {"name": "__VIEWSTATEGENERATOR"})
            vgen_val = vgen["value"] if vgen else ""
            tsm = soup.find("input", {"name": "_TSM_HiddenField_"})
            tsm_val = tsm["value"] if tsm else ""
            event_val = soup.find("input", {"name": "__EVENTVALIDATION"})
            event_val_val = event_val["value"] if event_val else ""

            # 2. Formulate Search Filter POST
            data = {
                "_TSM_HiddenField_": tsm_val,
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                "__VIEWSTATE": viewstate_val,
                "__VIEWSTATEGENERATOR": vgen_val,
                "__VIEWSTATEENCRYPTED": "",
                "ctl00$ContentPlaceHolder1$TextBox1": standard_number,
                "ctl00$ContentPlaceHolder1$btn_Filter": "Filter"
            }
            if event_val_val:
                data["__EVENTVALIDATION"] = event_val_val

            post_res = self.session.post(self.BASE_FREE_AMENDMENTS_URL, data=data, timeout=10)
            if post_res.status_code == 200:
                amendments = BISPreviewParser.parse_free_amendments_html(post_res.text, target_standard=standard_number)
                return amendments
        except Exception as e:
            pass
        return []

    def search_keyword(self, keyword: str, max_preview_fetch: int = 6) -> List[Dict[str, Any]]:
        clean_kw = keyword.strip()
        if not clean_kw:
            return []

        url = f"{self.BASE_SEARCH_URL}?keyword={requests.utils.quote(clean_kw)}&id=0"
        html = self.fetch_url(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        items_to_fetch = []

        # Find search result entries with preview and amendment links
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "BIS_Preview.aspx?id=" in href:
                p_url = f"https://standardsbis.bsbedge.com/{href.lstrip('./')}" if not href.startswith("http") else href
                
                # Check for nearby amendment link
                amd_url = None
                parent = a.find_parent("tr") or a.find_parent("div")
                if parent:
                    for amd_a in parent.find_all("a", href=True):
                        if "BIS_Amendments.aspx" in amd_a["href"]:
                            amd_url = f"https://standardsbis.bsbedge.com/{amd_a['href'].lstrip('./')}"
                            break

                items_to_fetch.append({"preview_url": p_url, "amendment_url": amd_url})

        # Autocomplete fallback if direct keyword search yielded 0
        if not items_to_fetch:
            auto_links = self.search_standard_number_autocomplete(clean_kw)
            for alink in auto_links[:2]:
                a_html = self.fetch_url(alink)
                if a_html:
                    asoup = BeautifulSoup(a_html, "html.parser")
                    for a in asoup.find_all("a", href=True):
                        if "BIS_Preview.aspx?id=" in a["href"]:
                            h = a["href"]
                            p_url = f"https://standardsbis.bsbedge.com/{h.lstrip('./')}" if not h.startswith("http") else h
                            items_to_fetch.append({"preview_url": p_url, "amendment_url": None})

        # Concurrently fetch and parse previews and amendments
        results = []
        targets = items_to_fetch[:max_preview_fetch]

        def _fetch_and_enrich(item: Dict[str, Any]):
            p_url = item["preview_url"]
            p_html = self.fetch_url(p_url)
            if not p_html:
                return None
            parsed = BISPreviewParser.parse_preview_html(p_html, source_url=p_url)
            if not parsed:
                return None
            
            # Fetch amendment details from Free Amendments endpoint or Preview link
            std_num = parsed.get("standard_number", "")
            amendments = self.fetch_free_amendments(std_num)
            
            if not amendments and item.get("amendment_url"):
                amd_html = self.fetch_url(item["amendment_url"])
                if amd_html:
                    amendments = BISPreviewParser.parse_amendments_html(amd_html, std_num)
            
            parsed["amendments"] = amendments
            parsed["no_of_amendments"] = len(amendments)
            
            domain = BISDomainClassifier.classify_domain(
                committee_code=parsed.get("committee_code", ""),
                ics_code=parsed.get("ics_code", ""),
                title=parsed.get("title", ""),
                scope=parsed.get("scope", "")
            )
            parsed["domain"] = domain
            parsed["preview_url"] = p_url
            parsed["safety_testing"] = BISDomainClassifier.analyze_safety_and_testing(
                title=parsed.get("title", ""),
                scope=parsed.get("scope", ""),
                committee_code=parsed.get("committee_code", "")
            )
            return parsed

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_url = {executor.submit(_fetch_and_enrich, it): it for it in targets}
            for future in as_completed(future_to_url):
                try:
                    res = future.result()
                    if res:
                        results.append(res)
                except Exception as e:
                    pass

        return results

