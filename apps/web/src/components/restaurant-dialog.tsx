"use client";

import { Loader2, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { CuisineTile } from "@/components/cuisine-tile";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api, type Restaurant } from "@/lib/api";

const EMPTY_FORM = {
  name: "",
  location: "",
  type: "",
  food_style: "",
  rating: "",
  price_range: "",
  vibe: "",
  environment: "",
  signatures: "",
  shortcomings: "",
};

type FormState = typeof EMPTY_FORM;

function restaurantToForm(r: Restaurant): FormState {
  return {
    name: r.name,
    location: r.location,
    type: r.type,
    food_style: r.food_style,
    rating: r.rating?.toString() ?? "",
    price_range: r.price_range?.toString() ?? "",
    vibe: r.vibe ?? "",
    environment: r.environment,
    signatures: r.signatures.join(", "),
    shortcomings: r.shortcomings.join(", "),
  };
}

function formToRestaurant(form: FormState, base: Partial<Restaurant>): Restaurant {
  return {
    item_id: base.item_id ?? 0,
    name: form.name,
    location: form.location,
    type: form.type,
    food_style: form.food_style,
    rating: form.rating ? Number(form.rating) : null,
    price_range: form.price_range ? Number(form.price_range) : null,
    vibe: form.vibe || null,
    environment: form.environment,
    signatures: form.signatures ? form.signatures.split(",").map((s) => s.trim()).filter(Boolean) : [],
    shortcomings: form.shortcomings ? form.shortcomings.split(",").map((s) => s.trim()).filter(Boolean) : [],
    source_text: base.source_text ?? "",
  };
}

export function RestaurantDialog({
  restaurant,
  open,
  onOpenChange,
  onSaved,
}: {
  restaurant: Restaurant | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: () => void;
}) {
  const isEdit = restaurant !== null;
  const [rawText, setRawText] = useState("");
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [base, setBase] = useState<Partial<Restaurant>>({});
  const [structuring, setStructuring] = useState(false);
  const [saving, setSaving] = useState(false);
  const [hasPreview, setHasPreview] = useState(false);

  useEffect(() => {
    if (open && restaurant) {
      setForm(restaurantToForm(restaurant));
      setBase(restaurant);
      setHasPreview(true);
      setRawText("");
    } else if (open) {
      setForm(EMPTY_FORM);
      setBase({});
      setHasPreview(false);
      setRawText("");
    }
  }, [open, restaurant]);

  async function structure() {
    if (!rawText.trim()) return;
    setStructuring(true);
    try {
      const preview = await api.previewRestaurant(rawText);
      setForm(restaurantToForm(preview));
      setBase(preview);
      setHasPreview(true);
      toast.success("Structured — review and save below.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to structure text.");
    } finally {
      setStructuring(false);
    }
  }

  async function save() {
    setSaving(true);
    try {
      if (isEdit) {
        await api.updateRestaurant(restaurant.item_id, formToRestaurant(form, base));
        toast.success("Restaurant updated.");
      } else {
        await api.saveRestaurant(formToRestaurant(form, base));
        toast.success("Restaurant saved.");
      }
      onSaved();
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit restaurant" : "Add restaurant"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Update the fields below and save."
              : "Paste a raw description, structure it with AI, then review and save."}
          </DialogDescription>
        </DialogHeader>

        {!isEdit && (
          <div className="flex flex-col gap-2">
            <Label>Raw description</Label>
            <Textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="A cozy 24-hour diner in Reseda called The Night Owl, serving classic American comfort food, rated 4.0/5. Price range: $$"
              className="min-h-[80px]"
            />
            <Button type="button" variant="secondary" onClick={structure} disabled={structuring || !rawText.trim()}>
              {structuring ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
              Structure with AI
            </Button>
          </div>
        )}

        {hasPreview && (
          <div className="flex items-center gap-3 rounded-lg border bg-muted/40 p-3">
            <CuisineTile name={form.name} foodStyle={form.food_style} type={form.type} size={44} />
            <div className="min-w-0">
              <div className="truncate text-sm font-medium">{form.name || "Untitled restaurant"}</div>
              <div className="truncate text-xs text-muted-foreground">
                {form.food_style || form.type || "Illustrated dish art preview"}
              </div>
            </div>
          </div>
        )}

        {hasPreview && (
          <div className="grid grid-cols-2 gap-3">
            <Field label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
            <Field label="Location" value={form.location} onChange={(v) => setForm({ ...form, location: v })} />
            <Field label="Type" value={form.type} onChange={(v) => setForm({ ...form, type: v })} />
            <Field
              label="Food style"
              value={form.food_style}
              onChange={(v) => setForm({ ...form, food_style: v })}
            />
            <Field
              label="Rating (0-5)"
              value={form.rating}
              onChange={(v) => setForm({ ...form, rating: v })}
            />
            <Field
              label="Price range (1-4)"
              value={form.price_range}
              onChange={(v) => setForm({ ...form, price_range: v })}
            />
            <Field label="Vibe" value={form.vibe} onChange={(v) => setForm({ ...form, vibe: v })} />
            <Field
              label="Environment"
              value={form.environment}
              onChange={(v) => setForm({ ...form, environment: v })}
            />
            <Field
              label="Signatures (comma-separated)"
              value={form.signatures}
              onChange={(v) => setForm({ ...form, signatures: v })}
              className="col-span-2"
            />
            <Field
              label="Shortcomings (comma-separated)"
              value={form.shortcomings}
              onChange={(v) => setForm({ ...form, shortcomings: v })}
              className="col-span-2"
            />
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={save} disabled={!hasPreview || saving}>
            {saving && <Loader2 className="size-4 animate-spin" />}
            {isEdit ? "Save changes" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  value,
  onChange,
  className,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-1 ${className ?? ""}`}>
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
