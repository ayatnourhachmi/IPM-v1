/**
 * TypeScript interfaces mirroring backend Pydantic schemas.
 */

export type Horizon = "court_terme" | "moyen_terme" | "long_terme";

export type Status = "draft" | "submitted" | "solutions_reviewed" | "selected" | "rework" | "abandoned" | "in_qualification" | "delivery";

export type Objectif = "cost_reduction" | "cx_improvement" | "risk_mitigation" | "market_opportunity";

export type Origine = "enjeu_marche" | "probleme_operationnel" | "demande_client";

/** LLM tagging confidence buckets */
export type ConfidenceLevel = "low" | "medium" | "high";

export interface TagScalar<T extends string = string> {
    value: T;
    confidence: ConfidenceLevel;
}

export interface Tags {
    objectif: TagScalar<Objectif>;
    domaine: TagScalar<string>[];
    impact: TagScalar<string>[];
    origine: TagScalar<Origine>;
}

export const CATEGORIES = ["Coût", "Expérience client", "Risque", "Opportunité marché"] as const;
export type Category = (typeof CATEGORIES)[number];

export interface DuplicateMatch {
    id: string;
    pitch: string;
    status: Status;
    similarity_score: number;
}

export interface RiskItem {
    risk: string;
    severity: "low" | "medium" | "high";
}

export interface Suggestion {
    label: string;
    text: string;
}

export interface BusinessNeed {
    id: string;
    pitch: string;
    horizon: Horizon;
    tags: Tags;
    /** Flattened per-dimension classification confidence from AI tags (mirrors AnalyzeResponse.confidence) */
    confidence?: TagsConfidenceSnapshot | null;
    constraints?: { domain: string; impact: string; objective: string } | null;
    risks: RiskItem[];
    justifications?: {
        maturite_justification?: string;
        expertise_justification?: string;
        duree_justification?: string;
        impact_justification?: string;
        fit_justification?: string;
    } | null;
    ivi_scores?: {
        maturite: number;
        expertise: number;
        duree: number;
        impact: number;
    } | null;
    status: Status;
    rework_note?: string | null;
    duplicate_matches: DuplicateMatch[];
    created_at: string;
    updated_at: string;
}

/** Flattened tag confidence envelope (analyze + DB persistence) */
export interface TagsConfidenceSnapshot {
    objectif?: ConfidenceLevel;
    origine?: ConfidenceLevel;
    domaine?: Array<{ value?: string | null; confidence: ConfidenceLevel }>;
    impact?: Array<{ value?: string | null; confidence: ConfidenceLevel }>;
}

export interface Constraints {
    domain: string;
    impact: string;
    objective: string;
}

export interface AnalyzeResponse {
    tags: Tags;
    suggestions: Suggestion[];
    constraints?: Constraints | null;
    confidence?: TagsConfidenceSnapshot | null;
}

export interface CreateNeedRequest {
    pitch: string;
    horizon: Horizon;
    tags?: Tags;
}

export interface UpdateStatusRequest {
    status: Status;
    note?: string;
}

export interface CatalogProduct {
    id: string;
    name: string;
    description: string;
    domain?: string;
    maturity?: string;
    ipm_stage?: string;
    internal_external?: string;
    industry_focus?: string;
    ai_type?: string;
    ai_criticality?: string;
    maturity_level?: string;
    complexity?: string;
    value_layer?: string;
    monetization_potential?: string;
    business_impact?: string;
    lead?: string;
    features: string[];
    relevance_score: number;
}

export interface CatalogSearchResponse {
    results: CatalogProduct[];
    total: number;
}

export interface EvaluationScores {
    maturite: number;
    maturite_justification: string;
    expertise: number;
    expertise_justification: string;
    duree: number;
    duree_justification: string;
    impact: number;
    impact_justification: string;
}

export interface GapAnalysisResponse {
    features_matching: string[];
    features_missing: string[];
    resources_needed: string[];
    risks: RiskItem[];
    fit_score: number;
    fit_justification: string;
    evaluation_scores: EvaluationScores;
    solution_name: string;
}

export interface GapAnalysisContextPayload {
    features_matching?: string[];
    features_missing?: string[];
    resources_needed?: string[];
    risks?: RiskItem[];
    fit_score?: number;
    fit_justification?: string;
    evaluation_scores?: EvaluationScores | null;
}

export interface RecommendationSolutionPayload {
    id?: string;
    name?: string;
    description?: string;
    domain?: string;
    features?: string[];
    business_impact?: string;
    maturity?: string;
    maturity_level?: string;
    complexity?: string;
    relevance_score?: number;
    /** Same shape as GET gap-analysis response (may be inlined from local persistence) */
    gap_analysis?: GapAnalysisContextPayload | null;
    /** Optional duplicate of nested gap_analysis.evaluation_scores when client denormalizes */
    evaluation_scores?: EvaluationScores | null;
    relevance?: number;
    overall?: number;
    source?: string;
}

export interface RecommendationKPI {
    name: string;
    target: string;
    measurement_criteria: string;
}

export interface OrganizationalRecommendation {
    role: string;
    action: string;
}

export interface SolutionRecommendations {
    solution_id: string;
    solution_name: string;
    mode?: "STANDARD" | "PREREQUIS";
    technical_recommendations: string[];
    organizational_recommendations: OrganizationalRecommendation[];
    kpis: RecommendationKPI[];
}

export interface RecommendationsResponse {
    recommendations: SolutionRecommendations[];
}

export interface RecommendationsRequest {
    selected_solutions: RecommendationSolutionPayload[];
}

export interface ExportDeliverySolution {
    id: string;
    name: string;
    relevance: number;
    overall: number;
}

export interface ExportReportRequest {
    recommendations: SolutionRecommendations[];
    delivery_solutions: ExportDeliverySolution[];
}

export const HORIZON_LABELS: Record<Horizon, { label: string; detail: string }> = {
    court_terme: { label: "Short term", detail: "< 3 months" },
    moyen_terme: { label: "Mid term", detail: "6–12 months" },
    long_terme: { label: "Long term", detail: "> 1 year" },
};

export const STATUS_LABELS: Record<Status, string> = {
    draft: "Draft",
    submitted: "Submitted",
    solutions_reviewed: "Solutions Reviewed",
    rework: "Rework",
    abandoned: "Abandoned",
    in_qualification: "In Qualification",
    selected: "Solution Selected",
    delivery: "Delivery",
};

export const OBJECTIF_LABELS: Record<Objectif, string> = {
    cost_reduction: "Cost Reduction",
    cx_improvement: "CX Improvement",
    risk_mitigation: "Risk Mitigation",
    market_opportunity: "Market Opportunity",
};
