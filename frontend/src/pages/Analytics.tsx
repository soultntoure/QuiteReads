import { useState } from "react";
import { useExperiments } from "@/hooks/use-experiments";
import { PageLoader } from "@/components/LoadingSpinner";
import {
    OverviewStats,
    ParadigmDistribution,
    PerformanceComparison,
    DurationComparison,
    TopExperimentsTable,
    FederatedInsights,
} from "@/components/analytics";

export default function Analytics() {
    const { data, isLoading } = useExperiments();
    const [activeSort, setActiveSort] = useState<string>("rmse");

    const experiments = data?.experiments ?? [];

    if (isLoading) {
        return <PageLoader />;
    }

    const handleCardClick = (sortBy: string) => {
        setActiveSort(sortBy);
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
                <p className="text-muted-foreground">
                    Aggregate insights across all experiments
                </p>
            </div>

            {/* Overview Stats - Clickable */}
            <OverviewStats
                experiments={experiments}
                loading={isLoading}
                onCardClick={handleCardClick}
                activeSort={activeSort}
            />

            {/* Charts Row */}
            <div className="grid gap-6 lg:grid-cols-2">
                <ParadigmDistribution experiments={experiments} />
                <PerformanceComparison experiments={experiments} />
            </div>

            {/* Duration Comparison */}
            <DurationComparison experiments={experiments} />

            {/* Top Experiments Table */}
            <TopExperimentsTable
                experiments={experiments}
                initialSort={activeSort}
                onSortChange={setActiveSort}
            />

            {/* Federated Insights - Collapsible */}
            <FederatedInsights experiments={experiments} />
        </div>
    );
}
