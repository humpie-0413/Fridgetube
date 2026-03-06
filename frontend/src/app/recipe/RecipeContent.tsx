"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  extractRecipe,
  RecipeData,
  RecipeIngredient,
} from "@/lib/api";
import Loading from "@/components/common/Loading";
import ErrorState from "@/components/common/ErrorState";

// ── scaling 로직 (프론트 실시간 재계산) ──

function scaleAmount(
  amount: number | null,
  strategy: string,
  ratio: number,
): number | null {
  if (amount === null) return null;
  if (strategy === "linear") return Math.round(amount * ratio * 100) / 100;
  if (strategy === "stepwise") return Math.ceil(amount * ratio);
  // to_taste, fixed
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

// ── GAP 색상 ──

const GAP_STYLES: Record<string, { bg: string; text: string; icon: string }> = {
  SUFFICIENT: { bg: "bg-green-50", text: "text-green-700", icon: "check" },
  PARTIAL: { bg: "bg-yellow-50", text: "text-yellow-700", icon: "alert" },
  UNKNOWN_QTY: { bg: "bg-blue-50", text: "text-blue-700", icon: "question" },
  MISSING: { bg: "bg-red-50", text: "text-red-700", icon: "x" },
  BASIC_ASSUMED: { bg: "bg-gray-50", text: "text-gray-500", icon: "minus" },
};

function GapIcon({ status }: { status: string }) {
  const s = GAP_STYLES[status] || GAP_STYLES.MISSING;
  const icons: Record<string, string> = {
    check: "M5 13l4 4L19 7",
    alert: "M12 9v2m0 4h.01",
    question: "M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01",
    x: "M6 18L18 6M6 6l12 12",
    minus: "M20 12H4",
  };
  return (
    <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full ${s.bg}`}>
      <svg className={`h-3 w-3 ${s.text}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={icons[s.icon]} />
      </svg>
    </span>
  );
}

function formatAmount(amount: number | null, unit: string | null): string {
  if (amount === null) return unit || "";
  const display = Number.isInteger(amount) ? String(amount) : amount.toFixed(1);
  return unit ? `${display}${unit}` : display;
}

// ── 메인 컴포넌트 ──

export default function RecipeContent() {
  const searchParams = useSearchParams();
  const videoId = searchParams.get("id") || "";
  const initialServings = Number(searchParams.get("servings")) || 2;

  const [recipe, setRecipe] = useState<RecipeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"original" | "scaled">("scaled");
  const [servings, setServings] = useState(initialServings);

  // URL에서 user_ingredients 복원
  const ingredientsStr = searchParams.get("ingredients") || "";
  const userIngredients = useMemo(
    () =>
      ingredientsStr
        ? ingredientsStr.split(",").map((n) => ({ name: n.trim() }))
        : [],
    [ingredientsStr],
  );

  const fetchRecipe = useCallback(() => {
    setLoading(true);
    setError(null);
    setErrorCode(null);
    extractRecipe({
      video_id: videoId,
      servings: initialServings,
      user_ingredients: userIngredients,
    })
      .then((res) => setRecipe(res.recipe))
      .catch((err) => {
        setError(err.message || "레시피를 추출하지 못했어요");
        // 에러 코드 추출
        try {
          const detail = JSON.parse(err.message);
          setErrorCode(detail?.code);
        } catch {
          if (err.message?.includes("EXTRACTION_FAILED")) {
            setErrorCode("EXTRACTION_FAILED");
          }
        }
      })
      .finally(() => setLoading(false));
  }, [videoId, initialServings, userIngredients]);

  useEffect(() => {
    fetchRecipe();
  }, [fetchRecipe]);

  // 프론트 실시간 재계산
  const displayIngredients = useMemo(() => {
    if (!recipe) return [];
    if (activeTab === "original") {
      // 원본: base_servings 기준 그대로
      return rescaleIngredients(
        recipe.ingredients,
        recipe.base_servings,
        recipe.base_servings,
      );
    }
    return rescaleIngredients(
      recipe.ingredients,
      recipe.base_servings,
      servings,
    );
  }, [recipe, activeTab, servings]);

  // 장보기 목록 (MISSING + PARTIAL만)
  const shoppingList = useMemo(
    () => displayIngredients.filter((i) => i.gap_status === "MISSING" || i.gap_status === "PARTIAL"),
    [displayIngredients],
  );

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12">
        <div className="flex flex-col items-center gap-4 py-16">
          <div className="relative">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-green-600" />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-gray-700">AI가 레시피를 분석 중이에요...</p>
            <p className="mt-1 text-xs text-gray-400">최대 15초 정도 걸릴 수 있어요</p>
          </div>
          <div className="mt-2 h-1.5 w-48 overflow-hidden rounded-full bg-gray-200">
            <div className="animate-progress h-full rounded-full bg-green-500" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !recipe) {
    const isExtractionFailed = errorCode === "EXTRACTION_FAILED";
    return (
      <div className="mx-auto max-w-2xl px-4 py-6">
        <Link href="/" className="mb-4 inline-block text-sm text-gray-500 hover:text-gray-700">
          &larr; 홈으로
        </Link>

        {/* 영상은 보여주기 */}
        <div className="mb-6 overflow-hidden rounded-xl bg-black" style={{ aspectRatio: "16/9" }}>
          <iframe
            src={`https://www.youtube.com/embed/${videoId}`}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            className="h-full w-full"
            title="YouTube video"
          />
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100">
            <svg className="h-6 w-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01" />
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-800">
            {isExtractionFailed
              ? "레시피를 자동 추출하지 못했어요"
              : error}
          </p>
          <p className="mt-2 text-xs text-gray-500">
            {isExtractionFailed
              ? "영상을 직접 보시거나, 레시피 텍스트를 입력해주세요"
              : "다시 시도해보세요"}
          </p>
          <div className="mt-4 flex justify-center gap-3">
            <a
              href={`https://www.youtube.com/watch?v=${videoId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              영상 보기
            </a>
            {!isExtractionFailed && (
              <button
                onClick={fetchRecipe}
                className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700"
              >
                다시 시도
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      {/* 뒤로가기 */}
      <button onClick={() => history.back()} className="mb-4 text-sm text-gray-500 hover:text-gray-700">
        &larr; 돌아가기
      </button>

      {/* YouTube 임베드 */}
      <div className="mb-6 overflow-hidden rounded-xl bg-black" style={{ aspectRatio: "16/9" }}>
        <iframe
          src={`https://www.youtube.com/embed/${videoId}`}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          className="h-full w-full"
          title="YouTube video"
        />
      </div>

      {/* 요리명 + 배너 */}
      <div className="mb-4">
        <h1 className="text-xl font-bold text-gray-900">{recipe.dish_name}</h1>
        <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-500">
          {recipe.cooking_time_min && <span>조리 {recipe.cooking_time_min}분</span>}
          {recipe.difficulty && <span>난이도: {recipe.difficulty}</span>}
        </div>
      </div>

      {/* 경고 배너 */}
      {(recipe.base_servings_source === "inferred" || recipe.base_servings_source === "default") && (
        <div className="mb-3 rounded-lg bg-yellow-50 px-4 py-2.5 text-xs text-yellow-800">
          인분은 AI 추정치입니다
        </div>
      )}
      {recipe.confidence_score < 0.7 && (
        <div className="mb-3 rounded-lg bg-yellow-50 px-4 py-2.5 text-xs text-yellow-800">
          추출 정확도가 낮을 수 있습니다 (신뢰도: {Math.round(recipe.confidence_score * 100)}%)
        </div>
      )}

      {/* 탭 */}
      <div className="mb-4 flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab("original")}
          className={`border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === "original"
              ? "border-green-600 text-green-700"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          원본 레시피 ({recipe.base_servings}인분)
        </button>
        <button
          onClick={() => setActiveTab("scaled")}
          className={`border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === "scaled"
              ? "border-green-600 text-green-700"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          내 인원수로 변환
        </button>
      </div>

      {/* 인원수 슬라이더 (변환 탭에서만) */}
      {activeTab === "scaled" && (
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
      )}

      {/* GAP 요약 */}
      <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-gray-800">
            {recipe.ingredient_gap_summary.verdict}
          </p>
          <span className={`rounded-full px-2.5 py-1 text-xs font-bold text-white ${
            recipe.ingredient_gap_summary.gap_score >= 0.9
              ? "bg-green-500"
              : recipe.ingredient_gap_summary.gap_score >= 0.7
                ? "bg-yellow-500"
                : "bg-red-500"
          }`}>
            {Math.round(recipe.ingredient_gap_summary.gap_score * 100)}%
          </span>
        </div>
        <p className="mt-1 text-xs text-gray-400">FridgeTube 분석 | YouTube 제공 아님</p>
      </div>

      {/* 재료 체크리스트 */}
      <div className="mb-6 rounded-xl border border-gray-200 bg-white">
        <h2 className="border-b border-gray-100 px-4 py-3 text-sm font-semibold text-gray-800">
          재료
        </h2>
        <ul className="divide-y divide-gray-50">
          {displayIngredients.map((ing, i) => {
            const style = GAP_STYLES[ing.gap_status] || GAP_STYLES.MISSING;
            return (
              <li key={i} className={`flex items-center gap-3 px-4 py-2.5 ${style.bg}`}>
                <GapIcon status={ing.gap_status} />
                <span className={`flex-1 text-sm ${style.text}`}>
                  {ing.name}
                  {ing.is_optional && (
                    <span className="ml-1 text-xs text-gray-400">(선택)</span>
                  )}
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
          <h2 className="border-b border-gray-100 px-4 py-3 text-sm font-semibold text-gray-800">
            조리 순서
          </h2>
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

      {/* 장보기 목록 */}
      {shoppingList.length > 0 && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50">
          <h2 className="border-b border-red-100 px-4 py-3 text-sm font-semibold text-red-800">
            장보기 목록
          </h2>
          <ul className="divide-y divide-red-100">
            {shoppingList.map((ing, i) => (
              <li key={i} className="flex items-center justify-between px-4 py-2.5">
                <span className="text-sm text-red-700">{ing.name}</span>
                <span className="text-sm font-medium text-red-600">
                  {formatAmount(ing.amount, ing.unit)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
