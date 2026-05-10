/**
 * StageGate — Diamond gate node with dashed lines, ◆/✓, pulse-ring when active.
 * Uses framer-motion spring animation. Clickable.
 * Completed gates show animated checkmark with accent-subtle filled background.
 * Adapted from stageflow-compass reference.
 */

"use client";

import { motion } from "framer-motion";

interface StageGateProps {
    label: string;
    isActive?: boolean;
    isCompleted?: boolean;
    color: "blue" | "emerald" | "orange";
    delay?: number;
    onClick?: () => void;
}

const colorClasses = {
    blue: {
        border: "var(--wf-sourcing)",
        ring: "var(--wf-sourcing-ring)",
        text: "var(--wf-sourcing)",
    },
    emerald: {
        border: "var(--wf-qualification)",
        ring: "var(--wf-qualification-ring)",
        text: "var(--wf-qualification)",
    },
    orange: {
        border: "var(--wf-delivery)",
        ring: "var(--wf-delivery-ring)",
        text: "var(--wf-delivery)",
    },
};

export default function StageGate({ label, isActive, isCompleted, color, delay = 0, onClick }: StageGateProps) {
    const c = colorClasses[color];

    return (
        <motion.div
            style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 12,
                cursor: isActive ? "pointer" : "default",
            }}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 300, damping: 30, delay }}
            onClick={isActive ? onClick : undefined}
        >
            {/* Dashed line top */}
            <div style={{
                width: 1,
                height: 8,
                borderLeft: "1px dashed var(--wf-connector-stroke)",
            }} />

            {/* Diamond */}
            <div style={{
                position: "relative",
                ...(isActive ? {
                    boxShadow: `0 0 0 4px ${c.ring}`,
                    borderRadius: 2,
                    animation: "pulseRing 2s ease-in-out infinite",
                } : {}),
            }}>
                <div style={{
                    width: 24,
                    height: 24,
                    transform: "rotate(45deg)",
                    border: `1px solid ${c.border}`,
                    background: isCompleted ? c.ring : "var(--wf-bg)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    transition: "background 0.3s, border-color 0.3s",
                }}>
                    <span style={{
                        transform: "rotate(-45deg)",
                        fontFamily: "var(--font-mono)",
                        fontSize: 9,
                        fontWeight: 500,
                        color: isCompleted ? c.text : "var(--wf-muted-fg)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                    }}>
                        {isCompleted ? (
                            <motion.div
                                initial={{ scale: 0, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                            >
                                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                                    <path d="M3 7L6 10L11 4" stroke={c.text} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            </motion.div>
                        ) : "◆"}
                    </span>
                </div>
            </div>

            {/* Dashed line bottom */}
            <div style={{
                width: 1,
                height: 8,
                borderLeft: "1px dashed var(--wf-connector-stroke)",
            }} />

            {/* Label */}
            <span style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                fontWeight: 500,
                color: isCompleted ? c.text : isActive ? c.text : "var(--wf-muted-fg)",
                transition: "color 0.3s",
            }}>
                {label}
            </span>
        </motion.div>
    );
}
