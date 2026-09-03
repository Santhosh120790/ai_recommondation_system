"use client";

import {
  ArrowRight,
  ChefHat,
  MapPin,
  MessageCircle,
  Salad,
  Soup,
  Sparkles,
  Star,
  Store,
  UtensilsCrossed,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Stats } from "@/lib/api";

const TILES = [
  { key: "restaurants" as const, label: "Restaurants", icon: Store, color: "#eb6834" },
  { key: "recipes" as const, label: "Recipes", icon: UtensilsCrossed, color: "#2a78d6" },
  { key: "reviews" as const, label: "Reviews captioned", icon: Salad, color: "#e87ba4" },
  { key: "cuisines" as const, label: "Cuisines covered", icon: MapPin, color: "#1baf7a" },
  { key: "locations" as const, label: "Neighborhoods", icon: MapPin, color: "#eda100" },
  { key: "avg_rating" as const, label: "Average rating", icon: Star, color: "#8b5cf6" },
];

const QUICK_ACTIONS = [
  {
    href: "/chat",
    icon: MessageCircle,
    title: "Ask for a recommendation",
    description: "Chat with the multi-agent assistant for restaurants & recipes.",
  },
  {
    href: "/manage",
    icon: Store,
    title: "Manage restaurants",
    description: "Browse, add, edit, and delete restaurant records.",
  },
  {
    href: "/recipes",
    icon: ChefHat,
    title: "Browse recipes",
    description: "Explore the captioned recipe gallery, ingredients & directions.",
  },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    api.getStats().then(setStats).catch(() => setStats(null));
  }, []);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 p-4">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-3xl border bg-[linear-gradient(135deg,var(--secondary),var(--background)_65%)] p-8 sm:p-10">
        <div className="pointer-events-none absolute top-1/2 right-6 hidden -translate-y-1/2 sm:block">
          <div className="relative size-40">
            <div className="absolute top-0 right-4 flex size-16 items-center justify-center rounded-2xl bg-primary/15 text-primary">
              <ChefHat className="size-7" />
            </div>
            <div className="absolute bottom-2 right-20 flex size-12 items-center justify-center rounded-2xl bg-[#1baf7a26] text-[#1baf7a] rotate-[-8deg]">
              <Soup className="size-5" />
            </div>
            <div className="absolute right-0 bottom-0 flex size-11 items-center justify-center rounded-2xl bg-[#2a78d626] text-[#2a78d6] rotate-[10deg]">
              <Sparkles className="size-5" />
            </div>
          </div>
        </div>

        <div className="relative flex max-w-xl flex-col gap-4">
          <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold tracking-wide text-primary uppercase">
            <Sparkles className="size-3.5" />
            Connoisseur
          </span>
          <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            Great taste, engineered.
          </h1>
          <p className="text-muted-foreground text-balance">
            Six specialized AI agents cross-reference trends, cuisine style, and dietary fit
            against a multimodal knowledge base to find your next great meal.
          </p>
          <div className="mt-2 flex flex-wrap gap-3">
            <Button size="lg" nativeButton={false} render={<Link href="/chat" />} className="gap-2">
              <MessageCircle className="size-4" />
              Ask for a recommendation
            </Button>
            <Button
              size="lg"
              variant="outline"
              nativeButton={false}
              render={<Link href="/manage" />}
              className="gap-2"
            >
              <Store className="size-4" />
              Manage restaurants
            </Button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-muted-foreground">Your knowledge base, at a glance</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {TILES.map((tile) => (
            <Card
              key={tile.key}
              className="gap-3 py-5 transition-all hover:-translate-y-0.5 hover:shadow-md"
            >
              <CardContent className="flex flex-col gap-3 px-5">
                <div
                  className="flex size-11 items-center justify-center rounded-2xl"
                  style={{ backgroundColor: `${tile.color}1f`, color: tile.color }}
                >
                  <tile.icon className="size-5" />
                </div>
                <div>
                  {stats ? (
                    <div className="text-2xl font-bold tabular-nums">
                      {tile.key === "avg_rating" ? (stats.avg_rating ?? "—") : stats[tile.key]}
                    </div>
                  ) : (
                    <Skeleton className="h-8 w-16" />
                  )}
                  <div className="text-sm text-muted-foreground">{tile.label}</div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-muted-foreground">Quick actions</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {QUICK_ACTIONS.map((action) => (
            <Link key={action.href} href={action.href} className="group">
              <Card className="h-full py-0 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md">
                <CardContent className="flex h-full flex-col gap-4 p-6">
                  <div className="flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                    <action.icon className="size-6" />
                  </div>
                  <div className="flex flex-1 flex-col gap-1">
                    <div className="flex items-center gap-1.5 font-medium">
                      {action.title}
                      <ArrowRight className="size-3.5 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-primary" />
                    </div>
                    <div className="text-sm text-muted-foreground">{action.description}</div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
