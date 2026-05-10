/**
 * Dashboard page — Pipeline view of all business needs with dark premium theme.
 */

"use client";

import React, { useEffect } from "react";
import { WorkflowBar } from "@/components/layout/WorkflowBar";
import { NeedCard } from "@/components/dashboard/NeedCard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { useNeeds } from "@/hooks/useNeeds";

export default function DashboardPage() {
    const { needs, isLoading, error, refresh, handleUpdateStatus } = useNeeds();

    useEffect(() => {
        const canvas = document.getElementById("bg-canvas") as HTMLCanvasElement | null;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        const chars = "0123456789ABCDEF";
        ctx.fillStyle = "rgba(180, 120, 60, 0.045)";
        ctx.font = "11px DM Mono, monospace";

        for (let x = 0; x < canvas.width; x += 28) {
            for (let y = 0; y < canvas.height; y += 20) {
                const char = chars[Math.floor(Math.random() * chars.length)];
                ctx.fillText(char, x + Math.random() * 8, y + Math.random() * 6);
            }
        }
    }, []);

    return (
        <div className="app-shell">
            <canvas id="bg-canvas" style={{ position: "fixed", top: 0, left: 0, zIndex: -1 }} />
            <WorkflowBar currentStep="business_need" />

            <div className="app-content">
                <div className="glow-divider" />

                <div style={{ display: "flex", flexDirection: "column", padding: "24px 0" }}>
                    <div className="dash-header">
                        <div>
                            <h1 className="dash-headline">
                                <span className="dash-thin">My </span>
                                <span className="dash-bold">initiatives</span>
                            </h1>
                            {!isLoading && (
                                <div className="dash-count" style={{ fontFamily: "var(--font-mono)", opacity: 0.7 }}>
                                    {needs.length} initiative{needs.length !== 1 ? "s" : ""} in your pipeline
                                </div>
                            )}
                        </div>
                        <a href="/sourcing" className="dash-new-btn">
                            + New Need
                        </a>
                    </div>

                    {isLoading && (
                        <div className="page-loader">
                            <span className="page-spinner" />
                            Loading initiatives…
                        </div>
                    )}

                    {error && (
                        <div style={{ textAlign: "center", padding: 40 }}>
                            <div style={{
                                maxWidth: 360,
                                margin: "0 auto",
                                padding: "16px 24px",
                                borderRadius: 12,
                                border: "1px solid rgba(220,80,80,0.2)",
                                background: "rgba(220,80,80,0.06)",
                            }}>
                                <p style={{ fontSize: 13, color: "#e87070" }}>{error}</p>
                                <button
                                    onClick={refresh}
                                    style={{
                                        marginTop: 12,
                                        fontSize: 12,
                                        fontWeight: 500,
                                        color: "var(--accent-light)",
                                        background: "none",
                                        border: "none",
                                        cursor: "pointer",
                                    }}
                                >
                                    Retry
                                </button>
                            </div>
                        </div>
                    )}

                    {!isLoading && !error && needs.length === 0 && <EmptyState />}

                    {!isLoading && !error && needs.length > 0 && (
                        <div className="dash-grid">
                            {needs.map((need) => (
                                <NeedCard
                                    key={need.id}
                                    need={need}
                                    onUpdateStatus={handleUpdateStatus}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
