/**
 * PitchPanel — Center panel: pitch textarea + horizon selector + primary submit CTA.
 */

"use client";

import React from "react";
import { HorizonSelector } from "@/components/sourcing/HorizonSelector";
import type { Horizon } from "@/lib/types";

interface PitchPanelProps {
    pitch: string;
    onPitchChange: (v: string) => void;
    horizon: Horizon | null;
    onHorizonChange: (h: Horizon) => void;
    canSubmit: boolean;
    isSubmitting: boolean;
    onSubmit: () => void;
}

export function PitchPanel({
    pitch,
    onPitchChange,
    horizon,
    onHorizonChange,
    canSubmit,
    isSubmitting,
    onSubmit,
}: PitchPanelProps) {
    return (
        <div className="panel" style={{ borderRight: "1px solid rgba(255,255,255,0.05)" }}>
            {/* Step pill */}
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span className="step-pill">
                    <span style={{ fontSize: 10 }}>●</span>
                    Step 1
                </span>
                <span className="step-subtitle">Describe your need</span>
            </div>

            {/* Pitch textarea */}
            <div className="pitch-area">
                <textarea
                    id="pitch-input"
                    value={pitch}
                    onChange={(e) => onPitchChange(e.target.value)}
                    placeholder="Describe your business problem, context, and expected impact…"
                    rows={2}
                />
            </div>

            {/* Horizon */}
            <HorizonSelector value={horizon} onChange={onHorizonChange} />

            {/* Character count */}
            {pitch.length > 0 && pitch.length < 20 && (
                <div style={{ fontSize: 11, color: "var(--text-muted)", textAlign: "center" }}>
                    {20 - pitch.length} more character{20 - pitch.length > 1 ? "s" : ""} required
                </div>
            )}

            {/* Submit */}
            <button
                id="submit-need"
                type="button"
                className={`submit-btn${canSubmit ? " ready" : ""}`}
                disabled={!canSubmit}
                onClick={onSubmit}
            >
                {isSubmitting ? (
                    <>
                        <span className="submit-spinner" />
                        Submitting…
                    </>
                ) : (
                    <>▸ Submit Business Need</>
                )}
            </button>
        </div>
    );
}
