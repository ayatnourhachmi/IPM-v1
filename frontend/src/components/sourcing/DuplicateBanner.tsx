/**
 * DuplicateBanner — Warning bar showing potential duplicates after submission.
 */

"use client";

import type { DuplicateMatch } from "@/lib/types";

interface DuplicateBannerProps {
    matches: DuplicateMatch[];
    onDismiss: () => void;
    onViewDuplicate: (id: string) => void;
}

export function DuplicateBanner({ matches, onDismiss, onViewDuplicate }: DuplicateBannerProps) {
    if (matches.length === 0) return null;

    return (
        <div className="dup-banner">
            <span className="dup-icon">◆</span>
            <div className="dup-content">
                <div style={{ fontSize: 11, fontWeight: 500, color: "var(--accent-light)" }}>
                    {matches.length} potential duplicate{matches.length > 1 ? "s" : ""} detected
                </div>
                {matches.map((m) => (
                    <div key={m.id} className="dup-match">
                        <span className="dup-id">{m.id}</span>
                        <span className="dup-text">
                            {m.pitch.length > 80 ? m.pitch.slice(0, 80) + "…" : m.pitch}
                        </span>
                        <span className="dup-score">{Math.round(m.similarity_score * 100)}%</span>
                        <button
                            className="dup-btn"
                            style={{ marginLeft: "auto", whiteSpace: "nowrap" }}
                            onClick={() => onViewDuplicate(m.id)}
                        >
                            View →
                        </button>
                    </div>
                ))}
                <div className="dup-actions">
                    <button className="dup-btn" onClick={onDismiss}>Continue anyway</button>
                </div>
            </div>
        </div>
    );
}
