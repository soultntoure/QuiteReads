import * as React from "react";
import { Button } from "@/components/ui/button";
import { Minus, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

// Valid powers of 2 for batch size selection
const POWERS_OF_TWO = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024];

interface PowerOfTwoInputProps {
    value: number;
    onChange: (value: number) => void;
    min?: number;
    max?: number;
    className?: string;
    disabled?: boolean;
}

export function PowerOfTwoInput({
    value,
    onChange,
    min = 2,
    max = 1024,
    className,
    disabled = false,
}: PowerOfTwoInputProps) {
    // Filter valid values based on min/max
    const validValues = POWERS_OF_TWO.filter((v) => v >= min && v <= max);

    // Find the current index in the valid values array
    const currentIndex = validValues.findIndex((v) => v === value);

    // If value is not a valid power of 2, find the nearest one
    const effectiveIndex = currentIndex >= 0
        ? currentIndex
        : validValues.findIndex((v) => v >= value) || 0;

    const canDecrement = effectiveIndex > 0;
    const canIncrement = effectiveIndex < validValues.length - 1;

    const handleDecrement = () => {
        if (canDecrement && !disabled) {
            onChange(validValues[effectiveIndex - 1]);
        }
    };

    const handleIncrement = () => {
        if (canIncrement && !disabled) {
            onChange(validValues[effectiveIndex + 1]);
        }
    };

    return (
        <div className={cn("flex items-center gap-2", className)}>
            <Button
                type="button"
                variant="outline"
                size="icon"
                className="h-9 w-9 shrink-0"
                onClick={handleDecrement}
                disabled={disabled || !canDecrement}
                aria-label="Decrease batch size"
            >
                <Minus className="h-4 w-4" />
            </Button>

            <div className="flex h-9 w-full items-center justify-center rounded-md border border-input bg-muted/50 px-3 text-sm font-medium tabular-nums">
                {validValues[effectiveIndex] ?? value}
            </div>

            <Button
                type="button"
                variant="outline"
                size="icon"
                className="h-9 w-9 shrink-0"
                onClick={handleIncrement}
                disabled={disabled || !canIncrement}
                aria-label="Increase batch size"
            >
                <Plus className="h-4 w-4" />
            </Button>
        </div>
    );
}
