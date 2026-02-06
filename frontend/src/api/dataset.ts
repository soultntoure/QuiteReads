import { API_BASE_URL } from './client';

export interface PreprocessingConfig {
    min_user_ratings: number;
    min_item_ratings: number;
    val_ratio: number;
    test_ratio: number;
    random_seed: number;
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

export interface PreprocessingResponse {
    message: string;
    config: PreprocessingConfig;
    statistics: DatasetStatistics;
    n_iterations: number;
}

export const uploadDataset = async (
    file: File,
    minUserRatings: number,
    minItemRatings: number,
    valRatio: number,
    testRatio: number
): Promise<PreprocessingResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('min_user_ratings', minUserRatings.toString());
    formData.append('min_item_ratings', minItemRatings.toString());
    formData.append('val_ratio', valRatio.toString());
    formData.append('test_ratio', testRatio.toString());

    const response = await fetch(`${API_BASE_URL}/datasets/upload`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to upload dataset');
    }

    return response.json();
};
