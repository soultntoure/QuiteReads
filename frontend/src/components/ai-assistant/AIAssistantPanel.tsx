/**
 * AI Assistant collapsible and resizable panel.
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageSquare, X, Send, Sparkles, Loader2, Maximize2, Minimize2, GripVertical, Plus } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { SuggestionChips } from "./SuggestionChips";
import { streamChat, type ChatMessage as ChatMessageType } from "@/api/chat";

const MIN_WIDTH = 350;
const MAX_WIDTH = 1200;
const DEFAULT_WIDTH = 450;

export function AIAssistantPanel() {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<ChatMessageType[]>([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [streamingContent, setStreamingContent] = useState("");
    const [panelWidth, setPanelWidth] = useState(DEFAULT_WIDTH);
    const [isMaximized, setIsMaximized] = useState(false);
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
        setIsMaximized(false);

        const startX = e.clientX;
        const startWidth = panelWidth;

        const handleMouseMove = (e: MouseEvent) => {
            const delta = startX - e.clientX;
            const newWidth = Math.min(window.innerWidth * 0.85, Math.max(MIN_WIDTH, startWidth + delta));
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
    const toggleMaximize = useCallback(() => {
        if (isMaximized) {
            setPanelWidth(DEFAULT_WIDTH);
        } else {
            setPanelWidth(Math.min(1000, window.innerWidth * 0.8));
        }
        setIsMaximized(!isMaximized);
    }, [isMaximized]);

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

    const handleNewChat = useCallback(() => {
        if (isLoading) return;
        setMessages([]);
        setStreamingContent("");
        setInput("");
        accumulatedContentRef.current = "";
    }, [isLoading]);

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
                style={{ width: isOpen ? panelWidth : 0 }}
                className={cn(
                    "fixed right-0 top-0 z-40 h-full bg-card/95 backdrop-blur-xl border-l shadow-2xl transition-all duration-300 ease-in-out flex flex-col",
                    !isOpen && "translate-x-full pointer-events-none",
                    isResizing && "transition-none select-none"
                )}
            >
                {/* Resize Handle - More prominent hit area */}
                <div
                    className={cn(
                        "absolute -left-1.5 top-0 bottom-0 w-4 cursor-ew-resize group z-50 transition-colors",
                        isResizing ? "bg-primary/20" : "hover:bg-primary/10"
                    )}
                    onMouseDown={handleMouseDown}
                >
                    <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-1.5 h-12 rounded-full bg-muted-foreground/30 group-hover:bg-primary/50 transition-all group-hover:h-20" />
                </div>

                {/* Header */}
                <div className="flex items-center justify-between p-5 border-b bg-gradient-to-r from-emerald-500/10 via-teal-500/5 to-transparent">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                            <Sparkles className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h3 className="font-bold text-base tracking-tight">RecSys Assistant</h3>
                            <div className="flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Expert Online</p>
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-9 w-9 rounded-xl hover:bg-emerald-500/10 hover:text-emerald-600 transition-colors"
                            onClick={handleNewChat}
                            title="New Conversation"
                            disabled={isLoading || (messages.length === 0 && !streamingContent)}
                        >
                            <Plus className="h-4.5 w-4.5" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-9 w-9 rounded-xl hover:bg-teal-500/10 hover:text-teal-600 transition-colors"
                            onClick={toggleMaximize}
                            title={isMaximized ? "Restore size" : "Wide view"}
                        >
                            {isMaximized ? (
                                <Minimize2 className="h-4.5 w-4.5" />
                            ) : (
                                <Maximize2 className="h-4.5 w-4.5" />
                            )}
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-9 w-9 rounded-xl hover:bg-destructive/10 hover:text-destructive transition-colors"
                            onClick={() => setIsOpen(false)}
                        >
                            <X className="h-4.5 w-4.5" />
                        </Button>
                    </div>
                </div>

                {/* Messages Area */}
                <ScrollArea className="flex-1 px-4 py-6" ref={scrollRef}>
                    <div className="max-w-4xl mx-auto w-full">
                        {messages.length === 0 && !streamingContent ? (
                            <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                                <div className="text-center py-10">
                                    <div className="w-20 h-20 mx-auto mb-6 rounded-3xl bg-gradient-to-br from-emerald-500/10 to-teal-500/10 flex items-center justify-center border border-emerald-500/20">
                                        <Sparkles className="w-10 h-10 text-emerald-600 dark:text-emerald-400" />
                                    </div>
                                    <h4 className="text-xl font-bold mb-2">How can I help today?</h4>
                                    <p className="text-sm text-muted-foreground max-w-sm mx-auto leading-relaxed">
                                        I'm your specialized AI for Recommendations & Federated Learning.
                                    </p>
                                </div>
                                <div className="bg-muted/30 rounded-3xl p-6 border border-border/50">
                                    <p className="text-[11px] font-bold text-muted-foreground uppercase tracking-widest mb-4 px-1">
                                        Quick Start
                                    </p>
                                    <SuggestionChips onSelect={handleSuggestionSelect} disabled={isLoading} />
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-6 pb-4">
                                {messages.map((message, index) => (
                                    <ChatMessage key={index} role={message.role} content={message.content} />
                                ))}
                                {streamingContent && (
                                    <ChatMessage role="assistant" content={streamingContent} isStreaming />
                                )}
                                {isLoading && !streamingContent && (
                                    <div className="flex items-center gap-3 text-muted-foreground text-sm p-4 bg-muted/30 rounded-2xl border border-border/50 animate-pulse">
                                        <Loader2 className="w-4 h-4 animate-spin text-emerald-500" />
                                        <span>Analysing codebase...</span>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </ScrollArea>

                {/* Input Area */}
                <div className="p-6 border-t bg-background/50 backdrop-blur-sm">
                    <div className="max-w-4xl mx-auto w-full">
                        <div className="relative group flex items-end gap-3 bg-muted/50 p-2 rounded-2xl border border-border/50 focus-within:border-emerald-500/50 focus-within:ring-4 focus-within:ring-emerald-500/10 transition-all">
                            <textarea
                                className="flex-1 bg-transparent border-0 focus:ring-0 resize-none py-3 px-2 text-sm max-h-40 min-h-[44px] scrollbar-none"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSend();
                                    }
                                }}
                                placeholder="Type your message..."
                                disabled={isLoading}
                                rows={1}
                            />
                            <Button
                                onClick={() => handleSend()}
                                disabled={!input.trim() || isLoading}
                                size="icon"
                                className="h-10 w-10 shrink-0 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-500/20 transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:grayscale"
                            >
                                <Send className="h-4.5 w-4.5 text-white" />
                            </Button>
                        </div>
                        <p className="mt-3 text-[10px] text-center text-muted-foreground">
                            AI may provide inaccurate info. Verify important details.
                        </p>
                    </div>
                </div>
            </div>

            {/* Backdrop */}
            {isOpen && (
                <div
                    className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm transition-all duration-300"
                    onClick={() => setIsOpen(false)}
                />
            )}
        </>
    );
}
