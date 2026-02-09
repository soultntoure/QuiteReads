// Enums
export type ExperimentType = "centralized" | "federated";
export type ExperimentStatus = "pending" | "running" | "completed" | "failed";
export type AggregationStrategy = "fedavg";

// Configuration for training
export interface ConfigurationSchema {
  n_factors: number;
  learning_rate: number;
  regularization: number;
  batch_size: number;
  epochs: number;
}

// Final metrics after training completes
export interface ExperimentMetricsSchema {
  final_rmse: number | null;
  final_mae: number | null;
  training_time_seconds: number | null;
}

// Main experiment response
export interface ExperimentResponse {
  id: string;
  name: string;
  type: ExperimentType;
  status: ExperimentStatus;
  config: ConfigurationSchema;
  metrics: ExperimentMetricsSchema;
  n_clients: number | null;
  n_rounds: number | null;
  aggregation_strategy: AggregationStrategy | null;
  created_at: string;
  completed_at: string | null;
}

// List response wrapper
export interface ExperimentListResponse {
  count: number;
  experiments: ExperimentResponse[];
}

// Request to create centralized experiment
export interface CreateCentralizedExperimentRequest {
  name: string;
  config: ConfigurationSchema;
}

// Request to create federated experiment
export interface CreateFederatedExperimentRequest {
  name: string;
  config: ConfigurationSchema;
  n_clients: number;
  n_rounds: number;
}

// Request to complete experiment
export interface CompleteExperimentRequest {
  final_rmse: number;
  final_mae: number;
  training_time_seconds: number;
}

// Individual metric record
export interface MetricResponse {
  experiment_id: string;
  name: string;
  value: number;
  round_number: number | null;
  client_id: string | null;
  context: string | null;  // 'training', 'validation', 'centralized_test', 'client_aggregated'
}

// Metrics list response
export interface MetricListResponse {
  count: number;
  metrics: MetricResponse[];
}

// Request to add a metric
export interface AddMetricRequest {
  name: string;
  value: number;
  round_number?: number;
  client_id?: string;
}

// Batch request for multiple metrics
export interface AddMetricsBatchRequest {
  metrics: AddMetricRequest[];
}

// API error response
export interface ErrorResponse {
  detail: string;
}

// Health check response
export interface HealthResponse {
  status: string;
}
