/**
 * RecapPanel — Left SUMMARY panel: single source of truth for metadata
 * (Pitch, Objective, Domains, Impact, Horizon) with inline editing.
 */

"use client";

import { useState } from "react";
import type { Horizon, Tags } from "@/lib/types";
import { HORIZON_LABELS } from "@/lib/types";
import { TagChips } from "@/components/sourcing/TagChips";

interface RecapPanelProps {
    pitch: string;
    onPitchChange: (value: string) => void;
    tags: Tags | null;
    horizon: Horizon | null;
    summaryObjectif: string;
    onSummaryObjectifChange: (value: string) => void;
    summaryDomains: string;
    onSummaryDomainsChange: (value: string) => void;
    summaryImpact: string;
    onSummaryImpactChange: (value: string) => void;
    dismissedTags: Set<string>;
    onDismissTag: (key: string) => void;
}

type EditableField = "pitch" | "objective" | "domains" | "impact" | null;

export function RecapPanel({
    pitch,
    onPitchChange,
    tags,
    horizon,
    summaryObjectif,
    onSummaryObjectifChange,
    summaryDomains,
    onSummaryDomainsChange,
    summaryImpact,
    onSummaryImpactChange,
    dismissedTags,
    onDismissTag,
}: RecapPanelProps) {
    const [editing, setEditing] = useState<EditableField>(null);

    const hasAnything =
        pitch.trim().length > 0 ||
        !!summaryObjectif ||
        !!summaryDomains ||
        !!summaryImpact ||
        horizon !== null ||
        !!tags;

    const renderValueOrPlaceholder = (value: string, placeholder: string) => (
        <div className="recap-value" style={!value ? { opacity: 0.6 } : undefined}>
            {value || placeholder}
        </div>
    );

    return (
        <div className="panel panel-scroll">
            <div className="panel-title">SUMMARY</div>

            {!hasAnything ? (
                <div className="recap-empty">
                    <div className="recap-empty-icon">◇</div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 300 }}>
                        Information will appear here as you type
                    </div>
                </div>
            ) : (
                <>
                    {/* PITCH */}
                    <div className="recap-field">
                        <div className="recap-label">PITCH</div>
                        {editing === "pitch" ? (
                            <textarea
                                className="recap-edit-input"
                                value={pitch}
                                onChange={(e) => onPitchChange(e.target.value)}
                                onBlur={() => setEditing(null)}
                                rows={3}
                                autoFocus
                            />
                        ) : (
                            renderValueOrPlaceholder(
                                pitch,
                                "Start writing your pitch in the main panel"
                            )
                        )}
                        <button
                            className="recap-edit"
                            aria-label="Edit pitch"
                            type="button"
                            onClick={() => setEditing(editing === "pitch" ? null : "pitch")}
                        >
                            ✎
                        </button>
                    </div>

                    {/* OBJECTIVE */}
                    <div className="recap-field" style={{ animationDelay: "0.06s" }}>
                        <div className="recap-label">OBJECTIVE</div>
                        {editing === "objective" ? (
                            <input
                                className="recap-edit-input"
                                value={summaryObjectif}
                                onChange={(e) => onSummaryObjectifChange(e.target.value)}
                                onBlur={() => setEditing(null)}
                                autoFocus
                            />
                        ) : (
                            renderValueOrPlaceholder(
                                summaryObjectif,
                                "Will be inferred from your pitch"
                            )
                        )}
                        <button
                            className="recap-edit"
                            aria-label="Edit objective"
                            type="button"
                            onClick={() => setEditing(editing === "objective" ? null : "objective")}
                        >
                            ✎
                        </button>
                    </div>

                    {/* DOMAINS + AI TAGS */}
                    <div className="recap-field" style={{ animationDelay: "0.12s" }}>
                        <div className="recap-label">DOMAINS</div>
                        {editing === "domains" ? (
                            <input
                                className="recap-edit-input"
                                value={summaryDomains}
                                onChange={(e) => onSummaryDomainsChange(e.target.value)}
                                onBlur={() => setEditing(null)}
                                autoFocus
                            />
                        ) : (
                            renderValueOrPlaceholder(
                                summaryDomains,
                                "AI will suggest relevant domains"
                            )
                        )}
                        <button
                            className="recap-edit"
                            aria-label="Edit domains"
                            type="button"
                            onClick={() => setEditing(editing === "domains" ? null : "domains")}
                        >
                            ✎
                        </button>

                        {tags && (
                            <div style={{ marginTop: 8 }}>
                                <TagChips
                                    tags={tags}
                                    dismissedTags={dismissedTags}
                                    onDismiss={onDismissTag}
                                />
                            </div>
                        )}
                    </div>

                    {/* IMPACT */}
                    <div className="recap-field" style={{ animationDelay: "0.18s" }}>
                        <div className="recap-label">IMPACT</div>
                        {editing === "impact" ? (
                            <textarea
                                className="recap-edit-input"
                                value={summaryImpact}
                                onChange={(e) => onSummaryImpactChange(e.target.value)}
                                onBlur={() => setEditing(null)}
                                rows={2}
                                autoFocus
                            />
                        ) : (
                            renderValueOrPlaceholder(
                                summaryImpact,
                                "Expected impact will be proposed by AI"
                            )
                        )}
                        <button
                            className="recap-edit"
                            aria-label="Edit impact"
                            type="button"
                            onClick={() => setEditing(editing === "impact" ? null : "impact")}
                        >
                            ✎
                        </button>
                    </div>

                    {/* TIME HORIZON */}
                    <div className="recap-field" style={{ animationDelay: "0.24s" }}>
                        <div className="recap-label">TIME HORIZON</div>
                        <div className="recap-value">
                            {horizon ? HORIZON_LABELS[horizon].label : "Not selected yet"}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
