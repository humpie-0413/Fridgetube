"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import TagInput, { IngredientTag } from "@/components/search/TagInput";
import ServingsSlider from "@/components/search/ServingsSlider";
import ModeToggle from "@/components/search/ModeToggle";
import PhotoRecognizeModal from "@/components/modals/PhotoRecognizeModal";
import TextRecipeModal from "@/components/modals/TextRecipeModal";

export default function HomePage() {
  const router = useRouter();
  const [searchText, setSearchText] = useState("");
  const [tags, setTags] = useState<IngredientTag[]>([]);
  const [servings, setServings] = useState(2);
  const [mode, setMode] = useState<"video" | "recipe">("video");
  const [showPhoto, setShowPhoto] = useState(false);
  const [showText, setShowText] = useState(false);

  // PWA 설치 프롬프트
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    // 서비스 워커 등록
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }

    // 설치 프롬프트 캐치
    const handler = (e: Event) => {
      e.preventDefault();
      setInstallPrompt(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleAddTag = (tag: IngredientTag) => {
    if (!tags.some((t) => t.id === tag.id)) {
      setTags([...tags, tag]);
    }
  };

  const handleRemoveTag = (id: string) => {
    setTags(tags.filter((t) => t.id !== id));
  };

  const handleSearch = () => {
    const params = new URLSearchParams();

    const query =
      searchText.trim() || tags.map((t) => t.name).join(" ");
    if (!query) return;

    params.set("q", query);
    if (tags.length > 0) {
      params.set("ingredients", tags.map((t) => t.name).join(","));
    }
    params.set("servings", String(servings));
    params.set("mode", mode);

    router.push(`/results?${params.toString()}`);
  };

  const handlePhotoConfirm = (ingredients: Array<{ id: string; name: string; category: string }>) => {
    const newTags: IngredientTag[] = ingredients
      .filter((ing) => !tags.some((t) => t.name === ing.name))
      .map((ing) => ({ id: ing.id, name: ing.name, category: ing.category }));
    setTags([...tags, ...newTags]);
  };

  const handleInstall = async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    setInstallPrompt(null);
  };

  const canSearch = tags.length > 0 || searchText.trim().length > 0;

  return (
    <div className="flex min-h-dvh flex-col items-center bg-gray-50 px-4 pb-8 pt-16">
      <div className="w-full max-w-lg">
        {/* 로고 */}
        <div className="mb-10 text-center">
          <h1 className="text-4xl font-bold text-green-600">FridgeTube</h1>
          <p className="mt-2 text-sm text-gray-500">
            냉장고 재료로 맛있는 레시피를 찾아보세요
          </p>
        </div>

        {/* 검색 입력 */}
        <TagInput
          tags={tags}
          onAddTag={handleAddTag}
          onRemoveTag={handleRemoveTag}
          searchText={searchText}
          onSearchTextChange={setSearchText}
          onSearch={handleSearch}
          placeholder="냉장고에 뭐가 있나요? 또는 먹고 싶은 요리를 검색하세요"
        />

        {/* 옵션 */}
        <div className="mt-6 space-y-4">
          <ServingsSlider value={servings} onChange={setServings} />
          <ModeToggle mode={mode} onChange={setMode} />
        </div>

        {/* 빠른 동작 */}
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={() => setShowPhoto(true)}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
          >
            <svg
              className="h-5 w-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            사진으로 인식
          </button>
          <button
            type="button"
            onClick={() => setShowText(true)}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
          >
            <svg
              className="h-5 w-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            레시피 텍스트 입력
          </button>
        </div>

        {/* 검색 버튼 */}
        <button
          onClick={handleSearch}
          disabled={!canSearch}
          className="mt-6 w-full rounded-xl bg-green-600 px-6 py-4 text-base font-semibold text-white shadow-sm transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          검색하기
        </button>

        {/* 채널 관리 링크 */}
        <div className="mt-4 text-center">
          <Link
            href="/channels"
            className="text-sm text-gray-500 transition-colors hover:text-green-600"
          >
            채널 관리 &rarr;
          </Link>
        </div>

        {/* PWA 설치 배너 */}
        {installPrompt && (
          <div className="mt-6 flex items-center justify-between rounded-xl border border-green-200 bg-green-50 px-4 py-3">
            <span className="text-sm text-green-800">홈 화면에 앱을 설치하세요</span>
            <button
              onClick={handleInstall}
              className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
            >
              설치
            </button>
          </div>
        )}
      </div>

      {/* 모달 */}
      <PhotoRecognizeModal
        open={showPhoto}
        onClose={() => setShowPhoto(false)}
        onConfirm={handlePhotoConfirm}
      />
      <TextRecipeModal
        open={showText}
        onClose={() => setShowText(false)}
      />
    </div>
  );
}

// TypeScript: beforeinstallprompt event 타입
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
}
