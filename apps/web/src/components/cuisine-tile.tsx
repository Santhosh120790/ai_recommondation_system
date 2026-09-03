import {
  Beef,
  ChefHat,
  Coffee,
  Croissant,
  Fish,
  Flame,
  type LucideIcon,
  Pizza,
  Salad,
  Soup,
  Wine,
} from "lucide-react";

/** Same five brand-adjacent colors as the dashboard's stat tiles
 * (see app/page.tsx TILES) — reused here so restaurant art reads as
 * part of the same system instead of a new palette. */
const TILE_COLORS = ["#eb6834", "#2a78d6", "#1baf7a", "#e87ba4", "#eda100"];

const CUISINE_MATCHES: { keywords: string[]; icon: LucideIcon }[] = [
  { keywords: ["pizza", "pasta", "italian", "trattoria", "osteria"], icon: Pizza },
  { keywords: ["ramen", "noodle", "pho", "soup", "curry", "indian", "thai", "vietnamese"], icon: Soup },
  { keywords: ["sushi", "seafood", "japanese", "fish", "oyster", "seaside"], icon: Fish },
  { keywords: ["steak", "bbq", "barbecue", "burger", "smokehouse", "grill", "diner", "american"], icon: Beef },
  { keywords: ["vegan", "vegetarian", "salad", "farm-to-table", "californian", "plant", "healthy"], icon: Salad },
  { keywords: ["bakery", "patisserie", "brunch", "croissant", "boulangerie"], icon: Croissant },
  { keywords: ["wine", "tapas", "spanish", "mediterranean", "bistro", "french"], icon: Wine },
  { keywords: ["mexican", "taco", "cantina", "spicy", "korean", "fusion"], icon: Flame },
  { keywords: ["cafe", "coffee", "espresso", "roastery"], icon: Coffee },
];

function hashString(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i++) {
    hash = (hash * 31 + value.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

function pickIcon(foodStyle: string, type: string): LucideIcon {
  const text = `${foodStyle} ${type}`.toLowerCase();
  for (const { keywords, icon } of CUISINE_MATCHES) {
    if (keywords.some((keyword) => text.includes(keyword))) return icon;
  }
  return ChefHat;
}

/**
 * A small illustrated "dish art" tile for a restaurant, in place of a photo —
 * restaurants have no image field. Deterministically picks a food-appropriate
 * lucide icon from the cuisine text and a tinted color from the app's
 * existing brand palette, following the same tinted-icon-tile pattern the
 * dashboard already uses for its stat cards.
 */
export function CuisineTile({
  name,
  foodStyle,
  type,
  size = 40,
  className = "",
}: {
  name: string;
  foodStyle: string;
  type: string;
  size?: number;
  className?: string;
}) {
  const Icon = pickIcon(foodStyle, type);
  const color = TILE_COLORS[hashString(name || foodStyle || type) % TILE_COLORS.length];

  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-xl ${className}`}
      style={{ width: size, height: size, backgroundColor: `${color}26`, color }}
    >
      <Icon style={{ width: size * 0.5, height: size * 0.5 }} />
    </div>
  );
}
