import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ExperimentResponse } from "@/types/experiment";
import {
    PieChart,
    Pie,
    Cell,
    ResponsiveContainer,
    Legend,
    Tooltip,
} from "recharts";

interface ParadigmDistributionProps {
    experiments: ExperimentResponse[];
}

export function ParadigmDistribution({ experiments }: ParadigmDistributionProps) {
    const data = [
        {
            name: "Centralized",
            value: experiments.filter((e) => e.type === "centralized").length,
            color: "#3b82f6", // blue-500
        },
        {
            name: "Federated",
            value: experiments.filter((e) => e.type === "federated").length,
            color: "#10b981", // emerald-500
        },
    ].filter((d) => d.value > 0);

    return (
        <Card className="col-span-1">
            <CardHeader>
                <CardTitle>Paradigm Distribution</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="h-[300px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={data}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={5}
                                dataKey="value"
                            >
                                {data.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                            </Pie>
                            <Tooltip />
                            <Legend verticalAlign="bottom" height={36} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </CardContent>
        </Card>
    );
}
