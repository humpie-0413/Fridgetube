"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { searchIngredients, IngredientItem } from "@/lib/api";

export interface IngredientTag {
  id: string;
  name: string;
  category: string;
}

interface TagInputProps {
  tags: IngredientTag[];
  onAddTag: (tag: IngredientTag) => void;
  onRemoveTag: (id: string) => void;
  searchText: string;
  onSearchTextChange: (text: string) => void;
  onSearch?: () => void;
  placeholder?: string;
}

export default function TagInput({
  tags,
  onAddTag,
  onRemoveTag,
  searchText,
  onSearchTextChange,
  onSearch,
  placeholder,
}: TagInputProps) {
  const [suggestions, setSuggestions] = useState<IngredientItem[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // 디바운스 자동완성
  useEffect(() => {
    if (searchText.trim().length === 0) {
      setSuggestions([]);
      setShowDropdown(false);
      return;
    }

    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await searchIngredients(searchText.trim());
        const filtered = res.ingredients.filter(
          (i) => !tags.some((t) => t.id === i.id),
        );
        setSuggestions(filtered);
        setShowDropdown(filtered.length > 0);
      } catch {
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timerRef.current);
  }, [searchText, tags]);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleSelect = useCallback(
    (item: IngredientItem) => {
      onAddTag({ id: item.id, name: item.name, category: item.category });
      onSearchTextChange("");
      setShowDropdown(false);
    },
    [onAddTag, onSearchTextChange],
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (showDropdown && suggestions.length > 0) {
        handleSelect(suggestions[0]);
      } else if (onSearch) {
        onSearch();
      }
    }
  };

  return (
    <div ref={wrapperRef} className="relative w-full">
      <div className="flex items-center gap-2 rounded-2xl border-2 border-gray-200 bg-white px-4 py-3.5 transition-colors focus-within:border-green-500">
        <svg
          className="h-5 w-5 shrink-0 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          type="text"
          value={searchText}
          onChange={(e) => onSearchTextChange(e.target.value)}
          onFocus={() => suggestions.length > 0 && setShowDropdown(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full bg-transparent text-base outline-none placeholder:text-gray-400"
        />
        {loading && (
          <div className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-gray-300 border-t-green-600" />
        )}
      </div>

      {/* 선택된 재료 태그 */}
      {tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {tags.map((tag) => (
            <span
              key={tag.id}
              className="inline-flex items-center gap-1 rounded-full bg-green-100 px-3 py-1.5 text-sm font-medium text-green-800"
            >
              {tag.name}
              <button
                onClick={() => onRemoveTag(tag.id)}
                className="ml-0.5 rounded-full p-0.5 transition-colors hover:bg-green-200"
                aria-label={`${tag.name} 삭제`}
              >
                <svg
                  className="h-3.5 w-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </span>
          ))}
        </div>
      )}

      {/* 자동완성 드롭다운 */}
      {showDropdown && (
        <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-60 overflow-y-auto rounded-xl border border-gray-200 bg-white py-1 shadow-lg">
          {suggestions.map((item) => (
            <button
              key={item.id}
              onClick={() => handleSelect(item)}
              className="flex w-full items-center justify-between px-4 py-2.5 text-left transition-colors hover:bg-green-50"
            >
              <span className="text-sm font-medium text-gray-900">
                {item.name}
              </span>
              <span className="text-xs text-gray-400">{item.category}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
