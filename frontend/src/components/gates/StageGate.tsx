/**
 * StageGate — Reusable modal for SG-1, SG-2, SG-3 decision gates.
 * Shows a checklist summary + GO / REWORK / STOP buttons.
 * REWORK and STOP require a note/reason before confirming.
 */

"use client";

import { useState } from "react";

interface ChecklistItem {
    label: string;
    met: boolean;
}

interface StageGateProps {
    gateId: "SG-1" | "SG-2" | "SG-3" | "SG-4" | "SG-5";
    title: string;
    checklist: ChecklistItem[];
    onGo: () => void;
    onRework: (note: string) => void;
    onStop: (reason: string) => void;
    onClose: () => void;
}

export function StageGate({
    gateId,
    title,
    checklist,
    onGo,
    onRework,
    onStop,
    onClose,
}: StageGateProps) {
    const [mode, setMode] = useState<"idle" | "rework" | "stop">("idle");
    const [note, setNote] = useState("");
    const allMet = checklist.every((c) => c.met);

    const handleConfirm = () => {
        if (!note.trim()) return;
        if (mode === "rework") onRework(note.trim());
        if (mode === "stop") onStop(note.trim());
    };

    return (
        <div className="gate-overlay" onClick={onClose}>
            <div className="gate-modal" onClick={(e) => e.stopPropagation()}>
                {/* Title */}
                <div className="gate-title">
                    <div className="gate-title-diamond" />
                    {gateId} — {title}
                </div>

                {/* Checklist */}
                <div className="gate-checklist">
                    {checklist.map((item, i) => (
                        <div key={i} className="gate-check-item">
                            <span className="gate-check-icon">
                                {item.met ? "✓" : "○"}
                            </span>
                            {item.label}
                        </div>
                    ))}
                </div>

                {/* Note field (shown for REWORK or STOP) */}
                {mode !== "idle" && (
                    <div>
                        <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 6 }}>
                            {mode === "rework" ? "Rework note (required):" : "Reason for stopping (required):"}
                        </div>
                        <textarea
                            className="gate-note-field"
                            value={note}
                            onChange={(e) => setNote(e.target.value)}
                            placeholder={mode === "rework" ? "Explain what needs to be reworked…" : "Explain why this IPM is being abandoned…"}
                            autoFocus
                        />
                    </div>
                )}

                {/* Action buttons */}
                <div className="gate-actions">
                    {mode === "idle" ? (
                        <>
                            <button
                                className="gate-btn go"
                                onClick={onGo}
                                disabled={!allMet}
                                style={{ opacity: allMet ? 1 : 0.4, cursor: allMet ? "pointer" : "not-allowed" }}
                            >
                                ✅ GO
                            </button>
                            {!allMet && (
                                <p style={{ fontSize: 11, color: "var(--text-muted)", textAlign: "center", margin: "2px 0 0" }}>
                                    Complete all checklist items to proceed
                                </p>
                            )}
                            <button className="gate-btn rework" onClick={() => setMode("rework")}>
                                🔄 Rework
                            </button>
                            <button className="gate-btn stop" onClick={() => setMode("stop")}>
                                ⛔ Stop
                            </button>
                        </>
                    ) : (
                        <>
                            <button
                                className={`gate-btn ${mode === "rework" ? "rework" : "stop"}`}
                                onClick={handleConfirm}
                                disabled={!note.trim()}
                                style={{ opacity: note.trim() ? 1 : 0.5 }}
                            >
                                Confirm {mode === "rework" ? "Rework" : "Abandon"}
                            </button>
                            <button
                                className="gate-btn rework"
                                onClick={() => { setMode("idle"); setNote(""); }}
                            >
                                Cancel
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
