import { useMemo } from "react";
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
import { TrendingDown, Target, ArrowUp, ArrowDown, Minus } from "lucide-react";
import type { ExperimentResponse } from "@/types/experiment";

interface PerformanceSectionProps {
    experiments: ExperimentResponse[];
    baselineId: string;
}

// Color palette for experiments
const COLORS = [
    "hsl(239, 84%, 67%)",  // Indigo
    "hsl(160, 84%, 39%)",  // Teal
    "hsl(38, 92%, 50%)",   // Amber
    "hsl(280, 65%, 60%)",  // Purple
    "hsl(0, 84%, 60%)",    // Red
];

function formatDelta(value: number | null, baseline: number | null): { text: string; type: "better" | "worse" | "same" } {
    if (value === null || baseline === null || baseline === 0) {
        return { text: "-", type: "same" };
    }
    const delta = ((value - baseline) / baseline) * 100;
    if (Math.abs(delta) < 0.5) {
        return { text: "≈", type: "same" };
    }
    // For RMSE/MAE, lower is better, so positive delta = worse
    const type = delta > 0 ? "worse" : "better";
    const sign = delta > 0 ? "+" : "";
    return { text: `${sign}${delta.toFixed(1)}%`, type };
}

function DeltaBadge({ delta }: { delta: { text: string; type: "better" | "worse" | "same" } }) {
    const config = {
        better: { icon: ArrowDown, className: "text-emerald-600 bg-emerald-500/10" },
        worse: { icon: ArrowUp, className: "text-red-600 bg-red-500/10" },
        same: { icon: Minus, className: "text-muted-foreground bg-muted" },
    };
    const { icon: Icon, className } = config[delta.type];

    return (
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${className}`}>
            <Icon className="h-3 w-3" />
            {delta.text}
        </span>
    );
}

/**
 * Performance comparison section showing RMSE/MAE metrics with
 * baseline-relative deltas and grouped bar chart visualization.
 */
export function PerformanceSection({ experiments, baselineId }: PerformanceSectionProps) {
    const baseline = experiments.find(e => e.id === baselineId);

    // Prepare data for bar chart
    const chartData = useMemo(() => {
        return [
            {
                metric: "RMSE",
                ...Object.fromEntries(
                    experiments.map((exp, i) => [exp.name, exp.metrics.final_rmse ?? 0])
                ),
            },
            {
                metric: "MAE",
                ...Object.fromEntries(
                    experiments.map((exp, i) => [exp.name, exp.metrics.final_mae ?? 0])
                ),
            },
        ];
    }, [experiments]);

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <TrendingDown className="h-5 w-5 text-primary" />
                    Performance
                </CardTitle>
                <CardDescription>
                    Final RMSE and MAE metrics. Lower values indicate better performance.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Metrics Table */}
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b">
                                <th className="py-3 px-4 text-left font-medium">Metric</th>
                                {experiments.map((exp, i) => (
                                    <th
                                        key={exp.id}
                                        className={`py-3 px-4 text-left font-medium ${exp.id === baselineId ? "bg-primary/5" : ""
                                            }`}
                                    >
                                        <div className="flex items-center gap-2">
                                            <div
                                                className="h-3 w-3 rounded-full"
                                                style={{ backgroundColor: COLORS[i % COLORS.length] }}
                                            />
                                            <span className="truncate max-w-[120px]">{exp.name}</span>
                                            {exp.id === baselineId && (
                                                <span className="text-xs text-primary">⭐</span>
                                            )}
                                        </div>
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            <tr className="border-b">
                                <td className="py-3 px-4 font-medium">
                                    <div className="flex items-center gap-2">
                                        <Target className="h-4 w-4 text-indigo-500" />
                                        RMSE
                                    </div>
                                </td>
                                {experiments.map((exp) => {
                                    const value = exp.metrics.final_rmse;
                                    const delta = formatDelta(value, baseline?.metrics.final_rmse ?? null);
                                    const isBaseline = exp.id === baselineId;
                                    return (
                                        <td
                                            key={exp.id}
                                            className={`py-3 px-4 ${isBaseline ? "bg-primary/5" : ""}`}
                                        >
                                            <div className="space-y-1">
                                                <span className="font-mono text-lg font-semibold">
                                                    {value?.toFixed(4) ?? "-"}
                                                </span>
                                                {!isBaseline && (
                                                    <div>
                                                        <DeltaBadge delta={delta} />
                                                    </div>
                                                )}
                                            </div>
                                        </td>
                                    );
                                })}
                            </tr>
                            <tr>
                                <td className="py-3 px-4 font-medium">
                                    <div className="flex items-center gap-2">
                                        <Target className="h-4 w-4 text-emerald-500" />
                                        MAE
                                    </div>
                                </td>
                                {experiments.map((exp) => {
                                    const value = exp.metrics.final_mae;
                                    const delta = formatDelta(value, baseline?.metrics.final_mae ?? null);
                                    const isBaseline = exp.id === baselineId;
                                    return (
                                        <td
                                            key={exp.id}
                                            className={`py-3 px-4 ${isBaseline ? "bg-primary/5" : ""}`}
                                        >
                                            <div className="space-y-1">
                                                <span className="font-mono text-lg font-semibold">
                                                    {value?.toFixed(4) ?? "-"}
                                                </span>
                                                {!isBaseline && (
                                                    <div>
                                                        <DeltaBadge delta={delta} />
                                                    </div>
                                                )}
                                            </div>
                                        </td>
                                    );
                                })}
                            </tr>
                        </tbody>
                    </table>
                </div>

                {/* Grouped Bar Chart */}
                <div className="pt-4">
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" className="stroke-border" vertical={false} />
                            <XAxis
                                dataKey="metric"
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
                                contentStyle={{
                                    backgroundColor: "hsl(var(--card))",
                                    border: "1px solid hsl(var(--border))",
                                    borderRadius: "var(--radius)",
                                }}
                                formatter={(value: number) => [value.toFixed(4), ""]}
                            />
                            <Legend wrapperStyle={{ paddingTop: 10 }} />
                            {experiments.map((exp, i) => (
                                <Bar
                                    key={exp.id}
                                    dataKey={exp.name}
                                    fill={COLORS[i % COLORS.length]}
                                    radius={[4, 4, 0, 0]}
                                    maxBarSize={60}
                                />
                            ))}
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
