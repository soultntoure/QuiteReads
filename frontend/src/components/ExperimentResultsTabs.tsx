import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { MetricsBarChart } from "@/components/MetricsBarChart";
import { ProgressChart } from "@/components/ProgressChart";
import type { ExperimentType, ExperimentMetricsSchema } from "@/types/experiment";
import { TrendingDown, LineChart } from "lucide-react";

interface ExperimentResultsTabsProps {
    experimentId: string;
    experimentType: ExperimentType;
    metrics: ExperimentMetricsSchema;
}

type TabValue = "metrics" | "progress";

export function ExperimentResultsTabs({
    experimentId,
    experimentType,
    metrics,
}: ExperimentResultsTabsProps) {
    const [activeTab, setActiveTab] = useState<TabValue>("metrics");

    return (
        <Card className="overflow-hidden">
            <CardHeader className="pb-0">
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="text-xl">Experiment Results</CardTitle>
                        <CardDescription className="mt-1">
                            {experimentType === "centralized"
                                ? "Per-epoch training metrics"
                                : "Per-round federated learning metrics"}
                        </CardDescription>
                    </div>
                </div>
            </CardHeader>

            <CardContent className="pt-4">
                <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabValue)}>
                    <TabsList className="grid w-full grid-cols-2 mb-6">
                        <TabsTrigger value="metrics" className="gap-2">
                            <TrendingDown className="h-4 w-4" />
                            Metrics
                        </TabsTrigger>
                        <TabsTrigger value="progress" className="gap-2">
                            <LineChart className="h-4 w-4" />
                            Progress
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="metrics" className="mt-0 space-y-6">
                        <MetricsBarChart metrics={metrics} />
                    </TabsContent>

                    <TabsContent value="progress" className="mt-0">
                        <ProgressChart
                            experimentId={experimentId}
                            experimentType={experimentType}
                        />
                    </TabsContent>
                </Tabs>
            </CardContent>
        </Card>
    );
}
