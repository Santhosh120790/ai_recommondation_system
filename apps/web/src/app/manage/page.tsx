"use client";

import { Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { CuisineTile } from "@/components/cuisine-tile";
import { RestaurantDialog } from "@/components/restaurant-dialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, type Restaurant } from "@/lib/api";

export default function ManagePage() {
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Restaurant | null>(null);
  const [deleting, setDeleting] = useState<Restaurant | null>(null);

  async function load() {
    setLoading(true);
    try {
      setRestaurants(await api.listRestaurants());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load restaurants.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return restaurants;
    return restaurants.filter(
      (r) =>
        r.name.toLowerCase().includes(q) ||
        r.location.toLowerCase().includes(q) ||
        r.food_style.toLowerCase().includes(q)
    );
  }, [restaurants, search]);

  async function confirmDelete() {
    if (!deleting) return;
    try {
      await api.deleteRestaurant(deleting.item_id);
      toast.success(`Deleted ${deleting.name}.`);
      setDeleting(null);
      load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete.");
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-4 p-4">
      <div className="flex items-center justify-between gap-2">
        <Input
          placeholder="Search by name, location, or cuisine…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <Button
          onClick={() => {
            setEditing(null);
            setDialogOpen(true);
          }}
        >
          <Plus className="size-4" />
          Add restaurant
        </Button>
      </div>

      {loading ? (
        <div className="flex flex-1 items-center justify-center text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
        </div>
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-14" />
                <TableHead>Name</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Cuisine</TableHead>
                <TableHead>Price</TableHead>
                <TableHead>Rating</TableHead>
                <TableHead className="w-20" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((r) => (
                <TableRow key={r.item_id}>
                  <TableCell>
                    <CuisineTile name={r.name} foodStyle={r.food_style} type={r.type} size={36} />
                  </TableCell>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell>{r.location}</TableCell>
                  <TableCell>{r.food_style}</TableCell>
                  <TableCell>{r.price_range ? "$".repeat(r.price_range) : "—"}</TableCell>
                  <TableCell>{r.rating ?? "—"}</TableCell>
                  <TableCell className="flex justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        setEditing(r);
                        setDialogOpen(true);
                      }}
                    >
                      <Pencil className="size-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => setDeleting(r)}>
                      <Trash2 className="size-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                    No restaurants match your search.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      )}

      <RestaurantDialog
        restaurant={editing}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSaved={load}
      />

      <Dialog open={deleting !== null} onOpenChange={(open) => !open && setDeleting(null)}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete restaurant?</DialogTitle>
            <DialogDescription>
              This will permanently remove &ldquo;{deleting?.name}&rdquo;. A backup of the current data file is
              kept automatically.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleting(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
