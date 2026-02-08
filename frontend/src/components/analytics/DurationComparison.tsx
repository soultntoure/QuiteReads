import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { PARADIGM_COLORS } from "./OverviewStats";
import type { ExperimentResponse as Experiment } from "@/types/experiment";

interface DurationComparisonProps {
    experiments: Experiment[];
}

function formatTime(seconds: number | null): string {
    if (seconds == null) return "-";
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
}

function calculateStats(values: number[]) {
    if (values.length === 0) return { avg: null, min: null, max: null };
    return {
        avg: values.reduce((a, b) => a + b, 0) / values.length,
        min: Math.min(...values),
        max: Math.max(...values),
    };
}

export function DurationComparison({ experiments }: DurationComparisonProps) {
    const stats = useMemo(() => {
        const completed = experiments.filter(e => e.status === "completed");
        const centralized = completed.filter(e => e.type === "centralized");
        const federated = completed.filter(e => e.type === "federated");

        const centTimes = centralized.map(e => e.metrics?.training_time_seconds).filter((v): v is number => v != null);
        const fedTimes = federated.map(e => e.metrics?.training_time_seconds).filter((v): v is number => v != null);

        return {
            centralized: { ...calculateStats(centTimes), count: centralized.length },
            federated: { ...calculateStats(fedTimes), count: federated.length },
        };
    }, [experiments]);

    const chartData = useMemo(() => [
        {
            name: "Centralized",
            avg: stats.centralized.avg,
            min: stats.centralized.min,
            max: stats.centralized.max,
            color: PARADIGM_COLORS.centralized,
        },
        {
            name: "Federated",
            avg: stats.federated.avg,
            min: stats.federated.min,
            max: stats.federated.max,
            color: PARADIGM_COLORS.federated,
        },
    ].filter(d => d.avg != null), [stats]);

    const hasData = chartData.length > 0;

    if (!hasData) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Duration Comparison</CardTitle>
                </CardHeader>
                <CardContent className="flex items-center justify-center h-32 text-muted-foreground">
                    No completed experiments yet
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-base">Duration Comparison</CardTitle>
                <p className="text-sm text-muted-foreground">Average training time by paradigm</p>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Stats summary */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                    {chartData.map(d => (
                        <div key={d.name} className="flex items-center gap-3">
                            <div
                                className="w-3 h-3 rounded-full"
                                style={{ backgroundColor: d.color }}
                            />
                            <div>
                                <span className="font-medium">{d.name}</span>
                                <div className="text-muted-foreground text-xs">
                                    Avg: {formatTime(d.avg)} · Min: {formatTime(d.min)} · Max: {formatTime(d.max)}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Horizontal Bar Chart */}
                <ResponsiveContainer width="100%" height={100}>
                    <BarChart
                        data={chartData}
                        layout="vertical"
                        margin={{ top: 5, right: 30, left: 80, bottom: 5 }}
                    >
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} horizontal={false} />
                        <XAxis type="number" tickFormatter={(v) => formatTime(v)} />
                        <YAxis type="category" dataKey="name" width={80} />
                        <Tooltip
                            formatter={(value: number) => [formatTime(value), "Avg Time"]}
                        />
                        <Bar dataKey="avg" radius={[0, 4, 4, 0]}>
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </CardContent>
        </Card>
    );
}
