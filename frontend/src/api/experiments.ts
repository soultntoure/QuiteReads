import { apiGet, apiPost, apiDelete } from "./client";
import type {
  ExperimentResponse,
  ExperimentListResponse,
  CreateCentralizedExperimentRequest,
  CreateFederatedExperimentRequest,
  CompleteExperimentRequest,
  HealthResponse,
} from "@/types/experiment";

export interface ExperimentFilters {
  status_filter?: string;
  type_filter?: string;
}

export const experimentsApi = {
  // Health check
  health: () => apiGet<HealthResponse>("/health"),

  // List all experiments
  list: (filters?: ExperimentFilters) => {
    const params = new URLSearchParams();
    if (filters?.status_filter) params.append("status_filter", filters.status_filter);
    if (filters?.type_filter) params.append("type_filter", filters.type_filter);
    const query = params.toString();
    return apiGet<ExperimentListResponse>(`/experiments/${query ? `?${query}` : "/"}`);
  },
  // return apiGet<ExperimentListResponse>(`/experiments${query ? `?${query}` : ""}`);

  // Get single experiment
  get: (id: string) => apiGet<ExperimentResponse>(`/experiments/${id}`),

  // Create centralized experiment
  createCentralized: (data: CreateCentralizedExperimentRequest) =>
    apiPost<ExperimentResponse, CreateCentralizedExperimentRequest>("/experiments/centralized", data),

  // Create federated experiment
  createFederated: (data: CreateFederatedExperimentRequest) =>
    apiPost<ExperimentResponse, CreateFederatedExperimentRequest>("/experiments/federated", data),

  // Start experiment
  start: (id: string) => apiPost<ExperimentResponse>(`/experiments/${id}/start`),

  // Complete experiment
  complete: (id: string, data: CompleteExperimentRequest) =>
    apiPost<ExperimentResponse, CompleteExperimentRequest>(`/experiments/${id}/complete`, data),

  // Mark experiment as failed
  fail: (id: string) => apiPost<ExperimentResponse>(`/experiments/${id}/fail`),

  // Delete experiment
  delete: (id: string) => apiDelete<void>(`/experiments/${id}`),
};
