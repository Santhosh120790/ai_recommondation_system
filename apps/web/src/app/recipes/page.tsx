"use client";

import { ChefHat, Clock, ImageOff, Search, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { api, recipeImageUrl, type Recipe } from "@/lib/api";

export default function RecipesPage() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [active, setActive] = useState<Recipe | null>(null);

  useEffect(() => {
    api
      .listRecipes()
      .then(setRecipes)
      .catch(() => setRecipes([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return recipes;
    return recipes.filter(
      (r) => r.name.toLowerCase().includes(q) || r.cuisine.toLowerCase().includes(q)
    );
  }, [recipes, search]);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name or cuisine…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
        <span className="text-sm text-muted-foreground">
          {loading ? "Loading…" : `${filtered.length} recipes`}
        </span>
      </div>

      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="aspect-4/5 rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {filtered.map((recipe) => {
            const src = recipeImageUrl(recipe.image_path);
            return (
              <Card
                key={recipe.id}
                className="cursor-pointer overflow-hidden py-0 transition-colors hover:bg-accent"
                onClick={() => setActive(recipe)}
              >
                <div className="relative aspect-square bg-muted">
                  {src ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={src}
                      alt={recipe.image_description ?? recipe.name}
                      className="size-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="flex size-full items-center justify-center text-muted-foreground">
                      <ImageOff className="size-6" />
                    </div>
                  )}
                  <Badge className="absolute top-2 left-2" variant="secondary">
                    {recipe.cuisine}
                  </Badge>
                </div>
                <CardContent className="flex flex-col gap-1 p-3">
                  <div className="line-clamp-1 text-sm font-medium">{recipe.name}</div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="size-3" />
                      {recipe.total_time}
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="size-3" />
                      {recipe.servings}
                    </span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
          {filtered.length === 0 && (
            <div className="col-span-full py-12 text-center text-muted-foreground">
              No recipes match your search.
            </div>
          )}
        </div>
      )}

      <Dialog open={active !== null} onOpenChange={(open) => !open && setActive(null)}>
        <DialogContent className="max-h-[85vh] overflow-hidden sm:max-w-2xl">
          {active &&
            (() => {
              const src = recipeImageUrl(active.image_path);
              return (
                <>
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <ChefHat className="size-5 text-primary" />
                      {active.name}
                    </DialogTitle>
                    <DialogDescription>
                      {active.cuisine} · Serves {active.servings} · {active.total_time}
                    </DialogDescription>
                  </DialogHeader>

                  <ScrollArea className="max-h-[60vh]">
                    <div className="flex flex-col gap-4 pr-4">
                      {src && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={src}
                          alt={active.image_description ?? active.name}
                          className="aspect-video w-full rounded-lg object-cover"
                        />
                      )}

                      <div className="grid gap-4 sm:grid-cols-2">
                        <div>
                          <div className="mb-2 text-sm font-medium">Ingredients</div>
                          <ul className="flex flex-col gap-1.5 text-sm text-muted-foreground">
                            {active.ingredients.map((ing, i) => (
                              <li key={i} className="flex gap-2">
                                <span className="text-primary">•</span>
                                {ing}
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <div className="mb-2 text-sm font-medium">Directions</div>
                          <ol className="flex flex-col gap-2 text-sm text-muted-foreground">
                            {active.directions.map((step, i) => (
                              <li key={i} className="flex gap-2">
                                <span className="font-medium text-primary">{i + 1}.</span>
                                {step}
                              </li>
                            ))}
                          </ol>
                        </div>
                      </div>
                    </div>
                  </ScrollArea>
                </>
              );
            })()}
        </DialogContent>
      </Dialog>
    </div>
  );
}
