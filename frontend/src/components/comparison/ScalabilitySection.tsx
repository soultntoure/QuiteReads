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
import { Users, Layers, ArrowUp, ArrowDown, Minus } from "lucide-react";
import type { ExperimentResponse } from "@/types/experiment";

interface ScalabilitySectionProps {
    experiments: ExperimentResponse[];
    baselineId: string;
}

// Color palette matching PerformanceSection
const COLORS = [
    "hsl(239, 84%, 67%)",
    "hsl(160, 84%, 39%)",
    "hsl(38, 92%, 50%)",
    "hsl(280, 65%, 60%)",
    "hsl(0, 84%, 60%)",
];

function formatDelta(value: number | null, baseline: number | null, higherIsBetter = false): { text: string; type: "better" | "worse" | "neutral" } {
    if (value === null || baseline === null || baseline === 0) {
        return { text: "-", type: "neutral" };
    }
    const delta = ((value - baseline) / baseline) * 100;
    if (Math.abs(delta) < 0.5) {
        return { text: "≈", type: "neutral" };
    }
    // For clients/rounds, more is just a difference, not better/worse
    const sign = delta > 0 ? "+" : "";
    return { text: `${sign}${delta.toFixed(0)}%`, type: "neutral" };
}

/**
 * Scalability comparison section for federated-to-federated comparisons.
 * Shows client count, rounds, and federation overhead metrics.
 */
export function ScalabilitySection({ experiments, baselineId }: ScalabilitySectionProps) {
    const baseline = experiments.find(e => e.id === baselineId);

    // Prepare chart data for client comparison
    const clientChartData = useMemo(() => {
        return experiments.map((exp, i) => ({
            name: exp.name,
            clients: exp.n_clients ?? 0,
            rounds: exp.n_rounds ?? 0,
            color: COLORS[i % COLORS.length],
        }));
    }, [experiments]);

    // Calculate efficiency metric (RMSE per round - lower is better)
    const efficiencyData = useMemo(() => {
        return experiments.map((exp, i) => {
            const rmse = exp.metrics.final_rmse ?? 0;
            const rounds = exp.n_rounds ?? 1;
            const efficiency = rounds > 0 ? rmse / rounds : 0;
            return {
                name: exp.name,
                efficiency: efficiency * 100, // Scale for visibility
                color: COLORS[i % COLORS.length],
            };
        });
    }, [experiments]);

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5 text-primary" />
                    Scalability
                </CardTitle>
                <CardDescription>
                    Federation configuration and client distribution comparison.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Configuration Table */}
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b">
                                <th className="py-3 px-4 text-left font-medium">Parameter</th>
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
                                        <Users className="h-4 w-4 text-blue-500" />
                                        Clients
                                    </div>
                                </td>
                                {experiments.map((exp) => {
                                    const value = exp.n_clients;
                                    const delta = formatDelta(value, baseline?.n_clients ?? null);
                                    const isBaseline = exp.id === baselineId;
                                    return (
                                        <td
                                            key={exp.id}
                                            className={`py-3 px-4 ${isBaseline ? "bg-primary/5" : ""}`}
                                        >
                                            <div className="space-y-1">
                                                <span className="font-mono text-lg font-semibold">
                                                    {value ?? "-"}
                                                </span>
                                                {!isBaseline && value !== baseline?.n_clients && (
                                                    <div>
                                                        <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium text-muted-foreground bg-muted">
                                                            {delta.text}
                                                        </span>
                                                    </div>
                                                )}
                                            </div>
                                        </td>
                                    );
                                })}
                            </tr>
                            <tr className="border-b">
                                <td className="py-3 px-4 font-medium">
                                    <div className="flex items-center gap-2">
                                        <Layers className="h-4 w-4 text-purple-500" />
                                        Rounds
                                    </div>
                                </td>
                                {experiments.map((exp) => {
                                    const value = exp.n_rounds;
                                    const delta = formatDelta(value, baseline?.n_rounds ?? null);
                                    const isBaseline = exp.id === baselineId;
                                    return (
                                        <td
                                            key={exp.id}
                                            className={`py-3 px-4 ${isBaseline ? "bg-primary/5" : ""}`}
                                        >
                                            <div className="space-y-1">
                                                <span className="font-mono text-lg font-semibold">
                                                    {value ?? "-"}
                                                </span>
                                                {!isBaseline && value !== baseline?.n_rounds && (
                                                    <div>
                                                        <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium text-muted-foreground bg-muted">
                                                            {delta.text}
                                                        </span>
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
                                        Strategy
                                    </div>
                                </td>
                                {experiments.map((exp) => {
                                    const isBaseline = exp.id === baselineId;
                                    return (
                                        <td
                                            key={exp.id}
                                            className={`py-3 px-4 ${isBaseline ? "bg-primary/5" : ""}`}
                                        >
                                            <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-blue-500/10 text-blue-600">
                                                {exp.aggregation_strategy?.toUpperCase() ?? "N/A"}
                                            </span>
                                        </td>
                                    );
                                })}
                            </tr>
                        </tbody>
                    </table>
                </div>

                {/* Client Count Bar Chart */}
                <div className="grid gap-6 md:grid-cols-2">
                    <div>
                        <h4 className="text-sm font-medium mb-4">Client Distribution</h4>
                        <ResponsiveContainer width="100%" height={200}>
                            <BarChart data={clientChartData} layout="vertical" margin={{ left: 80 }}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-border" horizontal={false} />
                                <XAxis type="number" tick={{ fontSize: 12 }} />
                                <YAxis
                                    type="category"
                                    dataKey="name"
                                    tick={{ fontSize: 11 }}
                                    width={70}
                                />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: "hsl(var(--card))",
                                        border: "1px solid hsl(var(--border))",
                                        borderRadius: "var(--radius)",
                                    }}
                                />
                                <Bar dataKey="clients" name="Clients" radius={[0, 4, 4, 0]}>
                                    {clientChartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                    <div>
                        <h4 className="text-sm font-medium mb-4">Federation Rounds</h4>
                        <ResponsiveContainer width="100%" height={200}>
                            <BarChart data={clientChartData} layout="vertical" margin={{ left: 80 }}>
                                <CartesianGrid strokeDasharray="3 3" className="stroke-border" horizontal={false} />
                                <XAxis type="number" tick={{ fontSize: 12 }} />
                                <YAxis
                                    type="category"
                                    dataKey="name"
                                    tick={{ fontSize: 11 }}
                                    width={70}
                                />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: "hsl(var(--card))",
                                        border: "1px solid hsl(var(--border))",
                                        borderRadius: "var(--radius)",
                                    }}
                                />
                                <Bar dataKey="rounds" name="Rounds" radius={[0, 4, 4, 0]}>
                                    {clientChartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
