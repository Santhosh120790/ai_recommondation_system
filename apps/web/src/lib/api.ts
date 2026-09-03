const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Restaurant {
  item_id: number;
  name: string;
  location: string;
  type: string;
  food_style: string;
  rating: number | null;
  price_range: number | null;
  signatures: string[];
  vibe: string | null;
  environment: string;
  shortcomings: string[];
  source_text: string;
}

export interface Recipe {
  id: number;
  name: string;
  cuisine: string;
  servings: number;
  prep_time: string;
  cook_time: string;
  total_time: string;
  ingredients: string[];
  directions: string[];
  image_path: string | null;
  image_description: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export interface Stats {
  restaurants: number;
  recipes: number;
  reviews: number;
  cuisines: number;
  locations: number;
  avg_rating: number | null;
}

export const api = {
  getStats: () => request<Stats>("/stats"),
  listRestaurants: () => request<Restaurant[]>("/restaurants"),
  getRestaurant: (id: number) => request<Restaurant>(`/restaurants/${id}`),
  previewRestaurant: (rawText: string) =>
    request<Restaurant>("/restaurants/preview", {
      method: "POST",
      body: JSON.stringify({ raw_text: rawText }),
    }),
  saveRestaurant: (restaurant: Restaurant) =>
    request<Restaurant>("/restaurants", {
      method: "POST",
      body: JSON.stringify(restaurant),
    }),
  updateRestaurant: (id: number, updates: Partial<Restaurant>) =>
    request<Restaurant>(`/restaurants/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ updates }),
    }),
  deleteRestaurant: (id: number) =>
    request<void>(`/restaurants/${id}`, { method: "DELETE" }),
  listRecipes: () => request<Recipe[]>("/recipes"),
};

export interface ChatEvent {
  stage: "profile" | "retrieve" | "trends" | "styles" | "nutrition" | "recommend" | "done" | "error";
  data: Record<string, unknown>;
}

/** Manually parses the SSE stream from POST /chat/stream (EventSource doesn't support
 * POST bodies, so we read the fetch body stream and parse `event:`/`data:` blocks). */
export async function streamChat(
  message: string,
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`Chat stream failed: ${res.status} ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const lines = block.split("\n").filter((l) => !l.startsWith(":"));
      const eventLine = lines.find((l) => l.startsWith("event:"));
      const dataLine = lines.find((l) => l.startsWith("data:"));
      if (!eventLine || !dataLine) continue;

      const stage = eventLine.slice("event:".length).trim() as ChatEvent["stage"];
      const data = JSON.parse(dataLine.slice("data:".length).trim());
      onEvent({ stage, data });
    }
  }
}
