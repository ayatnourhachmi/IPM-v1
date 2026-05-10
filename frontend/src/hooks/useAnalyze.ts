/**
 * Debounced hook for /needs/analyze — returns tags + suggestions.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { analyzePitch } from "@/lib/api";
import type { Suggestion, Tags } from "@/lib/types";

const DEBOUNCE_MS = 2000;
const MIN_PITCH_LENGTH = 30;

interface UseAnalyzeResult {
    tags: Tags | null;
    suggestions: Suggestion[];
    isAnalyzing: boolean;
    error: string | null;
}

export function useAnalyze(pitch: string, horizon?: string | null): UseAnalyzeResult {
    const [tags, setTags] = useState<Tags | null>(null);
    const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const analyze = useCallback(async (text: string, h: string | null | undefined) => {
        if (text.trim().length < MIN_PITCH_LENGTH) {
            setTags(null);
            setSuggestions([]);
            setIsAnalyzing(false);
            return;
        }

        setIsAnalyzing(true);
        setError(null);

        try {
            const result = await analyzePitch(text, h);
            setTags(result.tags);
            setSuggestions(result.suggestions || []);
        } catch (err) {
            if (err instanceof Error && err.name !== "AbortError") {
                setError(err.message);
            }
        } finally {
            setIsAnalyzing(false);
        }
    }, []);

    useEffect(() => {
        if (timerRef.current) clearTimeout(timerRef.current);

        timerRef.current = setTimeout(() => {
            analyze(pitch, horizon);
        }, DEBOUNCE_MS);

        return () => {
            if (timerRef.current) clearTimeout(timerRef.current);
        };
    }, [pitch, horizon, analyze]);

    return { tags, suggestions, isAnalyzing, error };
}
