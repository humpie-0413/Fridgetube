"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { recognizeIngredients, RecognizedIngredient } from "@/lib/api";

const BASIC_SEASONINGS = ["소금", "간장", "식용유", "고춧가루", "참기름", "설탕", "후추", "다진마늘", "맛술", "식초"];
const MAX_SIZE = 1280;

interface PhotoRecognizeModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (ingredients: Array<{ id: string; name: string; category: string }>) => void;
}

interface RecognizedTag {
  name: string;
  alternatives: string[];
  showAlts: boolean;
}

function resizeImage(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      let w = img.width;
      let h = img.height;
      if (w > MAX_SIZE || h > MAX_SIZE) {
        const ratio = Math.min(MAX_SIZE / w, MAX_SIZE / h);
        w = Math.round(w * ratio);
        h = Math.round(h * ratio);
      }
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d")!;
      ctx.drawImage(img, 0, 0, w, h);
      resolve(canvas.toDataURL("image/jpeg", 0.8));
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

export default function PhotoRecognizeModal({ open, onClose, onConfirm }: PhotoRecognizeModalProps) {
  const [tags, setTags] = useState<RecognizedTag[]>([]);
  const [seasonings, setSeasonings] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // ESC로 닫기
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (open) document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  // 리셋
  useEffect(() => {
    if (open) {
      setTags([]);
      setSeasonings(new Set());
      setError(null);
      setPreview(null);
      setLoading(false);
    }
  }, [open]);

  const handleFile = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    try {
      const dataUrl = await resizeImage(file);
      setPreview(dataUrl);
      const res = await recognizeIngredients(dataUrl);
      setTags(
        res.ingredients.map((ing: RecognizedIngredient) => ({
          name: ing.name,
          alternatives: ing.alternatives,
          showAlts: false,
        })),
      );
    } catch (err: unknown) {
      setError((err as Error).message || "인식에 실패했어요");
    } finally {
      setLoading(false);
    }
  }, []);

  const removeTag = (index: number) => {
    setTags((prev) => prev.filter((_, i) => i !== index));
  };

  const selectAlternative = (index: number, alt: string) => {
    setTags((prev) =>
      prev.map((t, i) => (i === index ? { ...t, name: alt, showAlts: false } : t)),
    );
  };

  const toggleAlts = (index: number) => {
    setTags((prev) =>
      prev.map((t, i) => (i === index ? { ...t, showAlts: !t.showAlts } : t)),
    );
  };

  const toggleSeasoning = (name: string) => {
    setSeasonings((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const handleConfirm = () => {
    const result = [
      ...tags.map((t) => ({ id: t.name, name: t.name, category: "인식됨" })),
      ...Array.from(seasonings).map((s) => ({ id: s, name: s, category: "양념" })),
    ];
    onConfirm(result);
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-2xl bg-white"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">사진으로 재료 인식</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5">
          {/* 파일 선택 */}
          <input ref={fileRef} type="file" accept="image/*" capture="environment" onChange={handleFile} className="hidden" />
          {!preview && !loading && (
            <button
              onClick={() => fileRef.current?.click()}
              className="flex w-full flex-col items-center gap-2 rounded-xl border-2 border-dashed border-gray-300 px-6 py-10 text-gray-500 transition-colors hover:border-green-400 hover:text-green-600"
            >
              <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span className="text-sm font-medium">사진 선택 또는 촬영</span>
              <span className="text-xs text-gray-400">최대 4MB</span>
            </button>
          )}

          {/* 로딩 */}
          {loading && (
            <div className="flex flex-col items-center gap-3 py-10">
              <div className="h-8 w-8 animate-spin rounded-full border-3 border-gray-200 border-t-green-600" />
              <p className="text-sm text-gray-500">재료를 인식하고 있어요...</p>
            </div>
          )}

          {/* 미리보기 */}
          {preview && !loading && (
            <div className="mb-4">
              <img src={preview} alt="업로드 이미지" className="w-full rounded-lg object-contain" style={{ maxHeight: 200 }} />
              <button
                onClick={() => { setPreview(null); setTags([]); fileRef.current?.click(); }}
                className="mt-2 text-xs text-green-600 hover:text-green-700"
              >
                다른 사진 선택
              </button>
            </div>
          )}

          {/* 에러 */}
          {error && (
            <p className="mb-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</p>
          )}

          {/* 인식 결과 */}
          {tags.length > 0 && (
            <div className="mb-4">
              <p className="mb-2 text-sm font-medium text-gray-700">인식된 재료</p>
              <div className="flex flex-wrap gap-2">
                {tags.map((tag, i) => (
                  <div key={i} className="relative">
                    <span
                      onClick={() => tag.alternatives.length > 0 && toggleAlts(i)}
                      className={`inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-sm font-medium ${
                        tag.alternatives.length > 0
                          ? "cursor-pointer bg-green-100 text-green-800 hover:bg-green-200"
                          : "bg-green-100 text-green-800"
                      }`}
                    >
                      {tag.name}
                      {tag.alternatives.length > 0 && (
                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      )}
                    </span>
                    <button
                      onClick={() => removeTag(i)}
                      className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-gray-500 text-[10px] text-white hover:bg-gray-700"
                    >
                      x
                    </button>
                    {/* 유사 후보 드롭다운 */}
                    {tag.showAlts && tag.alternatives.length > 0 && (
                      <div className="absolute left-0 top-full z-10 mt-1 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
                        {tag.alternatives.map((alt) => (
                          <button
                            key={alt}
                            onClick={() => selectAlternative(i, alt)}
                            className="block w-full whitespace-nowrap px-4 py-1.5 text-left text-sm text-gray-700 hover:bg-green-50"
                          >
                            {alt}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 기본 양념 체크 */}
          {tags.length > 0 && (
            <div className="mb-4">
              <p className="mb-2 text-sm font-medium text-gray-700">기본 양념 체크</p>
              <div className="flex flex-wrap gap-2">
                {BASIC_SEASONINGS.map((s) => (
                  <button
                    key={s}
                    onClick={() => toggleSeasoning(s)}
                    className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                      seasonings.has(s)
                        ? "bg-green-600 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 확인 버튼 */}
          {tags.length > 0 && (
            <button
              onClick={handleConfirm}
              className="w-full rounded-xl bg-green-600 py-3 text-sm font-semibold text-white transition-colors hover:bg-green-700"
            >
              확인 ({tags.length + seasonings.size}개 재료)
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
