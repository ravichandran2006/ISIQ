from typing import List, Dict, Any

class StandardsReranker:
    """
    Reranks candidate standards based primarily on dense BGE semantic score,
    with standard lifecycle (Active vs Withdrawn) and domain alignment calibration.
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

        for cand in candidates:
            # Base score is the BGE dense semantic cosine similarity
            semantic_score = cand.get("search_score", 0.5)
            std_num_clean = cand.get("standard_number", "").upper().replace(" ", "")
            cand_domain = cand.get("domain", "")
            title_lower = (cand.get("title", "") or "").lower()
            scope_lower = (cand.get("scope", "") or "").lower()

            adj = 0.0

            # 1. Exact IS number cited by user
            if std_num_clean in detected_is_set or any(det in std_num_clean for det in detected_is_set):
                adj += 0.15

            # 2. Precious Metals Semantic Disambiguation vs Food/Bakery Trap
            if is_precious_query:
                # Severe domain clash penalty: bakery/food standards are NEVER precious metals
                if cand_domain == "Food and Agriculture" or any(fw in (title_lower + " " + scope_lower) for fw in ["bakery", "flour", "maida", "bread", "edible", "wheat", "foodstuff", "biscuit manufacturing"]):
                    adj -= 0.60
                elif cand_domain == "Precious Metals and Hallmarking" or any(gw in (title_lower + " " + scope_lower) for gw in ["gold", "bullion", "silver", "hallmark", "precious", "carat", "karat", "assay", "refined bars"]):
                    adj += 0.10

            # 3. Domain alignment calibration
            elif detected_domain and cand_domain == detected_domain:
                adj += 0.05
            elif detected_domain and cand_domain and cand_domain != detected_domain and cand_domain != "General Standard":
                # Mild domain mismatch discouragement
                adj -= 0.10

            # 4. Active status preference over withdrawn
            status = cand.get("status", "Active")
            if "Active" in status or "Reaffirmed" in status:
                adj += 0.02
            elif "Withdrawn" in status or "Superseded" in status:
                adj -= 0.10

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

        # Sort descending by final score
        return sorted(candidates, key=lambda x: x["final_score"], reverse=True)

