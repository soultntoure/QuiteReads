import { experimentsApi } from "@/api/experiments";
import { useQuery } from "@tanstack/react-query";
import { OverviewStats } from "@/components/analytics/OverviewStats";
import { ParadigmDistribution } from "@/components/analytics/ParadigmDistribution";
import { PerformanceComparison } from "@/components/analytics/PerformanceComparison";
import { DurationComparison } from "@/components/analytics/DurationComparison";
import { TopExperimentsTable } from "@/components/analytics/TopExperimentsTable";
import { FederatedInsights } from "@/components/analytics/FederatedInsights";
import { Loader2 } from "lucide-react";

export default function AnalyticsPage() {
    const { data, isLoading, isError } = useQuery({
        queryKey: ["experiments"],
        queryFn: () => experimentsApi.list(),
    });

    if (isLoading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin" />
            </div>
        );
    }

    if (isError || !data) {
        return (
            <div className="flex h-screen items-center justify-center text-red-500">
                Failed to load analytics data.
            </div>
        );
    }

    const experiments = data.experiments;

    return (
        <div className="space-y-6  p-6">
            <div>
                <h2 className="text-3xl font-bold tracking-tight">Analytics Dashboard</h2>
                <p className="text-muted-foreground">
                    Aggregate insights and performance metrics across all experiments.
                </p>
            </div>

            <OverviewStats experiments={experiments} />

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                <ParadigmDistribution experiments={experiments} />
                <PerformanceComparison experiments={experiments} />
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <DurationComparison experiments={experiments} />
                <TopExperimentsTable experiments={experiments} />
            </div>

            <FederatedInsights experiments={experiments} />
        </div>
    );
}
