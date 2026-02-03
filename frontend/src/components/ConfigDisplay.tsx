import type { ExperimentResponse } from "@/types/experiment";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ConfigDisplayProps {
  experiment: ExperimentResponse;
}

interface ConfigItem {
  label: string;
  value: string | number;
}

export function ConfigDisplay({ experiment }: ConfigDisplayProps) {
  const config = experiment.config;
  
  const baseItems: ConfigItem[] = [
    { label: "Learning Rate", value: config.learning_rate },
    { label: "Batch Size", value: config.batch_size },
    { label: "Epochs", value: config.epochs },
    { label: "Model Type", value: config.model_type },
  ];
  
  const federatedItems: ConfigItem[] = experiment.type === "federated" 
    ? [
        { label: "Clients", value: experiment.n_clients ?? "-" },
        { label: "Rounds", value: experiment.n_rounds ?? "-" },
        { label: "Aggregation", value: experiment.aggregation_strategy ?? "-" },
      ]
    : [];
  
  const allItems = [...baseItems, ...federatedItems];
  
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Configuration</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {allItems.map((item) => (
            <div key={item.label}>
              <dt className="text-sm font-medium text-muted-foreground">
                {item.label}
              </dt>
              <dd className="mt-1 text-sm font-semibold">
                {item.value}
              </dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}
