/**
 * Selection page (QUALIFICATION PHASE — after SG-3 GO).
 * Reads the auto-evaluated ranking and lets the user choose the final solution(s)
 * to carry into the Delivery phase / Recos.
 */

"use client";

import React, { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { WorkflowBar } from "@/components/layout/WorkflowBar";
import { Sg3ValidationPanel } from "@/components/sourcing/Sg3ValidationPanel";
import { getNeed, updateNeedStatus } from "@/lib/api";
import type { Status } from "@/lib/types";

type GapAnalysisSnapshot = {
    features_matching: string[];
    features_missing: string[];
    resources_needed: string[];
    fit_score: number;
    evaluation_scores?: {
        fit: number;
        feasibility: number;
        cost: number;
        innovation: number;
    };
    solution_name: string;
};

type EvaluationRow = {
    id: string;
    name: string;
    relevance: number;
    overall: number;
    scores: {
        fit: number;
        feasibility: number;
        cost: number;
        innovation: number;
    };
    score_source?: string;
    gap_analysis?: GapAnalysisSnapshot | null;
};

type EvaluationState = {
    activeId?: string | null;
    rows: EvaluationRow[];
    updated_at?: string;
};

type DeliverySelection = {
    id: string;
    name: string;
    relevance: number;
    overall: number;
};

const SCORE_LABELS: Array<{ key: keyof EvaluationRow["scores"]; label: string }> = [
    { key: "fit", label: "Fit" },
    { key: "feasibility", label: "Feasibility" },
    { key: "cost", label: "Cost" },
    { key: "innovation", label: "Innovation" },
];

function round(value: number) {
    return Math.round(value * 100) / 100;
}

function normalizeEvaluationState(value: unknown): EvaluationState {
    if (!value || typeof value !== "object") return { rows: [] };
    const candidate = value as Partial<EvaluationState>;
    const parseEvaluationRow = (row: unknown): EvaluationRow | null => {
        if (!row || typeof row !== "object") return null;
        const item = row as Partial<EvaluationRow>;
        if (typeof item.id !== "string" || typeof item.name !== "string") return null;
        const scores = item.scores;
        if (!scores) return null;

        return {
            id: item.id,
            name: item.name,
            relevance: typeof item.relevance === "number" ? item.relevance : 0,
            overall: typeof item.overall === "number" ? item.overall : 0,
            score_source: typeof item.score_source === "string" ? item.score_source : undefined,
            gap_analysis: item.gap_analysis || null,
            scores: {
                fit: Number(scores.fit) || 1,
                feasibility: Number(scores.feasibility) || 1,
                cost: Number(scores.cost) || 1,
                innovation: Number(scores.innovation) || 1,
            },
        };
    };
    const rows = Array.isArray(candidate.rows)
        ? candidate.rows
            .map(parseEvaluationRow)
            .filter((row): row is EvaluationRow => row !== null)
        : [];

    return {
        activeId: typeof candidate.activeId === "string" ? candidate.activeId : null,
        rows,
        updated_at: typeof candidate.updated_at === "string" ? candidate.updated_at : undefined,
    };
}

function formatTimestamp(value?: string) {
    if (!value) return "Not saved yet";
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function SelectionPageContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const ipmId = searchParams.get("id") || undefined;
    const [evaluationState, setEvaluationState] = useState<EvaluationState>({ rows: [] });
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [savedAt, setSavedAt] = useState<string | undefined>(undefined);
    const [showGate, setShowGate] = useState(false);
    const [transitionError, setTransitionError] = useState<string | null>(null);

    useEffect(() => {
        const saved = localStorage.getItem("ipm_evaluation_state");
        if (saved) {
            try {
                const parsed = normalizeEvaluationState(JSON.parse(saved));
                setEvaluationState(parsed);
                setSavedAt(parsed.updated_at);
                const preselected = parsed.rows.length > 0 ? [parsed.rows[0].id] : [];
                setSelectedIds(new Set(preselected));
            } catch {
                setEvaluationState({ rows: [] });
                setSelectedIds(new Set());
            }
        }
    }, []);

    useEffect(() => {
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

    const rankedRows = useMemo(() => {
        return [...evaluationState.rows].sort((a, b) => b.overall - a.overall);
    }, [evaluationState.rows]);

    const selectedRows = useMemo(() => {
        return rankedRows.filter((row) => selectedIds.has(row.id));
    }, [rankedRows, selectedIds]);

    const toggleSelection = (solutionId: string) => {
        setSelectedIds((previous) => {
            const next = new Set(previous);
            if (next.has(solutionId)) {
                next.delete(solutionId);
            } else {
                next.add(solutionId);
            }
            return next;
        });
    };

    const proceedToRecos = () => {
        if (!ipmId || selectedRows.length === 0) return;
        setTransitionError(null);
        setShowGate(true);
    };

    const advanceNeedToSelected = async (needId: string) => {
        const need = await getNeed(needId);
        let currentStatus = need.status as Status;

        const nextByStatus: Partial<Record<Status, Status>> = {
            draft: "submitted",
            submitted: "in_qualification",
            in_qualification: "selected",
            rework: "submitted",
        };

        let guard = 0;
        while (currentStatus !== "selected" && currentStatus !== "delivery") {
            const next = nextByStatus[currentStatus];
            if (!next) {
                throw new Error(`Cannot continue from status '${currentStatus}'.`);
            }
            const updated = await updateNeedStatus(needId, { status: next });
            currentStatus = updated.status as Status;
            guard += 1;
            if (guard > 6) {
                throw new Error("Too many status transitions while validating SG-3.");
            }
        }
    };

    return (
        <div className="app-shell">
            <canvas id="bg-canvas" style={{ position: "fixed", top: 0, left: 0, zIndex: -1 }} />
            <WorkflowBar currentStep="selection" status="in_qualification" ipmId={ipmId} />

            <div className="app-content" style={{ overflowY: "auto" }}>
                <div className="glow-divider" />
                <div style={{ padding: "20px 24px 32px", display: "grid", gap: 20 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap", alignItems: "flex-start" }}>
                        <div style={{ display: "grid", gap: 8, maxWidth: 780 }}>
                            <div style={{ display: "inline-flex", width: "fit-content", padding: "6px 10px", borderRadius: 999, background: "var(--accent-subtle)", color: "var(--accent-light)", fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                                Selection Step
                            </div>
                            <h1 style={{ fontSize: 28, lineHeight: 1.1, margin: 0, fontWeight: 600 }}>Choose the solution(s) that move to Delivery.</h1>
                            <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>
                                This page reads the auto-evaluated ranking from Evaluation. Pick one or more solutions to carry forward into Recos.
                            </div>
                        </div>
                        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                            <button type="button" className="action-btn" onClick={() => router.push(ipmId ? `/evaluation?id=${ipmId}` : "/evaluation")} disabled={!ipmId}>
                                Back to Evaluation
                            </button>
                            <button type="button" className="action-btn primary" onClick={proceedToRecos} disabled={!ipmId || selectedRows.length === 0}>
                                Validate SG-3 →
                            </button>
                        </div>
                    </div>

                    {!ipmId && (
                        <div style={{ padding: 16, borderRadius: 14, background: "rgba(255, 88, 88, 0.08)", color: "var(--destructive)" }}>
                            Open a saved initiative before choosing delivery solutions.
                        </div>
                    )}

                    {ipmId && rankedRows.length === 0 && (
                        <div style={{ padding: 16, borderRadius: 14, background: "rgba(255, 184, 77, 0.08)", color: "var(--text-primary)" }}>
                            No auto-evaluated ranking found yet. Go back to Evaluation to generate the ranked result.
                        </div>
                    )}

                    {transitionError && (
                        <div style={{ padding: 16, borderRadius: 14, background: "rgba(255, 88, 88, 0.08)", color: "var(--destructive)" }}>
                            {transitionError}
                        </div>
                    )}

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
                        <div style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 8 }}>
                            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 700 }}>Ranked solutions</div>
                            <div style={{ fontSize: 28, fontWeight: 700 }}>{rankedRows.length}</div>
                            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Loaded from <strong style={{ color: "var(--text-primary)" }}>ipm_evaluation_state</strong>.</div>
                        </div>
                        <div style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 8 }}>
                            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 700 }}>Selected for delivery</div>
                            <div style={{ fontSize: 28, fontWeight: 700 }}>{selectedRows.length}</div>
                            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>These are the solutions that will continue to Recos.</div>
                        </div>
                        <div style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 8 }}>
                            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 700 }}>Evaluation timestamp</div>
                            <div style={{ fontSize: 28, fontWeight: 700 }}>{formatTimestamp(savedAt)}</div>
                            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Auto-ranked by the backend gap-analysis scoring.</div>
                        </div>
                    </div>

                    <div style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 16 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                            <div>
                                <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)" }}>Final ranked list</div>
                                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>Select the solution(s) that should move into the delivery phase.</div>
                            </div>
                            <div style={{ padding: "8px 12px", borderRadius: 999, background: "var(--accent-subtle)", color: "var(--accent-light)", fontSize: 12, fontWeight: 700 }}>
                                {selectedRows.length === 0 ? "None selected" : `${selectedRows.length} selected`}
                            </div>
                        </div>

                        <div style={{ overflowX: "auto" }}>
                            <div style={{ minWidth: 920, display: "grid", gap: 1, background: "var(--border-default)", borderRadius: 14, overflow: "hidden" }}>
                                <div style={{ display: "grid", gridTemplateColumns: "56px 240px repeat(4, minmax(120px, 1fr)) 120px", background: "var(--bg-inner)" }}>
                                    <div style={{ padding: "12px 14px", fontSize: 12, fontWeight: 700, textAlign: "center" }}>Pick</div>
                                    <div style={{ padding: "12px 14px", fontSize: 12, fontWeight: 700 }}>Solution</div>
                                    {SCORE_LABELS.map((score) => (
                                        <div key={score.key} style={{ padding: "12px 14px", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", textAlign: "center" }}>
                                            {score.label}
                                        </div>
                                    ))}
                                    <div style={{ padding: "12px 14px", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", textAlign: "center" }}>Overall</div>
                                </div>

                                {rankedRows.map((row, index) => {
                                    const selected = selectedIds.has(row.id);
                                    return (
                                        <div key={row.id} style={{ display: "grid", gridTemplateColumns: "56px 240px repeat(4, minmax(120px, 1fr)) 120px", background: selected ? "rgba(255, 153, 51, 0.06)" : "var(--bg-card)" }}>
                                            <div style={{ padding: 12, display: "flex", alignItems: "center", justifyContent: "center" }}>
                                                <input
                                                    type="checkbox"
                                                    checked={selected}
                                                    onChange={() => toggleSelection(row.id)}
                                                    style={{ width: 18, height: 18, accentColor: "var(--accent)" }}
                                                />
                                            </div>
                                            <button
                                                type="button"
                                                onClick={() => toggleSelection(row.id)}
                                                style={{
                                                    padding: "14px",
                                                    background: "transparent",
                                                    border: "none",
                                                    textAlign: "left",
                                                    cursor: "pointer",
                                                    display: "grid",
                                                    gap: 4,
                                                }}
                                            >
                                                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                                                    <span className="tag-chip tag-gray">#{index + 1}</span>
                                                    <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>{row.name}</div>
                                                </div>
                                                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Discovery relevance {row.relevance}%</div>
                                                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                                                    {row.score_source === "gap-analysis" ? "Auto-scored from gap-analysis" : "Fallback score"}
                                                </div>
                                            </button>
                                            {SCORE_LABELS.map((score) => (
                                                <div key={`${row.id}-${score.key}`} style={{ padding: 12, display: "flex", alignItems: "center", justifyContent: "center" }}>
                                                    <div style={{ width: "100%", borderRadius: 12, border: "1px solid var(--border-input)", background: "var(--bg-input)", color: "var(--text-primary)", padding: 10, fontWeight: 700, textAlign: "center" }}>
                                                        {row.scores[score.key]} / 5
                                                    </div>
                                                </div>
                                            ))}
                                            <div style={{ padding: 12, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, color: selected ? "var(--accent-light)" : "var(--text-primary)" }}>
                                                {row.overall.toFixed(2)}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>

                    {selectedRows.length > 0 && (
                        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.4fr) minmax(300px, 0.8fr)", gap: 16, alignItems: "start" }}>
                            <div style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 12 }}>
                                <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)" }}>Selected for delivery</div>
                                <div style={{ display: "grid", gap: 10 }}>
                                    {selectedRows.map((row) => (
                                        <div key={row.id} style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", padding: "10px 12px", borderRadius: 12, background: "var(--bg-inner)", border: "1px solid var(--border-default)" }}>
                                            <div>
                                                <div style={{ fontSize: 13, fontWeight: 600 }}>{row.name}</div>
                                                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Overall {row.overall.toFixed(2)} · Relevance {row.relevance}%</div>
                                            </div>
                                            <button type="button" className="action-btn" onClick={() => toggleSelection(row.id)}>
                                                Remove
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 16 }}>
                                <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)" }}>Handoff</div>
                                <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>
                                    Confirming SG-3 will persist the chosen solutions to <strong style={{ color: "var(--text-primary)" }}>ipm_delivery_solutions</strong> and open Recos.
                                </div>
                                <button type="button" className="action-btn primary" onClick={proceedToRecos} disabled={selectedRows.length === 0 || !ipmId}>
                                    Validate SG-3 →
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {showGate && (
                <Sg3ValidationPanel
                    open={showGate}
                    selectedSolutions={selectedRows}
                    onGo={async () => {
                        if (!ipmId || selectedRows.length === 0) return;

                        const payload: DeliverySelection[] = selectedRows.map((row) => ({
                            id: row.id,
                            name: row.name,
                            relevance: row.relevance,
                            overall: row.overall,
                        }));

                        localStorage.setItem("ipm_delivery_solutions", JSON.stringify(payload));
                        try {
                            await advanceNeedToSelected(ipmId);
                            setShowGate(false);
                            router.push(`/recos?id=${ipmId}`);
                        } catch (error) {
                            setShowGate(false);
                            setTransitionError(error instanceof Error ? error.message : "Unable to validate SG-3.");
                        }
                    }}
                    onRework={() => setShowGate(false)}
                    onAbandon={() => router.push("/dashboard")}
                    onClose={() => setShowGate(false)}
                />
            )}
        </div>
    );
}

export default function SelectionPage() {
    return (
        <Suspense fallback={<div className="app-shell" style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>Loading...</div>}>
            <SelectionPageContent />
        </Suspense>
    );
}
