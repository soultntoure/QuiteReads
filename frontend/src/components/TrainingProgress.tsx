import type { TrainingStatus } from "@/types/experiment";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, Circle, Loader2, AlertCircle } from "lucide-react";

// Step definitions matching backend
const CENTRALIZED_STEPS = [
    { key: "loading_data", label: "Loading dataset" },
    { key: "initializing", label: "Initializing model" },
    { key: "training", label: "Training model" },
    { key: "validating", label: "Validating results" },
    { key: "saving", label: "Saving metrics" },
    { key: "done", label: "Completed" },
];

const FEDERATED_STEPS = [
    { key: "loading_data", label: "Loading dataset" },
    { key: "initializing", label: "Setting up simulation" },
    { key: "training", label: "Running federated rounds" },
    { key: "aggregating", label: "Aggregating results" },
    { key: "saving", label: "Saving metrics" },
    { key: "done", label: "Completed" },
];

interface TrainingProgressProps {
    status: TrainingStatus | null | undefined;
    experimentType: "centralized" | "federated";
}

export function TrainingProgress({ status, experimentType }: TrainingProgressProps) {
    const steps = experimentType === "centralized" ? CENTRALIZED_STEPS : FEDERATED_STEPS;
    const currentStepNumber = status?.step_number ?? 0;

    // Calculate overall progress percentage
    const progressPercent = status ? Math.round((currentStepNumber / status.total_steps) * 100) : 0;

    // Get epoch/round progress for display
    const getSubProgress = () => {
        if (status?.step !== "training") return null;

        if (experimentType === "centralized" && status.current_epoch && status.total_epochs) {
            return {
                current: status.current_epoch,
                total: status.total_epochs,
                label: "Epoch",
            };
        }

        if (experimentType === "federated" && status.current_round && status.total_rounds) {
            return {
                current: status.current_round,
                total: status.total_rounds,
                label: "Round",
            };
        }

        return null;
    };

    const subProgress = getSubProgress();

    // Error state
    if (status?.status === "failed") {
        return (
            <Card className="border-destructive">
                <CardHeader>
                    <div className="flex items-center gap-3">
                        <div className="rounded-lg bg-destructive/10 p-2">
                            <AlertCircle className="h-5 w-5 text-destructive" />
                        </div>
                        <div>
                            <CardTitle>Training Failed</CardTitle>
                            <CardDescription>{status.error || "An error occurred during training."}</CardDescription>
                        </div>
                    </div>
                </CardHeader>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center gap-3">
                    <div className="rounded-lg bg-primary/10 p-2">
                        <Loader2 className="h-5 w-5 animate-spin text-primary" />
                    </div>
                    <div className="flex-1">
                        <CardTitle>Training in Progress</CardTitle>
                        <CardDescription>{status?.message || "Starting..."}</CardDescription>
                    </div>
                    <div className="text-sm font-medium text-muted-foreground">
                        {progressPercent}%
                    </div>
                </div>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Overall progress bar */}
                <Progress value={progressPercent} className="h-2" />

                {/* Sub-progress for epoch/round */}
                {subProgress && (
                    <div className="rounded-lg border bg-muted/30 p-4">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium">
                                {subProgress.label} {subProgress.current} of {subProgress.total}
                            </span>
                            <span className="text-sm text-muted-foreground">
                                {Math.round((subProgress.current / subProgress.total) * 100)}%
                            </span>
                        </div>
                        <Progress
                            value={(subProgress.current / subProgress.total) * 100}
                            className="h-1.5"
                        />
                    </div>
                )}

                {/* Step list */}
                <div className="space-y-3">
                    {steps.map((step, idx) => {
                        const stepNum = idx + 1;
                        const isDone = currentStepNumber > stepNum;
                        const isCurrent = currentStepNumber === stepNum;
                        const isPending = currentStepNumber < stepNum;

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
                                                : isPending
                                                    ? "text-sm text-muted-foreground"
                                                    : "text-sm"
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
    );
}
