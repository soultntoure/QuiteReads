import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { experimentsApi, ExperimentFilters } from "@/api/experiments";
import type {
  CreateCentralizedExperimentRequest,
  CreateFederatedExperimentRequest,
  CompleteExperimentRequest,
} from "@/types/experiment";
import { useToast } from "@/hooks/use-toast";

// Query keys
export const experimentKeys = {
  all: ["experiments"] as const,
  lists: () => [...experimentKeys.all, "list"] as const,
  list: (filters?: ExperimentFilters) => [...experimentKeys.lists(), filters] as const,
  details: () => [...experimentKeys.all, "detail"] as const,
  detail: (id: string) => [...experimentKeys.details(), id] as const,
  health: ["health"] as const,
};

// Health check hook
export function useHealthCheck() {
  return useQuery({
    queryKey: experimentKeys.health,
    queryFn: () => experimentsApi.health(),
    refetchInterval: 30000, // Check every 30 seconds
    retry: false,
  });
}

// List experiments hook
export function useExperiments(filters?: ExperimentFilters) {
  return useQuery({
    queryKey: experimentKeys.list(filters),
    queryFn: () => experimentsApi.list(filters),
    refetchInterval: (query) => {
      // Refetch more frequently if there are running experiments
      const data = query.state.data;
      if (data?.experiments.some((e) => e.status === "running")) {
        return 5000; // 5 seconds
      }
      return 30000; // 30 seconds
    },
  });
}

// Get single experiment hook
export function useExperiment(id: string) {
  return useQuery({
    queryKey: experimentKeys.detail(id),
    queryFn: () => experimentsApi.get(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === "running") {
        return 5000; // 5 seconds for running experiments
      }
      return false; // Don't auto-refetch for other statuses
    },
  });
}

// Create centralized experiment mutation
export function useCreateCentralizedExperiment() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: CreateCentralizedExperimentRequest) =>
      experimentsApi.createCentralized(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: experimentKeys.lists() });
      toast({
        title: "Experiment Created",
        description: "Your centralized experiment has been created successfully.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to Create Experiment",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

// Create federated experiment mutation
export function useCreateFederatedExperiment() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (data: CreateFederatedExperimentRequest) =>
      experimentsApi.createFederated(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: experimentKeys.lists() });
      toast({
        title: "Experiment Created",
        description: "Your federated experiment has been created successfully.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to Create Experiment",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

// Start experiment mutation
export function useStartExperiment() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (id: string) => experimentsApi.start(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: experimentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: experimentKeys.detail(data.id) });
      toast({
        title: "Experiment Started",
        description: "The experiment is now running.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to Start Experiment",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

// Complete experiment mutation
export function useCompleteExperiment() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: CompleteExperimentRequest }) =>
      experimentsApi.complete(id, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: experimentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: experimentKeys.detail(data.id) });
      toast({
        title: "Experiment Completed",
        description: "The experiment has been marked as completed.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to Complete Experiment",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

// Fail experiment mutation
export function useFailExperiment() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (id: string) => experimentsApi.fail(id),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: experimentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: experimentKeys.detail(data.id) });
      toast({
        title: "Experiment Failed",
        description: "The experiment has been marked as failed.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to Update Experiment",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

// Delete experiment mutation
export function useDeleteExperiment() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (id: string) => experimentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: experimentKeys.lists() });
      toast({
        title: "Experiment Deleted",
        description: "The experiment has been deleted successfully.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to Delete Experiment",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}
