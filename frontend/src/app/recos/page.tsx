/**
 * Recommendations and Output page (DELIVERY PHASE).
 * SG-4 gate must be passed before PDF/DOCX export buttons become active.
 */

"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { WorkflowBar } from "@/components/layout/WorkflowBar";
import { Sg4ValidationPanel } from "@/components/sourcing/Sg4ValidationPanel";
import { exportRecommendationsDocx, exportRecommendationsPdf, getNeed, getRecommendations, updateNeedStatus } from "@/lib/api";
import type { Status, ExportReportRequest, SolutionRecommendations, GapAnalysisResponse, RecommendationSolutionPayload } from "@/lib/types";

type DeliverySelection = {
    id: string;
    name: string;
    relevance: number;
    overall: number;
};

/** Saved from Discovery — matches localStorage + gap-analysis API shape */
type DiscoverySelectedSolution = {
    id: string;
    name: string;
    relevance?: number;
    description?: string;
    source?: string;
    features?: string[];
    business_impact?: string;
    maturity_level?: string;
    gap_analysis?: GapAnalysisResponse | null;
};

function RecosPageContent() {
    const searchParams = useSearchParams();
    const ipmId = searchParams.get("id") || undefined;
    const [showGate, setShowGate] = useState(false);
    const [gateCleared, setGateCleared] = useState(false);
    const [deliverySolutions, setDeliverySolutions] = useState<DeliverySelection[]>([]);
    const [selectedSolutions, setSelectedSolutions] = useState<DiscoverySelectedSolution[]>([]);
    const [recommendations, setRecommendations] = useState<SolutionRecommendations[]>([]);
    const [isGenerating, setIsGenerating] = useState(false);
    const [generationError, setGenerationError] = useState<string | null>(null);
    const [workflowStatus, setWorkflowStatus] = useState<Status>("selected");
    const [isExportingPdf, setIsExportingPdf] = useState(false);
    const [isExportingDocx, setIsExportingDocx] = useState(false);
    const [exportError, setExportError] = useState<string | null>(null);

    useEffect(() => {
        const saved = localStorage.getItem("ipm_delivery_solutions");
        if (saved) {
            try {
                setDeliverySolutions(JSON.parse(saved));
            } catch {
                setDeliverySolutions([]);
            }
        }

        const savedSelected = localStorage.getItem("ipm_selected_solutions");
        if (savedSelected) {
            try {
                setSelectedSolutions(JSON.parse(savedSelected));
            } catch {
                setSelectedSolutions([]);
            }
        }

        const canvas = document.getElementById("bg-canvas") as HTMLCanvasElement | null;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        ctx.fillStyle = "rgba(180, 120, 60, 0.045)";
        ctx.font = "11px DM Mono, monospace";
        const chars = "0123456789ABCDEF";
        for (let x = 0; x < canvas.width; x += 28) {
            for (let y = 0; y < canvas.height; y += 20) {
                ctx.fillText(chars[Math.floor(Math.random() * chars.length)], x + Math.random() * 8, y + Math.random() * 6);
            }
        }
    }, []);

    useEffect(() => {
        if (!ipmId) return;
        getNeed(ipmId)
            .then((need) => {
                if (need.status === "delivery") {
                    setGateCleared(true);
                    setWorkflowStatus("delivery");
                } else if (need.status === "selected" || need.status === "in_qualification") {
                    setWorkflowStatus("selected");
                }
            })
            .catch(() => {
                setWorkflowStatus("selected");
            });
    }, [ipmId]);

    useEffect(() => {
        if (!ipmId || deliverySolutions.length === 0) {
            setRecommendations([]);
            return;
        }

        const selectedById = new Map(selectedSolutions.map((solution) => [solution.id, solution]));
        const payload: RecommendationSolutionPayload[] = deliverySolutions.map((solution) => {
            const selectedContext = selectedById.get(solution.id);
            return {
                id: solution.id,
                name: solution.name,
                relevance: solution.relevance,
                overall: solution.overall,
                description: selectedContext?.description || "",
                source: selectedContext?.source || "",
                features: selectedContext?.features || [],
                business_impact: selectedContext?.business_impact || "",
                maturity_level: selectedContext?.maturity_level || "",
                gap_analysis: selectedContext?.gap_analysis || null,
                evaluation_scores: selectedContext?.gap_analysis?.evaluation_scores || null,
            };
        });

        let cancelled = false;

        const run = async () => {
            setIsGenerating(true);
            setGenerationError(null);
            try {
                const result = await getRecommendations(ipmId, { selected_solutions: payload });
                if (!cancelled) {
                    setRecommendations(result.recommendations || []);
                }
            } catch (error) {
                if (!cancelled) {
                    setGenerationError(error instanceof Error ? error.message : "Unable to generate recommendations.");
                    setRecommendations([]);
                }
            } finally {
                if (!cancelled) {
                    setIsGenerating(false);
                }
            }
        };

        run();

        return () => {
            cancelled = true;
        };
    }, [ipmId, deliverySolutions, selectedSolutions]);

    const triggerDownload = (blob: Blob, filename: string) => {
        const href = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = href;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        URL.revokeObjectURL(href);
    };

    const buildExportPayload = (): ExportReportRequest => ({
        recommendations,
        delivery_solutions: deliverySolutions,
    });

    const handlePdfExport = async () => {
        if (!ipmId) return;
        setExportError(null);
        setIsExportingPdf(true);
        try {
            const blob = await exportRecommendationsPdf(ipmId, buildExportPayload());
            triggerDownload(blob, `${ipmId.toLowerCase()}-recommendations.pdf`);
        } catch (error) {
            setExportError(error instanceof Error ? error.message : "Failed to export PDF report.");
        } finally {
            setIsExportingPdf(false);
        }
    };

    const handleDocxExport = async () => {
        if (!ipmId) return;
        setExportError(null);
        setIsExportingDocx(true);
        try {
            const blob = await exportRecommendationsDocx(ipmId, buildExportPayload());
            triggerDownload(blob, `${ipmId.toLowerCase()}-recommendations.docx`);
        } catch (error) {
            setExportError(error instanceof Error ? error.message : "Failed to export DOCX proposal.");
        } finally {
            setIsExportingDocx(false);
        }
    };

    return (
        <div className="app-shell">
            <canvas id="bg-canvas" style={{ position: "fixed", top: 0, left: 0, zIndex: -1 }} />
            <WorkflowBar currentStep="recos" status={workflowStatus} ipmId={ipmId} isInteractive={false} />

            <div className="app-content">
                <div className="glow-divider" />
                <div className="stub-page">
                    <div className="stub-page-header">
                        <h1 className="stub-page-title">{gateCleared ? "Recommendations & Export" : "Recommendations"}</h1>
                    </div>

                    {gateCleared && (
                        <>
                            <div className="stub-banner">
                                SG-4 validated. Generate your final delivery documents.
                            </div>

                            {exportError && (
                                <div style={{ padding: 14, borderRadius: 12, border: "1px solid rgba(220, 50, 50, 0.35)", background: "rgba(255, 88, 88, 0.08)", color: "var(--destructive)" }}>
                                    {exportError}
                                </div>
                            )}

                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                                <div style={{
                                    padding: "24px",
                                    background: "var(--bg-card)",
                                    border: "1px solid var(--border-default)",
                                    borderRadius: 12,
                                    textAlign: "center",
                                    opacity: 1,
                                    transition: "opacity 0.3s",
                                }}>
                                    <div style={{ fontWeight: 600, fontSize: 16 }}>PDF Report</div>
                                    <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>Comprehensive recommendation with solution details and ROI.</div>
                                    <button
                                        className="action-btn"
                                        style={{ marginTop: 20, width: "100%", cursor: "pointer" }}
                                        onClick={handlePdfExport}
                                        disabled={isExportingPdf || recommendations.length === 0}
                                    >
                                        {isExportingPdf ? "Generating PDF..." : "Download PDF"}
                                    </button>
                                </div>
                                <div style={{
                                    padding: "24px",
                                    background: "var(--bg-card)",
                                    border: "1px solid var(--border-default)",
                                    borderRadius: 12,
                                    textAlign: "center",
                                    opacity: 1,
                                    transition: "opacity 0.3s",
                                }}>
                                    <div style={{ fontWeight: 600, fontSize: 16 }}>DOCX Proposal</div>
                                    <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>Editable Word document for project launch and formalization.</div>
                                    <button
                                        className="action-btn"
                                        style={{ marginTop: 20, width: "100%", cursor: "pointer" }}
                                        onClick={handleDocxExport}
                                        disabled={isExportingDocx || recommendations.length === 0}
                                    >
                                        {isExportingDocx ? "Generating DOCX..." : "Download DOCX"}
                                    </button>
                                </div>
                            </div>
                        </>
                    )}

                    {isGenerating && (
                        <div style={{ padding: 14, borderRadius: 12, border: "1px solid var(--border-default)", background: "var(--bg-card)", color: "var(--text-secondary)" }}>
                            Generating technical, organizational, and KPI recommendations with AI for each selected solution...
                        </div>
                    )}

                    {generationError && (
                        <div style={{ padding: 14, borderRadius: 12, border: "1px solid rgba(220, 50, 50, 0.35)", background: "rgba(255, 88, 88, 0.08)", color: "var(--destructive)" }}>
                            {generationError}
                        </div>
                    )}

                    <div style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 12 }}>
                        <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)" }}>Delivery selection</div>
                        {deliverySolutions.length === 0 ? (
                            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>No delivery solutions selected yet. Return to Selection to choose what moves forward.</div>
                        ) : (
                            <div style={{ display: "grid", gap: 10 }}>
                                {deliverySolutions.map((solution) => (
                                    <div key={solution.id} style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", padding: "10px 12px", borderRadius: 12, background: "var(--bg-inner)", border: "1px solid var(--border-default)" }}>
                                        <div>
                                            <div style={{ fontSize: 13, fontWeight: 600 }}>{solution.name}</div>
                                            <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Overall {solution.overall.toFixed(2)} · Relevance {solution.relevance}%</div>
                                        </div>
                                        <span className="tag-chip tag-green">Selected</span>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, flexWrap: "wrap" }}>
                            {!gateCleared ? (
                                <button className="action-btn primary" style={{ minWidth: 180, fontWeight: 700 }} onClick={() => setShowGate(true)}>
                                    Validate SG-4
                                </button>
                            ) : (
                                <button className="action-btn" onClick={() => window.location.href = "/dashboard"}>
                                    Final Archive
                                </button>
                            )}
                        </div>
                    </div>

                    {recommendations.length > 0 && (
                        <div style={{ display: "grid", gap: 16 }}>
                            {recommendations.map((rec) => (
                                <div key={rec.solution_id} style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 16 }}>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                                        <div style={{ display: "grid", gap: 4 }}>
                                            <div style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 700 }}>
                                                Solution recommendation bundle
                                            </div>
                                            <div style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}>{rec.solution_name}</div>
                                        </div>
                                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                                            {rec.mode === "PREREQUIS" && (
                                                <span className="tag-chip tag-amber" title="Gap fit ≤4/10">
                                                    PREREQUIS mode
                                                </span>
                                            )}
                                            <span className="tag-chip tag-blue">AI generated</span>
                                        </div>
                                    </div>

                                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 14 }}>
                                        <div style={{ border: "1px solid var(--border-default)", borderRadius: 14, background: "var(--bg-inner)", padding: 14, display: "grid", gap: 10 }}>
                                            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                                                Technical recommendations
                                            </div>
                                            <div style={{ display: "grid", gap: 8 }}>
                                                {rec.technical_recommendations.map((item, index) => (
                                                    <div key={`${rec.solution_id}-tech-${index}`} style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.55 }}>
                                                        {index + 1}. {item}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        <div style={{ border: "1px solid var(--border-default)", borderRadius: 14, background: "var(--bg-inner)", padding: 14, display: "grid", gap: 10 }}>
                                            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                                                Organizational recommendations
                                            </div>
                                            <div style={{ display: "grid", gap: 8 }}>
                                                {rec.organizational_recommendations.map((item, index) => (
                                                    <div key={`${rec.solution_id}-org-${index}`} style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.55 }}>
                                                        <div style={{ fontWeight: 700 }}>{index + 1}. {item.role}</div>
                                                        <div style={{ color: "var(--text-secondary)", marginTop: 4 }}>{item.action}</div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>

                                    <div style={{ border: "1px solid var(--border-default)", borderRadius: 14, background: "var(--bg-inner)", padding: 14, display: "grid", gap: 10 }}>
                                        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                                            Target KPIs and measurable criteria
                                        </div>
                                        <div style={{ display: "grid", gap: 10 }}>
                                            {rec.kpis.map((kpi, index) => (
                                                <div key={`${rec.solution_id}-kpi-${index}`} style={{ border: "1px solid var(--border-default)", borderRadius: 12, background: "var(--bg-card)", padding: "10px 12px", display: "grid", gap: 4 }}>
                                                    <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{kpi.name}</div>
                                                    <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Target: {kpi.target}</div>
                                                    <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Measure: {kpi.measurement_criteria}</div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {showGate && (
                <Sg4ValidationPanel
                    open={showGate}
                    deliverySolutions={deliverySolutions}
                    hasRecommendations={recommendations.length > 0}
                    onGo={async () => {
                        if (ipmId && deliverySolutions.length > 0) {
                            await updateNeedStatus(ipmId, { status: "delivery" });
                        }
                        setGateCleared(true);
                        setWorkflowStatus("delivery");
                        setShowGate(false);
                    }}
                    onRework={() => setShowGate(false)}
                    onAbandon={() => {
                        window.location.href = "/dashboard";
                    }}
                    onClose={() => setShowGate(false)}
                />
            )}
        </div>
    );
}

export default function RecosPage() {
    return (
        <Suspense fallback={<div className="app-shell" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>Loading...</div>}>
            <RecosPageContent />
        </Suspense>
    );
}
