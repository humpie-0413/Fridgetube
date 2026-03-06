const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60000);

  try {
    const res = await fetch(url, { ...init, signal: controller.signal });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new ApiError(
        res.status,
        body?.error?.message || body?.detail || "요청에 실패했어요",
      );
    }
    return res.json();
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, "서버 응답 시간이 초과되었어요 (60초). 잠시 후 다시 시도해주세요.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

// ── 재료 자동완성 ──

export interface IngredientItem {
  id: string;
  name: string;
  category: string;
}

interface IngredientsSearchResponse {
  ingredients: IngredientItem[];
}

export function searchIngredients(
  q: string,
  limit = 10,
): Promise<IngredientsSearchResponse> {
  return request(
    `${BASE}/v1/ingredients/search?q=${encodeURIComponent(q)}&limit=${limit}`,
  );
}

// ── 영상 검색 ──

export interface SearchRequest {
  query: string;
  user_ingredients: Array<{ name: string; amount?: number; unit?: string }>;
  servings: number;
  mode: "video" | "recipe";
  sort_by?: "relevance" | "view_count" | "least_missing";
  limit?: number;
}

export interface GapEstimate {
  source: string;
  is_estimate: boolean;
  estimated_missing: number;
  gap_score: number;
}

export interface VideoResult {
  video_id: string;
  title: string;
  channel: { id: string; name: string };
  thumbnail: string;
  view_count: number | null;
  duration_seconds: number | null;
  has_cached_recipe: boolean;
  ingredient_gap_estimate: GapEstimate | null;
}

export interface SearchResponse {
  search_type: string;
  detected_query: {
    dish_name?: string;
    cuisine_type?: string;
    ingredient_names: string[];
    dish_candidates?: Array<Record<string, unknown>>;
  };
  videos: VideoResult[];
  next_cursor: string | null;
  total_estimate: number;
}

export function searchVideos(body: SearchRequest): Promise<SearchResponse> {
  return request(`${BASE}/v1/search/videos`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ── 레시피 추출 ──

export interface RecipeIngredient {
  name: string;
  amount: number | null;
  unit: string | null;
  scaling_strategy: string;
  is_optional: boolean;
  gap_status: string;
  gap_detail: {
    user_has?: number | null;
    recipe_needs?: number | null;
    shortage?: number | null;
    reason?: string;
  };
}

export interface RecipeData {
  dish_name: string;
  base_servings: number;
  base_servings_source: string;
  requested_servings: number;
  confidence_score: number;
  prompt_version: string;
  ingredients: RecipeIngredient[];
  steps: string[] | null;
  cooking_time_min: number | null;
  difficulty: string | null;
  ingredient_gap_summary: {
    total: number;
    sufficient: number;
    partial: number;
    missing: number;
    unknown_qty: number;
    basic_assumed: number;
    gap_score: number;
    verdict: string;
    shopping_list: Array<{ name: string; amount: string }>;
  };
}

export interface ExtractRequest {
  video_id: string;
  servings: number;
  user_ingredients: Array<{ name: string; amount?: number; unit?: string }>;
}

export function extractRecipe(
  body: ExtractRequest,
): Promise<{ recipe: RecipeData }> {
  return request(`${BASE}/v1/recipe/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export interface ParseTextRequest {
  text: string;
  servings: number;
  user_ingredients: Array<{ name: string; amount?: number; unit?: string }>;
}

export function parseTextRecipe(
  body: ParseTextRequest,
): Promise<{ recipe: RecipeData }> {
  return request(`${BASE}/v1/recipe/parse-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ── 채널 관리 ──

export interface ChannelSearchItem {
  channel_id: string;
  name: string;
  thumbnail_url: string | null;
  subscriber_count: number | null;
  description: string | null;
}

export function searchChannels(
  q: string,
  limit = 5,
): Promise<{ channels: ChannelSearchItem[] }> {
  return request(
    `${BASE}/v1/channels/search?q=${encodeURIComponent(q)}&limit=${limit}`,
  );
}

export interface FavoriteChannelItem {
  id: string;
  channel_id: string;
  channel_name: string;
  thumbnail_url: string | null;
  subscriber_count: number | null;
}

export function getFavoriteChannels(
  sessionId?: string,
): Promise<{ favorites: FavoriteChannelItem[] }> {
  const headers: Record<string, string> = {};
  if (sessionId) headers["X-Session-Id"] = sessionId;
  return request(`${BASE}/v1/channels/favorites`, { headers });
}

export function addFavoriteChannel(
  channelId: string,
  sessionId?: string,
): Promise<{ id: string; channel_id: string; channel_name: string }> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (sessionId) headers["X-Session-Id"] = sessionId;
  return request(`${BASE}/v1/channels/favorites`, {
    method: "POST",
    headers,
    body: JSON.stringify({ channel_id: channelId }),
  });
}

export function removeFavoriteChannel(
  channelId: string,
  sessionId?: string,
): Promise<{ deleted: boolean }> {
  const headers: Record<string, string> = {};
  if (sessionId) headers["X-Session-Id"] = sessionId;
  return request(`${BASE}/v1/channels/favorites/${channelId}`, {
    method: "DELETE",
    headers,
  });
}

// ── 사진 인식 ──

export interface RecognizedIngredient {
  name: string;
  estimated_amount: number | null;
  unit: string | null;
  confidence: number;
  alternatives: string[];
}

export function recognizeIngredients(
  imageBase64: string,
): Promise<{ ingredients: RecognizedIngredient[] }> {
  return request(`${BASE}/v1/ingredients/recognize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: imageBase64 }),
  });
}
