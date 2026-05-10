/**
 * StatusBadge — Colour-coded status pill.
 */

"use client";

import type { Status } from "@/lib/types";
import { STATUS_LABELS } from "@/lib/types";

interface StatusBadgeProps {
    status: Status;
}

export function StatusBadge({ status }: StatusBadgeProps) {
    return (
        <span className={`status-badge ${status}`}>
            {STATUS_LABELS[status]}
        </span>
    );
}
