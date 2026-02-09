import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useCreateCentralizedExperiment } from "@/hooks/use-experiments";
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
import { ArrowLeft, Server } from "lucide-react";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Link } from "react-router-dom";
import { PowerOfTwoInput } from "@/components/ui/power-of-two-input";

// Helper function to check if a number is a power of 2
const isPowerOfTwo = (n: number): boolean => {
  return n > 0 && (n & (n - 1)) === 0;
};

const formSchema = z.object({
  name: z.string().min(1, "Name is required").max(255, "Name must be less than 255 characters"),
  n_factors: z.coerce
    .number()
    .int("Latent factors must be an integer")
    .min(1, "Latent factors must be at least 1")
    .max(200, "Latent factors must be at most 200"),
  learning_rate: z.coerce
    .number()
    .min(0.001, "Learning rate must be at least 0.001")
    .max(1, "Learning rate must be at most 1"),
  regularization: z.coerce
    .number()
    .min(0, "Regularization must be non-negative")
    .max(1, "Regularization must be at most 1"),
  batch_size: z.coerce
    .number()
    .int("Batch size must be an integer")
    .min(1, "Batch size must be at least 1")
    .refine((val) => isPowerOfTwo(val), {
      message: "Batch size must be a power of 2 (e.g., 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024)",
    }),
  epochs: z.coerce
    .number()
    .int("Epochs must be an integer")
    .min(1, "Epochs must be at least 1"),
});

type FormValues = z.infer<typeof formSchema>;

export default function CreateCentralizedExperiment() {
  const navigate = useNavigate();
  const createExperiment = useCreateCentralizedExperiment();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      n_factors: 20,
      learning_rate: 0.02,
      regularization: 0.003,
      batch_size: 64,
      epochs: 8,
    },
  });

  const onSubmit = (values: FormValues) => {
    createExperiment.mutate(
      {
        name: values.name,
        config: {
          n_factors: values.n_factors,
          learning_rate: values.learning_rate,
          regularization: values.regularization,
          batch_size: values.batch_size,
          epochs: values.epochs,
        },
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
              <Server className="h-5 w-5 text-primary" />
            </div>
            <div>
              <CardTitle>New Centralized Experiment</CardTitle>
              <CardDescription>
                Train a model on a single server with all data combined
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
                      <Input placeholder="Baseline Centralized MF" {...field} />
                    </FormControl>
                    <FormDescription>
                      A descriptive name for this experiment
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid gap-6 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="n_factors"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Latent Factors</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="1"
                          max="200"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        Number of latent dimensions (1-200)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

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
                      <FormDescription>
                        Step size for gradient descent (0.001-1.0)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid gap-6 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="regularization"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Regularization</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          step="0.001"
                          min="0"
                          max="1"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        L2 penalty weight (0-1.0)
                      </FormDescription>
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
                        <PowerOfTwoInput
                          value={field.value}
                          onChange={field.onChange}
                          min={2}
                          max={1024}
                        />
                      </FormControl>
                      <FormDescription>
                        Samples per batch (power of 2)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="epochs"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Epochs</FormLabel>
                    <FormControl>
                      <Input type="number" min="1" {...field} />
                    </FormControl>
                    <FormDescription>
                      Number of training epochs
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

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
