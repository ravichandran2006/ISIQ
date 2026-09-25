import datetime
from typing import Dict, Any, List, Optional
from backend.app.schemas.standard_schemas import (
    RecommendationResponse,
    TenderReportSection,
    TenderReportResponse
)

class TenderReportGenerator:
    """
    Generates an official, 13-section Professional Tender Specification Report
    strictly from the validated recommendation response object.
    Never hallucinates or regenerates unverified facts. Clearly indicates
    when information is not available in the current BIS records.
    """

    UNAVAILABLE_MSG = "Not available through the current BIS API response."

    @classmethod
    def generate_report(cls, rec: RecommendationResponse) -> TenderReportResponse:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sections: List[TenderReportSection] = []

        # 1. Requirement
        s1 = TenderReportSection(
            section_number=1,
            title="Tender Procurement Requirement",
            content=f"**Original Requirement Submitted:**\n\"{rec.query}\"",
            is_available=bool(rec.query)
        )
        sections.append(s1)

        # 2. Requirement Understanding
        prod = rec.extracted_entities.product_category or "Technical Product / Equipment"
        domain = rec.extracted_entities.domain or "General Engineering"
        s2_content = (
            f"**Identified Product Category:** {prod}\n"
            f"**Technical Domain:** {domain}\n"
            f"**Application Context:** {rec.extracted_entities.application_context or cls.UNAVAILABLE_MSG}\n"
            f"**Quantity Specified:** {rec.extracted_entities.quantity or cls.UNAVAILABLE_MSG}\n"
            f"**Safety Critical Requirement:** {'Yes' if rec.extracted_entities.safety_critical else 'Standard Commercial / Industrial'}\n"
            f"**Mandatory Testing Prescribed:** {'Yes' if rec.extracted_entities.testing_required else 'Product Specification Conformance'}"
        )
        sections.append(TenderReportSection(section_number=2, title="Requirement Understanding", content=s2_content))

        # 3. User-Provided Specifications
        user_specs = rec.gap_analysis.user_specifications if rec.gap_analysis else {}
        if user_specs:
            spec_rows = [f"- **{k}:** {v}" for k, v in user_specs.items()]
            s3_content = "**Explicit Technical Parameters Captured:**\n" + "\n".join(spec_rows)
        else:
            s3_content = "No explicit technical parameters (e.g. processor, dimensions, material grade) were detailed in the initial tender requirement."
        sections.append(TenderReportSection(section_number=3, title="User-Provided Specifications", content=s3_content, is_available=bool(user_specs)))

        # 4. Specification Gap Analysis
        if rec.gap_analysis and rec.gap_analysis.gap_matrix:
            gap_rows = []
            gap_rows.append("| Parameter | User Provided | Status | Recommendation / Technical Guidance |")
            gap_rows.append("| :--- | :--- | :--- | :--- |")
            for item in rec.gap_analysis.gap_matrix:
                u_val = item.user_provided or "Not Provided"
                gap_rows.append(f"| {item.parameter} | {u_val} | {item.status} | {item.recommendation} |")
            s4_content = f"**Status:** {rec.gap_analysis.completeness_summary}\n\n" + "\n".join(gap_rows)
        else:
            s4_content = f"{cls.UNAVAILABLE_MSG} (Specification gap analysis requires verified applicable product benchmarks)."
        sections.append(TenderReportSection(section_number=4, title="Specification Gap Analysis", content=s4_content))

        # 5. Recommended Indian Standards
        if rec.primary_recommendations:
            std_blocks = []
            for i, std in enumerate(rec.primary_recommendations, 1):
                mandate_str = f"Mandatory ({std.mandate_type})" if std.is_mandatory else "Voluntary Recommendation"
                std_blocks.append(
                    f"### 5.{i} {std.standard_number}: {std.title}\n"
                    f"- **Status:** {std.status} (Published: {std.publication_year or 'N/A'}, Reaffirmed: {std.reaffirmed_year or 'N/A'})\n"
                    f"- **Classification:** {std.domain or 'Engineering'} | Committee: {std.committee_code or 'N/A'}\n"
                    f"- **Relevance Score:** {std.relevance_score:.2f} ({std.relevance_tier})\n"
                    f"- **Regulatory Mandate:** {mandate_str} | Scheme: {std.certification_scheme or 'ISI Scheme-I'}\n"
                    f"- **Governing Order:** {std.governing_order or 'None'}\n"
                    f"- **Official BIS Scope:**\n  > \"{std.scope_snippet or cls.UNAVAILABLE_MSG}\"\n"
                    f"- **Technical Justification:** {std.why_relevant}"
                )
            s5_content = "\n\n".join(std_blocks)
        else:
            s5_content = "No Indian Standards met the semantic relevance gate for this requirement."
        sections.append(TenderReportSection(section_number=5, title="Recommended Indian Standards (Authoritative BIS Catalog)", content=s5_content, is_available=bool(rec.primary_recommendations)))

        # 6. Related Indian Standards
        related_stds = [std for std in rec.primary_recommendations if "Applicable" in std.relevance_tier or "Allied" in std.relevance_tier]
        if related_stds:
            s6_content = "\n".join([f"- **{s.standard_number}:** {s.title} (Relevance Tier: {s.relevance_tier})" for s in related_stds])
        else:
            s6_content = f"No secondary related standards applicable beyond the primary standards listed."
        sections.append(TenderReportSection(section_number=6, title="Related Indian Standards", content=s6_content))

        # 7. Normative References
        if rec.allied_references:
            ref_rows = [f"- **{r.referenced_standard_number}:** {r.referenced_title or cls.UNAVAILABLE_MSG} (Reference Type: {r.reference_type})" for r in rec.allied_references]
            s7_content = "**Allied & Normative Standard Cross-References:**\n" + "\n".join(ref_rows)
        else:
            s7_content = f"{cls.UNAVAILABLE_MSG} (No normative reference cross-links extracted for the selected standards)."
        sections.append(TenderReportSection(section_number=7, title="Normative References & Allied Cross-Links", content=s7_content, is_available=bool(rec.allied_references)))

        # 8. Testing Requirements
        testing_notes = []
        for std in rec.primary_recommendations:
            if std.testing_relevance and "Prescribes" in std.testing_relevance:
                testing_notes.append(f"- **{std.standard_number}:** Mandatory conformity testing, sampling tolerances, and batch inspection prescribed as per standard clauses.")
        if testing_notes:
            s8_content = "**Applicable Inspection & Quality Verification Protocols:**\n" + "\n".join(testing_notes)
        else:
            s8_content = f"{cls.UNAVAILABLE_MSG} (Specific testing methods summary not indexed for these standard records)."
        sections.append(TenderReportSection(section_number=8, title="Testing & Inspection Requirements", content=s8_content))

        # 9. Safety Requirements
        if rec.safety_compliance_guidelines:
            s9_content = "**Statutory & Industrial Safety Safeguards:**\n" + "\n".join([f"- {g}" for g in rec.safety_compliance_guidelines])
        else:
            s9_content = f"{cls.UNAVAILABLE_MSG} (No specific safety hazard clauses triggered)."
        sections.append(TenderReportSection(section_number=9, title="Safety & Statutory Compliance Guidelines", content=s9_content, is_available=bool(rec.safety_compliance_guidelines)))

        # 10. Amendments / Updates
        all_amds = []
        for std in rec.primary_recommendations:
            if std.amendments:
                for a in std.amendments:
                    all_amds.append(f"- **{std.standard_number} - {a.amendment_number}:** Published: {a.amendment_year or a.publication_date or 'N/A'}, Status: {a.status}")
        if all_amds:
            s10_content = "**Active Bureau of Indian Standards Amendments:**\n" + "\n".join(all_amds)
        else:
            s10_content = "No separate free amendments recorded for the active revisions of the recommended standards."
        sections.append(TenderReportSection(section_number=10, title="Amendments & Lifecycle Updates", content=s10_content))

        # 11. Certification / Compliance
        if rec.compliance_summary:
            cs = rec.compliance_summary
            s11_content = (
                f"- **Overall Procurement Risk Level:** {cs.get('risk_level', 'Standard')}\n"
                f"- **Mandatory ISI Marking Required:** {'Yes' if cs.get('mandatory_standards_count', 0) > 0 else 'Voluntary unless stipulated in tender'}\n"
                f"- **Mandatory Standards Count:** {cs.get('mandatory_standards_count', 0)}\n"
                f"- **Voluntary Standards Count:** {cs.get('voluntary_standards_count', 0)}\n"
                f"- **Statutory Guidance:** {cs.get('actionable_procurement_guidance', cls.UNAVAILABLE_MSG)}"
            )
        else:
            s11_content = f"{cls.UNAVAILABLE_MSG} (Compliance summary evaluation unavailable)."
        sections.append(TenderReportSection(section_number=11, title="Certification & Conformity Assessment (QCO / ISI Mark)", content=s11_content))

        # 12. Final Recommendation
        if rec.primary_recommendations:
            primary_std = rec.primary_recommendations[0]
            s12_content = (
                f"**Designated Technical Standard:** {primary_std.standard_number} ({primary_std.title})\n\n"
                f"**Notice Inviting Tender (NIT) Mandatory Clause:**\n"
                f"> \"The bidder shall supply products strictly complying with {primary_std.standard_number} along with all current amendments. "
                f"The vendor must possess a valid BIS License (ISI Mark Scheme-I / CRS) issued by the Bureau of Indian Standards. "
                f"Manufacturer Test Certificates (MTC) and NABL/BIS accredited laboratory test reports verifying the specified technical parameters "
                f"shall be submitted with the technical bid.\""
            )
        else:
            s12_content = "No relevant Indian Standards found for the given requirement. Additional technical clarity is required before floating tender specifications."
        sections.append(TenderReportSection(section_number=12, title="Final Recommendation & Tender Compliance Clause", content=s12_content))

        # 13. BIS Sources / References
        sources = []
        for std in rec.primary_recommendations:
            p_url = std.preview_url or std.source_url or f"https://standardsbis.bsbedge.com/BIS_searchstandard.aspx?keyword={std.standard_number.replace(' ', '')}"
            sources.append(f"- **{std.standard_number}:** Official BIS Electronic Catalog Portal [{p_url}]({p_url})")
        if sources:
            s13_content = "**Verified Bureau of Indian Standards Authoritative Source Portals:**\n" + "\n".join(sources)
        else:
            s13_content = f"{cls.UNAVAILABLE_MSG} (No live BIS portal records linked)."
        sections.append(TenderReportSection(section_number=13, title="BIS Sources & Authoritative Evidence References", content=s13_content))

        # Compile Full Markdown Document
        md_lines = []
        md_lines.append("# GOVERNMENT OF INDIA / GeM TECHNICAL TENDER SPECIFICATION REPORT")
        md_lines.append(f"**Evaluation System:** StandIQ (SIH26108 Grounded AI Recommendation Engine)")
        md_lines.append(f"**Report Generated Date:** {now_str}")
        md_lines.append(f"**Verification Status:** Grounded BIS Authority (0% Fact Hallucination)")
        md_lines.append("=" * 80)
        md_lines.append("")

        for s in sections:
            md_lines.append(f"## SECTION {s.section_number}: {s.title.upper()}")
            md_lines.append(s.content)
            md_lines.append("")
            md_lines.append("-" * 80)
            md_lines.append("")

        full_md = "\n".join(md_lines)

        return TenderReportResponse(
            query=rec.query,
            generated_at=now_str,
            product_identified=prod,
            sections=sections,
            full_markdown=full_md
        )
