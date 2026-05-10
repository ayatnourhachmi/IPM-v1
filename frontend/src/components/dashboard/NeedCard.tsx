/**
 * NeedCard — Dashboard card for a single business need.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import type { BusinessNeed, Status } from "@/lib/types";
import { HORIZON_LABELS } from "@/lib/types";

const ACTIONS: Record<string, Array<{ label: string; status: Status; style: string }>> = {
    draft: [
        { label: "Submit", status: "submitted", style: "primary" },
        { label: "Abandon", status: "abandoned", style: "danger" },
    ],
    submitted: [
        { label: "Qualify", status: "in_qualification", style: "success" },
        { label: "Abandon", status: "abandoned", style: "danger" },
    ],
    in_qualification: [
        { label: "Deliver", status: "delivery", style: "success" },
        { label: "Abandon", status: "abandoned", style: "danger" },
    ],
    rework: [
        { label: "Re-submit", status: "submitted", style: "primary" },
        { label: "Back to Draft", status: "draft", style: "" },
    ],
    delivery: [],     // terminal
    abandoned: [],    // terminal
};

interface NeedCardProps {
    need: BusinessNeed;
    onUpdateStatus: (needId: string, status: Status, note?: string) => Promise<void>;
}

export function NeedCard({ need, onUpdateStatus }: NeedCardProps) {
    const router = useRouter();
    const [reworkNote, setReworkNote] = useState("");
    const [showReworkInput, setShowReworkInput] = useState(false);
    const [isUpdating, setIsUpdating] = useState(false);

    const actions = ACTIONS[need.status] || [];

    const handleAction = async (status: Status) => {
        if (status === "abandoned" && !confirm("Confirm abandoning this initiative?")) return;

        setIsUpdating(true);
        try {
            await onUpdateStatus(need.id, status);
        } finally {
            setIsUpdating(false);
        }
    };

    const handleReworkSubmit = async () => {
        if (!reworkNote.trim()) return;
        setIsUpdating(true);
        try {
            await onUpdateStatus(need.id, "rework", reworkNote.trim());
            setShowReworkInput(false);
            setReworkNote("");
        } finally {
            setIsUpdating(false);
        }
    };

    return (
        <div className={`need-card${need.status === "abandoned" ? " abandoned" : ""}`}>
            <div className="need-header">
                <span className="bn-id" style={{ cursor: "pointer", textDecoration: "underline" }}
                    onClick={() => {
                        let target = "/discovery";
                        if (need.status === "submitted") target = "/evaluation";
                        else if (need.status === "in_qualification") target = "/selection";
                        else if (need.status === "delivery") target = "/recos";
                        router.push(`${target}?id=${need.id}`);
                    }}
                >
                    {need.id}
                </span>
                <StatusBadge status={need.status} />
            </div>

            <p className="need-pitch">{need.pitch}</p>

            <div className="need-meta">
                <span className="tag-chip amber" style={{ fontSize: 10 }}>
                    {HORIZON_LABELS[need.horizon].label}
                </span>
                {need.tags.domaine.slice(0, 3).map((d) => (
                    <span key={d.value} className="tag-chip blue" style={{ fontSize: 10 }}>{d.value}</span>
                ))}
            </div>

            {need.rework_note && (
                <div className="need-rework-note">
                    <div className="need-rework-note-label">REWORK NOTE</div>
                    {need.rework_note}
                </div>
            )}

            {actions.length > 0 && (
                <div className="need-actions">
                    {actions.map((action) => (
                        <button
                            key={action.status}
                            className={`action-btn ${action.style}`}
                            onClick={() => handleAction(action.status)}
                            disabled={isUpdating}
                        >
                            {action.label}
                        </button>
                    ))}

                    {(need.status === "submitted" || need.status === "in_qualification") && (
                        <button
                            className="action-btn"
                            onClick={() => setShowReworkInput(!showReworkInput)}
                            disabled={isUpdating}
                        >
                            Rework
                        </button>
                    )}
                </div>
            )}

            {showReworkInput && (
                <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                    <input
                        type="text"
                        value={reworkNote}
                        onChange={(e) => setReworkNote(e.target.value)}
                        placeholder="Reason for rework…"
                        style={{
                            flex: 1,
                            padding: "7px 12px",
                            borderRadius: 8,
                            border: "1px solid var(--border-input)",
                            background: "var(--bg-input)",
                            color: "var(--text-primary)",
                            fontFamily: "var(--font-sans)",
                            fontSize: 12,
                            outline: "none",
                        }}
                    />
                    <button className="action-btn primary" onClick={handleReworkSubmit} disabled={isUpdating}>
                        OK
                    </button>
                </div>
            )}
        </div>
    );
}
