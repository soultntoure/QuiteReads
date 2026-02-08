import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Cell,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { TrendingDown, Target, Clock, Award } from "lucide-react";
import type { ExperimentMetricsSchema } from "@/types/experiment";

interface MetricsBarChartProps {
    metrics: ExperimentMetricsSchema;
}

// Metric colors - vibrant and distinct
const METRIC_COLORS = {
    rmse: "hsl(239, 84%, 67%)",  // Indigo for RMSE
    mae: "hsl(160, 84%, 39%)",   // Teal/Green for MAE
};

function formatMetric(value: number | null): string {
    if (value === null) return "-";
    return value.toFixed(4);
}

function formatTime(seconds: number | null): string {
    if (seconds === null) return "-";
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
}

export function MetricsBarChart({ metrics }: MetricsBarChartProps) {
    const hasMetrics = metrics.final_rmse !== null || metrics.final_mae !== null;

    // Data for bar chart
    const chartData = [
        {
            name: "RMSE",
            value: metrics.final_rmse ?? 0,
            displayValue: metrics.final_rmse,
            color: METRIC_COLORS.rmse,
        },
        {
            name: "MAE",
            value: metrics.final_mae ?? 0,
            displayValue: metrics.final_mae,
            color: METRIC_COLORS.mae,
        },
    ];

    // Summary cards data
    const summaryCards = [
        {
            label: "Best RMSE",
            value: formatMetric(metrics.final_rmse),
            icon: TrendingDown,
            description: "Root Mean Square Error",
            color: "bg-indigo-500/10 text-indigo-600",
        },
        {
            label: "Best MAE",
            value: formatMetric(metrics.final_mae),
            icon: Target,
            description: "Mean Absolute Error",
            color: "bg-emerald-500/10 text-emerald-600",
        },
        {
            label: "Training Time",
            value: formatTime(metrics.training_time_seconds),
            icon: Clock,
            description: "Total duration",
            color: "bg-amber-500/10 text-amber-600",
        },
    ];

    if (!hasMetrics) {
        return (
            <div className="flex h-[300px] items-center justify-center text-muted-foreground">
                <div className="text-center">
                    <Award className="mx-auto h-12 w-12 opacity-30 mb-3" />
                    <p>No final metrics available yet</p>
                    <p className="text-sm mt-1">Run the experiment to see results</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Best Validation Metrics Header */}
            <div className="rounded-lg bg-emerald-50 dark:bg-emerald-950/30 p-4 border border-emerald-200 dark:border-emerald-900">
                <div className="flex items-center gap-2 mb-2">
                    <Award className="h-5 w-5 text-emerald-600" />
                    <h3 className="font-semibold text-emerald-800 dark:text-emerald-200">Best Validation Metrics</h3>
                </div>
                <p className="text-sm text-emerald-700 dark:text-emerald-300">
                    These are the best validation metrics achieved during training. The model checkpoint with these metrics is saved for deployment.
                </p>
            </div>

            {/* Summary Cards */}
            <div className="grid gap-4 sm:grid-cols-3">
                {summaryCards.map((card) => (
                    <div
                        key={card.label}
                        className="relative overflow-hidden rounded-xl border bg-card p-4 shadow-sm"
                    >
                        <div className="flex items-start justify-between">
                            <div className="space-y-1">
                                <p className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
                                    {card.label}
                                </p>
                                <p className="text-3xl font-bold tabular-nums tracking-tight">
                                    {card.value}
                                </p>
                            </div>
                            <div className={`rounded-lg p-2 ${card.color}`}>
                                <card.icon className="h-5 w-5" />
                            </div>
                        </div>
                        <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
                    </div>
                ))}
            </div>

            {/* Performance Metrics Bar Chart */}
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <TrendingDown className="h-5 w-5 text-primary" />
                        Performance Metrics
                    </CardTitle>
                    <CardDescription>
                        Final RMSE and MAE values comparison
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <ResponsiveContainer width="100%" height={280}>
                        <BarChart
                            data={chartData}
                            margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                            barCategoryGap="30%"
                        >
                            <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
                            <XAxis
                                dataKey="name"
                                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                                tickLine={false}
                                axisLine={false}
                            />
                            <YAxis
                                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                                tickLine={false}
                                axisLine={false}
                                tickFormatter={(value) => value.toFixed(2)}
                            />
                            <Tooltip
                                cursor={{ fill: "hsl(var(--muted))", opacity: 0.3 }}
                                contentStyle={{
                                    backgroundColor: "hsl(var(--card))",
                                    border: "1px solid hsl(var(--border))",
                                    borderRadius: "var(--radius)",
                                    boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                                }}
                                labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600 }}
                                formatter={(value: number) => [value.toFixed(4), "Value"]}
                            />
                            <Legend
                                wrapperStyle={{ paddingTop: 20 }}
                                formatter={(value) => <span className="text-sm font-medium">{value}</span>}
                            />
                            <Bar
                                dataKey="value"
                                name="Metric Value"
                                radius={[6, 6, 0, 0]}
                                maxBarSize={80}
                            >
                                {chartData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </CardContent>
            </Card>
        </div>
    );
}
