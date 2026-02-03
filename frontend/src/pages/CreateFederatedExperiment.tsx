import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useCreateFederatedExperiment } from "@/hooks/use-experiments";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ArrowLeft, Network } from "lucide-react";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Link } from "react-router-dom";

const formSchema = z.object({
  name: z.string().min(1, "Name is required").max(255, "Name must be less than 255 characters"),
  learning_rate: z.coerce
    .number()
    .min(0.001, "Learning rate must be at least 0.001")
    .max(1, "Learning rate must be at most 1"),
  batch_size: z.coerce
    .number()
    .int("Batch size must be an integer")
    .min(1, "Batch size must be at least 1"),
  epochs: z.coerce
    .number()
    .int("Epochs must be an integer")
    .min(1, "Epochs must be at least 1"),
  model_type: z.string().min(1, "Model type is required"),
  n_clients: z.coerce
    .number()
    .int("Number of clients must be an integer")
    .min(2, "At least 2 clients are required"),
  n_rounds: z.coerce
    .number()
    .int("Number of rounds must be an integer")
    .min(1, "At least 1 round is required"),
  aggregation_strategy: z.enum(["fedavg"]),
});

type FormValues = z.infer<typeof formSchema>;

export default function CreateFederatedExperiment() {
  const navigate = useNavigate();
  const createExperiment = useCreateFederatedExperiment();
  
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      learning_rate: 0.01,
      batch_size: 32,
      epochs: 5,
      model_type: "biased_svd",
      n_clients: 5,
      n_rounds: 10,
      aggregation_strategy: "fedavg",
    },
  });
  
  const onSubmit = (values: FormValues) => {
    createExperiment.mutate(
      {
        name: values.name,
        config: {
          learning_rate: values.learning_rate,
          batch_size: values.batch_size,
          epochs: values.epochs,
          model_type: values.model_type,
        },
        n_clients: values.n_clients,
        n_rounds: values.n_rounds,
        aggregation_strategy: values.aggregation_strategy,
      },
      {
        onSuccess: (data) => {
          navigate(`/experiments/${data.id}`);
        },
      }
    );
  };
  
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Back Button */}
      <Button variant="ghost" size="sm" asChild>
        <Link to="/experiments">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Experiments
        </Link>
      </Button>
      
      {/* Form Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Network className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle>New Federated Experiment</CardTitle>
              <CardDescription>
                Train a model across multiple distributed clients
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Experiment Name</FormLabel>
                    <FormControl>
                      <Input placeholder="FedAvg 10 Clients" {...field} />
                    </FormControl>
                    <FormDescription>
                      A descriptive name for this experiment
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
              
              {/* Training Parameters */}
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-muted-foreground">Training Parameters</h3>
                <div className="grid gap-6 sm:grid-cols-2">
                  <FormField
                    control={form.control}
                    name="learning_rate"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Learning Rate</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            step="0.001"
                            min="0.001"
                            max="1"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={form.control}
                    name="batch_size"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Batch Size</FormLabel>
                        <FormControl>
                          <Input type="number" min="1" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                
                <div className="grid gap-6 sm:grid-cols-2">
                  <FormField
                    control={form.control}
                    name="epochs"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Local Epochs</FormLabel>
                        <FormControl>
                          <Input type="number" min="1" {...field} />
                        </FormControl>
                        <FormDescription>
                          Epochs per client per round
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={form.control}
                    name="model_type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Model Type</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select model type" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="biased_svd">Biased SVD</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
              
              {/* Federated Parameters */}
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-muted-foreground">Federated Settings</h3>
                <div className="grid gap-6 sm:grid-cols-3">
                  <FormField
                    control={form.control}
                    name="n_clients"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Number of Clients</FormLabel>
                        <FormControl>
                          <Input type="number" min="2" {...field} />
                        </FormControl>
                        <FormDescription>
                          Min. 2 clients
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={form.control}
                    name="n_rounds"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Training Rounds</FormLabel>
                        <FormControl>
                          <Input type="number" min="1" {...field} />
                        </FormControl>
                        <FormDescription>
                          Aggregation rounds
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={form.control}
                    name="aggregation_strategy"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Aggregation</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="fedavg">FedAvg</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormDescription>
                          Strategy
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
              
              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createExperiment.isPending}>
                  {createExperiment.isPending && <LoadingSpinner size="sm" className="mr-2" />}
                  Create Experiment
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
