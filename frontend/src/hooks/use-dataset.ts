import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { datasetApi } from "@/api/dataset";
import type { DatasetUploadConfig } from "@/types/dataset";
import { useToast } from "@/hooks/use-toast";

export const datasetKeys = {
  all: ["dataset"] as const,
  metadata: () => [...datasetKeys.all, "metadata"] as const,
  status: () => [...datasetKeys.all, "status"] as const,
};

export function useDatasetMetadata() {
  return useQuery({
    queryKey: datasetKeys.metadata(),
    queryFn: () => datasetApi.getMetadata(),
  });
}

export function usePreprocessingStatus(enabled: boolean) {
  return useQuery({
    queryKey: datasetKeys.status(),
    queryFn: () => datasetApi.getStatus(),
    refetchInterval: enabled ? 1000 : false,
    enabled,
  });
}

export function useUploadDataset() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ file, config }: { file: File; config: DatasetUploadConfig }) =>
      datasetApi.upload(file, config),
    onSuccess: () => {
      toast({
        title: "Upload Started",
        description: "Your dataset is being preprocessed.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Upload Failed",
        description: error.message,
        variant: "destructive",
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: datasetKeys.metadata() });
    },
  });
}
