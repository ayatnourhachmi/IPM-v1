/**
 * HorizonSelector — Three-button selector for temporal horizon.
 */

"use client";

import type { Horizon } from "@/lib/types";
import { HORIZON_LABELS } from "@/lib/types";

interface HorizonSelectorProps {
    value: Horizon | null;
    onChange: (h: Horizon) => void;
}

const HORIZONS: Horizon[] = ["court_terme", "moyen_terme", "long_terme"];

export function HorizonSelector({ value, onChange }: HorizonSelectorProps) {
    return (
        <div>
            <div className="ai-tags-label" style={{ marginBottom: 8 }}>
                TIME HORIZON
            </div>
            <div className="horizon-group">
                {HORIZONS.map((h) => (
                    <button
                        key={h}
                        type="button"
                        className={`horizon-btn${value === h ? " selected" : ""}`}
                        onClick={() => onChange(h)}
                    >
                        {HORIZON_LABELS[h].label}
                        <span className="horizon-detail">{HORIZON_LABELS[h].detail}</span>
                    </button>
                ))}
            </div>
        </div>
    );
}
