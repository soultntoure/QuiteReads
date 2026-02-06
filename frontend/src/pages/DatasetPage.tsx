import { useState } from "react";
import { Upload, FileJson, AlertCircle, CheckCircle2, Info } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { uploadDataset, PreprocessingResponse } from "@/api/dataset";
import { SummaryCard } from "@/components/SummaryCard";

export default function DatasetPage() {
    const [file, setFile] = useState<File | null>(null);
    const [minUserRatings, setMinUserRatings] = useState(20);
    const [valRatio, setValRatio] = useState(0.1);
    const [testRatio, setTestRatio] = useState(0.2);
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState<PreprocessingResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setError(null);
        }
    };

    const handleProcess = async () => {
        if (!file) {
            setError("Please select a file to upload");
            return;
        }

        if (valRatio + testRatio >= 1.0) {
            setError("Validation + Test ratios must be less than 1.0");
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            const response = await uploadDataset(
                file,
                minUserRatings,
                minUserRatings, // Use same config for items for now as per plan focus on user simplicity
                valRatio,
                testRatio
            );
            setResult(response);
        } catch (err: any) {
            setError(err.message || "An unexpected error occurred");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">Dataset Management</h1>
                <p className="text-muted-foreground">
                    Upload and preprocess raw interaction data for federated experiments.
                </p>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                {/* Configuration Section */}
                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Configuration</CardTitle>
                            <CardDescription>
                                Configure preprocessing parameters and upload your dataset.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {/* File Upload */}
                            <div className="space-y-2">
                                <Label htmlFor="file">Raw Dataset (JSON/JSONL)</Label>
                                <div className="flex items-center gap-2">
                                    <Input
                                        id="file"
                                        type="file"
                                        accept=".json,.jsonl"
                                        onChange={handleFileChange}
                                        className="cursor-pointer"
                                    />
                                    {file && <FileJson className="h-4 w-4 text-primary" />}
                                </div>
                            </div>

                            {/* Min Ratings */}
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <Label htmlFor="minRatings">Minimum Ratings per User/Item</Label>
                                    <span className="text-sm font-medium">{minUserRatings}</span>
                                </div>
                                <Input
                                    id="minRatings"
                                    type="number"
                                    min={1}
                                    value={minUserRatings}
                                    onChange={(e) => setMinUserRatings(parseInt(e.target.value) || 0)}
                                />
                                <p className="text-xs text-muted-foreground flex items-center gap-1">
                                    <Info className="h-3 w-3" />
                                    Recommended: 20+ (Consistent with Goodreads policy for personalized recs)
                                </p>
                            </div>

                            {/* Split Ratios */}
                            <div className="space-y-4 pt-2">
                                <Label>Data Splits</Label>

                                <div className="space-y-2">
                                    <div className="flex justify-between text-sm">
                                        <span>Validation Ratio</span>
                                        <span className="font-medium">{(valRatio * 100).toFixed(0)}%</span>
                                    </div>
                                    <Slider
                                        value={[valRatio]}
                                        min={0.05}
                                        max={0.4}
                                        step={0.05}
                                        onValueChange={(v) => setValRatio(v[0])}
                                    />
                                </div>

                                <div className="space-y-2">
                                    <div className="flex justify-between text-sm">
                                        <span>Test Ratio</span>
                                        <span className="font-medium">{(testRatio * 100).toFixed(0)}%</span>
                                    </div>
                                    <Slider
                                        value={[testRatio]}
                                        min={0.05}
                                        max={0.4}
                                        step={0.05}
                                        onValueChange={(v) => setTestRatio(v[0])}
                                    />
                                </div>

                                <div className="rounded-md bg-muted p-2 text-xs text-muted-foreground text-center">
                                    Training Set: {((1 - valRatio - testRatio) * 100).toFixed(0)}%
                                </div>
                            </div>

                            {error && (
                                <Alert variant="destructive">
                                    <AlertCircle className="h-4 w-4" />
                                    <AlertTitle>Error</AlertTitle>
                                    <AlertDescription>{error}</AlertDescription>
                                </Alert>
                            )}

                            <Button
                                className="w-full"
                                onClick={handleProcess}
                                disabled={isLoading || !file}
                            >
                                {isLoading ? (
                                    <>Processing Dataset...</>
                                ) : (
                                    <>
                                        <Upload className="mr-2 h-4 w-4" /> Upload & Process
                                    </>
                                )}
                            </Button>
                        </CardContent>
                    </Card>
                </div>

                {/* Results & Notes Section */}
                <div className="space-y-6">
                    {result && (
                        <>
                            <Card className="border-green-500/50 bg-green-500/10">
                                <CardHeader>
                                    <div className="flex items-center gap-2">
                                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                                        <CardTitle className="text-green-700">Success</CardTitle>
                                    </div>
                                    <CardDescription className="text-green-700/80">
                                        {result.message}
                                    </CardDescription>
                                </CardHeader>
                            </Card>

                            <div className="grid grid-cols-2 gap-4">
                                <SummaryCard
                                    title="Users"
                                    value={result.statistics.filtered_users.toLocaleString()}
                                    trend="Active users"
                                />
                                <SummaryCard
                                    title="Items"
                                    value={result.statistics.filtered_items.toLocaleString()}
                                    trend="Books"
                                />
                                <SummaryCard
                                    title="Interactions"
                                    value={result.statistics.filtered_interactions.toLocaleString()}
                                    trend="Total ratings"
                                />
                                <SummaryCard
                                    title="Sparsity"
                                    value={result.statistics.sparsity_percent}
                                    trend="Matrix sparsity"
                                />
                            </div>
                        </>
                    )}

                    <Card>
                        <CardHeader>
                            <CardTitle>Preprocessing Steps</CardTitle>
                            <CardDescription>
                                Understanding the data transformation pipeline.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ul className="space-y-4 text-sm text-muted-foreground">
                                <li className="flex gap-3">
                                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">1</span>
                                    <div>
                                        <span className="font-semibold text-foreground">Implicit Feedback Filtering</span>
                                        <p>Removes interactions with rating 0, as they indicate "shelved but not rated" books which don't provide explicit preference signals.</p>
                                    </div>
                                </li>
                                <li className="flex gap-3">
                                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">2</span>
                                    <div>
                                        <span className="font-semibold text-foreground">Iterative Core Filtering</span>
                                        <p>Recursively removes users and items with fewer than {minUserRatings} ratings. This ensures sufficient data density for the matrix factorization model to learn meaningful embeddings.</p>
                                    </div>
                                </li>
                                <li className="flex gap-3">
                                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">3</span>
                                    <div>
                                        <span className="font-semibold text-foreground">ID Mapping</span>
                                        <p>Maps original extensive string IDs to contiguous integers [0, N-1] required for PyTorch embedding layers.</p>
                                    </div>
                                </li>
                                <li className="flex gap-3">
                                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">4</span>
                                    <div>
                                        <span className="font-semibold text-foreground">Data Splitting</span>
                                        <p>Partitions data into Training (for model updates), Validation (for tuning), and Test (for final evaluation) sets based on configured ratios.</p>
                                    </div>
                                </li>
                            </ul>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
