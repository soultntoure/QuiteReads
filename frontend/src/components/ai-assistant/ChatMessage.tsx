/**
 * Individual chat message component.
 */

import { cn } from "@/lib/utils";
import { User, Sparkles } from "lucide-react";

interface ChatMessageProps {
    role: "user" | "assistant";
    content: string;
    isStreaming?: boolean;
}

export function ChatMessage({ role, content, isStreaming }: ChatMessageProps) {
    const isUser = role === "user";

    return (
        <div
            className={cn(
                "flex gap-4 group animate-in fade-in slide-in-from-bottom-2 duration-300",
                isUser ? "flex-row-reverse" : "flex-row"
            )}
        >
            <div
                className={cn(
                    "flex-shrink-0 w-9 h-9 rounded-2xl flex items-center justify-center shadow-lg transition-transform group-hover:scale-110",
                    isUser
                        ? "bg-primary text-primary-foreground shadow-primary/20"
                        : "bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-emerald-500/20"
                )}
            >
                {isUser ? (
                    <User className="w-5 h-5" />
                ) : (
                    <Sparkles className="w-5 h-5" />
                )}
            </div>

            <div className={cn(
                "flex flex-col gap-1.5 max-w-[85%]",
                isUser ? "items-end" : "items-start"
            )}>
                <div className="flex items-center gap-2 px-1">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70">
                        {isUser ? "You" : "Assistant"}
                    </span>
                </div>

                <div
                    className={cn(
                        "relative p-4 rounded-3xl text-sm leading-relaxed shadow-sm",
                        isUser
                            ? "bg-primary text-primary-foreground rounded-tr-none"
                            : "bg-muted/50 backdrop-blur-sm border border-border/50 rounded-tl-none"
                    )}
                >
                    <div className={cn(
                        "prose prose-sm max-w-none dark:prose-invert",
                        isUser ? "prose-p:text-primary-foreground text-primary-foreground" : "text-foreground"
                    )}>
                        {content}
                    </div>
                    {isStreaming && (
                        <span className="inline-flex gap-1 ml-2 translate-y-0.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
                            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" />
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}
