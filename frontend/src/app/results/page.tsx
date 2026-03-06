"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { searchVideos, SearchResponse } from "@/lib/api";
import VideoCard from "@/components/results/VideoCard";
import VideoCardSkeleton from "@/components/results/VideoCardSkeleton";
import ErrorState from "@/components/common/ErrorState";
import EmptyState from "@/components/common/EmptyState";

function ResultsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const q = searchParams.get("q") || "";
  const ingredientsStr = searchParams.get("ingredients") || "";
  const servings = Number(searchParams.get("servings")) || 2;
  const mode =
    (searchParams.get("mode") as "video" | "recipe") || "video";

  const [activeTab, setActiveTab] = useState<"local" | "youtube">("local");
  const [sortBy, setSortBy] = useState<"relevance" | "least_missing">(
    "relevance",
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);

  useEffect(() => {
    if (!q) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    const ingredients = ingredientsStr
      ? ingredientsStr.split(",").map((name) => ({ name: name.trim() }))
      : [];

    searchVideos({
      query: q,
      user_ingredients: ingredients,
      servings,
      mode,
      limit: 20,
    })
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [q, ingredientsStr, servings, mode]);

  const sortedVideos = useMemo(() => {
    if (!data?.videos) return [];
    const videos = [...data.videos];
    if (sortBy === "least_missing") {
      videos.sort((a, b) => {
        const aGap = a.ingredient_gap_estimate?.estimated_missing ?? 999;
        const bGap = b.ingredient_gap_estimate?.estimated_missing ?? 999;
        return aGap - bGap;
      });
    }
    return videos;
  }, [data, sortBy]);

  if (!q) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6">
        <EmptyState
          message="검색어를 입력해주세요"
          description="홈에서 재료나 요리명을 검색해보세요"
        />
        <div className="mt-4 text-center">
          <Link
            href="/"
            className="text-sm font-medium text-green-600 hover:text-green-700"
          >
            홈으로 돌아가기
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      {/* 헤더 */}
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="mb-2 text-sm text-gray-500 transition-colors hover:text-gray-700"
        >
          &larr; 돌아가기
        </button>
        <h1 className="text-xl font-bold text-gray-900">
          &ldquo;{q}&rdquo; 검색 결과
        </h1>
        <p className="mt-1 text-sm text-gray-500">{servings}인분 기준</p>
      </div>

      {/* 탭 */}
      <div className="mb-4 flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab("local")}
          className={`border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === "local"
              ? "border-green-600 text-green-700"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          내 채널 추천
        </button>
        <button
          onClick={() => setActiveTab("youtube")}
          className={`border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
            activeTab === "youtube"
              ? "border-green-600 text-green-700"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          YouTube 검색
        </button>
      </div>

      {/* 탭1: 내 채널 추천 */}
      {activeTab === "local" && (
        <>
          <div className="mb-4 flex items-center justify-between">
            <p className="text-xs text-gray-400">
              FridgeTube 분석 | YouTube 제공 아님
            </p>
            <select
              value={sortBy}
              onChange={(e) =>
                setSortBy(e.target.value as "relevance" | "least_missing")
              }
              className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700"
            >
              <option value="relevance">인기순</option>
              <option value="least_missing">부족 적은 순</option>
            </select>
          </div>

          {loading && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <VideoCardSkeleton key={i} />
              ))}
            </div>
          )}

          {error && (
            <ErrorState
              message={error}
              onRetry={() => window.location.reload()}
            />
          )}

          {!loading && !error && sortedVideos.length === 0 && (
            <EmptyState
              message="검색 결과가 없어요"
              description="다른 재료나 요리명으로 검색해보세요"
            />
          )}

          {!loading && !error && sortedVideos.length > 0 && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {sortedVideos.map((video) => (
                <VideoCard
                  key={video.video_id}
                  video={video}
                  showGap={true}
                  servings={servings}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* 탭2: YouTube 검색 (원본 순서 유지, 뱃지/재정렬 금지) */}
      {activeTab === "youtube" && (
        <>
          <p className="mb-4 text-xs text-gray-400">
            YouTube 검색 결과입니다
          </p>
          <EmptyState
            message="YouTube 검색 기능은 준비 중이에요"
            description="search.list API 연동 후 사용할 수 있어요"
          />
        </>
      )}
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-3xl px-4 py-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <VideoCardSkeleton key={i} />
            ))}
          </div>
        </div>
      }
    >
      <ResultsContent />
    </Suspense>
  );
}
