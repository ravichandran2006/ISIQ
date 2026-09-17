document.addEventListener("DOMContentLoaded", () => {
    const inputArea = document.getElementById("procurement-input");
    const charCount = document.getElementById("char-count");
    const btnRecommend = document.getElementById("btn-recommend");
    const domainFilter = document.getElementById("domain-filter");
    const resultsSection = document.getElementById("results-section");
    const entitiesContainer = document.getElementById("entities-container");
    const recsContainer = document.getElementById("recommendations-container");
    const alliedContainer = document.getElementById("allied-container");
    const processingTimeBadge = document.getElementById("processing-time-badge");
    const presetButtons = document.querySelectorAll(".preset-btn");
    const btnBenchmark = document.getElementById("btn-run-benchmark");
    const benchmarkModal = document.getElementById("benchmark-modal");
    const closeModal = document.getElementById("close-modal");
    const benchmarkBody = document.getElementById("benchmark-results-body");
    const btnExportAnnexure = document.getElementById("btn-export-annexure");

    let currentResponseData = null;

    // Character Counter
    inputArea.addEventListener("input", () => {
        charCount.textContent = `${inputArea.value.length} characters`;
    });

    // Preset Scenario click handler
    presetButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            inputArea.value = btn.getAttribute("data-query");
            charCount.textContent = `${inputArea.value.length} characters`;
            triggerRecommendation();
        });
    });

    // Recommend Button click handler
    btnRecommend.addEventListener("click", triggerRecommendation);

    async function triggerRecommendation() {
        const queryText = inputArea.value.trim();
        if (!queryText) {
            alert("Please enter a procurement specification or select a test scenario.");
            return;
        }

        btnRecommend.disabled = true;
        btnRecommend.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Discovering & Analyzing...`;

        try {
            const resp = await fetch("/api/v1/recommend", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    requirement: queryText,
                    domain_hint: domainFilter.value || null,
                    top_k: 5
                })
            });

            if (!resp.ok) {
                throw new Error(`API returned status ${resp.status}`);
            }

            const data = await resp.json();
            currentResponseData = data;
            renderResults(data);
        } catch (err) {
            console.error("Recommendation error:", err);
            alert(`Error discovering standards: ${err.message}`);
        } finally {
            btnRecommend.disabled = false;
            btnRecommend.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Discover Applicable Standards`;
        }
    }

    function renderResults(data) {
        resultsSection.classList.remove("hidden");
        processingTimeBadge.textContent = `${data.processing_time_ms} ms`;

        // 1. Render Extracted Entities
        const ent = data.extracted_entities;
        entitiesContainer.innerHTML = `
            <div class="entity-item">
                <div class="entity-label">Product Category</div>
                <div class="entity-value">${ent.product_category || "General Spec"}</div>
            </div>
            <div class="entity-item">
                <div class="entity-label">Domain Area</div>
                <div class="entity-value">${ent.domain || "Cross-Disciplinary"}</div>
            </div>
            <div class="entity-item">
                <div class="entity-label">Safety Critical</div>
                <div class="entity-value" style="color: ${ent.safety_critical ? '#fda4af' : '#6ee7b7'};">
                    <i class="fa-solid ${ent.safety_critical ? 'fa-shield-halved' : 'fa-check'}"></i> ${ent.safety_critical ? 'Yes (Safety Clauses Apply)' : 'Standard Quality'}
                </div>
            </div>
            <div class="entity-item">
                <div class="entity-label">Testing Requirement</div>
                <div class="entity-value" style="color: #93c5fd;">
                    <i class="fa-solid fa-vial"></i> ${ent.testing_required ? 'Lab Testing Prescribed' : 'Conformity Verification'}
                </div>
            </div>
            ${ent.quantity ? `
            <div class="entity-item">
                <div class="entity-label">Quantity / Capacity</div>
                <div class="entity-value">${ent.quantity}</div>
            </div>` : ''}
        `;

        // 2. Render Recommended Indian Standards
        recsContainer.innerHTML = "";
        if (!data.primary_recommendations || data.primary_recommendations.length === 0) {
            recsContainer.innerHTML = `<div class="standard-card"><p>No directly matching Indian Standards found. Try refining your keywords.</p></div>`;
        } else {
            data.primary_recommendations.forEach(std => {
                const card = document.createElement("div");
                card.className = "standard-card";
                
                // Construct Timeline HTML
                const timelineBadges = (std.lifecycle_timeline || []).map(step => `
                    <span class="timeline-pill"><i class="fa-solid fa-circle-notch"></i> ${step}</span>
                `).join('<i class="fa-solid fa-arrow-right timeline-arrow"></i>');

                // Construct Amendments HTML
                let amendmentsHtml = "";
                if (std.amendments && std.amendments.length > 0) {
                    amendmentsHtml = `
                        <div class="amendments-section">
                            <div class="amendments-header">
                                <i class="fa-solid fa-file-pen"></i> Official BIS Active Amendments (${std.amendments.length})
                            </div>
                            <div class="amendments-list">
                                ${std.amendments.map(a => `
                                    <div class="amendment-item">
                                        <span class="amd-badge">${a.amendment_number} ${a.amendment_year ? '(' + a.amendment_year + ')' : ''}</span>
                                        <span class="amd-title">${a.title || (a.amendment_number + ' to ' + std.standard_number)}</span>
                                        ${a.publication_date ? `<span class="amd-pubdate"><i class="fa-regular fa-calendar"></i> Pub: ${a.publication_date}</span>` : ''}
                                        ${a.committee_code ? `<span class="amd-comm"><i class="fa-solid fa-users"></i> ${a.committee_code}</span>` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }


                card.innerHTML = `
                    <div class="card-top">
                        <div class="std-num-row">
                            <span class="std-number">${std.standard_number} ${std.publication_year ? ': ' + std.publication_year : ''}</span>
                            ${std.reaffirmed_year ? `<span class="badge-tag badge-reaff"><i class="fa-solid fa-arrows-rotate"></i> Reaffirmed ${std.reaffirmed_year}</span>` : ''}
                            ${std.revision_count > 0 ? `<span class="badge-tag badge-rev"><i class="fa-solid fa-code-branch"></i> ${std.revision_text}</span>` : ''}
                            ${std.no_of_amendments > 0 ? `<span class="badge-tag badge-amd"><i class="fa-solid fa-paperclip"></i> ${std.no_of_amendments} Amendments</span>` : ''}
                            <span class="badge-tag badge-primary">${std.status}</span>
                            <span class="badge-tag badge-mand"><i class="fa-solid fa-stamp"></i> ${std.certification_scheme || 'Mandatory ISI'}</span>
                        </div>
                        <div class="score-badge">
                            <div class="score-num">${(std.relevance_score * 100).toFixed(0)}%</div>
                            <div class="score-tier">${std.relevance_tier}</div>
                        </div>
                    </div>
                    <div class="std-title">${std.title}</div>
                    
                    <!-- Lifecycle Timeline -->
                    <div class="timeline-container">
                        <div class="timeline-label"><i class="fa-solid fa-timeline"></i> Standard Life Cycle:</div>
                        <div class="timeline-flow">${timelineBadges}</div>
                    </div>

                    <div class="why-relevant-box">
                        <strong><i class="fa-solid fa-circle-check"></i> Grounded Compliance Rationale:</strong> ${std.why_relevant}
                    </div>

                    <div class="scope-text">
                        <strong>Official BIS Scope:</strong> ${std.scope_snippet || "Scope document available in full standard preview."}
                    </div>

                    ${amendmentsHtml}

                    <div class="card-meta-row">
                        <div class="meta-col"><strong>Committee:</strong> ${std.committee_code || 'N/A'}</div>
                        <div class="meta-col"><strong>ICS Code:</strong> ${std.ics_code || 'N/A'}</div>
                        <div class="meta-col"><strong>Safety Status:</strong> ${std.safety_relevance}</div>
                        <div class="meta-col"><strong>Testing:</strong> ${std.testing_relevance}</div>
                        ${std.preview_url ? `
                        <a href="${std.preview_url}" target="_blank" class="source-link">
                            <i class="fa-solid fa-arrow-up-right-from-square"></i> Official BIS Preview
                        </a>` : ''}
                    </div>
                `;
                recsContainer.appendChild(card);
            });
        }

        // 3. Render Allied & Normative References
        alliedContainer.innerHTML = "";
        if (data.allied_references && data.allied_references.length > 0) {
            data.allied_references.forEach(ref => {
                const ac = document.createElement("div");
                ac.className = "allied-card";
                ac.innerHTML = `
                    <div class="allied-num">${ref.referenced_standard_number} ${ref.referenced_year ? ': ' + ref.referenced_year : ''}</div>
                    <div class="allied-title">${ref.referenced_title || 'Normative Cross-Reference'}</div>
                    <span class="badge-tag badge-primary" style="margin-top: 6px; display: inline-block;">${ref.reference_type}</span>
                `;
                alliedContainer.appendChild(ac);
            });
        } else {
            alliedContainer.innerHTML = `<p style="color: var(--text-muted); font-size: 13px;">No secondary normative references linked for this query.</p>`;
        }

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: "smooth" });
    }

    // Benchmark Trigger
    btnBenchmark.addEventListener("click", async () => {
        benchmarkModal.classList.remove("hidden");
        benchmarkBody.innerHTML = `
            <div class="loader-spinner"></div>
            <p style="text-align: center; color: var(--text-secondary);">Executing SIH benchmark across official procurement scenarios...</p>
        `;

        try {
            const resp = await fetch("/api/v1/evaluation/benchmark");
            const metrics = await resp.json();

            benchmarkBody.innerHTML = `
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px;">
                    <div class="entity-item" style="text-align: center;">
                        <div class="entity-label">Precision @ 1</div>
                        <div class="entity-value" style="font-size: 22px; color: #10b981;">${(metrics.mean_precision_at_1 * 100).toFixed(1)}%</div>
                    </div>
                    <div class="entity-item" style="text-align: center;">
                        <div class="entity-label">Recall @ 5</div>
                        <div class="entity-value" style="font-size: 22px; color: #3b82f6;">${(metrics.mean_recall_at_5 * 100).toFixed(1)}%</div>
                    </div>
                    <div class="entity-item" style="text-align: center;">
                        <div class="entity-label">Mean Reciprocal Rank</div>
                        <div class="entity-value" style="font-size: 22px; color: #f59e0b;">${metrics.mean_reciprocal_rank_mrr.toFixed(3)}</div>
                    </div>
                </div>
                <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
                    <p><strong>Total Test Queries:</strong> ${metrics.total_queries_evaluated}</p>
                    <p><strong>Mean nDCG @ 5:</strong> ${metrics.mean_ndcg_at_5.toFixed(4)}</p>
                    <p><strong>Average Query Latency:</strong> ${metrics.avg_latency_ms} ms</p>
                    <p><strong>Hallucination Rate:</strong> ${metrics.hallucination_rate}</p>
                </div>
                <h4 style="margin-bottom: 8px; font-size: 14px; color: #fff;">Detailed Query Breakdown (Sample):</h4>
                <div style="max-height: 250px; overflow-y: auto; font-size: 12px;">
                    ${metrics.detailed_query_results.map(r => `
                        <div style="padding: 8px; border-bottom: 1px solid var(--border-color);">
                            <div><strong>Query #${r.id}:</strong> ${r.query}</div>
                            <div style="color: #6ee7b7;">Expected: ${r.expected.join(', ')} | Retrieved: ${r.retrieved.join(', ')} (MRR: ${r.mrr})</div>
                        </div>
                    `).join('')}
                </div>
            `;
        } catch (err) {
            benchmarkBody.innerHTML = `<p style="color: #f43f5e;">Failed to run benchmark: ${err.message}</p>`;
        }
    });

    closeModal.addEventListener("click", () => {
        benchmarkModal.classList.add("hidden");
    });

    // GeM Tender Annexure Exporter
    btnExportAnnexure.addEventListener("click", () => {
        if (!currentResponseData) return;
        
        let text = `# TECHNICAL SPECIFICATION ANNEXURE: MANDATORY APPLICABLE INDIAN STANDARDS (BIS)\n`;
        text += `Generated for: "${currentResponseData.query}"\n`;
        text += `Date: ${new Date().toISOString()}\n\n`;
        text += `## 1. Primary Applicable Standards & Life Cycle\n`;
        currentResponseData.primary_recommendations.forEach((s, idx) => {
            text += `${idx + 1}. **${s.standard_number} : ${s.publication_year || ''}** - ${s.title}\n`;
            text += `   - Life Cycle: ${(s.lifecycle_timeline || []).join(' -> ')}\n`;
            text += `   - Certification Scheme: ${s.certification_scheme || 'Mandatory ISI'}\n`;
            text += `   - Revisions: ${s.revision_text || 'Original Publication'}\n`;
            text += `   - Amendments: ${s.no_of_amendments || 0} active amendments\n`;
            text += `   - Compliance Rationale: ${s.why_relevant}\n`;
            text += `   - Safety Relevance: ${s.safety_relevance}\n`;
            text += `   - Testing Methods: ${s.testing_relevance}\n\n`;
        });

        text += `## 2. Allied & Normative Cross-References\n`;
        currentResponseData.allied_references.forEach((r, idx) => {
            text += `- ${r.referenced_standard_number}: ${r.referenced_title || ''} (${r.reference_type})\n`;
        });

        const blob = new Blob([text], { type: "text/markdown" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `GeM_BIS_Standards_Annexure.md`;
        a.click();
        URL.revokeObjectURL(url);
    });
});
