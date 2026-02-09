/**
 * Suggestion chips for the AI assistant.
 */

import { Button } from "@/components/ui/button";

interface SuggestionChipsProps {
    onSelect: (suggestion: string) => void;
    disabled?: boolean;
}

const SUGGESTIONS = [
    "What is matrix factorization?",
    "Explain latent factors",
    "Federated vs centralized learning",
    "What is the MovieLens dataset?",
    "How does FedAvg work?",
    "Types of recommender systems",
];

export function SuggestionChips({ onSelect, disabled }: SuggestionChipsProps) {
    return (
        <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((suggestion) => (
                <Button
                    key={suggestion}
                    variant="outline"
                    size="sm"
                    className="text-xs h-auto py-1.5 px-3 whitespace-normal text-left hover:bg-primary/10 hover:border-primary/50 transition-colors"
                    onClick={() => onSelect(suggestion)}
                    disabled={disabled}
                >
                    {suggestion}
                </Button>
            ))}
        </div>
    );
}
