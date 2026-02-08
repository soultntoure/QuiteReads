import { useMemo } from "react";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Clock, Zap, ArrowUp, ArrowDown, Trophy } from "lucide-react";
import type { ExperimentResponse } from "@/types/experiment";

interface TimeSectionProps {
    experiments: ExperimentResponse[];
    baselineId: string;
}

// Color palette matching other sections
const COLORS = [
    "hsl(239, 84%, 67%)",
    "hsl(160, 84%, 39%)",
    "hsl(38, 92%, 50%)",
    "hsl(280, 65%, 60%)",
    "hsl(0, 84%, 60%)",
];

function formatTime(seconds: number | null): string {
    if (seconds === null) return "-";
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
}

function formatDelta(value: number | null, baseline: number | null): { text: string; type: "better" | "worse" | "same" } {
    if (value === null || baseline === null || baseline === 0) {
        return { text: "-", type: "same" };
    }
    const delta = ((value - baseline) / baseline) * 100;
    if (Math.abs(delta) < 0.5) {
        return { text: "≈", type: "same" };
    }
    // For time, lower is better, so positive delta = worse
    const type = delta > 0 ? "worse" : "better";
    const sign = delta > 0 ? "+" : "";
    return { text: `${sign}${delta.toFixed(0)}%`, type };
}

/**
 * Time comparison section showing training duration and efficiency metrics.
 */
export function TimeSection({ experiments, baselineId }: TimeSectionProps) {
    const baseline = experiments.find(e => e.id === baselineId);

    // Prepare chart data
    const chartData = useMemo(() => {
        return experiments.map((exp, i) => ({
            name: exp.name,
            time: exp.metrics.training_time_seconds ?? 0,
            color: COLORS[i % COLORS.length],
        }));
    }, [experiments]);

    // Find fastest experiment
    const fastestId = useMemo(() => {
        let fastest = experiments[0];
        experiments.forEach(exp => {
            const fastestTime = fastest?.metrics.training_time_seconds ?? Infinity;
            const currentTime = exp.metrics.training_time_seconds ?? Infinity;
            if (currentTime < fastestTime) {
                fastest = exp;
            }
        });
        return fastest?.id;
    }, [experiments]);

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Clock className="h-5 w-5 text-primary" />
                    Time
                </CardTitle>
                <CardDescription>
                    Training duration comparison. Lower time with similar accuracy indicates better efficiency.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Time Cards */}
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {experiments.map((exp, i) => {
                        const time = exp.metrics.training_time_seconds;
                        const delta = formatDelta(time, baseline?.metrics.training_time_seconds ?? null);
                        const isBaseline = exp.id === baselineId;
                        const isFastest = exp.id === fastestId;

                        return (
                            <div
                                key={exp.id}
                                className={`relative rounded-lg border p-4 ${isBaseline ? "border-primary bg-primary/5" : ""
                                    } ${isFastest && !isBaseline ? "border-amber-500 bg-amber-500/5" : ""}`}
                            >
                                {isFastest && (
                                    <div className="absolute -top-2 -right-2">
                                        <div className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-500 text-white">
                                            <Trophy className="h-3 w-3" />
                                        </div>
                                    </div>
                                )}
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        <div
                                            className="h-3 w-3 rounded-full"
                                            style={{ backgroundColor: COLORS[i % COLORS.length] }}
                                        />
                                        <span className="text-sm font-medium truncate">{exp.name}</span>
                                    </div>
                                    <div className="flex items-baseline gap-2">
                                        <span className="text-2xl font-bold tabular-nums">
                                            {formatTime(time)}
                                        </span>
                                        {!isBaseline && delta.type !== "same" && (
                                            <span className={`text-xs font-medium ${delta.type === "better" ? "text-emerald-600" : "text-red-600"
                                                }`}>
                                                {delta.type === "better" ? (
                                                    <ArrowDown className="inline h-3 w-3" />
                                                ) : (
                                                    <ArrowUp className="inline h-3 w-3" />
                                                )}
                                                {delta.text}
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex gap-2 text-xs">
                                        {isBaseline && (
                                            <span className="text-primary font-medium">⭐ Baseline</span>
                                        )}
                                        {isFastest && (
                                            <span className="text-amber-600 font-medium">🏆 Fastest</span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Horizontal Bar Chart */}
                <div className="pt-4">
                    <h4 className="text-sm font-medium mb-4">Duration Comparison</h4>
                    <ResponsiveContainer width="100%" height={Math.max(150, experiments.length * 50)}>
                        <BarChart
                            data={chartData}
                            layout="vertical"
                            margin={{ top: 10, right: 30, left: 100, bottom: 10 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" className="stroke-border" horizontal={false} />
                            <XAxis
                                type="number"
                                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                                tickFormatter={(value) => formatTime(value)}
                            />
                            <YAxis
                                type="category"
                                dataKey="name"
                                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
                                width={90}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: "hsl(var(--card))",
                                    border: "1px solid hsl(var(--border))",
                                    borderRadius: "var(--radius)",
                                }}
                                formatter={(value: number) => [formatTime(value), "Duration"]}
                            />
                            <Bar
                                dataKey="time"
                                name="Training Time"
                                radius={[0, 4, 4, 0]}
                            >
                                {chartData.map((entry, index) => (
                                    <Cell
                                        key={`cell-${index}`}
                                        fill={entry.color}
                                    />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
