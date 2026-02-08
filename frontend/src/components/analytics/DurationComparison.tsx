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

interface DurationComparisonProps {
    experiments: ExperimentResponse[];
}

export function DurationComparison({ experiments }: DurationComparisonProps) {
    const completed = experiments.filter(
        (e) => e.status === "completed" && e.metrics
    );

    const centralized = completed.filter((e) => e.type === "centralized");
    const federated = completed.filter((e) => e.type === "federated");

    const getStats = (exps: ExperimentResponse[]) => {
        if (exps.length === 0) return { avg: 0, min: 0, max: 0 };
        const times = exps.map((e) => e.metrics.training_time_seconds || 0);
        const sum = times.reduce((a, b) => a + b, 0);
        return {
            avg: parseFloat((sum / times.length).toFixed(2)),
            min: parseFloat(Math.min(...times).toFixed(2)),
            max: parseFloat(Math.max(...times).toFixed(2)),
        };
    };

    const federatedStats = getStats(federated);
    const centralizedStats = getStats(centralized);

    const data = [
        {
            name: "Avg Time (s)",
            Centralized: centralizedStats.avg,
            Federated: federatedStats.avg,
        },
        {
            name: "Min Time (s)",
            Centralized: centralizedStats.min,
            Federated: federatedStats.min,
        },
        {
            name: "Max Time (s)",
            Centralized: centralizedStats.max,
            Federated: federatedStats.max,
        },
    ];

    return (
        <Card className="col-span-1 lg:col-span-2">
            <CardHeader>
                <CardTitle>Training Duration Comparison</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="h-[300px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                            layout="vertical"
                            data={data}
                            margin={{ top: 20, right: 30, left: 40, bottom: 5 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                            <XAxis type="number" />
                            <YAxis dataKey="name" type="category" width={100} />
                            <Tooltip
                                cursor={{ fill: "transparent" }}
                                contentStyle={{
                                    backgroundColor: "hsl(var(--card))",
                                    borderColor: "hsl(var(--border))",
                                }}
                                itemStyle={{ color: "hsl(var(--foreground))" }}
                            />
                            <Legend />
                            <Bar dataKey="Centralized" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                            <Bar dataKey="Federated" fill="#10b981" radius={[0, 4, 4, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
