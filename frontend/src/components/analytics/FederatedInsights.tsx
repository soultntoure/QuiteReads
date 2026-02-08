import { useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";
import { ChevronDown, ChevronRight, Users, RefreshCw, Layers } from "lucide-react";
import { PARADIGM_COLORS } from "./OverviewStats";
import type { ExperimentResponse as Experiment } from "@/types/experiment";

interface FederatedInsightsProps {
    experiments: Experiment[];
}

const COLORS = [
    PARADIGM_COLORS.federated,
    "hsl(199, 89%, 48%)", // cyan
    "hsl(262, 83%, 58%)", // purple
    "hsl(24, 95%, 53%)",  // orange
    "hsl(326, 85%, 51%)", // pink
];

export function FederatedInsights({ experiments }: FederatedInsightsProps) {
    const federated = useMemo(() =>
        experiments.filter(e => e.type === "federated" && e.status === "completed"),
        [experiments]
    );

    const totalCompleted = experiments.filter(e => e.status === "completed").length;
    const isMostlyCentralized = federated.length < totalCompleted / 2;

    const [isOpen, setIsOpen] = useState(!isMostlyCentralized && federated.length > 0);

    const clientDistribution = useMemo(() => {
        const groups: Record<number, number> = {};
        federated.forEach(e => {
            const clients = e.n_clients ?? 0;
            groups[clients] = (groups[clients] || 0) + 1;
        });
        return Object.entries(groups)
            .map(([clients, count]) => ({
                clients: `${clients} clients`,
                count,
            }))
            .sort((a, b) => parseInt(a.clients) - parseInt(b.clients));
    }, [federated]);

    const roundsDistribution = useMemo(() => {
        const groups: Record<number, number> = {};
        federated.forEach(e => {
            const rounds = e.n_rounds ?? 0;
            groups[rounds] = (groups[rounds] || 0) + 1;
        });
        return Object.entries(groups)
            .map(([rounds, count]) => ({
                rounds: `${rounds} rounds`,
                count,
            }))
            .sort((a, b) => parseInt(a.rounds) - parseInt(b.rounds));
    }, [federated]);

    const strategyDistribution = useMemo(() => {
        const groups: Record<string, number> = {};
        federated.forEach(e => {
            const strategy = e.aggregation_strategy ?? "unknown";
            groups[strategy] = (groups[strategy] || 0) + 1;
        });
        return Object.entries(groups)
            .map(([name, value]) => ({ name, value }));
    }, [federated]);

    const bestFederatedConfig = useMemo(() => {
        if (federated.length === 0) return null;

        const sorted = [...federated].sort((a, b) => {
            const aRmse = a.metrics?.final_rmse ?? Infinity;
            const bRmse = b.metrics?.final_rmse ?? Infinity;
            return aRmse - bRmse;
        });

        const best = sorted[0];
        return {
            name: best.name,
            rmse: best.metrics?.final_rmse,
            clients: best.n_clients,
            rounds: best.n_rounds,
            strategy: best.aggregation_strategy,
        };
    }, [federated]);

    if (federated.length === 0) {
        return null; // Don't show at all if no federated experiments
    }

    return (
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
            <Card>
                <CollapsibleTrigger asChild>
                    <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                                <CardTitle className="text-base">Federated Insights</CardTitle>
                                <span className="text-sm text-muted-foreground">
                                    ({federated.length} experiment{federated.length !== 1 ? "s" : ""})
                                </span>
                            </div>
                            <Button variant="ghost" size="sm">
                                {isOpen ? "Collapse" : "Expand"}
                            </Button>
                        </div>
                    </CardHeader>
                </CollapsibleTrigger>

                <CollapsibleContent>
                    <CardContent className="space-y-6">
                        {/* Best Configuration Summary */}
                        {bestFederatedConfig && (
                            <div className="p-4 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800">
                                <h4 className="font-medium text-emerald-800 dark:text-emerald-200 mb-2">
                                    🏆 Best Federated Configuration
                                </h4>
                                <p className="text-sm text-emerald-700 dark:text-emerald-300">
                                    <strong>{bestFederatedConfig.name}</strong> achieved RMSE of{" "}
                                    <strong>{bestFederatedConfig.rmse?.toFixed(4)}</strong> with{" "}
                                    {bestFederatedConfig.clients} clients, {bestFederatedConfig.rounds} rounds,{" "}
                                    using {bestFederatedConfig.strategy}
                                </p>
                            </div>
                        )}

                        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                            {/* Client Distribution */}
                            <div>
                                <h4 className="flex items-center gap-2 font-medium mb-3 text-sm">
                                    <Users className="h-4 w-4" />
                                    Client Distribution
                                </h4>
                                {clientDistribution.length > 0 ? (
                                    <ResponsiveContainer width="100%" height={150}>
                                        <BarChart data={clientDistribution} margin={{ left: 0, right: 0 }}>
                                            <XAxis dataKey="clients" tick={{ fontSize: 11 }} />
                                            <YAxis allowDecimals={false} width={30} />
                                            <Tooltip />
                                            <Bar dataKey="count" fill={PARADIGM_COLORS.federated} radius={[4, 4, 0, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <p className="text-sm text-muted-foreground">No data</p>
                                )}
                            </div>

                            {/* Rounds Distribution */}
                            <div>
                                <h4 className="flex items-center gap-2 font-medium mb-3 text-sm">
                                    <RefreshCw className="h-4 w-4" />
                                    Rounds Distribution
                                </h4>
                                {roundsDistribution.length > 0 ? (
                                    <ResponsiveContainer width="100%" height={150}>
                                        <BarChart data={roundsDistribution} margin={{ left: 0, right: 0 }}>
                                            <XAxis dataKey="rounds" tick={{ fontSize: 11 }} />
                                            <YAxis allowDecimals={false} width={30} />
                                            <Tooltip />
                                            <Bar dataKey="count" fill="hsl(199, 89%, 48%)" radius={[4, 4, 0, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <p className="text-sm text-muted-foreground">No data</p>
                                )}
                            </div>

                            {/* Aggregation Strategy */}
                            <div>
                                <h4 className="flex items-center gap-2 font-medium mb-3 text-sm">
                                    <Layers className="h-4 w-4" />
                                    Aggregation Strategies
                                </h4>
                                {strategyDistribution.length > 0 ? (
                                    <ResponsiveContainer width="100%" height={150}>
                                        <PieChart>
                                            <Pie
                                                data={strategyDistribution}
                                                cx="50%"
                                                cy="50%"
                                                innerRadius={30}
                                                outerRadius={50}
                                                paddingAngle={2}
                                                dataKey="value"
                                                label={({ name }) => name}
                                                labelLine={false}
                                            >
                                                {strategyDistribution.map((_, index) => (
                                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                                ))}
                                            </Pie>
                                            <Tooltip />
                                        </PieChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <p className="text-sm text-muted-foreground">No data</p>
                                )}
                            </div>
                        </div>
                    </CardContent>
                </CollapsibleContent>
            </Card>
        </Collapsible>
    );
}
