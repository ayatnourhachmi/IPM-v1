/**
 * EmptyState — Shown when the dashboard has no business needs.
 */

"use client";

export function EmptyState() {
    return (
        <div className="empty-state">
            <div className="empty-icon">◇</div>
            <h2 className="empty-title">No initiatives yet</h2>
            <p className="empty-desc">
                Start by submitting your first business need.
                AI will help categorize it automatically.
            </p>
            <a href="/sourcing" className="dash-new-btn">
                Create my first need
            </a>
        </div>
    );
}
