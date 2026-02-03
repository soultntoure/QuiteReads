import { apiGet, apiPost, apiDelete } from "./client";
import type {
  MetricResponse,
  MetricListResponse,
  AddMetricRequest,
  AddMetricsBatchRequest,
} from "@/types/experiment";

export interface MetricFilters {
  name?: string;
  client_id?: string;
  round_number?: number;
}

export const metricsApi = {
  // List metrics for an experiment
  list: (experimentId: string, filters?: MetricFilters) => {
    const params = new URLSearchParams();
    if (filters?.name) params.append("name", filters.name);
    if (filters?.client_id) params.append("client_id", filters.client_id);
    if (filters?.round_number !== undefined) params.append("round_number", String(filters.round_number));
    const query = params.toString();
    return apiGet<MetricListResponse>(`/experiments/${experimentId}/metrics${query ? `?${query}` : ""}`);
  },

  // Add single metric
  add: (experimentId: string, data: AddMetricRequest) =>
    apiPost<MetricResponse, AddMetricRequest>(`/experiments/${experimentId}/metrics`, data),

  // Add batch of metrics
  addBatch: (experimentId: string, data: AddMetricsBatchRequest) =>
    apiPost<MetricResponse[], AddMetricsBatchRequest>(`/experiments/${experimentId}/metrics/batch`, data),

  // Delete all metrics for an experiment
  deleteAll: (experimentId: string) => apiDelete<void>(`/experiments/${experimentId}/metrics`),
};
