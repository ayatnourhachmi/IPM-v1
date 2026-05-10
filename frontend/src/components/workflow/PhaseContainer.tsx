/**
 * PhaseContainer — Colored border-left container grouping steps by phase.
 * Collapses with AnimatePresence when phase is done and later phase is active.
 * Shows "✓ N/M" chip when collapsed.
 * Adapted from stageflow-compass reference.
 */

"use client";

import React from "react";
import { motion, AnimatePresence } from "framer-motion";

interface PhaseContainerProps {
    title: string;
    color: "blue" | "emerald" | "orange";
    children: React.ReactNode;
    isCollapsed?: boolean;
    completedCount?: number;
    totalCount?: number;
}

const phaseColors = {
    blue: {
        border: "var(--wf-sourcing)",
        bg: "var(--wf-sourcing-bg-panel)",
        bgCollapsed: "var(--wf-sourcing-bg-collapsed)",
        text: "var(--wf-sourcing)",
    },
    emerald: {
        border: "var(--wf-qualification)",
        bg: "var(--wf-qualification-bg-panel)",
        bgCollapsed: "var(--wf-qualification-bg-collapsed)",
        text: "var(--wf-qualification)",
    },
    orange: {
        border: "var(--wf-delivery)",
        bg: "var(--wf-delivery-bg-panel)",
        bgCollapsed: "var(--wf-delivery-bg-collapsed)",
        text: "var(--wf-delivery)",
    },
};

export default function PhaseContainer({
    title,
    color,
    children,
    isCollapsed = false,
    completedCount,
    totalCount,
}: PhaseContainerProps) {
    const c = phaseColors[color];

    return (
        <motion.div
            style={{
                borderLeft: `2px solid ${c.border}`,
                background: isCollapsed ? c.bgCollapsed : c.bg,
                borderRadius: "0 12px 12px 0",
                position: "relative",
                overflow: "hidden",
            }}
            layout
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
        >
            {/* Title row */}
            <div style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: isCollapsed ? "12px 16px" : "12px 16px 0",
            }}>
                <span style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 10,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    fontWeight: 500,
                    color: c.text,
                    opacity: isCollapsed ? 0.5 : 1,
                }}>
                    {title}
                </span>
                {isCollapsed && completedCount !== undefined && (
                    <motion.span
                        style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: 9,
                            color: c.text,
                            opacity: 0.6,
                        }}
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 0.6, scale: 1 }}
                    >
                        ✓ {completedCount}/{totalCount}
                    </motion.span>
                )}
            </div>

            {/* Expandable content */}
            <AnimatePresence initial={false}>
                {!isCollapsed && (
                    <motion.div
                        key="content"
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                        style={{ overflow: "hidden" }}
                    >
                        <div style={{
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            gap: 8,
                            padding: "8px 10px 10px",
                        }}
                            className="phase-content-desktop"
                        >
                            {children}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
