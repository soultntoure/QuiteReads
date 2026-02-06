export interface PreprocessingStatus {
  status: "idle" | "processing" | "completed" | "failed";
  step: string;
  step_number: number;
  total_steps: number;
  message: string;
  error: string | null;
}

export interface DatasetStatistics {
  original_interactions: number;
  original_users: number;
  original_items: number;
  filtered_interactions: number;
  filtered_users: number;
  filtered_items: number;
  sparsity: number;
  sparsity_percent: string;
  density_percent: string;
  rating_mean: number;
  rating_std: number;
  rating_min: number;
  rating_max: number;
  retention_rate: string;
}

export interface DatasetMetadata {
  is_loaded: boolean;
  preprocessing_date: string | null;
  config: {
    min_user_ratings: number;
    min_item_ratings: number;
    val_ratio: number;
    test_ratio: number;
    random_seed: number;
  } | null;
  statistics: DatasetStatistics | null;
  filter_iterations: number | null;
  train_size: number | null;
  val_size: number | null;
  test_size: number | null;
}

export interface UploadResponse {
  message: string;
  status: string;
}

export interface DatasetUploadConfig {
  min_ratings: number;
  val_ratio: number;
  test_ratio: number;
  seed: number;
}
