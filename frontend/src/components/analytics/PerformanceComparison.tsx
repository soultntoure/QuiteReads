import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { ArrowUp, ArrowDown, Minus } from "lucide-react";
import { PARADIGM_COLORS } from "./OverviewStats";
import type { ExperimentResponse as Experiment } from "@/types/experiment";

interface PerformanceComparisonProps {
    experiments: Experiment[];
}

function calculateAvg(values: number[]): number | null {
    if (values.length === 0) return null;
    return values.reduce((a, b) => a + b, 0) / values.length;
}

function calculateMedian(values: number[]): number | null {
    if (values.length === 0) return null;
    const sorted = [...values].sort((a, b) => a - b);
    return sorted[Math.floor(sorted.length / 2)];
}

interface ComparisonRowProps {
    metric: string;
    centralizedValue: number | null;
    federatedValue: number | null;
    lowerIsBetter?: boolean;
}

function ComparisonRow({ metric, centralizedValue, federatedValue, lowerIsBetter = true }: ComparisonRowProps) {
    const formatValue = (v: number | null) => v?.toFixed(4) ?? "-";

    let percentDiff: number | null = null;
    let winner: "centralized" | "federated" | "tie" | null = null;

    if (centralizedValue != null && federatedValue != null) {
        const diff = ((federatedValue - centralizedValue) / centralizedValue) * 100;
        percentDiff = Math.abs(diff);

        if (Math.abs(diff) < 1) {
            winner = "tie";
        } else if (lowerIsBetter) {
            winner = diff < 0 ? "federated" : "centralized";
        } else {
            winner = diff > 0 ? "federated" : "centralized";
        }
    }

    return (
        <tr className="border-b">
            <td className="py-3 font-medium">{metric}</td>
            <td className={`py-3 text-center ${winner === "centralized" ? "bg-blue-50 dark:bg-blue-900/20" : ""}`}>
                {formatValue(centralizedValue)}
            </td>
            <td className={`py-3 text-center ${winner === "federated" ? "bg-emerald-50 dark:bg-emerald-900/20" : ""}`}>
                {formatValue(federatedValue)}
            </td>
            <td className="py-3 text-center">
                {winner === "tie" && (
                    <span className="inline-flex items-center gap-1 text-muted-foreground">
                        <Minus className="h-4 w-4" />
                        Similar
                    </span>
                )}
                {winner === "centralized" && (
                    <span className="inline-flex items-center gap-1 text-blue-600">
                        <ArrowUp className="h-4 w-4" />
                        Centralized {percentDiff?.toFixed(1)}% better
                    </span>
                )}
                {winner === "federated" && (
                    <span className="inline-flex items-center gap-1 text-emerald-600">
                        <ArrowUp className="h-4 w-4" />
                        Federated {percentDiff?.toFixed(1)}% better
                    </span>
                )}
                {winner == null && <span className="text-muted-foreground">-</span>}
            </td>
        </tr>
    );
}

export function PerformanceComparison({ experiments }: PerformanceComparisonProps) {
    const stats = useMemo(() => {
        const completed = experiments.filter(e => e.status === "completed");
        const centralized = completed.filter(e => e.type === "centralized");
        const federated = completed.filter(e => e.type === "federated");

        const centRmse = centralized.map(e => e.metrics?.final_rmse).filter((v): v is number => v != null);
        const fedRmse = federated.map(e => e.metrics?.final_rmse).filter((v): v is number => v != null);
        const centMae = centralized.map(e => e.metrics?.final_mae).filter((v): v is number => v != null);
        const fedMae = federated.map(e => e.metrics?.final_mae).filter((v): v is number => v != null);

        return {
            centralized: {
                count: centralized.length,
                avgRmse: calculateAvg(centRmse),
                avgMae: calculateAvg(centMae),
                medianRmse: calculateMedian(centRmse),
            },
            federated: {
                count: federated.length,
                avgRmse: calculateAvg(fedRmse),
                avgMae: calculateAvg(fedMae),
                medianRmse: calculateMedian(fedRmse),
            },
        };
    }, [experiments]);

    const chartData = useMemo(() => [
        {
            metric: "RMSE",
            Centralized: stats.centralized.avgRmse,
            Federated: stats.federated.avgRmse,
        },
        {
            metric: "MAE",
            Centralized: stats.centralized.avgMae,
            Federated: stats.federated.avgMae,
        },
    ], [stats]);

    const hasData = stats.centralized.count > 0 || stats.federated.count > 0;

    if (!hasData) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Performance Comparison</CardTitle>
                </CardHeader>
                <CardContent className="flex items-center justify-center h-48 text-muted-foreground">
                    No completed experiments yet
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base">Performance Comparison</CardTitle>
                <p className="text-sm text-muted-foreground">
                    Centralized ({stats.centralized.count}) vs Federated ({stats.federated.count})
                </p>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Comparison Table */}
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b">
                                <th className="py-2 text-left font-medium">Metric</th>
                                <th className="py-2 text-center font-medium" style={{ color: PARADIGM_COLORS.centralized }}>
                                    Centralized (avg)
                                </th>
                                <th className="py-2 text-center font-medium" style={{ color: PARADIGM_COLORS.federated }}>
                                    Federated (avg)
                                </th>
                                <th className="py-2 text-center font-medium">Comparison</th>
                            </tr>
                        </thead>
                        <tbody>
                            <ComparisonRow
                                metric="RMSE"
                                centralizedValue={stats.centralized.avgRmse}
                                federatedValue={stats.federated.avgRmse}
                                lowerIsBetter={true}
                            />
                            <ComparisonRow
                                metric="MAE"
                                centralizedValue={stats.centralized.avgMae}
                                federatedValue={stats.federated.avgMae}
                                lowerIsBetter={true}
                            />
                        </tbody>
                    </table>
                </div>

                {/* Grouped Bar Chart */}
                <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis dataKey="metric" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="Centralized" fill={PARADIGM_COLORS.centralized} radius={[4, 4, 0, 0]} />
                        <Bar dataKey="Federated" fill={PARADIGM_COLORS.federated} radius={[4, 4, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
}
