import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

class BISPreviewParser:
    """
    Robust, DOM-resilient parser for Bureau of Indian Standards (BIS) preview and search pages.
    Extracts:
    - Standard number, publication year, reaffirmed year
    - Number of revisions & revision text (e.g. Sixth Revision)
    - Status (Active / Withdrawn / Superseded)
    - Technical Committee & ICS code
    - Scope and normative references
    - Superseding and lifecycle details
    """

    REVISION_MAP = {
        "first revision": 1, "second revision": 2, "third revision": 3,
        "fourth revision": 4, "fifth revision": 5, "sixth revision": 6,
        "seventh revision": 7, "eighth revision": 8, "ninth revision": 9,
        "tenth revision": 10
    }

    @classmethod
    def parse_preview_html(cls, html_content: str, source_url: str = "") -> Optional[Dict[str, Any]]:
        if not html_content or len(html_content.strip()) < 50:
            return None

        soup = BeautifulSoup(html_content, "html.parser")
        body_text = soup.get_text(separator="\n", strip=True)

        if not ("Bureau of Indian Standards" in body_text or "IS " in body_text or "Specification" in body_text or "Standard" in body_text):
            return None

        # 1. Extract Header Element (typically in <b> tag or <p><b>)
        b_tags = [b.get_text(strip=True) for b in soup.find_all(["b", "strong"]) if b.get_text(strip=True)]
        
        header_text = ""
        for b in b_tags:
            if re.search(r'IS\s+\d+|SP\s+\d+', b, re.IGNORECASE):
                header_text = b
                break

        if not header_text:
            match = re.search(r'((?:IS|SP)\s+[\d\(\)\-\:\sPart]+?:\s*\d{4}[^\n\r<]+)', body_text, re.IGNORECASE)
            if match:
                header_text = match.group(1).strip()
            elif b_tags:
                header_text = b_tags[0]

        if not header_text or len(header_text) < 3:
            return None

        # Deconstruct Header into Standard Number, Publication Year, and Title
        std_match = re.search(r'((?:IS|SP)\s+[\d\(\)\-\:\sPart]+?)\s*:\s*(\d{4})\s*[:\-]*(.*)', header_text, re.IGNORECASE)
        
        if std_match:
            standard_number = std_match.group(1).strip()
            standard_number = re.sub(r'\s*:\s*Part\s*', ' (Part ', standard_number)
            if '(Part' in standard_number and not standard_number.endswith(')'):
                standard_number += ')'
            pub_year = int(std_match.group(2).strip())
            title = std_match.group(3).strip()
        else:
            simple_match = re.search(r'((?:IS|SP)\s+[\d\(\)\-\sPart]+)(.*)', header_text, re.IGNORECASE)
            if simple_match:
                standard_number = simple_match.group(1).strip()
                title = simple_match.group(2).strip(" :-")
                pub_year = 0
            else:
                standard_number = header_text[:30]
                title = header_text[30:]
                pub_year = 0

        # Clean title
        title = re.sub(r'^[–\-\:\s]+', '', title).strip()
        if not title:
            for b in b_tags:
                if b != header_text and len(b) > 5 and not b.startswith("ICS") and not b.startswith("Reaffirmed"):
                    title = b
                    break
        if not title:
            title = standard_number

        # 2. Extract Revisions & Superseding Information from Title
        revision_count = 0
        revision_text = "Original Publication"
        for rev_name, rev_num in cls.REVISION_MAP.items():
            if rev_name in title.lower():
                revision_count = rev_num
                revision_text = rev_name.title()
                break

        # Check for superseding IS numbers in title or text
        supersedes_match = re.search(r'(?:superseding|replaces|superseded)\s+(IS\s+[\d\s,and]+)', title + " " + body_text[:1000], re.I)
        supersedes_is = supersedes_match.group(1).strip() if supersedes_match else None

        # 3. Extract ICS Code, Technical Committee and Reaffirmation Year
        ics_code = None
        committee_code = None
        reaffirmed_year = None

        for td in soup.find_all(["td", "b", "p", "div"]):
            t = td.get_text(strip=True)
            if re.match(r'ICS\s+[\d\.]+', t, re.IGNORECASE):
                ics_code = t.replace("ICS", "").strip()
            elif re.match(r'^(FAD|CED|ETD|MED|CHD|PCD|TED|TXD|LITD|MSD|WRD)\s+\d+', t, re.IGNORECASE):
                committee_code = t.strip()
            elif "Reaffirmed" in t:
                re_match = re.search(r'Reaffirmed\s+(\d{4})', t, re.IGNORECASE)
                if re_match:
                    reaffirmed_year = int(re_match.group(1))

        # 4. Extract Scope
        scope_text = ""
        scope_header = soup.find(lambda tag: tag.name in ["b", "p", "strong"] and re.search(r'^\s*1\s+Scope', tag.get_text(strip=True), re.I))
        if scope_header:
            curr = scope_header.find_next_sibling()
            scope_parts = []
            while curr:
                t = curr.get_text(strip=True)
                if re.search(r'^\s*2\s+References', t, re.I) or re.search(r'^\s*2\s+Normative', t, re.I):
                    break
                if t and not curr.find(["b", "strong"]):
                    scope_parts.append(t)
                elif t and curr.name == "p":
                    scope_parts.append(t)
                curr = curr.find_next_sibling()
            scope_text = " ".join(scope_parts).strip()

        if not scope_text:
            scope_match = re.search(r'1\s+Scope\s*(.*?)(?:2\s+References|\Z)', body_text, re.DOTALL | re.IGNORECASE)
            if scope_match:
                scope_text = scope_match.group(1).strip()

        # 5. Extract Normative References
        references = []
        ref_header = soup.find(lambda tag: tag.name in ["b", "p", "strong"] and re.search(r'^\s*2\s+References', tag.get_text(strip=True), re.I))
        if ref_header:
            parent = ref_header.parent
            if parent:
                for p in parent.find_all("p"):
                    p_text = p.get_text(strip=True)
                    if not p_text or "1 Scope" in p_text or "2 References" in p_text:
                        continue
                    a_tag = p.find("a")
                    ref_link = a_tag.get("href") if a_tag else ""
                    
                    ref_match = re.search(r'(IS\s+[\d\(\)\-\:\sPart]+?)(?:\s*:\s*(\d{4}))?\s+(.*)', p_text)
                    if ref_match:
                        ref_std = ref_match.group(1).strip()
                        ref_yr = int(ref_match.group(2)) if ref_match.group(2) else None
                        ref_title = ref_match.group(3).strip()
                        references.append({
                            "standard_number": ref_std,
                            "year": ref_yr,
                            "title": ref_title,
                            "link": ref_link
                        })

        status = "Active"
        if reaffirmed_year:
            status = f"Reaffirmed ({reaffirmed_year})"

        return {
            "standard_number": standard_number.strip(),
            "publication_year": pub_year,
            "reaffirmed_year": reaffirmed_year,
            "revision_count": revision_count,
            "revision_text": revision_text,
            "supersedes_is": supersedes_is,
            "title": title.strip(),
            "ics_code": ics_code,
            "committee_code": committee_code,
            "status": status,
            "scope": scope_text,
            "references": references,
            "source_url": source_url,
            "is_official": True
        }

    @staticmethod
    def parse_amendments_html(html_content: str, parent_standard: str = "") -> List[Dict[str, Any]]:
        """
        Parses BIS_Amendments.aspx to extract all individual amendments, amendment years, and preview links.
        """
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        amendments = []
        
        # Look for amendment rows / text
        # Pattern e.g. "IS 208 Amd. 1 : 2023" or "IS 1011 Amd. 1 : 2006"
        body_text = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in body_text.split("\n") if l.strip()]

        for i, line in enumerate(lines):
            amd_match = re.search(r'(IS\s+[\d\(\)\-\s]+)\s+Amd\.?\s*(\d+)\s*:\s*(\d{4})', line, re.I)
            if amd_match:
                std_num = amd_match.group(1).strip()
                amd_num = f"Amd. {amd_match.group(2)}"
                amd_yr = int(amd_match.group(3))
                
                # Look for title on next line
                amd_title = f"Amendment No. {amd_match.group(2)} to {std_num}"
                if i + 1 < len(lines) and "Amendment" in lines[i + 1]:
                    amd_title = lines[i + 1]

                amendments.append({
                    "amendment_number": amd_num,
                    "amendment_year": amd_yr,
                    "title": amd_title,
                    "status": "Active"
                })

        return amendments

    @classmethod
    def parse_free_amendments_html(cls, html_content: str, target_standard: str = "") -> List[Dict[str, Any]]:
        """
        Parses BIS_FreeAmendments.aspx DOM response containing:
        - Repeater rows with div.div_abc_main
        - Amendment label (e.g. IS 1011 Amd. 1 : 2006)
        - Technical Committee (e.g. FAD 24, CED 15)
        - Status (Active)
        - Publication Date (e.g. 4/24/2018, 1/17/2023)
        """
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        items = soup.select("div.div_abc_main")
        amendments = []

        # Normalize target standard for exact matching (e.g., 'IS 1011' vs 'IS 10110')
        target_norm = re.sub(r'[\s\(\)\:]+', '', target_standard).upper() if target_standard else ""

        for item in items:
            std_elem = item.select_one('span[id*="lblstdno_rptr"]')
            std_text = std_elem.get_text(strip=True) if std_elem else ''

            status_elem = item.select_one('span[id*="lblstatus"]')
            status = status_elem.get_text(strip=True) if status_elem else 'Active'

            div1 = item.select_one('div.div-abc1')
            desc = ''
            committee = ''
            if div1:
                div_text = div1.get_text('\n', strip=True)
                lines = [l.strip() for l in div_text.split('\n') if l.strip()]
                for idx, line in enumerate(lines):
                    if 'Amendment No.' in line:
                        desc = line
                    if 'Technical Committee :' in line:
                        committee = lines[idx + 1] if idx + 1 < len(lines) else ''

            div2 = item.select_one('div.div-abc2')
            pub_date = ''
            if div2:
                div2_text = div2.get_text('\n', strip=True)
                if 'Publication Date :' in div2_text:
                    parts = div2_text.split('Publication Date :')
                    if len(parts) > 1:
                        pub_date = parts[1].strip().split('\n')[0]

            # Parse standard number, amendment number and year
            m = re.search(r'((?:IS|SP)\s+[\d\(\)\-\sPart]+?)\s*Amd\.?\s*(\d+)\s*:\s*(\d{4})', std_text, re.IGNORECASE)
            if m:
                base_std = m.group(1).strip()
                amd_num_int = m.group(2)
                amd_yr = int(m.group(3))
                amd_num = f"Amd. {amd_num_int}"

                # Check if this belongs to target_standard
                base_norm = re.sub(r'[\s\(\)\:]+', '', base_std).upper()
                if target_norm and base_norm != target_norm:
                    continue

                if not desc:
                    desc = f"Amendment No. {amd_num_int} to {base_std}"

                amendments.append({
                    "amendment_number": amd_num,
                    "amendment_year": amd_yr,
                    "publication_date": pub_date,
                    "committee_code": committee,
                    "title": desc,
                    "status": status,
                    "source_url": "https://standardsbis.bsbedge.com/BIS_FreeAmendments.aspx?id=0"
                })

        return amendments

