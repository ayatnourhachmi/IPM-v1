/**
 * Hook for fetching and managing business needs from the API.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { listNeeds, updateNeedStatus } from "@/lib/api";
import type { BusinessNeed, Status } from "@/lib/types";

interface UseNeedsResult {
    needs: BusinessNeed[];
    isLoading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
    handleUpdateStatus: (needId: string, status: Status, note?: string) => Promise<void>;
}

export function useNeeds(): UseNeedsResult {
    const [needs, setNeeds] = useState<BusinessNeed[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const refresh = useCallback(async () => {
        try {
            setError(null);
            const data = await listNeeds();
            setNeeds(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Impossible de charger les données.");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        refresh();
    }, [refresh]);

    const handleUpdateStatus = useCallback(async (needId: string, status: Status, note?: string) => {
        try {
            const updated = await updateNeedStatus(needId, { status, note });
            setNeeds((prev) => prev.map((n) => (n.id === updated.id ? updated : n)));
        } catch (err) {
            throw err;
        }
    }, []);

    return { needs, isLoading, error, refresh, handleUpdateStatus };
}
