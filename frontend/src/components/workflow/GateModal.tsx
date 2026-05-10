/**
 * GateModal — Right-side slide panel for gate decisions (GO / REWORK / STOP).
 * Extended from reference: adds note/reason textarea.
 * REWORK and STOP buttons are disabled until text is non-empty.
 * Uses framer-motion spring slide + AnimatePresence.
 * Adapted from stageflow-compass reference.
 */

"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface GateData {
    id: string;
    title: string;
    subtitle: string;
    checklist: string[];
    color: "blue" | "emerald" | "orange";
}

interface GateModalProps {
    isOpen: boolean;
    onClose: () => void;
    gate: GateData;
    onGo: () => void;
    onRework: (note: string) => void;
    onStop: (reason: string) => void;
    /** Optional content rendered above the checklist (e.g., SG-2 solution recap). */
    headerContent?: React.ReactNode;
}

export default function GateModal({ isOpen, onClose, gate, onGo, onRework, onStop, headerContent }: GateModalProps) {
    const [mode, setMode] = useState<"idle" | "rework" | "stop">("idle");
    const [noteText, setNoteText] = useState("");
    const isCommittedRequest = mode !== "idle";

    const stateDescriptor = isCommittedRequest
        ? {
            label: mode === "rework" ? "Submitted - formal rework request" : "Submitted - formal abandon request",
            detail: "This is submitted. Changes now require confirming a formal request with rationale.",
        }
        : {
            label: "Under review - rework available",
            detail: "You can still make changes: choose Request changes to return this gate for revision.",
        };

    const handleConfirm = () => {
        if (!noteText.trim()) return;
        if (mode === "rework") onRework(noteText.trim());
        if (mode === "stop") onStop(noteText.trim());
        setMode("idle");
        setNoteText("");
    };

    const handleCancel = () => {
        setMode("idle");
        setNoteText("");
    };

    return (
        <AnimatePresence>
            {isOpen && (
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
                        onClick={onClose}
                    />

                    {/* Panel */}
                    <motion.div
                        style={{
                            position: "fixed",
                            right: 0,
                            top: 0,
                            height: "100%",
                            width: "100%",
                            maxWidth: 448,
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
                        <div style={{
                            padding: 24,
                            borderBottom: "1px solid var(--wf-border)",
                        }}>
                            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                                <span style={{
                                    fontFamily: "var(--font-mono)",
                                    fontSize: 10,
                                    color: "var(--wf-muted-fg)",
                                    letterSpacing: "0.08em",
                                    textTransform: "uppercase",
                                }}>
                                    {gate.id}
                                </span>
                                <button
                                    onClick={onClose}
                                    style={{
                                        background: "none",
                                        border: "none",
                                        color: "var(--wf-muted-fg)",
                                        cursor: "pointer",
                                        fontSize: 14,
                                        padding: 4,
                                    }}
                                >
                                    ✕
                                </button>
                            </div>
                            <h2 style={{ fontSize: 18, fontWeight: 600, color: "var(--wf-fg)" }}>{gate.title}</h2>
                            <p style={{ fontSize: 14, color: "var(--wf-muted-fg)", marginTop: 4 }}>{gate.subtitle}</p>
                            <div style={{
                                marginTop: 10,
                                padding: "8px 10px",
                                borderRadius: 6,
                                border: `1px solid ${isCommittedRequest ? "var(--wf-border)" : "var(--wf-badge-border)"}`,
                                background: isCommittedRequest ? "var(--wf-muted)" : "var(--wf-badge-bg)",
                            }}>
                                <p style={{
                                    margin: 0,
                                    fontFamily: "var(--font-mono)",
                                    fontSize: 10,
                                    letterSpacing: "0.05em",
                                    textTransform: "uppercase",
                                    color: "var(--wf-fg)",
                                }}>
                                    {stateDescriptor.label}
                                </p>
                                <p style={{
                                    margin: "4px 0 0",
                                    fontSize: 12,
                                    lineHeight: 1.45,
                                    color: "var(--wf-muted-fg)",
                                }}>
                                    {stateDescriptor.detail}
                                </p>
                            </div>
                        </div>

                        {/* Checklist */}
                        <div style={{ flex: 1, padding: 24, overflowY: "auto" }}>
                            {/* Optional header content (e.g., solution recap) */}
                            {headerContent && (
                                <div style={{ marginBottom: 20 }}>
                                    {headerContent}
                                </div>
                            )}

                            <span style={{
                                fontFamily: "var(--font-mono)",
                                fontSize: 10,
                                letterSpacing: "0.08em",
                                textTransform: "uppercase",
                                fontWeight: 500,
                                color: "var(--wf-muted-fg)",
                                display: "block",
                                marginBottom: 16,
                            }}>
                                Checklist
                            </span>
                            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                                {gate.checklist.map((item, i) => (
                                    <motion.div
                                        key={i}
                                        style={{
                                            display: "flex",
                                            alignItems: "flex-start",
                                            gap: 12,
                                            padding: 12,
                                            borderRadius: 6,
                                            background: "var(--wf-muted)",
                                            border: "1px solid var(--wf-border)",
                                        }}
                                        initial={{ opacity: 0, x: 20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: 0.3 + i * 0.08 }}
                                    >
                                        <div style={{
                                            width: 16,
                                            height: 16,
                                            marginTop: 2,
                                            borderRadius: 3,
                                            border: "1px solid var(--wf-muted-fg)",
                                            display: "flex",
                                            alignItems: "center",
                                            justifyContent: "center",
                                            flexShrink: 0,
                                            opacity: 0.4,
                                        }}>
                                            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                                                <path d="M2 5L4 7L8 3" stroke="var(--wf-qualification)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                        </div>
                                        <span style={{ fontSize: 14, color: "var(--wf-fg)", opacity: 0.8 }}>{item}</span>
                                    </motion.div>
                                ))}
                            </div>

                            {/* Note textarea — shown for REWORK or STOP */}
                            {mode !== "idle" && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: "auto" }}
                                    style={{ marginTop: 20 }}
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
                                        {mode === "rework" ? "Change Request Note (required)" : "Reason for Abandon (required)"}
                                    </span>
                                    <textarea
                                        value={noteText}
                                        onChange={(e) => setNoteText(e.target.value)}
                                        placeholder={mode === "rework" ? "Explain what should change and why…" : "Explain why this IPM is being abandoned…"}
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
                                        style={{
                                            width: "100%",
                                            padding: "10px 16px",
                                            borderRadius: 6,
                                            background: "var(--wf-qualification)",
                                            color: "var(--wf-btn-strong-fg)",
                                            fontWeight: 700,
                                            fontSize: 14,
                                            border: "none",
                                            cursor: "pointer",
                                            fontFamily: "var(--font-mono)",
                                            transition: "filter 0.15s",
                                        }}
                                        onMouseOver={(e) => (e.currentTarget.style.filter = "brightness(1.1)")}
                                        onMouseOut={(e) => (e.currentTarget.style.filter = "")}
                                    >
                                        GO
                                    </button>
                                    <button
                                        onClick={() => setMode("rework")}
                                        style={{
                                            width: "100%",
                                            padding: "10px 16px",
                                            borderRadius: 6,
                                            background: "transparent",
                                            color: "var(--wf-muted-fg)",
                                            fontSize: 14,
                                            border: "1px solid var(--wf-border)",
                                            cursor: "pointer",
                                            fontFamily: "var(--font-mono)",
                                            transition: "all 0.15s",
                                        }}
                                        onMouseOver={(e) => { e.currentTarget.style.color = "var(--wf-fg)"; e.currentTarget.style.borderColor = "var(--wf-muted-fg)"; }}
                                        onMouseOut={(e) => { e.currentTarget.style.color = "var(--wf-muted-fg)"; e.currentTarget.style.borderColor = "var(--wf-border)"; }}
                                    >
                                        REQUEST CHANGES
                                    </button>
                                    <button
                                        onClick={() => setMode("stop")}
                                        style={{
                                            width: "100%",
                                            padding: "10px 16px",
                                            borderRadius: 6,
                                            background: "transparent",
                                            color: "var(--wf-destructive)",
                                            fontSize: 14,
                                            border: "none",
                                            cursor: "pointer",
                                            fontFamily: "var(--font-mono)",
                                            transition: "background 0.15s",
                                        }}
                                        onMouseOver={(e) => (e.currentTarget.style.background = "var(--wf-stop-hover-bg)")}
                                        onMouseOut={(e) => (e.currentTarget.style.background = "transparent")}
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
                                            padding: "10px 16px",
                                            borderRadius: 6,
                                            background: mode === "rework" ? "var(--wf-sourcing)" : "var(--wf-destructive)",
                                            color: "var(--wf-btn-on-color)",
                                            fontWeight: 600,
                                            fontSize: 14,
                                            border: "none",
                                            cursor: noteText.trim() ? "pointer" : "not-allowed",
                                            fontFamily: "var(--font-mono)",
                                            opacity: noteText.trim() ? 1 : 0.4,
                                            transition: "opacity 0.15s",
                                        }}
                                    >
                                        Confirm {mode === "rework" ? "Change Request" : "Abandon"}
                                    </button>
                                    <button
                                        onClick={handleCancel}
                                        style={{
                                            width: "100%",
                                            padding: "10px 16px",
                                            borderRadius: 6,
                                            background: "transparent",
                                            color: "var(--wf-muted-fg)",
                                            fontSize: 14,
                                            border: "1px solid var(--wf-border)",
                                            cursor: "pointer",
                                            fontFamily: "var(--font-mono)",
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
