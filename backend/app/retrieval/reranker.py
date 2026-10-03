import re
import difflib
from typing import List, Dict, Any

class StandardsReranker:
    """
    Reranks candidate standards based primarily on dense BGE semantic score,
    with title concordance, sequence similarity, standard lifecycle (Active vs Withdrawn)
    and domain alignment calibration.
    """

    @staticmethod
    def rerank(
        candidates: List[Dict[str, Any]],
        query: str,
        detected_domain: str = None,
        detected_is_numbers: List[str] = None
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        detected_is_set = set(num.upper().replace(" ", "") for num in (detected_is_numbers or []))

        is_precious_query = (detected_domain == "Precious Metals and Hallmarking") or any(
            w in query.lower() for w in ["gold", "silver", "bullion", "hallmark", "hallmarking", "carat", "karat"]
        )

        clean_q = re.sub(r'\(.*?\)', '', query.strip())
        raw_q_words = re.findall(r'[a-zA-Z0-9]+', clean_q.lower())
        generic_tokens = {
            "code", "practice", "specification", "specifications", "standard", "standards",
            "part", "revision", "first", "second", "third", "fourth", "fifth",
            "for", "and", "the", "in", "of", "use", "general", "requirements", "method", "methods",
            "technical", "proposed", "details", "description", "scope", "item", "items", "clause",
            "make", "model", "type", "latest", "available", "website", "warranty", "period",
            "must", "service", "pack", "preloaded", "generation", "higher", "better", "name",
            "procure", "procurement", "purchase", "supply"
        }
        q_content = {w for w in raw_q_words if len(w) > 2 and w not in generic_tokens}

        q_part_match = re.search(r'\bpart\s*[:\-]?\s*(\d+|[ivx]+)\b', clean_q.lower())
        target_part = q_part_match.group(1).lower() if q_part_match else None
        roman_map = {"1": "i", "2": "ii", "3": "iii", "4": "iv", "5": "v", "i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5"}
        alt_part = roman_map.get(target_part, "") if target_part else ""

        for cand in candidates:
            # Base score is the BGE dense semantic cosine similarity or exact title match score
            semantic_score = cand.get("search_score", 0.5)
            std_num_clean = cand.get("standard_number", "").upper().replace(" ", "")
            cand_domain = cand.get("domain", "")
            title_lower = (cand.get("title", "") or "").lower()
            scope_lower = (cand.get("scope", "") or "").lower()

            clean_cand_title = re.sub(r'\(.*?\)', '', title_lower).strip()
            seq_sim = difflib.SequenceMatcher(None, clean_q.lower(), clean_cand_title.lower()).ratio()
            cand["seq_sim"] = round(seq_sim, 4)

            adj = 0.0

            # 1. Title token concordance and sequence match boost
            t_words = re.findall(r'[a-zA-Z0-9]+', clean_cand_title)
            t_content = {w for w in t_words if len(w) > 2 and w not in generic_tokens}

            is_sub = (len(clean_q.strip()) > 8 and clean_q.strip().lower() in title_lower) or (len(clean_cand_title) > 8 and clean_cand_title in clean_q.strip().lower())

            if t_content and q_content:
                overlap = len(q_content & t_content)
                concordance = overlap / len(t_content)
                if is_sub or (concordance >= 0.75 and overlap >= 2):
                    adj += 0.35
                elif concordance >= 0.45 and overlap >= 2:
                    adj += 0.20
                elif concordance >= 0.25 and overlap >= 1:
                    adj += 0.08

            # 2. Specific Part number alignment
            if target_part:
                cand_full_text = (cand.get("standard_number", "") + " " + title_lower).lower()
                has_target_part = (f"part {target_part}" in cand_full_text or
                                   f"part {alt_part}" in cand_full_text or
                                   f"part-{target_part}" in cand_full_text or
                                   f"part{target_part}" in cand_full_text or
                                   f"({target_part})" in cand_full_text or
                                   f"({alt_part})" in cand_full_text or
                                   f"(part {target_part})" in cand_full_text or
                                   f"(part {alt_part})" in cand_full_text)
                if has_target_part:
                    adj += 0.15
                else:
                    adj -= 0.15

            # 3. Exact IS number cited by user
            if std_num_clean in detected_is_set or any(det in std_num_clean for det in detected_is_set):
                adj += 0.15

            # 4. Precious Metals Semantic Disambiguation vs Food/Bakery Trap
            if is_precious_query:
                # Severe domain clash penalty: bakery/food standards are NEVER precious metals
                if cand_domain == "Food and Agriculture" or any(fw in (title_lower + " " + scope_lower) for fw in ["bakery", "flour", "maida", "bread", "edible", "wheat", "foodstuff", "biscuit manufacturing"]):
                    adj -= 0.60
                elif cand_domain == "Precious Metals and Hallmarking" or any(gw in (title_lower + " " + scope_lower) for gw in ["gold", "bullion", "silver", "hallmark", "precious", "carat", "karat", "assay", "refined bars"]):
                    adj += 0.10

            # 5. Domain alignment calibration
            elif detected_domain and cand_domain == detected_domain:
                adj += 0.15
            elif detected_domain and cand_domain and cand_domain != detected_domain and cand_domain != "General Standard":
                # Severe penalty for cross-domain discordance
                severe_mismatch = (
                    (detected_domain == "Electronics and Information Technology" and cand_domain in ["Chemicals", "Food and Agriculture", "Textiles", "Civil Engineering"]) or
                    (detected_domain == "Precious Metals and Hallmarking" and cand_domain in ["Food and Agriculture", "Chemicals", "Electronics and Information Technology"]) or
                    (detected_domain == "Food and Agriculture" and cand_domain in ["Precious Metals and Hallmarking", "Chemicals", "Mechanical Engineering", "Electronics and Information Technology"]) or
                    (detected_domain == "Civil Engineering" and cand_domain in ["Food and Agriculture", "Precious Metals and Hallmarking", "Electronics and Information Technology"])
                )
                if severe_mismatch:
                    adj -= 0.60
                else:
                    adj -= 0.25

            # 6. Active status preference over withdrawn
            status = cand.get("status", "Active")
            if "Active" in status or "Reaffirmed" in status:
                adj += 0.02
            elif "Withdrawn" in status or "Superseded" in status:
                adj -= 0.10

            # 7. In-domain mandatory statutory compliance boost
            if cand.get("is_mandatory") and detected_domain and cand_domain == detected_domain:
                adj += 0.12

            final_score = min(1.0, max(0.0, semantic_score + adj))
            cand["final_score"] = round(final_score, 4)
            cand["semantic_score"] = round(semantic_score, 4)

            # Determine relevance tier dynamically
            is_mand = cand.get("is_mandatory", False)
            if final_score >= 0.65:
                cand["relevance_tier"] = "Primary Mandatory Standard" if is_mand else "Primary Recommended Standard (Voluntary)"
            elif final_score >= 0.50:
                cand["relevance_tier"] = "Applicable Standard"
            else:
                cand["relevance_tier"] = "Allied Reference Standard"

        # Sort descending by final score, using sequence similarity to the query as the tie-breaker
        return sorted(candidates, key=lambda x: (x["final_score"], x.get("seq_sim", 0.0)), reverse=True)

