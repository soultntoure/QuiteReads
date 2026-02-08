import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ExperimentResponse } from "@/types/experiment";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";

interface PerformanceComparisonProps {
    experiments: ExperimentResponse[];
}

export function PerformanceComparison({ experiments }: PerformanceComparisonProps) {
    const completed = experiments.filter(
        (e) => e.status === "completed" && e.metrics
    );

    const centralized = completed.filter((e) => e.type === "centralized");
    const federated = completed.filter((e) => e.type === "federated");

    const getAvg = (exps: ExperimentResponse[], metric: "final_rmse" | "final_mae") => {
        if (exps.length === 0) return 0;
        return (
            exps.reduce((sum, e) => sum + (e.metrics[metric] || 0), 0) / exps.length
        );
    };

    const avgRmseC = getAvg(centralized, "final_rmse");
    const avgRmseF = getAvg(federated, "final_rmse");
    const avgMaeC = getAvg(centralized, "final_mae");
    const avgMaeF = getAvg(federated, "final_mae");

    const diffRmse =
        avgRmseC > 0 ? ((avgRmseF - avgRmseC) / avgRmseC) * 100 : 0;

    // Improvement logic: Lower RMSE is better.
    // If diff is negative, it means Federated is lower (better).
    const isBetter = diffRmse < 0;
    const improvement = Math.abs(diffRmse);

    const data = [
        {
            name: "RMSE",
            Centralized: avgRmseC,
            Federated: avgRmseF,
        },
        {
            name: "MAE",
            Centralized: avgMaeC,
            Federated: avgMaeF,
        },
    ];

    return (
        <Card className="col-span-1 lg:col-span-2">
            <CardHeader>
                <CardTitle>Performance Comparison</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="mb-6 flex items-center justify-between rounded-lg border p-4 shadow-sm">
                    <div>
                        <h4 className="text-sm font-medium text-muted-foreground">
                            Federated vs Centralized (RMSE)
                        </h4>
                        <div className="mt-2 flex items-baseline space-x-2">
                            <span className="text-2xl font-bold">
                                {avgRmseF > 0 ? avgRmseF.toFixed(4) : "N/A"}
                            </span>
                            <span className="text-sm text-muted-foreground">vs</span>
                            <span className="text-sm font-medium">
                                {avgRmseC > 0 ? avgRmseC.toFixed(4) : "N/A"}
                            </span>
                        </div>
                    </div>
                    {avgRmseC > 0 && avgRmseF > 0 && (
                        <div
                            className={`flex items-center rounded-full px-3 py-1 text-sm font-medium ${isBetter
                                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                                    : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                                }`}
                        >
                            {isBetter ? (
                                <ArrowDown className="mr-1 h-4 w-4" />
                            ) : (
                                <ArrowUp className="mr-1 h-4 w-4" />
                            )}
                            {isBetter ? "Federated is " : "Centralized is "}
                            {improvement.toFixed(1)}% better
                        </div>
                    )}
                </div>

                <div className="h-[300px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                            data={data}
                            margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" vertical={false} />
                            <XAxis dataKey="name" />
                            <YAxis />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: "hsl(var(--card))",
                                    borderColor: "hsl(var(--border))",
                                }}
                                itemStyle={{ color: "hsl(var(--foreground))" }}
                            />
                            <Legend />
                            <Bar dataKey="Centralized" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="Federated" fill="#10b981" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
