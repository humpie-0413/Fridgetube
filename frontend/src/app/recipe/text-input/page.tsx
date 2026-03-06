"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { RecipeData, RecipeIngredient } from "@/lib/api";

function scaleAmount(
  amount: number | null,
  strategy: string,
  ratio: number,
): number | null {
  if (amount === null) return null;
  if (strategy === "linear") return Math.round(amount * ratio * 100) / 100;
  if (strategy === "stepwise") return Math.ceil(amount * ratio);
  return amount;
}

function rescaleIngredients(
  ingredients: RecipeIngredient[],
  baseServings: number,
  newServings: number,
): RecipeIngredient[] {
  const ratio = newServings / baseServings;
  return ingredients.map((ing) => ({
    ...ing,
    amount: scaleAmount(ing.amount, ing.scaling_strategy, ratio),
  }));
}

function formatAmount(amount: number | null, unit: string | null): string {
  if (amount === null) return unit || "";
  const display = Number.isInteger(amount) ? String(amount) : amount.toFixed(1);
  return unit ? `${display}${unit}` : display;
}

const GAP_STYLES: Record<string, { bg: string; text: string }> = {
  SUFFICIENT: { bg: "bg-green-50", text: "text-green-700" },
  PARTIAL: { bg: "bg-yellow-50", text: "text-yellow-700" },
  UNKNOWN_QTY: { bg: "bg-blue-50", text: "text-blue-700" },
  MISSING: { bg: "bg-red-50", text: "text-red-700" },
  BASIC_ASSUMED: { bg: "bg-gray-50", text: "text-gray-500" },
};

export default function TextRecipePage() {
  const router = useRouter();
  const [recipe, setRecipe] = useState<RecipeData | null>(null);
  const [servings, setServings] = useState(2);

  useEffect(() => {
    const stored = sessionStorage.getItem("fridgetube_text_recipe");
    if (stored) {
      try {
        setRecipe(JSON.parse(stored));
      } catch {
        router.replace("/");
      }
    } else {
      router.replace("/");
    }
  }, [router]);

  const displayIngredients = useMemo(() => {
    if (!recipe) return [];
    return rescaleIngredients(recipe.ingredients, recipe.base_servings, servings);
  }, [recipe, servings]);

  if (!recipe) return null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      <button onClick={() => router.push("/")} className="mb-4 text-sm text-gray-500 hover:text-gray-700">
        &larr; 홈으로
      </button>

      <div className="mb-4">
        <h1 className="text-xl font-bold text-gray-900">{recipe.dish_name}</h1>
        <div className="mt-1 flex gap-2 text-xs text-gray-500">
          {recipe.cooking_time_min && <span>조리 {recipe.cooking_time_min}분</span>}
          {recipe.difficulty && <span>난이도: {recipe.difficulty}</span>}
          <span className="rounded bg-blue-100 px-1.5 text-blue-700">텍스트 입력</span>
        </div>
      </div>

      {/* 인원수 */}
      <div className="mb-4 flex items-center gap-3 rounded-xl bg-gray-50 px-4 py-3">
        <label className="whitespace-nowrap text-sm font-medium text-gray-700">인원수</label>
        <button
          onClick={() => setServings(Math.max(1, servings - 1))}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-gray-300 text-gray-500 hover:border-green-500 hover:text-green-600"
        >
          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
          </svg>
        </button>
        <input
          type="range"
          min={1}
          max={10}
          value={servings}
          onChange={(e) => setServings(Number(e.target.value))}
          className="h-2 w-full cursor-pointer appearance-none rounded-full bg-gray-200 accent-green-600"
        />
        <button
          onClick={() => setServings(Math.min(10, servings + 1))}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-gray-300 text-gray-500 hover:border-green-500 hover:text-green-600"
        >
          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>
        <span className="min-w-[3.5rem] text-center text-sm font-semibold text-green-700">
          {servings}인분
        </span>
      </div>

      {/* 재료 */}
      <div className="mb-6 rounded-xl border border-gray-200 bg-white">
        <h2 className="border-b border-gray-100 px-4 py-3 text-sm font-semibold text-gray-800">재료</h2>
        <ul className="divide-y divide-gray-50">
          {displayIngredients.map((ing, i) => {
            const style = GAP_STYLES[ing.gap_status] || GAP_STYLES.MISSING;
            return (
              <li key={i} className={`flex items-center justify-between px-4 py-2.5 ${style.bg}`}>
                <span className={`text-sm ${style.text}`}>
                  {ing.name}
                  {ing.is_optional && <span className="ml-1 text-xs text-gray-400">(선택)</span>}
                </span>
                <span className={`text-sm font-medium ${style.text}`}>
                  {formatAmount(ing.amount, ing.unit)}
                </span>
              </li>
            );
          })}
        </ul>
      </div>

      {/* 조리 순서 */}
      {recipe.steps && recipe.steps.length > 0 && (
        <div className="mb-6 rounded-xl border border-gray-200 bg-white">
          <h2 className="border-b border-gray-100 px-4 py-3 text-sm font-semibold text-gray-800">조리 순서</h2>
          <ol className="divide-y divide-gray-50">
            {recipe.steps.map((step, i) => (
              <li key={i} className="flex gap-3 px-4 py-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-green-100 text-xs font-bold text-green-700">
                  {i + 1}
                </span>
                <p className="text-sm leading-relaxed text-gray-700">{step}</p>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
