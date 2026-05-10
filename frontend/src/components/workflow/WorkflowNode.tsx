/**
 * WorkflowNode — Circular step node with phase-colored border.
 * Shows ✓ when complete, pulsing dot when active, grey dot when locked.
 * Uses framer-motion spring scale-in animation.
 * Adapted from stageflow-compass reference.
 */

"use client";

import { motion } from "framer-motion";

interface WorkflowNodeProps {
    label: string;
    index: string;
    color: "blue" | "emerald" | "orange";
    isActive?: boolean;
    isCompleted?: boolean;
    subtitle?: string;
    delay?: number;
}

const colorMap = {
    blue: {
        border: "var(--wf-sourcing)",
        glow: "0 0 15px var(--wf-sourcing-glow)",
        text: "var(--wf-sourcing)",
        bg: "var(--wf-sourcing)",
        subtitleBg: "var(--wf-sourcing-bg-active)",
    },
    emerald: {
        border: "var(--wf-qualification)",
        glow: "0 0 15px var(--wf-qualification-glow)",
        text: "var(--wf-qualification)",
        bg: "var(--wf-qualification)",
        subtitleBg: "var(--wf-qualification-bg-chip)",
    },
    orange: {
        border: "var(--wf-delivery)",
        glow: "0 0 15px var(--wf-delivery-glow)",
        text: "var(--wf-delivery)",
        bg: "var(--wf-delivery)",
        subtitleBg: "var(--wf-delivery-bg-chip)",
    },
};

export default function WorkflowNode({ label, index, color, isActive, isCompleted, subtitle, delay = 0 }: WorkflowNodeProps) {
    const c = colorMap[color];

    return (
        <motion.div
            style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 300, damping: 30, delay }}
        >
            {/* Index label */}
            <span style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                fontWeight: 500,
                color: c.text,
                opacity: 0.6,
            }}>
                {index}
            </span>

            {/* Circle node */}
            <div style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                border: `2px solid ${c.border}`,
                background: "var(--wf-bg)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                position: "relative",
                boxShadow: isActive ? c.glow : "none",
            }}>
                {isCompleted && (
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                        <path d="M3 7L6 10L11 4" stroke={c.text} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                )}
                {isActive && (
                    <div style={{
                        width: 12,
                        height: 12,
                        borderRadius: "50%",
                        background: c.bg,
                        animation: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                    }} />
                )}
                {!isCompleted && !isActive && (
                    <div style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: "var(--wf-muted-fg)",
                        opacity: 0.3,
                    }} />
                )}
            </div>

            {/* Label */}
            <span style={{
                fontSize: 10,
                fontWeight: 500,
                color: "var(--wf-fg)",
                textAlign: "center",
                maxWidth: 60,
                lineHeight: 1.3,
            }}>
                {label}
            </span>

            {/* Subtitle chip */}
            {subtitle && (
                <span style={{
                    fontSize: 9,
                    fontFamily: "var(--font-mono)",
                    color: c.text,
                    background: c.subtitleBg,
                    padding: "2px 8px",
                    borderRadius: 4,
                }}>
                    {subtitle}
                </span>
            )}
        </motion.div>
    );
}
