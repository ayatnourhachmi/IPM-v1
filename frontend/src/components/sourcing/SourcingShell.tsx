/**
 * SourcingShell — Orchestrates the 3-panel sourcing layout.
 * Manages state, integrates useAnalyze, and coordinates panels.
 * Updated for Phase 1: editable AI fields, new WorkflowBar integration.
 */

"use client";

import React, { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAnalyze } from "@/hooks/useAnalyze";
import { createNeed, updateNeedStatus } from "@/lib/api";
import { WorkflowBar } from "@/components/layout/WorkflowBar";
import { RecapPanel } from "@/components/sourcing/RecapPanel";
import { PitchPanel } from "@/components/sourcing/PitchPanel";
import { SuggestionsPanel } from "@/components/sourcing/SuggestionsPanel";
import { DuplicateBanner } from "@/components/sourcing/DuplicateBanner";
import type { BusinessNeed, DuplicateMatch, Horizon } from "@/lib/types";
import { HORIZON_LABELS, OBJECTIF_LABELS } from "@/lib/types";
import { Sg1ValidationPanel } from "@/components/sourcing/Sg1ValidationPanel";

export function SourcingShell() {
    const router = useRouter();
    const [pitch, setPitch] = useState("");
    const [horizon, setHorizon] = useState<Horizon | null>(null);
    const [dismissedTags, setDismissedTags] = useState<Set<string>>(new Set());
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [duplicates, setDuplicates] = useState<DuplicateMatch[]>([]);
    const [showDuplicates, setShowDuplicates] = useState(false);

    // Summary metadata (editable via left SUMMARY panel)
    const [summaryObjectif, setSummaryObjectif] = useState("");
    const [summaryDomains, setSummaryDomains] = useState("");
    const [summaryImpact, setSummaryImpact] = useState("");

    // Created need for this session (used for SG-1 validation flow)
    const [currentNeed, setCurrentNeed] = useState<BusinessNeed | null>(null);
    const [isValidationOpen, setIsValidationOpen] = useState(false);
    const [workflowStatus, setWorkflowStatus] = useState<"draft" | "submitted">("draft");

    const { tags, suggestions, isAnalyzing, error: analyzeError } = useAnalyze(pitch, horizon);

    // Sync summary fields whenever AI tags change.
    // Always overwrite — horizon changes and re-analysis should be reflected immediately.
    useEffect(() => {
        if (!tags) return;
        if (tags.objectif?.value) {
            setSummaryObjectif(OBJECTIF_LABELS[tags.objectif.value]);
        }
        if (tags.domaine && tags.domaine.length > 0) {
            setSummaryDomains(tags.domaine.map((d) => d.value).join(", "));
        }
        if (tags.impact && tags.impact.length > 0) {
            setSummaryImpact(tags.impact.map((i) => i.value).join(", "));
        }
    }, [tags]);

    const canSubmit = pitch.trim().length >= 20 && horizon !== null && !isSubmitting;

    const handleDismissTag = (tagKey: string) => {
        setDismissedTags((prev) => {
            const next = new Set(prev);
            next.add(tagKey);
            return next;
        });
    };

    const handleApplySuggestion = (text: string) => {
        setPitch(text);
    };

    // Create the need first, then open the SG-1 panel when ready
    const handleSubmit = async () => {
        if (!canSubmit || !horizon) return;

        // Need already created this session — just re-open the panel
        if (currentNeed) {
            setIsValidationOpen(true);
            return;
        }

        if (isSubmitting) return;

        setIsSubmitting(true);
        try {
            const precomputedTags = !isAnalyzing && tags ? tags : undefined;
            const need = await createNeed({ pitch: pitch.trim(), horizon, tags: precomputedTags });
            setCurrentNeed(need);

            if (need.duplicate_matches && need.duplicate_matches.length > 0) {
                setDuplicates(need.duplicate_matches);
                setShowDuplicates(true);
            }

            // Open panel only once the need is persisted.
            // SG-1 is only completed once the user confirms GO and moves to Discovery.
            setIsValidationOpen(true);
        } catch {
            // submission failed — button returns to ready state, user can retry
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleGo = useCallback(async () => {
        if (!currentNeed) return;
        setIsSubmitting(true);
        try {
            const updated = await updateNeedStatus(currentNeed.id, { status: "submitted" });
            setCurrentNeed(updated);
            setWorkflowStatus("submitted");
            setIsValidationOpen(false);
            router.push(`/discovery?id=${updated.id}`);
        } catch {
            setIsSubmitting(false);
        }
    }, [currentNeed, router]);

    const handleCloseValidation = useCallback(() => {
        setIsValidationOpen(false);
    }, []);

    const handleRework = useCallback((_note?: string) => {
        setWorkflowStatus("draft");
        setIsValidationOpen(false);
        // Return focus to the main pitch textarea for quick editing
        setTimeout(() => {
            const el = document.getElementById("pitch-input") as HTMLTextAreaElement | null;
            el?.focus();
        }, 0);
    }, []);

    const handleAbandon = useCallback(async () => {
        // If no need was persisted yet, simply reset and go back to dashboard
        if (!currentNeed) {
            setPitch("");
            setHorizon(null);
            setSummaryObjectif("");
            setSummaryDomains("");
            setSummaryImpact("");
            setIsValidationOpen(false);
            router.push("/dashboard");
            return;
        }

        setIsSubmitting(true);
        try {
            await updateNeedStatus(currentNeed.id, { status: "abandoned" });
            setIsValidationOpen(false);
            router.push("/dashboard");
        } catch {
            setIsSubmitting(false);
        }
    }, [currentNeed, router]);

    return (
        <div className="app-shell">
            <WorkflowBar
                currentStep={showDuplicates && duplicates.length > 0 ? "business_need" : isValidationOpen ? "sg1" : "business_need"}
                status={workflowStatus}
                isInteractive={false}
            />

            <div className="app-content">
                <div className="glow-divider" />

                {showDuplicates && duplicates.length > 0 && (
                    <DuplicateBanner
                        matches={duplicates}
                        onDismiss={() => {
                            setShowDuplicates(false);
                            router.push(`/discovery?id=${currentNeed?.id}&sg1=completed`);
                        }}
                        onViewDuplicate={(id) => {
                            setShowDuplicates(false);
                            router.push(`/discovery?id=${id}&sg1=completed`);
                        }}
                    />
                )}

                <div className="workspace">
                    <RecapPanel
                        pitch={pitch}
                        onPitchChange={setPitch}
                        tags={tags}
                        horizon={horizon}
                        summaryObjectif={summaryObjectif}
                        onSummaryObjectifChange={setSummaryObjectif}
                        summaryDomains={summaryDomains}
                        onSummaryDomainsChange={setSummaryDomains}
                        summaryImpact={summaryImpact}
                        onSummaryImpactChange={setSummaryImpact}
                        dismissedTags={dismissedTags}
                        onDismissTag={handleDismissTag}
                    />

                    <PitchPanel
                        pitch={pitch}
                        onPitchChange={setPitch}
                        horizon={horizon}
                        onHorizonChange={setHorizon}
                        canSubmit={canSubmit}
                        isSubmitting={isSubmitting}
                        onSubmit={handleSubmit}
                    />

                    <SuggestionsPanel
                        suggestions={suggestions}
                        isAnalyzing={isAnalyzing}
                        hasPitch={pitch.trim().length >= 10}
                        onApply={handleApplySuggestion}
                        error={analyzeError}
                    />
                </div>
            </div>

            <Sg1ValidationPanel
                open={isValidationOpen}
                isProcessing={isSubmitting}
                pitch={pitch}
                horizonLabel={horizon ? HORIZON_LABELS[horizon].label : "Not selected"}
                objectif={summaryObjectif}
                domains={summaryDomains}
                impact={summaryImpact}
                hasDuplicates={(currentNeed?.duplicate_matches?.length ?? 0) > 0}
                onClose={handleCloseValidation}
                onGo={handleGo}
                onRework={handleRework}
                onAbandon={handleAbandon}
            />
        </div>
    );
}
