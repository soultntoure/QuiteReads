import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";
import {
  useDatasetMetadata,
  usePreprocessingStatus,
  useUploadDataset,
  useRemoveDataset,
  datasetKeys,
} from "@/hooks/use-dataset";
import type { DatasetMetadata, PreprocessingStatus } from "@/types/dataset";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Slider } from "@/components/ui/slider";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { SummaryCard } from "@/components/SummaryCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import {
  Upload,
  CheckCircle2,
  Circle,
  Loader2,
  BarChart3,
  Users,
  BookOpen,
  Grid3X3,
  FlaskConical,
  RotateCcw,
  FileText,
  Info,
  Trash2,
} from "lucide-react";

// =============================================================================
// Types
// =============================================================================

type ViewState = "loading" | "upload" | "processing" | "failed" | "loaded";

// =============================================================================
// Form Schema
// =============================================================================

const uploadSchema = z.object({
  min_ratings: z.coerce.number().int().min(1).max(100),
  val_ratio: z.number().min(0).max(0.4),
  test_ratio: z.number().min(0).max(0.4),
  seed: z.coerce.number().int().min(0),
});

type UploadFormValues = z.infer<typeof uploadSchema>;

// =============================================================================
// Step Definitions
// =============================================================================

const STEPS = [
  { key: "uploading", label: "Uploading file" },
  { key: "loading", label: "Loading raw data" },
  { key: "filtering", label: "Filtering sparse users & items" },
  { key: "mapping", label: "Creating ID mappings" },
  { key: "splitting", label: "Creating train/val/test splits" },
  { key: "saving", label: "Saving processed artifacts" },
];

// =============================================================================
// Upload View
// =============================================================================

function UploadView({
  onUpload,
  isPending,
}: {
  onUpload: (file: File, values: UploadFormValues) => void;
  isPending: boolean;
}) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const form = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      min_ratings: 20,
      val_ratio: 0.1,
      test_ratio: 0.2,
      seed: 42,
    },
  });

  const onSubmit = (values: UploadFormValues) => {
    if (!selectedFile) return;
    onUpload(selectedFile, values);
  };

  const valRatio = form.watch("val_ratio");
  const testRatio = form.watch("test_ratio");
  const trainRatio = Math.max(0, 1 - valRatio - testRatio);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dataset</h1>
        <p className="text-muted-foreground">
          Upload a Goodreads JSON Lines file to preprocess for experiments
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Upload className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle>Upload Dataset</CardTitle>
              <CardDescription>
                JSON Lines format with user_id, book_id, rating fields
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              {/* File Input */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Dataset File</label>
                <div
                  className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-muted-foreground/25 p-8 transition-colors hover:border-primary/50"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <FileText className="mb-2 h-8 w-8 text-muted-foreground" />
                  {selectedFile ? (
                    <div className="text-center">
                      <p className="text-sm font-medium">{selectedFile.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB
                      </p>
                    </div>
                  ) : (
                    <div className="text-center">
                      <p className="text-sm text-muted-foreground">
                        Click to select a .json or .jsonl file
                      </p>
                    </div>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json,.jsonl"
                  className="hidden"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                />
              </div>

              {/* Preprocessing Config */}
              <div className="space-y-4 rounded-lg border p-4">
                <h3 className="text-sm font-semibold">Preprocessing Settings</h3>

                <FormField
                  control={form.control}
                  name="min_ratings"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Minimum Ratings per User/Item</FormLabel>
                      <FormControl>
                        <Input type="number" min={1} max={100} {...field} />
                      </FormControl>
                      <FormDescription>
                        Users and items with fewer ratings are removed (default: 20)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="val_ratio"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Validation Ratio: {(field.value * 100).toFixed(0)}%</FormLabel>
                      <FormControl>
                        <Slider
                          min={0}
                          max={0.4}
                          step={0.05}
                          value={[field.value]}
                          onValueChange={([val]) => field.onChange(val)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="test_ratio"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Test Ratio: {(field.value * 100).toFixed(0)}%</FormLabel>
                      <FormControl>
                        <Slider
                          min={0}
                          max={0.4}
                          step={0.05}
                          value={[field.value]}
                          onValueChange={([val]) => field.onChange(val)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <p className="text-xs text-muted-foreground">
                  Train: {(trainRatio * 100).toFixed(0)}% | Val: {(valRatio * 100).toFixed(0)}% |
                  Test: {(testRatio * 100).toFixed(0)}%
                </p>

                <FormField
                  control={form.control}
                  name="seed"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Random Seed</FormLabel>
                      <FormControl>
                        <Input type="number" min={0} {...field} />
                      </FormControl>
                      <FormDescription>For reproducibility</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="flex justify-end">
                <Button type="submit" disabled={!selectedFile || isPending}>
                  {isPending && <LoadingSpinner size="sm" className="mr-2" />}
                  Process Dataset
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// Processing View
// =============================================================================

function ProcessingView({ status }: { status?: PreprocessingStatus | null }) {
  const currentStep = status?.step_number ?? 0;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dataset</h1>
        <p className="text-muted-foreground">Processing your dataset...</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
            </div>
            <div>
              <CardTitle>Preprocessing in Progress</CardTitle>
              <CardDescription>{status?.message || "Starting..."}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {STEPS.map((step, idx) => {
              const stepNum = idx + 1;
              const isDone = currentStep > stepNum;
              const isCurrent = currentStep === stepNum;

              return (
                <div key={step.key} className="flex items-center gap-3">
                  {isDone ? (
                    <CheckCircle2 className="h-5 w-5 shrink-0 text-green-500" />
                  ) : isCurrent ? (
                    <Loader2 className="h-5 w-5 shrink-0 animate-spin text-primary" />
                  ) : (
                    <Circle className="h-5 w-5 shrink-0 text-muted-foreground/40" />
                  )}
                  <span
                    className={
                      isDone
                        ? "text-sm text-muted-foreground line-through"
                        : isCurrent
                          ? "text-sm font-medium"
                          : "text-sm text-muted-foreground"
                    }
                  >
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// Failed View
// =============================================================================

function FailedView({
  error,
  onRetry,
}: {
  error?: string | null;
  onRetry: () => void;
}) {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dataset</h1>
        <p className="text-muted-foreground">Preprocessing failed</p>
      </div>

      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">Preprocessing Failed</CardTitle>
          <CardDescription>{error || "An unknown error occurred."}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={onRetry} variant="outline">
            <RotateCcw className="mr-2 h-4 w-4" />
            Try Again
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

// =============================================================================
// Loaded View (Stats)
// =============================================================================

function LoadedView({
  metadata,
  onReupload,
  onRemove,
}: {
  metadata: DatasetMetadata;
  onReupload: () => void;
  onRemove: () => void;
}) {
  const navigate = useNavigate();
  const stats = metadata.statistics;

  if (!stats) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dataset</h1>
          <p className="text-muted-foreground">
            Preprocessed and ready for experiments
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard
          title="Total Interactions"
          value={stats.filtered_interactions.toLocaleString()}
          icon={BarChart3}
        />
        <SummaryCard
          title="Users"
          value={stats.filtered_users.toLocaleString()}
          icon={Users}
        />
        <SummaryCard
          title="Items (Books)"
          value={stats.filtered_items.toLocaleString()}
          icon={BookOpen}
        />
        <SummaryCard
          title="Sparsity"
          value={stats.sparsity_percent}
          icon={Grid3X3}
        />
      </div>

      {/* Before / After Comparison Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Before vs After Filtering</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Metric</TableHead>
                <TableHead className="text-right">Before</TableHead>
                <TableHead className="text-right">After</TableHead>
                <TableHead className="text-right">Change</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell className="font-medium">Interactions</TableCell>
                <TableCell className="text-right">
                  {stats.original_interactions.toLocaleString()}
                </TableCell>
                <TableCell className="text-right">
                  {stats.filtered_interactions.toLocaleString()}
                </TableCell>
                <TableCell className="text-right text-muted-foreground">
                  {stats.retention_rate} retained
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">Users</TableCell>
                <TableCell className="text-right">
                  {stats.original_users.toLocaleString()}
                </TableCell>
                <TableCell className="text-right">
                  {stats.filtered_users.toLocaleString()}
                </TableCell>
                <TableCell className="text-right text-muted-foreground">
                  {((stats.filtered_users / stats.original_users) * 100).toFixed(1)}% retained
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell className="font-medium">Items (Books)</TableCell>
                <TableCell className="text-right">
                  {stats.original_items.toLocaleString()}
                </TableCell>
                <TableCell className="text-right">
                  {stats.filtered_items.toLocaleString()}
                </TableCell>
                <TableCell className="text-right text-muted-foreground">
                  {((stats.filtered_items / stats.original_items) * 100).toFixed(1)}% retained
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Preprocessing Notes */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Info className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-lg">Preprocessing Notes</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Steps Applied</p>
              <ol className="mt-1 list-inside list-decimal space-y-1 text-sm">
                <li>Removed implicit ratings (rating = 0)</li>
                <li>Iteratively filtered sparse users/items</li>
                <li>Created contiguous ID mappings</li>
                <li>Split into train/val/test sets</li>
              </ol>
            </div>
            <div className="space-y-2">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Configuration</p>
                <p className="text-sm">
                  Min ratings: {metadata.config?.min_user_ratings ?? "N/A"}
                </p>
                <p className="text-sm">
                  Splits: {((metadata.config?.val_ratio ?? 0) * 100).toFixed(0)}% val /{" "}
                  {((metadata.config?.test_ratio ?? 0) * 100).toFixed(0)}% test
                </p>
                <p className="text-sm">Seed: {metadata.config?.random_seed ?? "N/A"}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Filter Iterations</p>
                <p className="text-sm">{metadata.filter_iterations ?? "N/A"} iterations to converge</p>
              </div>
            </div>
            <div className="space-y-2">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Split Sizes</p>
                <p className="text-sm">Train: {metadata.train_size?.toLocaleString() ?? "N/A"}</p>
                <p className="text-sm">Validation: {metadata.val_size?.toLocaleString() ?? "N/A"}</p>
                <p className="text-sm">Test: {metadata.test_size?.toLocaleString() ?? "N/A"}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground">Rating Stats</p>
                <p className="text-sm">
                  Mean: {stats.rating_mean.toFixed(2)} | Std: {stats.rating_std.toFixed(2)}
                </p>
                <p className="text-sm">
                  Range: {stats.rating_min} - {stats.rating_max}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* CTA Buttons */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button onClick={() => navigate("/experiments/new/centralized")} size="lg">
          <FlaskConical className="mr-2 h-4 w-4" />
          Create Experiment
        </Button>
        <Button variant="outline" size="lg" onClick={onReupload}>
          <RotateCcw className="mr-2 h-4 w-4" />
          Re-upload Dataset
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" size="lg">
              <Trash2 className="mr-2 h-4 w-4" />
              Remove Dataset
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Remove Dataset?</AlertDialogTitle>
              <AlertDialogDescription>
                This will delete all processed data, splits, and metadata.
                You will need to upload and process a dataset again before running experiments.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={onRemove}>Remove</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function DatasetPage() {
  const queryClient = useQueryClient();
  const { data: metadata, isLoading: metaLoading } = useDatasetMetadata();
  const uploadMutation = useUploadDataset();
  const removeMutation = useRemoveDataset();

  const [viewState, setViewState] = useState<ViewState>("loading");

  const { data: status } = usePreprocessingStatus(viewState === "processing");

  // Determine initial view state from server data
  useEffect(() => {
    if (metaLoading) return;

    if (metadata?.is_loaded) {
      setViewState("loaded");
    } else {
      // Not loaded yet — check if server is mid-processing
      setViewState("processing");
    }
  }, [metaLoading, metadata?.is_loaded]);

  // React to preprocessing status changes
  useEffect(() => {
    if (!status) return;

    if (status.status === "completed") {
      queryClient.invalidateQueries({ queryKey: datasetKeys.metadata() });
      setViewState("loaded");
    } else if (status.status === "failed") {
      setViewState("failed");
    } else if (status.status === "idle" && viewState === "processing") {
      // Server is not processing and no dataset — show upload
      if (!metadata?.is_loaded) {
        setViewState("upload");
      }
    }
  }, [status?.status, queryClient, viewState, metadata?.is_loaded]);

  const handleUpload = (file: File, values: UploadFormValues) => {
    setViewState("processing");
    // Clear stale metadata cache immediately so old data can't trigger LoadedView
    queryClient.setQueryData(datasetKeys.metadata(), null);
    uploadMutation.mutate({ file, config: values });
  };

  const handleRemove = () => {
    removeMutation.mutate(undefined, {
      onSuccess: () => setViewState("upload"),
    });
  };

  switch (viewState) {
    case "loading":
      return (
        <div className="flex items-center justify-center py-20">
          <LoadingSpinner />
        </div>
      );

    case "failed":
      return <FailedView error={status?.error} onRetry={() => setViewState("upload")} />;

    case "processing":
      return <ProcessingView status={status} />;

    case "loaded":
      return metadata ? (
        <LoadedView
          metadata={metadata}
          onReupload={() => setViewState("upload")}
          onRemove={handleRemove}
        />
      ) : (
        <div className="flex items-center justify-center py-20">
          <LoadingSpinner />
        </div>
      );

    case "upload":
    default:
      return <UploadView onUpload={handleUpload} isPending={uploadMutation.isPending} />;
  }
}
