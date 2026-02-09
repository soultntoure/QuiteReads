import { apiDelete, apiGet, apiUploadFile } from "./client";
import type {
  DatasetMetadata,
  DatasetUploadConfig,
  PreprocessingStatus,
  UploadResponse,
} from "@/types/dataset";

export const datasetApi = {
  upload: (file: File, config: DatasetUploadConfig) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("min_ratings", String(config.min_ratings));
    formData.append("val_ratio", String(config.val_ratio));
    formData.append("test_ratio", String(config.test_ratio));
    formData.append("seed", String(config.seed));
    return apiUploadFile<UploadResponse>("/dataset/upload", formData);
  },

  getStatus: () => apiGet<PreprocessingStatus>("/dataset/status"),

  getMetadata: () => apiGet<DatasetMetadata>("/dataset/metadata"),

  remove: () => apiDelete<void>("/dataset"),
};
