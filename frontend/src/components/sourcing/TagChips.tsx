/**
 * TagChips — Displays AI-generated tags with confidence indicators.
 * Each chip has a left accent border + a compact H/M/L badge showing AI confidence.
 */

"use client";

import type { Tags } from "@/lib/types";

interface TagChipsProps {
    tags: Tags;
    dismissedTags: Set<string>;
    onDismiss: (tagKey: string) => void;
}

const TAG_COLORS: Record<string, string> = {
    objectif: "amber",
    domaine: "blue",
    impact: "green",
    origine: "purple",
};

const CONFIDENCE_LABEL: Record<string, string> = {
    high: "H",
    medium: "M",
    low: "L",
};

const CONFIDENCE_TITLE: Record<string, string> = {
    high:   "AI confidence: high — pitch clearly signals this classification",
    medium: "AI confidence: medium — pitch implies this classification",
    low:    "AI confidence: low — classification inferred from weak signals",
};

export function TagChips({ tags, dismissedTags, onDismiss }: TagChipsProps) {
    const chips: Array<{ key: string; label: string; color: string; confidence: string }> = [];

    if (tags.objectif) {
        chips.push({ key: `obj-${tags.objectif.value}`, label: tags.objectif.value.replace(/_/g, " "), color: TAG_COLORS.objectif, confidence: tags.objectif.confidence });
    }

    tags.domaine.forEach((d) => {
        chips.push({ key: `dom-${d.value}`, label: d.value, color: TAG_COLORS.domaine, confidence: d.confidence });
    });

    tags.impact.forEach((imp) => {
        chips.push({ key: `imp-${imp.value}`, label: imp.value, color: TAG_COLORS.impact, confidence: imp.confidence });
    });

    if (tags.origine) {
        chips.push({ key: `ori-${tags.origine.value}`, label: tags.origine.value.replace(/_/g, " "), color: TAG_COLORS.origine, confidence: tags.origine.confidence });
    }

    if (chips.length === 0) return null;

    return (
        <div className="tags-row">
            {chips.map((chip) => (
                <span
                    key={chip.key}
                    className={`tag-chip ${chip.color} confidence-border-${chip.confidence}${dismissedTags.has(chip.key) ? " dismissed" : ""}`}
                    onClick={() => onDismiss(chip.key)}
                    title={CONFIDENCE_TITLE[chip.confidence]}
                >
                    <span className={`tag-confidence-dot confidence-${chip.confidence}`}>
                        {CONFIDENCE_LABEL[chip.confidence]}
                    </span>
                    {chip.label}
                    {!dismissedTags.has(chip.key) && (
                        <button className="tag-chip-x" aria-label="Dismiss">×</button>
                    )}
                </span>
            ))}
        </div>
    );
}
