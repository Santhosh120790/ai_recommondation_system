"use client";

import { ChevronDown, Loader2, Send } from "lucide-react";
import { useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { streamChat } from "@/lib/api";
import { cn } from "@/lib/utils";

const STAGE_LABELS: Record<string, string> = {
  profile: "Building your profile…",
  retrieve: "Searching restaurants & recipes…",
  trends: "Checking food trends…",
  styles: "Matching cuisine style…",
  nutrition: "Reviewing dietary fit…",
  recommend: "Finalizing recommendations…",
};

const QUICK_START = [
  "I prefer plant-based meals, avoid gluten, and love Mediterranean cuisine.",
  "I love trying new cuisines, no dietary restrictions, and enjoy fine dining.",
  "I need quick, affordable meals and order delivery often — comfort food please.",
  "Looking for kid-friendly, casual restaurants — one of us has a nut allergy.",
];

interface Candidate {
  modality: "article" | "image";
  name: string;
  fused_score: number;
}

interface Turn {
  role: "user" | "assistant";
  content: string;
  candidates?: Candidate[];
}

export default function ChatPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [stage, setStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const busy = stage !== null;
  const scrollRef = useRef<HTMLDivElement>(null);

  async function send(message: string) {
    if (!message.trim() || busy) return;
    setError(null);
    setInput("");
    setTurns((prev) => [...prev, { role: "user", content: message }]);
    setStage("profile");

    let candidates: Candidate[] = [];
    try {
      await streamChat(message, (event) => {
        if (event.stage === "error") {
          setError(String(event.data.message ?? "Something went wrong."));
          return;
        }
        if (event.stage === "retrieve" && typeof event.data.candidates === "string") {
          try {
            candidates = JSON.parse(event.data.candidates);
          } catch {
            candidates = [];
          }
        }
        if (event.stage === "done") {
          const finalText = String(event.data.final_recommendation ?? "No recommendation produced.");
          setTurns((prev) => [...prev, { role: "assistant", content: finalText, candidates }]);
          setStage(null);
        } else {
          setStage(event.stage);
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed.");
      setStage(null);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-4">
      <ScrollArea className="flex-1 rounded-lg border" ref={scrollRef}>
        <div className="flex flex-col gap-4 p-4">
          {turns.length === 0 && (
            <div className="flex flex-col gap-2 py-8 text-center text-muted-foreground">
              <p>Tell me about your dining preferences and I&apos;ll recommend restaurants and recipes.</p>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {QUICK_START.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => send(prompt)}
                    className="rounded-md border p-3 text-left text-sm hover:bg-accent"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {turns.map((turn, i) => (
            <div
              key={i}
              className={cn(
                "max-w-[85%] rounded-lg px-4 py-3 text-sm whitespace-pre-wrap",
                turn.role === "user"
                  ? "ml-auto bg-primary text-primary-foreground"
                  : "mr-auto bg-muted"
              )}
            >
              {turn.content}
              {turn.candidates && turn.candidates.length > 0 && (
                <CandidatesPanel candidates={turn.candidates} />
              )}
            </div>
          ))}

          {busy && (
            <div className="mr-auto flex items-center gap-2 rounded-lg bg-muted px-4 py-3 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              {STAGE_LABELS[stage ?? ""] ?? "Thinking…"}
            </div>
          )}

          {error && (
            <div className="mr-auto rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}
        </div>
      </ScrollArea>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-2"
      >
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(input);
            }
          }}
          placeholder="Describe what you're in the mood for…"
          className="min-h-[44px] resize-none"
          disabled={busy}
        />
        <Button type="submit" disabled={busy || !input.trim()} size="icon">
          <Send className="size-4" />
        </Button>
      </form>
    </div>
  );
}

function CandidatesPanel({ candidates }: { candidates: Candidate[] }) {
  const [open, setOpen] = useState(false);
  return (
    <Card className="mt-3 bg-background/50">
      <CardContent className="p-3">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between text-xs font-medium text-muted-foreground"
        >
          Retrieved candidates ({candidates.length})
          <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
        </button>
        {open && (
          <ul className="mt-2 flex flex-col gap-1">
            {candidates.map((c, i) => (
              <li key={i} className="flex items-center gap-2 text-xs">
                <Badge variant={c.modality === "article" ? "default" : "secondary"} className="w-14 justify-center">
                  {c.modality}
                </Badge>
                <span className="flex-1">{c.name}</span>
                <span className="text-muted-foreground">{c.fused_score.toFixed(2)}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
