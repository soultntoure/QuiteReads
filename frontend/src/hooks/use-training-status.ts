import { useQuery } from "@tanstack/react-query";
import { experimentsApi } from "@/api/experiments";

export const trainingStatusKeys = {
    all: ["training-status"] as const,
    byExperiment: (id: string) => [...trainingStatusKeys.all, id] as const,
};

/**
 * Hook to poll training status for a running experiment.
 * Polls every second when enabled.
 */
export function useTrainingStatus(experimentId: string, enabled: boolean) {
    return useQuery({
        queryKey: trainingStatusKeys.byExperiment(experimentId),
        queryFn: () => experimentsApi.getTrainingStatus(experimentId),
        refetchInterval: enabled ? 1000 : false,
        enabled,
    });
}
