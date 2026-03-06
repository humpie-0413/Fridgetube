"use client";

import { useEffect, useState } from "react";

export default function Loading({ message = "불러오는 중..." }: { message?: string }) {
  const [showColdStart, setShowColdStart] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShowColdStart(true), 5000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="h-8 w-8 animate-spin rounded-full border-3 border-gray-200 border-t-green-600" />
      <p className="mt-3 text-sm text-gray-500">{message}</p>
      {showColdStart && (
        <p className="mt-1 text-xs text-gray-400">
          서버를 깨우는 중이에요... 최대 30초 소요될 수 있어요
        </p>
      )}
    </div>
  );
}
