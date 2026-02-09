import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  useExperiment,
  useStartExperiment,
  useFailExperiment,
  useDeleteExperiment,
} from "@/hooks/use-experiments";
import { useTrainingStatus } from "@/hooks/use-training-status";
import { StatusBadge } from "@/components/StatusBadge";
import { TypeBadge } from "@/components/TypeBadge";
import { ConfigDisplay } from "@/components/ConfigDisplay";
import { ExperimentResultsTabs } from "@/components/ExperimentResultsTabs";
import { TrainingProgress } from "@/components/TrainingProgress";
import { PageLoader } from "@/components/LoadingSpinner";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { CompareCTA } from "@/components/CompareCTA";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Play, XCircle, Trash2, Calendar, Clock } from "lucide-react";
import { format } from "date-fns";

export default function ExperimentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [failDialogOpen, setFailDialogOpen] = useState(false);

  const { data: experiment, isLoading, isError } = useExperiment(id!);
  const startExperiment = useStartExperiment();
  const failExperiment = useFailExperiment();
  const deleteExperiment = useDeleteExperiment();

  // Poll training status when experiment is running
  const isRunning = experiment?.status === "running";
  const { data: trainingStatus } = useTrainingStatus(id!, isRunning);

  if (isLoading) {
    return <PageLoader />;
  }

  if (isError || !experiment) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <h2 className="text-2xl font-bold">Experiment Not Found</h2>
        <p className="mt-2 text-muted-foreground">
          The experiment you're looking for doesn't exist or has been deleted.
        </p>
        <Button className="mt-6" asChild>
          <Link to="/experiments">Back to Experiments</Link>
        </Button>
      </div>
    );
  }

  const handleStart = () => {
    startExperiment.mutate(experiment.id);
  };

  const handleFail = () => {
    failExperiment.mutate(experiment.id, {
      onSuccess: () => setFailDialogOpen(false),
    });
  };

  const handleDelete = () => {
    deleteExperiment.mutate(experiment.id, {
      onSuccess: () => {
        navigate("/experiments");
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <Button variant="ghost" size="sm" asChild>
        <Link to="/experiments">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Experiments
        </Link>
      </Button>

      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight">{experiment.name}</h1>
            <TypeBadge type={experiment.type} />
            <StatusBadge status={experiment.status} />
          </div>

          <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              <span>Created {format(new Date(experiment.created_at), "MMM d, yyyy 'at' h:mm a")}</span>
            </div>
            {experiment.completed_at && (
              <div className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                <span>Completed {format(new Date(experiment.completed_at), "MMM d, yyyy 'at' h:mm a")}</span>
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          {experiment.status === "pending" && (
            <Button onClick={handleStart} disabled={startExperiment.isPending}>
              <Play className="mr-2 h-4 w-4" />
              Start Experiment
            </Button>
          )}

          {experiment.status === "running" && (
            <Button
              variant="destructive"
              onClick={() => setFailDialogOpen(true)}
            >
              <XCircle className="mr-2 h-4 w-4" />
              Mark as Failed
            </Button>
          )}

          <Button
            variant="outline"
            onClick={() => setDeleteDialogOpen(true)}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Configuration */}
      <ConfigDisplay experiment={experiment} />

      {/* Training Progress (for running experiments) */}
      {experiment.status === "running" && (
        <TrainingProgress
          status={trainingStatus}
          experimentType={experiment.type}
        />
      )}

      {/* Experiment Results (Metrics, Progress, History tabs) */}
      <ExperimentResultsTabs
        experimentId={experiment.id}
        experimentType={experiment.type}
        metrics={experiment.metrics}
      />

      {/* Fail Confirmation Dialog */}
      <ConfirmDialog
        open={failDialogOpen}
        onOpenChange={setFailDialogOpen}
        title="Mark Experiment as Failed"
        description="Are you sure you want to mark this experiment as failed? This will stop tracking the experiment."
        confirmLabel="Mark as Failed"
        variant="destructive"
        isLoading={failExperiment.isPending}
        onConfirm={handleFail}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Experiment"
        description="Are you sure you want to delete this experiment? This action cannot be undone and all associated metrics will be lost."
        confirmLabel="Delete"
        variant="destructive"
        isLoading={deleteExperiment.isPending}
        onConfirm={handleDelete}
      />

      {/* Compare CTA for completed experiments */}
      {experiment.status === "completed" && (
        <CompareCTA
          experimentId={experiment.id}
          experimentName={experiment.name}
        />
      )}
    </div>
  );
}
