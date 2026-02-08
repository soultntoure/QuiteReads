import { useMemo, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useExperiment, useExperiments } from "@/hooks/use-experiments";
import { useMetrics } from "@/hooks/use-metrics";
import { TypeBadge } from "@/components/TypeBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { PageLoader } from "@/components/LoadingSpinner";
import { PerformanceSection } from "@/components/comparison/PerformanceSection";
import { ScalabilitySection } from "@/components/comparison/ScalabilitySection";
import { TimeSection } from "@/components/comparison/TimeSection";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Star, AlertCircle } from "lucide-react";
import type { ExperimentResponse } from "@/types/experiment";

/**
 * Comparison page displaying multiple experiments side-by-side
 * with baseline-relative metrics and categorized infographic sections.
 */
export default function CompareExperiments() {
    const [searchParams] = useSearchParams();
    const idsParam = searchParams.get("ids") || "";
    const experimentIds = idsParam.split(",").filter(Boolean);

    // Baseline: first experiment by default, user can change
    const [baselineId, setBaselineId] = useState<string>(experimentIds[0] || "");

    // Fetch all experiments data
    const { data: experimentsData, isLoading } = useExperiments({});

    // Filter to only the selected experiments
    const experiments = useMemo(() => {
        if (!experimentsData?.experiments) return [];
        return experimentIds
            .map(id => experimentsData.experiments.find(e => e.id === id))
            .filter((e): e is ExperimentResponse => e !== undefined);
    }, [experimentsData, experimentIds]);

    // Check if we have any federated-to-federated comparison
    const allFederated = experiments.length >= 2 && experiments.every(e => e.type === "federated");
    const hasMixedTypes = experiments.some(e => e.type === "centralized") &&
        experiments.some(e => e.type === "federated");

    // Find baseline experiment
    const baselineExperiment = experiments.find(e => e.id === baselineId) || experiments[0];

    if (experimentIds.length < 2) {
        return (
            <div className="flex flex-col items-center justify-center py-12">
                <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
                <h2 className="text-2xl font-bold">Not Enough Experiments</h2>
                <p className="mt-2 text-muted-foreground">
                    Select at least 2 experiments to compare.
                </p>
                <Button className="mt-6" asChild>
                    <Link to="/experiments">Back to Experiments</Link>
                </Button>
            </div>
        );
    }

    if (isLoading) {
        return <PageLoader />;
    }

    if (experiments.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center py-12">
                <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
                <h2 className="text-2xl font-bold">Experiments Not Found</h2>
                <p className="mt-2 text-muted-foreground">
                    The experiments you're trying to compare don't exist.
                </p>
                <Button className="mt-6" asChild>
                    <Link to="/experiments">Back to Experiments</Link>
                </Button>
            </div>
        );
    }

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
            <div className="space-y-3">
                <h1 className="text-3xl font-bold tracking-tight">
                    Experiment Comparison
                </h1>
                <p className="text-muted-foreground">
                    Comparing {experiments.length} experiments
                    {hasMixedTypes && " (cross-type comparison)"}
                </p>
            </div>

            {/* Experiment Cards Overview */}
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Selected Experiments</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                        {experiments.map((exp) => (
                            <div
                                key={exp.id}
                                className={`relative rounded-lg border p-4 transition-all ${exp.id === baselineId
                                        ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                                        : "hover:border-muted-foreground/50"
                                    }`}
                            >
                                {exp.id === baselineId && (
                                    <div className="absolute -top-2 -right-2">
                                        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
                                            <Star className="h-3 w-3" />
                                        </div>
                                    </div>
                                )}
                                <div className="space-y-2">
                                    <div className="flex items-start justify-between gap-2">
                                        <h3 className="font-semibold truncate">{exp.name}</h3>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                        <TypeBadge type={exp.type} />
                                        <StatusBadge status={exp.status} />
                                    </div>
                                    {exp.id !== baselineId && (
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="w-full mt-2"
                                            onClick={() => setBaselineId(exp.id)}
                                        >
                                            <Star className="mr-2 h-3 w-3" />
                                            Make Baseline
                                        </Button>
                                    )}
                                    {exp.id === baselineId && (
                                        <p className="text-xs text-primary font-medium text-center mt-2">
                                            ⭐ Baseline
                                        </p>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Performance Section */}
            <PerformanceSection
                experiments={experiments}
                baselineId={baselineId}
            />

            {/* Scalability Section (only for federated-to-federated) */}
            {allFederated && (
                <ScalabilitySection
                    experiments={experiments}
                    baselineId={baselineId}
                />
            )}

            {/* Time Section */}
            <TimeSection
                experiments={experiments}
                baselineId={baselineId}
            />
        </div>
    );
}
