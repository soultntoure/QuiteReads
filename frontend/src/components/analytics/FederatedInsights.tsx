import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ExperimentResponse } from "@/types/experiment";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import {
    Bar,
    BarChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";

interface FederatedInsightsProps {
    experiments: ExperimentResponse[];
}

export function FederatedInsights({ experiments }: FederatedInsightsProps) {
    const [isOpen, setIsOpen] = useState(false);

    const federatedExps = experiments.filter((e) => e.type === "federated");

    if (federatedExps.length === 0) return null;

    // Aggregate Client Counts
    const clientCounts: Record<string, number> = {};
    federatedExps.forEach((e) => {
        const clients = e.n_clients?.toString() || "Unknown";
        clientCounts[clients] = (clientCounts[clients] || 0) + 1;
    });

    const clientData = Object.entries(clientCounts).map(([clients, count]) => ({
        clients: `Clients: ${clients}`,
        count,
    }));

    // Aggregate Round Counts
    const roundCounts: Record<string, number> = {};
    federatedExps.forEach((e) => {
        const rounds = e.n_rounds?.toString() || "Unknown";
        roundCounts[rounds] = (roundCounts[rounds] || 0) + 1;
    });

    const roundData = Object.entries(roundCounts).map(([rounds, count]) => ({
        rounds: `Rounds: ${rounds}`,
        count,
    }));

    return (
        <Card className="col-span-1 lg:col-span-2">
            <Collapsible open={isOpen} onOpenChange={setIsOpen}>
                <div className="flex items-center justify-between px-6 py-4">
                    <CardTitle className="text-lg">
                        Federated Insights ({federatedExps.length} experiments)
                    </CardTitle>
                    <CollapsibleTrigger asChild>
                        <Button variant="ghost" size="sm" className="w-9 p-0">
                            {isOpen ? (
                                <ChevronUp className="h-4 w-4" />
                            ) : (
                                <ChevronDown className="h-4 w-4" />
                            )}
                            <span className="sr-only">Toggle</span>
                        </Button>
                    </CollapsibleTrigger>
                </div>
                <CollapsibleContent>
                    <CardContent className="grid gap-4 md:grid-cols-2">
                        <div className="h-[200px] w-full rounded-md border p-2">
                            <h4 className="mb-2 text-center text-sm font-medium">
                                Client Distribution
                            </h4>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={clientData}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis dataKey="clients" fontSize={12} />
                                    <YAxis allowDecimals={false} />
                                    <Tooltip />
                                    <Bar dataKey="count" fill="#8884d8" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>

                        <div className="h-[200px] w-full rounded-md border p-2">
                            <h4 className="mb-2 text-center text-sm font-medium">
                                Round Distribution
                            </h4>
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={roundData}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis dataKey="rounds" fontSize={12} />
                                    <YAxis allowDecimals={false} />
                                    <Tooltip />
                                    <Bar dataKey="count" fill="#82ca9d" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </CollapsibleContent>
            </Collapsible>
        </Card>
    );
}
