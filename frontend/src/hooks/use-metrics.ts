import { useQuery } from "@tanstack/react-query";
import { metricsApi, MetricFilters } from "@/api/metrics";

// Query keys
export const metricKeys = {
  all: ["metrics"] as const,
  lists: () => [...metricKeys.all, "list"] as const,
  list: (experimentId: string, filters?: MetricFilters) =>
    [...metricKeys.lists(), experimentId, filters] as const,
};

// List metrics for an experiment
export function useMetrics(experimentId: string, filters?: MetricFilters) {
  return useQuery({
    queryKey: metricKeys.list(experimentId, filters),
    queryFn: () => metricsApi.list(experimentId, filters),
    enabled: !!experimentId,
  });
}
