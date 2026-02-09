import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ExperimentResponse } from "@/types/experiment";
import { Badge } from "@/components/ui/badge";

interface AnalyticsInfographicProps {
    experiments: ExperimentResponse[];
}

/**
 * Analytics Infographic Component
 * A specialized component designed to create a beautiful, print-ready infographic
 * that summarizes all analytics data. This component is used primarily for PDF export.
 */
export function AnalyticsInfographic({ experiments }: AnalyticsInfographicProps) {
    const completed = experiments.filter((e) => e.status === "completed" && e.metrics);
    const centralized = completed.filter((e) => e.type === "centralized");
    const federated = completed.filter((e) => e.type === "federated");

    const getAvg = (exps: ExperimentResponse[], metric: "final_rmse" | "final_mae" | "training_time_seconds") => {
        if (exps.length === 0) return 0;
        return exps.reduce((sum, e) => sum + (e.metrics?.[metric] || 0), 0) / exps.length;
    };

    const totalExperiments = experiments.length;
    const avgRmseC = getAvg(centralized, "final_rmse");
    const avgRmseF = getAvg(federated, "final_rmse");
    const avgMaeC = getAvg(centralized, "final_mae");
    const avgMaeF = getAvg(federated, "final_mae");
    const avgTimeC = getAvg(centralized, "training_time_seconds");
    const avgTimeF = getAvg(federated, "training_time_seconds");

    const topExperiments = [...completed]
        .sort((a, b) => (a.metrics?.final_rmse || 0) - (b.metrics?.final_rmse || 0))
        .slice(0, 5);

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8 dark:from-slate-900 dark:to-slate-800">
            <div className="mx-auto max-w-5xl space-y-6">
                {/* Header */}
                <div className="text-center">
                    <h1 className="text-4xl font-bold tracking-tight text-slate-900 dark:text-white">
                        Analytics Dashboard Report
                    </h1>
                    <p className="mt-2 text-lg text-slate-600 dark:text-slate-300">
                        FedRec Experiment Analytics · {new Date().toLocaleDateString()}
                    </p>
                </div>

                {/* Overview Stats */}
                <div className="grid grid-cols-4 gap-4">
                    <Card className="bg-gradient-to-br from-blue-500 to-blue-600 text-white">
                        <CardContent className="p-6 text-center">
                            <div className="text-4xl font-bold">{totalExperiments}</div>
                            <div className="mt-1 text-sm font-medium">Total Experiments</div>
                        </CardContent>
                    </Card>
                    <Card className="bg-gradient-to-br from-green-500 to-green-600 text-white">
                        <CardContent className="p-6 text-center">
                            <div className="text-4xl font-bold">{completed.length}</div>
                            <div className="mt-1 text-sm font-medium">Completed</div>
                        </CardContent>
                    </Card>
                    <Card className="bg-gradient-to-br from-purple-500 to-purple-600 text-white">
                        <CardContent className="p-6 text-center">
                            <div className="text-4xl font-bold">{centralized.length}</div>
                            <div className="mt-1 text-sm font-medium">Centralized</div>
                        </CardContent>
                    </Card>
                    <Card className="bg-gradient-to-br from-pink-500 to-pink-600 text-white">
                        <CardContent className="p-6 text-center">
                            <div className="text-4xl font-bold">{federated.length}</div>
                            <div className="mt-1 text-sm font-medium">Federated</div>
                        </CardContent>
                    </Card>
                </div>

                {/* Performance Metrics */}
                <div className="grid grid-cols-2 gap-6">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-xl">Average Performance - RMSE</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <span className="font-medium">Centralized</span>
                                    <span className="rounded-full bg-blue-100 px-4 py-1 text-lg font-bold text-blue-900 dark:bg-blue-900 dark:text-blue-100">
                                        {avgRmseC > 0 ? avgRmseC.toFixed(4) : "N/A"}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="font-medium">Federated</span>
                                    <span className="rounded-full bg-green-100 px-4 py-1 text-lg font-bold text-green-900 dark:bg-green-900 dark:text-green-100">
                                        {avgRmseF > 0 ? avgRmseF.toFixed(4) : "N/A"}
                                    </span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="text-xl">Average Performance - MAE</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <span className="font-medium">Centralized</span>
                                    <span className="rounded-full bg-blue-100 px-4 py-1 text-lg font-bold text-blue-900 dark:bg-blue-900 dark:text-blue-100">
                                        {avgMaeC > 0 ? avgMaeC.toFixed(4) : "N/A"}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="font-medium">Federated</span>
                                    <span className="rounded-full bg-green-100 px-4 py-1 text-lg font-bold text-green-900 dark:bg-green-900 dark:text-green-100">
                                        {avgMaeF > 0 ? avgMaeF.toFixed(4) : "N/A"}
                                    </span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Training Time */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-xl">Average Training Time (seconds)</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="rounded-lg border-2 border-blue-300 bg-blue-50 p-4 text-center dark:border-blue-700 dark:bg-blue-950">
                                <div className="text-sm font-medium text-blue-900 dark:text-blue-100">Centralized</div>
                                <div className="mt-2 text-3xl font-bold text-blue-700 dark:text-blue-300">
                                    {avgTimeC > 0 ? avgTimeC.toFixed(2) : "N/A"}
                                </div>
                            </div>
                            <div className="rounded-lg border-2 border-green-300 bg-green-50 p-4 text-center dark:border-green-700 dark:bg-green-950">
                                <div className="text-sm font-medium text-green-900 dark:text-green-100">Federated</div>
                                <div className="mt-2 text-3xl font-bold text-green-700 dark:text-green-300">
                                    {avgTimeF > 0 ? avgTimeF.toFixed(2) : "N/A"}
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Top 5 Experiments */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-xl">Top 5 Experiments by RMSE</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            {topExperiments.map((exp, idx) => (
                                <div
                                    key={exp.id}
                                    className="flex items-center justify-between rounded-lg border p-3"
                                >
                                    <div className="flex items-center space-x-3">
                                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-sm font-bold dark:bg-slate-700">
                                            {idx + 1}
                                        </div>
                                        <span className="font-medium">{exp.name}</span>
                                        <Badge variant={exp.type === "federated" ? "secondary" : "default"}>
                                            {exp.type}
                                        </Badge>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-lg font-bold">
                                            {exp.metrics?.final_rmse?.toFixed(4) || "N/A"}
                                        </div>
                                        <div className="text-xs text-muted-foreground">RMSE</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                {/* Footer */}
                <div className="rounded-lg border bg-white/50 p-4 text-center text-sm text-slate-600 dark:bg-slate-800/50 dark:text-slate-400">
                    Generated by FedRec Dashboard Analytics System
                </div>
            </div>
        </div>
    );
}
