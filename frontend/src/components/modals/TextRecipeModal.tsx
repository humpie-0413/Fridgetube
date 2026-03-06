"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { parseTextRecipe, RecipeData } from "@/lib/api";

interface TextRecipeModalProps {
  open: boolean;
  onClose: () => void;
}

export default function TextRecipeModal({ open, onClose }: TextRecipeModalProps) {
  const router = useRouter();
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<RecipeData | null>(null);

  // ESC로 닫기
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (open) document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  useEffect(() => {
    if (open) {
      setText("");
      setError(null);
      setPreview(null);
      setLoading(false);
    }
  }, [open]);

  const handleParse = async () => {
    if (text.trim().length < 10) {
      setError("최소 10자 이상 입력해주세요");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await parseTextRecipe({
        text: text.trim(),
        servings: 2,
        user_ingredients: [],
      });
      setPreview(res.recipe);
    } catch (err: unknown) {
      setError((err as Error).message || "구조화에 실패했어요");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = () => {
    if (!preview) return;
    // text 레시피는 source_id가 text_해시이므로, /recipe/text 경로로 이동
    // 실제로는 parse-text 결과를 캐시하고 상세 페이지에서 표시
    // 여기서는 로컬 스토리지에 저장 후 이동
    sessionStorage.setItem("fridgetube_text_recipe", JSON.stringify(preview));
    onClose();
    router.push("/recipe/text-input");
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-2xl bg-white"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">레시피 텍스트 입력</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5">
          {!preview ? (
            <>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="레시피를 붙여넣으세요...&#10;&#10;예: 김치찌개 (2인분)&#10;재료: 김치 300g, 돼지고기 150g, 두부 1/2모...&#10;만드는 법:&#10;1. 돼지고기를 볶는다..."
                rows={10}
                className="w-full resize-none rounded-xl border-2 border-gray-200 p-4 text-sm outline-none transition-colors placeholder:text-gray-400 focus:border-green-500"
              />

              {error && (
                <p className="mt-2 text-sm text-red-500">{error}</p>
              )}

              <button
                onClick={handleParse}
                disabled={loading || text.trim().length < 10}
                className="mt-4 w-full rounded-xl bg-green-600 py-3 text-sm font-semibold text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-gray-300"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    구조화 중...
                  </span>
                ) : (
                  "구조화"
                )}
              </button>
            </>
          ) : (
            <>
              {/* 미리보기 */}
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                <h3 className="text-base font-bold text-gray-900">{preview.dish_name}</h3>
                <p className="mt-1 text-xs text-gray-500">
                  {preview.base_servings}인분
                  {preview.cooking_time_min && ` | ${preview.cooking_time_min}분`}
                  {preview.difficulty && ` | ${preview.difficulty}`}
                </p>

                <div className="mt-3">
                  <p className="mb-1 text-xs font-semibold text-gray-600">재료 ({preview.ingredients.length}개)</p>
                  <div className="flex flex-wrap gap-1">
                    {preview.ingredients.slice(0, 10).map((ing, i) => (
                      <span key={i} className="rounded-full bg-white px-2 py-0.5 text-xs text-gray-700">
                        {ing.name}
                        {ing.amount != null && ` ${ing.amount}${ing.unit || ""}`}
                      </span>
                    ))}
                    {preview.ingredients.length > 10 && (
                      <span className="text-xs text-gray-400">+{preview.ingredients.length - 10}개</span>
                    )}
                  </div>
                </div>

                {preview.steps && preview.steps.length > 0 && (
                  <div className="mt-3">
                    <p className="mb-1 text-xs font-semibold text-gray-600">조리 순서 ({preview.steps.length}단계)</p>
                    <p className="text-xs text-gray-500">{preview.steps[0].slice(0, 60)}...</p>
                  </div>
                )}
              </div>

              <div className="mt-4 flex gap-3">
                <button
                  onClick={() => setPreview(null)}
                  className="flex-1 rounded-xl border border-gray-200 py-3 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
                >
                  다시 입력
                </button>
                <button
                  onClick={handleConfirm}
                  className="flex-1 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white transition-colors hover:bg-green-700"
                >
                  확인
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
