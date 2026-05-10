/**
 * Evaluation / Comparaison page.
 * First qualification step after SG-2 GO.
 * Reads the solutions selected in Discovery and lets the user score them.
 */

"use client";

import React, { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { WorkflowBar } from "@/components/layout/WorkflowBar";

type SelectedSolution = {
    id: string;
    name: string;
    relevance: number;
    description: string | undefined;
    source: string | undefined;
    gap_analysis: GapAnalysisSnapshot | null;
};

type GapAnalysisSnapshot = {
    features_matching: string[];
    features_missing: string[];
    resources_needed: string[];
    fit_score: number;
    evaluation_scores?: {
        maturite: number;
        maturite_justification: string;
        expertise: number;
        expertise_justification: string;
        duree: number;
        duree_justification: string;
        impact: number;
        impact_justification: string;
    };
    solution_name: string;
};

type EvaluationScores = {
    fit: number;
    feasibility: number;
    cost: number;
    innovation: number;
};

type Sg2State = {
    cardStates: Record<string, string>;
    totalSelected: number;
};

type ScoreKey = keyof EvaluationScores;

const CRITERIA: Array<{ key: ScoreKey; label: string; helper: string }> = [
    { key: "fit", label: "Impact", helper: "Business impact on the identified need (1=marginal, 5=transformational)." },
    { key: "feasibility", label: "Maturité", helper: "Solution maturity level (1=PoC, 3=pilot, 5=production-ready)." },
    { key: "cost", label: "Durée", helper: "Delivery speed (5=fast/simple, 1=long/complex)." },
    { key: "innovation", label: "Expertise", helper: "DXC expertise available to deliver (1=low, 5=high)." },
];

function round(value: number) {
    return Math.round(value * 100) / 100;
}

function clampScore(value: number) {
    return Math.min(5, Math.max(1, Math.round(value)));
}

function buildInitialScores(solution: SelectedSolution): EvaluationScores {
    const base = clampScore(solution.relevance / 20);
    return {
        fit: clampScore(base + 1),
        feasibility: clampScore(base),
        cost: clampScore(6 - base),
        innovation: clampScore(base + (solution.relevance >= 80 ? 1 : 0)),
    };
}

function buildScoresFromGap(solution: SelectedSolution): { scores: EvaluationScores; source: "gap-analysis" | "fallback" } {
    const gap = solution.gap_analysis;
    if (!gap) {
        return { scores: buildInitialScores(solution), source: "fallback" };
    }

    const es = gap.evaluation_scores;
    if (
        es &&
        typeof es.impact === "number" &&
        typeof es.maturite === "number" &&
        typeof es.duree === "number" &&
        typeof es.expertise === "number"
    ) {
        return {
            scores: {
                fit: clampScore(es.impact),
                feasibility: clampScore(es.maturite),
                cost: clampScore(es.duree),
                innovation: clampScore(es.expertise),
            },
            source: "gap-analysis",
        };
    }

    const matching = gap.features_matching.length;
    const missing = gap.features_missing.length;
    const resources = gap.resources_needed.length;

    const fit = clampScore(gap.fit_score / 2);
    const feasibility = clampScore(5 - (missing * 0.45) - (resources * 0.35) + (matching * 0.1));
    const cost = clampScore(5 - (resources * 0.4) - (missing * 0.2) + (matching * 0.05));
    const innovation = clampScore((gap.fit_score / 2.5) + Math.min(1, missing * 0.2) + Math.min(0.6, matching * 0.1));

    return {
        scores: { fit, feasibility, cost, innovation },
        source: "gap-analysis",
    };
}

function scoreSolution(scores: EvaluationScores) {
    return round(((scores.fit + scores.feasibility + scores.cost + scores.innovation) / 20) * 100);
}

function normalizeSolutions(value: unknown): SelectedSolution[] {
    if (!Array.isArray(value)) return [];
    return value.flatMap((item) => {
        if (!item || typeof item !== "object") return [];
        const candidate = item as Partial<SelectedSolution>;
        if (typeof candidate.id !== "string" || typeof candidate.name !== "string") return [];
        return [{
            id: candidate.id,
            name: candidate.name,
            relevance: typeof candidate.relevance === "number" ? candidate.relevance : 0,
            description: candidate.description,
            source: candidate.source,
                gap_analysis: candidate.gap_analysis || null,
        } satisfies SelectedSolution];
    });
}

function formatTimestamp(value: string | null) {
    if (!value) return "Not saved yet";
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function EvaluationPageContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const ipmId = searchParams.get("id") || undefined;
    const [solutions, setSolutions] = useState<SelectedSolution[]>([]);
    const [sg2State, setSg2State] = useState<Sg2State>({ cardStates: {}, totalSelected: 0 });
    const [activeId, setActiveId] = useState<string | null>(null);
    const [evaluationUpdatedAt, setEvaluationUpdatedAt] = useState<string | null>(null);

    useEffect(() => {
        let parsedSolutions: SelectedSolution[] = [];
        const savedSolutions = localStorage.getItem("ipm_selected_solutions");
        if (savedSolutions) {
            try {
                parsedSolutions = normalizeSolutions(JSON.parse(savedSolutions));
            } catch {
                parsedSolutions = [];
            }
        }

        const savedSg2State = localStorage.getItem("ipm_sg2_state");
        if (savedSg2State) {
            try {
                setSg2State(JSON.parse(savedSg2State) as Sg2State);
            } catch {
                setSg2State({ cardStates: {}, totalSelected: parsedSolutions.length });
            }
        } else {
            setSg2State({ cardStates: {}, totalSelected: parsedSolutions.length });
        }

        setSolutions(parsedSolutions);
        setActiveId(parsedSolutions[0]?.id || null);

        const savedEvaluation = localStorage.getItem("ipm_evaluation_state");
        if (savedEvaluation) {
            try {
                const parsed = JSON.parse(savedEvaluation) as { updated_at?: string };
                setEvaluationUpdatedAt(parsed.updated_at || null);
            } catch {
                setEvaluationUpdatedAt(null);
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

    const rows = useMemo(() => {
        return solutions
            .map((solution) => {
                const auto = buildScoresFromGap(solution);
                const scores = auto.scores;
                const overall = scoreSolution(scores);
                return {
                    solution,
                    scores,
                    overall,
                    score_source: auto.source,
                };
            })
            .sort((a, b) => b.overall - a.overall);
    }, [solutions]);

    useEffect(() => {
        if (!rows.length) return;
        setActiveId((current) => current && rows.some((row) => row.solution.id === current) ? current : rows[0].solution.id);
    }, [rows]);

    useEffect(() => {
        if (!rows.length) return;
        localStorage.setItem(
            "ipm_evaluation_state",
            JSON.stringify({
                activeId: activeId || rows[0].solution.id,
                rows: rows.map((row) => ({
                    id: row.solution.id,
                    name: row.solution.name,
                    relevance: row.solution.relevance,
                    overall: row.overall,
                    scores: row.scores,
                })),
                updated_at: new Date().toISOString(),
            }),
        );
        setEvaluationUpdatedAt(new Date().toISOString());
    }, [activeId, rows]);

    const activeRow = rows.find((row) => row.solution.id === activeId) || rows[0] || null;
    const averageScore = rows.length ? round(rows.reduce((sum, row) => sum + row.overall, 0) / rows.length) : 0;
    const selectedCount = rows.length;
    const readyForSelection = Boolean(ipmId) && selectedCount > 0;

    const proceedToSelection = () => {
        if (!ipmId || selectedCount === 0) return;
        router.push(`/selection?id=${ipmId}`);
    };

    return (
        <div className="app-shell">
            <canvas id="bg-canvas" style={{ position: "fixed", top: 0, left: 0, zIndex: -1 }} />
            <WorkflowBar currentStep="evaluation" status="in_qualification" ipmId={ipmId} />

            <div className="app-content" style={{ overflowY: "auto" }}>
                <div className="glow-divider" />
                <div style={{ padding: "20px 24px 32px", display: "grid", gap: 20 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap", alignItems: "flex-start" }}>
                        <div style={{ display: "grid", gap: 8, maxWidth: 780 }}>
                            <div style={{ display: "inline-flex", width: "fit-content", padding: "6px 10px", borderRadius: 999, background: "var(--accent-subtle)", color: "var(--accent-light)", fontSize: 11, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                                Evaluation step
                            </div>
                            <h1 style={{ fontSize: 28, lineHeight: 1.1, margin: 0, fontWeight: 600 }}>Evaluate the solutions carried forward from Discovery.</h1>
                            <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>
                                This page is the first step of qualification after SG-2. It loads the solutions selected in Discovery, lets you score them, and then hands off to the Selection step.
                            </div>
                        </div>

                        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                            <button type="button" className="action-btn" onClick={() => router.push(ipmId ? `/discovery?id=${ipmId}` : "/discovery")} disabled={!ipmId}>
                                Back to Discovery
                            </button>
                            <button type="button" className="action-btn primary" onClick={proceedToSelection} disabled={!readyForSelection}>
                                Proceed to Selection step →
                            </button>
                        </div>
                    </div>

                    {!ipmId && (
                        <div style={{ padding: 16, borderRadius: 14, background: "rgba(255, 88, 88, 0.08)", color: "var(--destructive)" }}>
                            Open a saved initiative before starting evaluation.
                        </div>
                    )}

                    {ipmId && !selectedCount && (
                        <div style={{ padding: 16, borderRadius: 14, background: "rgba(255, 184, 77, 0.08)", color: "var(--text-primary)" }}>
                            No selected solutions were found from Discovery. Go back and choose at least one solution to evaluate.
                        </div>
                    )}

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
                        <div style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 8 }}>
                            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 700 }}>Loaded from Discovery</div>
                            <div style={{ fontSize: 28, fontWeight: 700 }}>{selectedCount}</div>
                            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Solutions carried forward from <strong style={{ color: "var(--text-primary)" }}>ipm_selected_solutions</strong>.</div>
                        </div>
                        <div style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 8 }}>
                            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 700 }}>Average evaluation</div>
                            <div style={{ fontSize: 28, fontWeight: 700 }}>{averageScore.toFixed(2)}</div>
                            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Local ranking computed from the four evaluation criteria.</div>
                        </div>
                        <div style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 8 }}>
                            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 700 }}>SG-2 context</div>
                            <div style={{ fontSize: 28, fontWeight: 700 }}>{sg2State.totalSelected}</div>
                            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>Last evaluation refresh: {formatTimestamp(evaluationUpdatedAt)}</div>
                        </div>
                    </div>

                    <div style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 16 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                            <div>
                                <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)" }}>Evaluation matrix</div>
                                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>Scores are AI-generated by the backend from Discovery gap-analysis (Impact, Maturité, Durée, Expertise).</div>
                            </div>
                            {activeRow && (
                                <div style={{ padding: "8px 12px", borderRadius: 999, background: "var(--accent-subtle)", color: "var(--accent-light)", fontSize: 12, fontWeight: 700 }}>
                                    Focus: {activeRow.solution.name}
                                </div>
                            )}
                        </div>

                        <div style={{ overflowX: "auto" }}>
                            <div style={{ minWidth: 860, display: "grid", gap: 1, background: "var(--border-default)", borderRadius: 14, overflow: "hidden" }}>
                                <div style={{ display: "grid", gridTemplateColumns: "240px repeat(4, minmax(140px, 1fr)) 120px", background: "var(--bg-inner)" }}>
                                    <div style={{ padding: "12px 14px", fontSize: 12, fontWeight: 700 }}>Solution</div>
                                    {CRITERIA.map((criterion) => (
                                        <div key={criterion.key} style={{ padding: "12px 14px", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", textAlign: "center" }}>
                                            {criterion.label}
                                        </div>
                                    ))}
                                    <div style={{ padding: "12px 14px", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-muted)", textAlign: "center" }}>Overall</div>
                                </div>

                                {rows.map((row) => {
                                    const isActive = activeRow?.solution.id === row.solution.id;
                                    return (
                                        <div key={row.solution.id} style={{ display: "grid", gridTemplateColumns: "240px repeat(4, minmax(140px, 1fr)) 120px", background: isActive ? "rgba(255, 153, 51, 0.05)" : "var(--bg-card)" }}>
                                            <button
                                                type="button"
                                                onClick={() => setActiveId(row.solution.id)}
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
                                                <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>{row.solution.name}</div>
                                                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>Discovery relevance {row.solution.relevance}%</div>
                                                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                                                    {row.score_source === "gap-analysis" ? "AI scored from gap-analysis" : "Fallback score (gap-analysis missing)"}
                                                </div>
                                            </button>
                                            {CRITERIA.map((criterion) => (
                                                <div key={`${row.solution.id}-${criterion.key}`} style={{ padding: 12, display: "flex", flexDirection: "column", gap: 6 }}>
                                                    <div style={{ width: "100%", borderRadius: 12, border: "1px solid var(--border-input)", background: "var(--bg-input)", color: "var(--text-primary)", padding: 10, fontWeight: 700, textAlign: "center" }}>
                                                        {row.scores[criterion.key]} / 5
                                                    </div>
                                                    <div style={{ fontSize: 11, color: "var(--text-muted)", lineHeight: 1.4 }}>{criterion.helper}</div>
                                                </div>
                                            ))}
                                            <div style={{ padding: 12, display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, color: isActive ? "var(--accent-light)" : "var(--text-primary)" }}>
                                                {row.overall.toFixed(2)}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>

                    {activeRow && (
                        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.4fr) minmax(300px, 0.8fr)", gap: 16, alignItems: "start" }}>
                            <div style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 12 }}>
                                <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)" }}>Why this is in front</div>
                                <div style={{ fontSize: 22, fontWeight: 700 }}>{activeRow.solution.name}</div>
                                <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>
                                    {activeRow.solution.description || "This solution was selected from Discovery and automatically evaluated during qualification."}
                                </div>
                                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                                    <span className="tag-chip tag-gray">Relevance {activeRow.solution.relevance}%</span>
                                    <span className="tag-chip tag-green">Evaluation {activeRow.overall.toFixed(2)}</span>
                                    <span className="tag-chip tag-amber">{selectedCount} candidate{selectedCount > 1 ? "s" : ""}</span>
                                    <span className={`tag-chip ${activeRow.score_source === "gap-analysis" ? "tag-blue" : "tag-orange"}`}>
                                        {activeRow.score_source === "gap-analysis" ? "AI gap-analysis score" : "Fallback score"}
                                    </span>
                                </div>
                                {activeRow.solution.gap_analysis && (
                                    <div style={{ display: "grid", gap: 8, padding: "10px 12px", borderRadius: 12, background: "var(--bg-inner)", border: "1px solid var(--border-default)" }}>
                                        <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                                            Gap fit: <strong style={{ color: "var(--text-primary)" }}>{activeRow.solution.gap_analysis.fit_score}/10</strong>
                                        </div>
                                        <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                                            Matching: {activeRow.solution.gap_analysis.features_matching.length} · Missing: {activeRow.solution.gap_analysis.features_missing.length} · Resources: {activeRow.solution.gap_analysis.resources_needed.length}
                                        </div>
                                    </div>
                                )}
                                <div style={{ display: "grid", gap: 10 }}>
                                    {CRITERIA.map((criterion) => (
                                        <div key={criterion.key} style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", padding: "10px 12px", borderRadius: 12, background: "var(--bg-inner)", border: "1px solid var(--border-default)" }}>
                                            <div>
                                                <div style={{ fontSize: 13, fontWeight: 600 }}>{criterion.label}</div>
                                                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{criterion.helper}</div>
                                            </div>
                                            <div style={{ fontSize: 16, fontWeight: 700 }}>{activeRow.scores[criterion.key]} / 5</div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div style={{ padding: 20, borderRadius: 20, border: "1px solid var(--border-default)", background: "var(--bg-card)", display: "grid", gap: 16 }}>
                                <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--text-muted)" }}>Next step</div>
                                <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>
                                    Once you are satisfied with the ranking, move to the Selection step to choose delivery candidates and run SG-3 there.
                                </div>
                                <button type="button" className="action-btn primary" onClick={proceedToSelection} disabled={!readyForSelection}>
                                    Proceed to Selection step →
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function EvaluationPage() {
    return (
        <Suspense fallback={<div className="app-shell" style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>Loading...</div>}>
            <EvaluationPageContent />
        </Suspense>
    );
}
