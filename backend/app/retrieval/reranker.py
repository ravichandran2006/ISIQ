from typing import List, Dict, Any

class StandardsReranker:
    """
    Reranks candidate standards by combining lexical token overlap,
    semantic vector score, domain context matching, and exact identifier boost.
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

        query_tokens = set(query.lower().split())
        detected_is_set = set(num.upper().replace(" ", "") for num in (detected_is_numbers or []))

        for cand in candidates:
            base_score = cand.get("search_score", 0.5)
            std_num_clean = cand.get("standard_number", "").upper().replace(" ", "")
            cand_title = cand.get("title", "").lower()
            cand_domain = cand.get("domain", "")

            bonus = 0.0

            # 1. Exact IS number match bonus (Critical: Exact IS match must never be lost)
            if std_num_clean in detected_is_set or any(det in std_num_clean for det in detected_is_set):
                bonus += 1.5

            # 2. Domain alignment bonus
            if detected_domain and cand_domain == detected_domain:
                bonus += 0.25

            # 3. Product title overlap
            title_tokens = set(cand_title.split())
            overlap = len(query_tokens.intersection(title_tokens))
            bonus += min(0.3, overlap * 0.1)

            # 4. Active status boost over withdrawn
            status = cand.get("status", "Active")
            if "Active" in status or "Reaffirmed" in status:
                bonus += 0.1
            elif "Withdrawn" in status or "Superseded" in status:
                bonus -= 0.3

            final_score = base_score + bonus
            cand["final_score"] = round(final_score, 4)

            # Determine relevance tier
            if final_score >= 0.8:
                cand["relevance_tier"] = "Primary Mandatory Standard"
            elif final_score >= 0.45:
                cand["relevance_tier"] = "Applicable Standard"
            else:
                cand["relevance_tier"] = "Allied Reference Standard"

        # Sort descending by final score
        return sorted(candidates, key=lambda x: x["final_score"], reverse=True)
