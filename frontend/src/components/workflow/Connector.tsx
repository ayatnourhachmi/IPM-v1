/**
 * Connector — animated line with arrowhead between workflow nodes.
 * Horizontal on desktop, vertical on mobile. Uses framer-motion.
 * Adapted from stageflow-compass reference.
 */

"use client";

import { motion } from "framer-motion";

interface ConnectorProps {
    delay?: number;
    vertical?: boolean;
}

export default function Connector({ delay = 0, vertical = false }: ConnectorProps) {
    if (vertical) {
        return (
            <motion.div
                style={{ display: "flex", justifyContent: "center" }}
                initial={{ scaleY: 0, opacity: 0 }}
                animate={{ scaleY: 1, opacity: 1 }}
                transition={{ duration: 0.3, delay }}
            >
                <div style={{
                    height: 24,
                    width: 1,
                    background: "var(--wf-connector-stroke)",
                    position: "relative",
                }}>
                    {/* Arrowhead */}
                    <div style={{
                        position: "absolute",
                        bottom: 0,
                        left: "50%",
                        transform: "translateX(-50%)",
                        width: 0,
                        height: 0,
                        borderTop: "4px solid var(--wf-connector-stroke)",
                        borderLeft: "3px solid transparent",
                        borderRight: "3px solid transparent",
                    }} />
                </div>
            </motion.div>
        );
    }

    return (
        <motion.div
            style={{ display: "flex", alignItems: "center" }}
            initial={{ scaleX: 0, opacity: 0 }}
            animate={{ scaleX: 1, opacity: 1 }}
            transition={{ duration: 0.3, delay }}
        >
            <div style={{
                width: 24,
                height: 1,
                background: "var(--wf-connector-stroke)",
                position: "relative",
            }}>
                {/* Arrowhead */}
                <div style={{
                    position: "absolute",
                    right: 0,
                    top: "50%",
                    transform: "translateY(-50%)",
                    width: 0,
                    height: 0,
                    borderLeft: "4px solid var(--wf-connector-stroke)",
                    borderTop: "3px solid transparent",
                    borderBottom: "3px solid transparent",
                }} />
            </div>
        </motion.div>
    );
}
