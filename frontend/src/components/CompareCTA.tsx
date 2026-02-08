import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { GitCompare, Sparkles } from "lucide-react";

interface CompareCTAProps {
    experimentId: string;
    experimentName: string;
}

/**
 * Inline CTA card that appears at the bottom of the ExperimentDetail page
 * for completed experiments, prompting users to compare with other experiments.
 */
export function CompareCTA({ experimentId, experimentName }: CompareCTAProps) {
    return (
        <Card className="bg-gradient-to-r from-primary/5 via-background to-primary/5 border-primary/20">
            <CardContent className="flex items-center justify-between py-4">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                        <Sparkles className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                        <p className="text-sm font-medium">
                            Want to compare this experiment?
                        </p>
                        <p className="text-xs text-muted-foreground">
                            See how it stacks up against other runs
                        </p>
                    </div>
                </div>
                <Button asChild className="gap-2">
                    <Link to={`/experiments?preselect=${experimentId}`}>
                        <GitCompare className="h-4 w-4" />
                        <span className="hidden sm:inline">Compare with Others</span>
                        <span className="sm:hidden">Compare</span>
                    </Link>
                </Button>
            </CardContent>
        </Card>
    );
}

