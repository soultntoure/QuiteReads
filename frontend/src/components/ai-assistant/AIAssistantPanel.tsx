/**
 * AI Assistant collapsible and resizable panel.
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageSquare, X, Send, Sparkles, Loader2, Maximize2, Minimize2, GripVertical } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { SuggestionChips } from "./SuggestionChips";
import { streamChat, type ChatMessage as ChatMessageType } from "@/api/chat";

const MIN_WIDTH = 320;
const MAX_WIDTH = 800;
const DEFAULT_WIDTH = 320;
const EXPANDED_WIDTH = 500;

export function AIAssistantPanel() {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<ChatMessageType[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [streamingContent, setStreamingContent] = useState("");
    const [panelWidth, setPanelWidth] = useState(DEFAULT_WIDTH);
    const [isExpanded, setIsExpanded] = useState(false);
    const [isResizing, setIsResizing] = useState(false);

    const scrollRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const accumulatedContentRef = useRef("");
    const panelRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when messages change
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, streamingContent]);

    // Focus input when panel opens
    useEffect(() => {
        if (isOpen && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isOpen]);

    // Handle resize drag
    const handleMouseDown = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        setIsResizing(true);

        const startX = e.clientX;
        const startWidth = panelWidth;

        const handleMouseMove = (e: MouseEvent) => {
            const delta = startX - e.clientX;
            const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidth + delta));
            setPanelWidth(newWidth);
        };

        const handleMouseUp = () => {
            setIsResizing(false);
            document.removeEventListener("mousemove", handleMouseMove);
            document.removeEventListener("mouseup", handleMouseUp);
        };

        document.addEventListener("mousemove", handleMouseMove);
        document.addEventListener("mouseup", handleMouseUp);
    }, [panelWidth]);

    // Toggle expand/collapse
    const toggleExpand = useCallback(() => {
        if (isExpanded) {
            setPanelWidth(DEFAULT_WIDTH);
        } else {
            setPanelWidth(EXPANDED_WIDTH);
        }
        setIsExpanded(!isExpanded);
    }, [isExpanded]);

    const handleSend = useCallback(async (messageText?: string) => {
        const text = messageText || input.trim();
        if (!text || isLoading) return;

        const userMessage: ChatMessageType = { role: "user", content: text };
        setMessages((prev) => [...prev, userMessage]);
        setInput("");
        setIsLoading(true);
        setStreamingContent("");
        accumulatedContentRef.current = "";

        await streamChat(
            { message: text, history: messages },
            (chunk) => {
                accumulatedContentRef.current += chunk;
                setStreamingContent(accumulatedContentRef.current);
            },
            (error) => {
                setMessages((prev) => [
                    ...prev,
                    { role: "assistant", content: `Sorry, I encountered an error: ${error}` },
                ]);
                setIsLoading(false);
                setStreamingContent("");
                accumulatedContentRef.current = "";
            },
            () => {
                const finalContent = accumulatedContentRef.current;
                if (finalContent) {
                    setMessages((prev) => [
                        ...prev,
                        { role: "assistant", content: finalContent },
                    ]);
                }
                setIsLoading(false);
                setStreamingContent("");
                accumulatedContentRef.current = "";
            }
        );
    }, [input, isLoading, messages]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleSuggestionSelect = (suggestion: string) => {
        handleSend(suggestion);
    };

    return (
        <>
            {/* Toggle Button */}
            <Button
                variant="default"
                size="icon"
                className={cn(
                    "fixed right-4 bottom-4 z-50 h-12 w-12 rounded-full shadow-lg transition-all",
                    "bg-gradient-to-br from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700",
                    isOpen && "opacity-0 pointer-events-none"
                )}
                onClick={() => setIsOpen(true)}
            >
                <MessageSquare className="h-5 w-5 text-white" />
            </Button>

            {/* Panel */}
            <div
                ref={panelRef}
                style={{ width: panelWidth }}
                className={cn(
                    "fixed right-0 top-0 z-40 h-full bg-card border-l shadow-2xl transition-transform duration-300 ease-in-out flex flex-col",
                    isOpen ? "translate-x-0" : "translate-x-full",
                    isResizing && "transition-none select-none"
                )}
            >
                {/* Resize Handle */}
                <div
                    className={cn(
                        "absolute left-0 top-0 bottom-0 w-2 cursor-ew-resize group flex items-center justify-center hover:bg-primary/10 transition-colors",
                        isResizing && "bg-primary/20"
                    )}
                    onMouseDown={handleMouseDown}
                >
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-4 h-12 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                        <GripVertical className="w-4 h-4 text-muted-foreground" />
                    </div>
                </div>

                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-emerald-500/10 to-teal-500/10">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                            <Sparkles className="w-4 h-4 text-white" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-sm">RecSys Expert</h3>
                            <p className="text-xs text-muted-foreground">Ask me about RecSys & FL</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-1">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={toggleExpand}
                            title={isExpanded ? "Collapse panel" : "Expand panel"}
                        >
                            {isExpanded ? (
                                <Minimize2 className="h-4 w-4" />
                            ) : (
                                <Maximize2 className="h-4 w-4" />
                            )}
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => setIsOpen(false)}
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                </div>

                {/* Messages Area */}
                <ScrollArea className="flex-1 p-4" ref={scrollRef}>
                    {messages.length === 0 && !streamingContent ? (
                        <div className="space-y-4">
                            <div className="text-center py-6">
                                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-emerald-500/20 to-teal-500/20 flex items-center justify-center">
                                    <Sparkles className="w-8 h-8 text-emerald-600 dark:text-emerald-400" />
                                </div>
                                <h4 className="font-medium mb-1">How can I help you?</h4>
                                <p className="text-sm text-muted-foreground">
                                    I'm your RecSys & Federated Learning expert. Ask me anything about matrix factorization, recommender systems, or federated learning!
                                </p>
                            </div>
                            <div className="border-t pt-4">
                                <p className="text-xs font-medium text-muted-foreground mb-3">
                                    Suggested questions:
                                </p>
                                <SuggestionChips onSelect={handleSuggestionSelect} disabled={isLoading} />
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {messages.map((message, index) => (
                                <ChatMessage key={index} role={message.role} content={message.content} />
                            ))}
                            {streamingContent && (
                                <ChatMessage role="assistant" content={streamingContent} isStreaming />
                            )}
                            {isLoading && !streamingContent && (
                                <div className="flex items-center gap-2 text-muted-foreground text-sm p-3">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Thinking...
                                </div>
                            )}
                        </div>
                    )}
                </ScrollArea>

                {/* Input Area */}
                <div className="p-4 border-t bg-muted/30">
                    <div className="flex gap-2">
                        <Input
                            ref={inputRef}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask about RecSys, MF, FL..."
                            disabled={isLoading}
                            className="flex-1"
                        />
                        <Button
                            onClick={() => handleSend()}
                            disabled={!input.trim() || isLoading}
                            size="icon"
                            className="bg-gradient-to-br from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700"
                        >
                            <Send className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </div>

            {/* Backdrop */}
            {isOpen && (
                <div
                    className="fixed inset-0 z-30 bg-black/20 lg:hidden"
                    onClick={() => setIsOpen(false)}
                />
            )}
        </>
    );
}
