"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  searchChannels,
  ChannelSearchItem,
  getFavoriteChannels,
  FavoriteChannelItem,
  addFavoriteChannel,
  removeFavoriteChannel,
} from "@/lib/api";
import { useToast } from "@/components/common/Toast";
import Loading from "@/components/common/Loading";
import EmptyState from "@/components/common/EmptyState";

function formatSubscribers(count: number | null): string {
  if (!count) return "";
  if (count >= 10_000) return `${(count / 10_000).toFixed(1)}만`;
  return count.toLocaleString();
}

export default function ChannelsPage() {
  const { show } = useToast();

  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<ChannelSearchItem[]>([]);
  const [favorites, setFavorites] = useState<FavoriteChannelItem[]>([]);
  const [loadingFavs, setLoadingFavs] = useState(true);
  const [addingIds, setAddingIds] = useState<Set<string>>(new Set());
  const [removingIds, setRemovingIds] = useState<Set<string>>(new Set());
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // 즐겨찾기 로딩
  const loadFavorites = useCallback(async () => {
    try {
      const res = await getFavoriteChannels();
      setFavorites(res.favorites);
    } catch (err: unknown) {
      show((err as Error).message || "채널 목록을 불러오지 못했어요", "error");
    } finally {
      setLoadingFavs(false);
    }
  }, [show]);

  useEffect(() => {
    loadFavorites();
  }, [loadFavorites]);

  // 검색 디바운스
  useEffect(() => {
    if (query.trim().length === 0) {
      setSearchResults([]);
      return;
    }
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await searchChannels(query.trim());
        setSearchResults(res.channels);
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 400);
    return () => clearTimeout(timerRef.current);
  }, [query]);

  const handleAdd = async (channel: ChannelSearchItem) => {
    setAddingIds((s) => new Set(s).add(channel.channel_id));
    try {
      await addFavoriteChannel(channel.channel_id);
      show(`${channel.name} 추가됨`, "success");
      await loadFavorites();
    } catch (err: unknown) {
      show((err as Error).message || "추가 실패", "error");
    } finally {
      setAddingIds((s) => {
        const next = new Set(s);
        next.delete(channel.channel_id);
        return next;
      });
    }
  };

  const handleRemove = async (fav: FavoriteChannelItem) => {
    setRemovingIds((s) => new Set(s).add(fav.channel_id));
    try {
      await removeFavoriteChannel(fav.channel_id);
      setFavorites((prev) => prev.filter((f) => f.channel_id !== fav.channel_id));
      show(`${fav.channel_name} 삭제됨`, "info");
    } catch (err: unknown) {
      show((err as Error).message || "삭제 실패", "error");
    } finally {
      setRemovingIds((s) => {
        const next = new Set(s);
        next.delete(fav.channel_id);
        return next;
      });
    }
  };

  const favChannelIds = new Set(favorites.map((f) => f.channel_id));

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      {/* 헤더 */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <Link href="/" className="mb-1 block text-sm text-gray-500 hover:text-gray-700">
            &larr; 홈으로
          </Link>
          <h1 className="text-xl font-bold text-gray-900">채널 관리</h1>
        </div>
      </div>

      {/* 채널 검색 */}
      <div className="mb-6">
        <div className="flex items-center gap-2 rounded-xl border-2 border-gray-200 bg-white px-4 py-3 transition-colors focus-within:border-green-500">
          <svg className="h-5 w-5 shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="YouTube 채널 검색..."
            className="w-full bg-transparent text-sm outline-none placeholder:text-gray-400"
          />
          {searching && (
            <div className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-green-600" />
          )}
        </div>

        {/* 검색 결과 */}
        {searchResults.length > 0 && (
          <div className="mt-3 space-y-2">
            {searchResults.map((ch) => (
              <div
                key={ch.channel_id}
                className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-3"
              >
                <div className="h-10 w-10 shrink-0 overflow-hidden rounded-full bg-gray-200">
                  {ch.thumbnail_url && (
                    <img src={ch.thumbnail_url} alt="" className="h-full w-full object-cover" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">{ch.name}</p>
                  {ch.subscriber_count != null && (
                    <p className="text-xs text-gray-400">구독자 {formatSubscribers(ch.subscriber_count)}명</p>
                  )}
                </div>
                <button
                  onClick={() => handleAdd(ch)}
                  disabled={addingIds.has(ch.channel_id) || favChannelIds.has(ch.channel_id)}
                  className="shrink-0 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-green-700 disabled:bg-gray-300"
                >
                  {favChannelIds.has(ch.channel_id)
                    ? "추가됨"
                    : addingIds.has(ch.channel_id)
                      ? "..."
                      : "추가"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 내 채널 */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-700">내 채널 목록</h2>

        {loadingFavs && <Loading message="채널을 불러오는 중..." />}

        {!loadingFavs && favorites.length === 0 && (
          <EmptyState
            message="아직 추가한 채널이 없어요"
            description="위에서 즐겨찾는 요리 채널을 검색해 추가하세요"
          />
        )}

        {!loadingFavs && favorites.length > 0 && (
          <div className="space-y-2">
            {favorites.map((fav) => (
              <div
                key={fav.id}
                className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-3"
              >
                <div className="h-10 w-10 shrink-0 overflow-hidden rounded-full bg-gray-200">
                  {fav.thumbnail_url && (
                    <img src={fav.thumbnail_url} alt="" className="h-full w-full object-cover" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">{fav.channel_name}</p>
                  {fav.subscriber_count != null && (
                    <p className="text-xs text-gray-400">구독자 {formatSubscribers(fav.subscriber_count)}명</p>
                  )}
                </div>
                <button
                  onClick={() => handleRemove(fav)}
                  disabled={removingIds.has(fav.channel_id)}
                  className="shrink-0 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 transition-colors hover:bg-red-50 disabled:opacity-50"
                >
                  {removingIds.has(fav.channel_id) ? "..." : "삭제"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
