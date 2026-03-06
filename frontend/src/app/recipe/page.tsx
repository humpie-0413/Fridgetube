"use client";

import { Suspense } from "react";
import RecipeContent from "./RecipeContent";

function RecipeLoading() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <div className="flex flex-col items-center gap-4 py-16">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-green-600" />
        <p className="text-sm font-medium text-gray-700">로딩 중...</p>
      </div>
    </div>
  );
}

export default function RecipePage() {
  return (
    <Suspense fallback={<RecipeLoading />}>
      <RecipeContent />
    </Suspense>
  );
}
