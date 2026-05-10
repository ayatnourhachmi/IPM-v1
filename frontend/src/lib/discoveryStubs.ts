/**
 * Discovery stub data — mock items for supplemental discovery sources (startup / tech-watch stubs).
 * Each source returns items with name, description, and relevance score (0-100).
 *
 * // TODO: replace each stub with real API calls in Phase 2
 */

export interface DiscoveryItem {
    id: string;
    name: string;
    description: string;
    relevance: number; // 0-100
}

export interface DiscoverySource {
    key: string;
    title: string;
    sourceLabel: string;
    items: DiscoveryItem[];
}

// REPLACED: Panel 1 now calls /api/v1/needs/{id}/catalog-search
// Keep the stub data below commented out for reference only
export const STUB_DXC_CATALOG: DiscoverySource = {
    key: "dxc_catalog",
    title: "DXC Internal Catalog",
    sourceLabel: "DAIC / AI Catalog",
    items: [
        // { id: "dxc-1", name: "DXC SmartAssist AI", description: "Enterprise-grade NLP chatbot platform for IT service desk automation with multi-language support.", relevance: 92 },
        // { id: "dxc-2", name: "DXC Analytics Cloud", description: "Unified BI and data analytics platform with predictive modeling capabilities.", relevance: 78 },
        // { id: "dxc-3", name: "DXC Process Miner", description: "RPA-enabled process discovery tool that identifies automation opportunities in business workflows.", relevance: 85 },
        // { id: "dxc-4", name: "DXC Secure Vault", description: "Zero-trust identity and access management platform for hybrid cloud environments.", relevance: 64 },
    ],
};

// TODO: replace stub with real StartupConnect AI API
export const STUB_STARTUPS: DiscoverySource = {
    key: "startups",
    title: "Startups",
    sourceLabel: "StartupConnect AI",
    items: [
        { id: "st-1", name: "Mistral AI", description: "European LLM provider — open-weight models optimized for enterprise deployment, competitive with GPT-4.", relevance: 91 },
        { id: "st-2", name: "Dataiku", description: "End-to-end AI/ML platform for data scientists and business analysts with no-code/low-code options.", relevance: 82 },
        { id: "st-3", name: "Snyk", description: "Developer-first security platform for automated vulnerability detection in code, containers, and IaC.", relevance: 69 },
        { id: "st-4", name: "Pigment", description: "AI-native financial planning platform for enterprise FP&A with scenario modeling.", relevance: 75 },
    ],
};

// TODO: replace stub with real AI Watch / tech watch API
export const STUB_TECH_WATCH: DiscoverySource = {
    key: "tech_watch",
    title: "Tech Watch",
    sourceLabel: "AI Watch",
    items: [
        { id: "tw-1", name: "Agentic AI Frameworks (2025 Trend)", description: "Industry trend toward autonomous AI agents orchestrating multi-step workflows — key players: LangGraph, CrewAI.", relevance: 86 },
        { id: "tw-2", name: "EU AI Act Compliance Deadline", description: "Regulatory watch: AI Act enforcement starting Q3 2025 — impact on high-risk AI systems classification.", relevance: 79 },
        { id: "tw-3", name: "Edge AI for IoT Manufacturing", description: "Market analysis on deploying ML models at the edge for real-time quality control in Industry 4.0.", relevance: 71 },
    ],
};

export const ALL_SOURCES: DiscoverySource[] = [
    STUB_DXC_CATALOG,
    STUB_STARTUPS,
    STUB_TECH_WATCH,
];
