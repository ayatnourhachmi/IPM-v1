"use client";

/**
 * Sg2ValidationPanel — Right-side slide panel for SG-2 gate decision.
 * Mirrors Sg1ValidationPanel layout and animation exactly.
 * Shows selected solutions from localStorage, plus a manual validation checkbox.
 */

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface Solution {
    id: string;
    name: string;
    relevance: number;
}

interface Sg2ValidationPanelProps {
    open: boolean;
    onGo: () => void;
    onRework: () => void;
    onAbandon: () => void;
}

const CheckIcon = ({ met }: { met: boolean }) => (
    <div style={{
        width: 18,
        height: 18,
        borderRadius: 4,
        border: met ? "none" : "1px solid var(--wf-muted-fg)",
        background: met ? "var(--wf-success-bg)" : "transparent",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        marginTop: 1,
        opacity: met ? 1 : 0.35,
        transition: "all 0.2s",
    }}>
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
            <path d="M2 5L4 7L8 3" stroke={met ? "var(--wf-btn-on-color)" : "var(--wf-qualification)"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    </div>
);

export function Sg2ValidationPanel({ open, onGo, onRework, onAbandon }: Sg2ValidationPanelProps) {
    const [solutions, setSolutions] = useState<Solution[]>([]);
    const [reviewed, setReviewed] = useState(false);
    const [mode, setMode] = useState<"idle" | "rework" | "stop">("idle");
    const [noteText, setNoteText] = useState("");

    useEffect(() => {
        if (open) {
            const saved = localStorage.getItem("ipm_selected_solutions");
            if (saved) {
                try { setSolutions(JSON.parse(saved)); } catch { /* malformed — ignore */ }
            }
            setReviewed(false);
            setMode("idle");
            setNoteText("");
        }
    }, [open]);

    const hasSolutions = solutions.length > 0;
    const allMet = hasSolutions && reviewed;

    const handleConfirm = () => {
        if (!noteText.trim()) return;
        if (mode === "rework") onRework();
        if (mode === "stop") onAbandon();
        setMode("idle");
        setNoteText("");
    };

    const handleCancel = () => {
        setMode("idle");
        setNoteText("");
    };

    return (
        <AnimatePresence>
            {open && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        style={{
                            position: "fixed",
                            inset: 0,
                            background: "var(--wf-overlay-bg)",
                            backdropFilter: "blur(4px)",
                            zIndex: 40,
                        }}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onRework}
                    />

                    {/* Panel */}
                    <motion.div
                        style={{
                            position: "fixed",
                            right: 0,
                            top: 0,
                            height: "100%",
                            width: "100%",
                            maxWidth: 480,
                            background: "var(--wf-card)",
                            borderLeft: "1px solid var(--wf-border)",
                            zIndex: 50,
                            display: "flex",
                            flexDirection: "column",
                        }}
                        initial={{ x: "100%" }}
                        animate={{ x: 0 }}
                        exit={{ x: "100%" }}
                        transition={{ ease: [0.16, 1, 0.3, 1], duration: 0.5 }}
                    >
                        {/* Header */}
                        <div style={{ padding: 24, borderBottom: "1px solid var(--wf-border)" }}>
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                                <span style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: 10,
                                    color: "var(--wf-muted-fg)",
                                    letterSpacing: "0.08em",
                                    textTransform: "uppercase",
                                }}>
                                    SG-2
                                </span>
                                <button
                                    onClick={onRework}
                                    style={{
                                        background: "none",
                                        border: "none",
                                        color: "var(--wf-muted-fg)",
                                        cursor: "pointer",
                                        fontSize: 14,
                                        padding: 4,
                                        lineHeight: 1,
                                    }}
                                >
                                    ✕
                                </button>
                            </div>
                            <h2 style={{ fontSize: 18, fontWeight: 600, color: "var(--wf-fg)", margin: 0 }}>
                                Validation of Selected Solutions
                            </h2>
                            <p style={{ fontSize: 13, color: "var(--wf-muted-fg)", marginTop: 4, marginBottom: 0, lineHeight: 1.5 }}>
                                Review the solutions selected during Discovery before proceeding to Qualification.
                            </p>
                        </div>

                        {/* Scrollable body */}
                        <div style={{ flex: 1, overflowY: "auto", padding: 24, display: "flex", flexDirection: "column", gap: 24 }}>

                            {/* SELECTED SOLUTIONS */}
                            <div>
                                <span style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: 10,
                                    letterSpacing: "0.08em",
                                    textTransform: "uppercase",
                                    fontWeight: 500,
                                    color: "var(--wf-muted-fg)",
                                    display: "block",
                                    marginBottom: 14,
                                }}>
                                    Selected Solutions
                                </span>
                                {solutions.length === 0 ? (
                                    <div style={{
                                        background: "var(--wf-muted)",
                                        border: "1px solid var(--wf-border)",
                                        borderRadius: 8,
                                        padding: 16,
                                        fontSize: 13,
                                        color: "var(--wf-muted-fg)",
                                        fontStyle: "italic",
                                    }}>
                                        No solutions confirmed yet
                                    </div>
                                ) : (
                                    <div style={{
                                        background: "var(--wf-muted)",
                                        border: "1px solid var(--wf-border)",
                                        borderRadius: 8,
                                        overflow: "hidden",
                                    }}>
                                        {solutions.map((s, i) => (
                                            <motion.div
                                                key={s.id}
                                                style={{
                                                    display: "flex",
                                                    alignItems: "center",
                                                    justifyContent: "space-between",
                                                    padding: "10px 16px",
                                                    borderBottom: i < solutions.length - 1 ? "1px solid var(--wf-border)" : "none",
                                                    gap: 12,
                                                }}
                                                initial={{ opacity: 0, x: 20 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: 0.15 + i * 0.06 }}
                                            >
                                                <span style={{ fontSize: 13, fontWeight: 500, color: "var(--wf-fg)" }}>{s.name}</span>
                                                <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
                                                    <span style={{
                                                        fontFamily: "var(--font-mono)",
                                                        fontSize: 11,
                                                        color: s.relevance >= 80
                                                            ? "var(--wf-qualification)"
                                                            : s.relevance >= 65
                                                            ? "var(--wf-sourcing)"
                                                            : "var(--wf-muted-fg)",
                                                    }}>
                                                        {s.relevance}%
                                                    </span>
                                                    <span style={{
                                                        fontSize: 10,
                                                        fontFamily: "var(--font-mono)",
                                                        color: "var(--wf-muted-fg)",
                                                        background: "var(--wf-badge-bg)",
                                                        border: "1px solid var(--wf-badge-border)",
                                                        padding: "2px 8px",
                                                        borderRadius: 4,
                                                        letterSpacing: "0.04em",
                                                    }}>
                                                        DXC Catalog
                                                    </span>
                                                </div>
                                            </motion.div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* CHECKLIST */}
                            <div>
                                <span style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: 10,
                                    letterSpacing: "0.08em",
                                    textTransform: "uppercase",
                                    fontWeight: 500,
                                    color: "var(--wf-muted-fg)",
                                    display: "block",
                                    marginBottom: 14,
                                }}>
                                    Checklist
                                </span>
                                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>

                                    {/* Auto-checked: at least one solution */}
                                    <motion.div
                                        style={{
                                            display: "flex",
                                            alignItems: "flex-start",
                                            gap: 12,
                                            padding: 12,
                                            borderRadius: 6,
                                            background: "var(--wf-muted)",
                                            border: `1px solid ${hasSolutions ? "var(--wf-success-border)" : "var(--wf-border)"}`,
                                        }}
                                        initial={{ opacity: 0, x: 20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: 0.3 }}
                                    >
                                        <CheckIcon met={hasSolutions} />
                                        <span style={{ fontSize: 13, color: "var(--wf-fg)", lineHeight: 1.5, opacity: hasSolutions ? 1 : 0.6 }}>
                                            At least one solution selected
                                        </span>
                                    </motion.div>

                                    {/* Manual checkbox: reviewed */}
                                    <motion.div
                                        style={{
                                            display: "flex",
                                            alignItems: "flex-start",
                                            gap: 12,
                                            padding: 12,
                                            borderRadius: 6,
                                            background: "var(--wf-muted)",
                                            border: `1px solid ${reviewed ? "var(--wf-success-border)" : "var(--wf-border)"}`,
                                            cursor: "pointer",
                                            userSelect: "none",
                                        }}
                                        onClick={() => setReviewed(r => !r)}
                                        initial={{ opacity: 0, x: 20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: 0.38 }}
                                    >
                                        <CheckIcon met={reviewed} />
                                        <span style={{ fontSize: 13, color: "var(--wf-fg)", lineHeight: 1.5, opacity: reviewed ? 1 : 0.6 }}>
                                            Solutions reviewed and validated
                                        </span>
                                    </motion.div>
                                </div>
                            </div>

                            {/* Note textarea — REWORK or STOP mode */}
                            {mode !== "idle" && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: "auto" }}
                                >
                                    <span style={{
                                        fontFamily: "var(--font-mono)",
                                        fontSize: 10,
                                        letterSpacing: "0.08em",
                                        textTransform: "uppercase",
                                        fontWeight: 500,
                                        color: "var(--wf-muted-fg)",
                                        display: "block",
                                        marginBottom: 8,
                                    }}>
                                        {mode === "rework" ? "Rework Note (required)" : "Reason for Abandon (required)"}
                                    </span>
                                    <textarea
                                        value={noteText}
                                        onChange={e => setNoteText(e.target.value)}
                                        placeholder={mode === "rework"
                                            ? "Explain what needs to be reworked…"
                                            : "Explain why this IPM is being abandoned…"
                                        }
                                        autoFocus
                                        style={{
                                            width: "100%",
                                            minHeight: 80,
                                            padding: 12,
                                            borderRadius: 6,
                                            border: "1px solid var(--wf-border)",
                                            background: "var(--wf-bg)",
                                            color: "var(--wf-fg)",
                                            fontFamily: "var(--font-sans)",
                                            fontSize: 13,
                                            outline: "none",
                                            resize: "vertical",
                                            boxSizing: "border-box",
                                        }}
                                    />
                                </motion.div>
                            )}
                        </div>

                        {/* Actions */}
                        <div style={{
                            padding: 24,
                            borderTop: "1px solid var(--wf-border)",
                            display: "flex",
                            flexDirection: "column",
                            gap: 8,
                        }}>
                            {mode === "idle" ? (
                                <>
                                    <button
                                        onClick={onGo}
                                        disabled={!allMet}
                                        style={{
                                            width: "100%",
                                            padding: "11px 16px",
                                            borderRadius: 6,
                                            background: !allMet ? "var(--wf-success-bg-disabled)" : "var(--wf-success-bg)",
                                            color: "var(--wf-btn-strong-fg)",
                                            fontWeight: 700,
                                            fontSize: 14,
                                            border: "none",
                                            cursor: !allMet ? "not-allowed" : "pointer",
                                            fontFamily: "var(--font-mono)",
                                            letterSpacing: "0.06em",
                                            transition: "filter 0.15s",
                                        }}
                                        onMouseOver={e => { if (allMet) e.currentTarget.style.filter = "brightness(1.1)"; }}
                                        onMouseOut={e => (e.currentTarget.style.filter = "")}
                                    >
                                        GO
                                    </button>
                                    {!allMet && (
                                        <span style={{
                                            fontSize: 11,
                                            color: "var(--wf-muted-fg)",
                                            textAlign: "center",
                                            lineHeight: 1.4,
                                        }}>
                                            Complete all checklist items to proceed
                                        </span>
                                    )}
                                    <button
                                        onClick={() => setMode("rework")}
                                        style={{
                                            width: "100%",
                                            padding: "11px 16px",
                                            borderRadius: 6,
                                            background: "transparent",
                                            color: "var(--wf-muted-fg)",
                                            fontSize: 14,
                                            border: "1px solid var(--wf-border)",
                                            cursor: "pointer",
                                            fontFamily: "var(--font-mono)",
                                            letterSpacing: "0.06em",
                                            transition: "all 0.15s",
                                        }}
                                        onMouseOver={e => { e.currentTarget.style.color = "var(--wf-fg)"; e.currentTarget.style.borderColor = "var(--wf-muted-fg)"; }}
                                        onMouseOut={e => { e.currentTarget.style.color = "var(--wf-muted-fg)"; e.currentTarget.style.borderColor = "var(--wf-border)"; }}
                                    >
                                        REWORK
                                    </button>
                                    <button
                                        onClick={() => setMode("stop")}
                                        style={{
                                            width: "100%",
                                            padding: "11px 16px",
                                            borderRadius: 6,
                                            background: "transparent",
                                            color: "var(--wf-destructive)",
                                            fontSize: 14,
                                            border: "1px solid rgba(220, 50, 50, 0.35)",
                                            cursor: "pointer",
                                            fontFamily: "var(--font-mono)",
                                            letterSpacing: "0.06em",
                                            transition: "background 0.15s, border-color 0.15s",
                                        }}
                                        onMouseOver={e => {
                                            e.currentTarget.style.background = "var(--wf-stop-hover-bg)";
                                            e.currentTarget.style.borderColor = "var(--wf-destructive)";
                                        }}
                                        onMouseOut={e => {
                                            e.currentTarget.style.background = "transparent";
                                            e.currentTarget.style.borderColor = "rgba(220, 50, 50, 0.35)";
                                        }}
                                    >
                                        STOP / ABANDON
                                    </button>
                                </>
                            ) : (
                                <>
                                    <button
                                        onClick={handleConfirm}
                                        disabled={!noteText.trim()}
                                        style={{
                                            width: "100%",
                                            padding: "11px 16px",
                                            borderRadius: 6,
                                            background: mode === "rework" ? "var(--wf-sourcing)" : "var(--wf-destructive)",
                                            color: "var(--wf-btn-on-color)",
                                            fontWeight: 600,
                                            fontSize: 14,
                                            border: "none",
                                            cursor: noteText.trim() ? "pointer" : "not-allowed",
                                            fontFamily: "var(--font-mono)",
                                            letterSpacing: "0.06em",
                                            opacity: noteText.trim() ? 1 : 0.4,
                                            transition: "opacity 0.15s",
                                        }}
                                    >
                                        Confirm {mode === "rework" ? "Rework" : "Abandon"}
                                    </button>
                                    <button
                                        onClick={handleCancel}
                                        style={{
                                            width: "100%",
                                            padding: "11px 16px",
                                            borderRadius: 6,
                                            background: "transparent",
                                            color: "var(--wf-muted-fg)",
                                            fontSize: 14,
                                            border: "1px solid var(--wf-border)",
                                            cursor: "pointer",
                                            fontFamily: "var(--font-mono)",
                                            letterSpacing: "0.06em",
                                        }}
                                    >
                                        Cancel
                                    </button>
                                </>
                            )}
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
