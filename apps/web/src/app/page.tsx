"use client";

import { MapPin, MessageCircle, Salad, Star, Store, UtensilsCrossed } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Stats } from "@/lib/api";

const TILES = [
  { key: "restaurants" as const, label: "Restaurants", icon: Store, color: "#eb6834" },
  { key: "recipes" as const, label: "Recipes", icon: UtensilsCrossed, color: "#2a78d6" },
  { key: "reviews" as const, label: "Reviews captioned", icon: Salad, color: "#e87ba4" },
  { key: "cuisines" as const, label: "Cuisines covered", icon: MapPin, color: "#1baf7a" },
  { key: "locations" as const, label: "Neighborhoods", icon: MapPin, color: "#eda100" },
];

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    api.getStats().then(setStats).catch(() => setStats(null));
  }, []);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 p-4">
      <div>
        <h2 className="text-2xl font-semibold">Welcome back 👋</h2>
        <p className="text-muted-foreground">
          A snapshot of the restaurant &amp; recipe knowledge base powering your recommendations.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {TILES.map((tile) => (
          <Card key={tile.key}>
            <CardContent className="flex flex-col gap-3 p-4">
              <div
                className="flex size-10 items-center justify-center rounded-xl"
                style={{ backgroundColor: `${tile.color}26`, color: tile.color }}
              >
                <tile.icon className="size-5" />
              </div>
              <div>
                {stats ? (
                  <div className="text-2xl font-semibold tabular-nums">{stats[tile.key]}</div>
                ) : (
                  <Skeleton className="h-8 w-16" />
                )}
                <div className="text-sm text-muted-foreground">{tile.label}</div>
              </div>
            </CardContent>
          </Card>
        ))}

        <Card>
          <CardContent className="flex flex-col gap-3 p-4">
            <div
              className="flex size-10 items-center justify-center rounded-xl"
              style={{ backgroundColor: "#4a3aa726", color: "#4a3aa7" }}
            >
              <Star className="size-5" />
            </div>
            <div>
              {stats ? (
                <div className="text-2xl font-semibold tabular-nums">{stats.avg_rating ?? "—"}</div>
              ) : (
                <Skeleton className="h-8 w-16" />
              )}
              <div className="text-sm text-muted-foreground">Average rating</div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Link href="/chat">
          <Card className="h-full transition-colors hover:bg-accent">
            <CardContent className="flex items-center gap-4 p-6">
              <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <MessageCircle className="size-6" />
              </div>
              <div>
                <div className="font-medium">Ask for a recommendation</div>
                <div className="text-sm text-muted-foreground">
                  Chat with the multi-agent assistant for restaurants &amp; recipes.
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link href="/manage">
          <Card className="h-full transition-colors hover:bg-accent">
            <CardContent className="flex items-center gap-4 p-6">
              <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Store className="size-6" />
              </div>
              <div>
                <div className="font-medium">Manage restaurants</div>
                <div className="text-sm text-muted-foreground">
                  Browse, add, edit, and delete restaurant records.
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
}
