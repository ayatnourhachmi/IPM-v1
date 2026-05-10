/**
 * Sourcing page — Background texture canvas + full 3-panel sourcing layout.
 */

"use client";

import { useEffect } from "react";
import { SourcingShell } from "@/components/sourcing/SourcingShell";

export default function SourcingPage() {
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
        <>
            <canvas id="bg-canvas" />
            <SourcingShell />
        </>
    );
}
