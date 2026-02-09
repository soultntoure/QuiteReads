import { experimentsApi } from "@/api/experiments";
import { useQuery } from "@tanstack/react-query";
import { OverviewStats } from "@/components/analytics/OverviewStats";
import { ParadigmDistribution } from "@/components/analytics/ParadigmDistribution";
import { PerformanceComparison } from "@/components/analytics/PerformanceComparison";
import { DurationComparison } from "@/components/analytics/DurationComparison";
import { TopExperimentsTable } from "@/components/analytics/TopExperimentsTable";
import { FederatedInsights } from "@/components/analytics/FederatedInsights";
import { AnalyticsInfographic } from "@/components/analytics/AnalyticsInfographic";
import { Button } from "@/components/ui/button";
import { Loader2, FileDown } from "lucide-react";
import { generatePdfReport } from "@/lib/export-utils";
import { useState } from "react";
import { createPortal } from "react-dom";

export default function AnalyticsPage() {
    const [isExporting, setIsExporting] = useState(false);
    const [showInfographic, setShowInfographic] = useState(false);

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

    const handleExportReport = async () => {
        setIsExporting(true);
        setShowInfographic(true);

        // Wait for the infographic to render
        await new Promise((resolve) => setTimeout(resolve, 500));

        try {
            await generatePdfReport(["analytics-infographic"], "analytics-report");
        } catch (error) {
            console.error("Failed to export report:", error);
        } finally {
            setIsExporting(false);
            setShowInfographic(false);
        }
    };

    return (
        <div className="space-y-6  p-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Analytics Dashboard</h2>
                    <p className="text-muted-foreground">
                        Aggregate insights and performance metrics across all experiments.
                    </p>
                </div>
                <Button onClick={handleExportReport} disabled={isExporting}>
                    {isExporting ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Exporting...
                        </>
                    ) : (
                        <>
                            <FileDown className="mr-2 h-4 w-4" />
                            Export Report
                        </>
                    )}
                </Button>
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

            {/* Hidden infographic for PDF export using portal */}
            {showInfographic &&
                createPortal(
                    <div
                        id="analytics-infographic"
                        style={{
                            position: "fixed",
                            top: "-9999px",
                            left: "-9999px",
                            width: "1200px",
                        }}
                    >
                        <AnalyticsInfographic experiments={experiments} />
                    </div>,
                    document.body
                )}
        </div>
    );
}
