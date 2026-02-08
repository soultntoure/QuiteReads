import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { PARADIGM_COLORS } from "./OverviewStats";
import type { ExperimentResponse as Experiment } from "@/types/experiment";

interface ParadigmDistributionProps {
    experiments: Experiment[];
}

export function ParadigmDistribution({ experiments }: ParadigmDistributionProps) {
    const chartData = useMemo(() => {
        const completed = experiments.filter(e => e.status === "completed");
        const centralized = completed.filter(e => e.type === "centralized").length;
        const federated = completed.filter(e => e.type === "federated").length;

        return [
            { name: "Centralized", value: centralized, color: PARADIGM_COLORS.centralized },
            { name: "Federated", value: federated, color: PARADIGM_COLORS.federated },
        ].filter(d => d.value > 0);
    }, [experiments]);

    const total = chartData.reduce((acc, d) => acc + d.value, 0);

    if (total === 0) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Paradigm Distribution</CardTitle>
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
                <CardTitle className="text-base">Paradigm Distribution</CardTitle>
            </CardHeader>
            <CardContent>
                <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                        <Pie
                            data={chartData}
                            cx="50%"
                            cy="50%"
                            innerRadius={50}
                            outerRadius={80}
                            paddingAngle={2}
                            dataKey="value"
                            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                            labelLine={false}
                        >
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                        </Pie>
                        <Tooltip
                            formatter={(value: number) => [`${value} experiments`, ""]}
                        />
                        <Legend />
                    </PieChart>
                </ResponsiveContainer>
                <div className="flex justify-center gap-6 mt-2 text-sm text-muted-foreground">
                    {chartData.map(d => (
                        <span key={d.name}>
                            <span
                                className="inline-block w-3 h-3 rounded-full mr-1"
                                style={{ backgroundColor: d.color }}
                            />
                            {d.name}: {d.value}
                        </span>
                    ))}
                </div>
            </CardContent>
        </Card>
    );
}
