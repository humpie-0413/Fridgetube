"use client";

interface ModeToggleProps {
  mode: "video" | "recipe";
  onChange: (mode: "video" | "recipe") => void;
}

export default function ModeToggle({ mode, onChange }: ModeToggleProps) {
  return (
    <div className="flex rounded-xl bg-gray-100 p-1">
      <button
        onClick={() => onChange("video")}
        className={`flex-1 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors ${
          mode === "video"
            ? "bg-white text-green-700 shadow-sm"
            : "text-gray-500 hover:text-gray-700"
        }`}
      >
        영상 추천
      </button>
      <button
        onClick={() => onChange("recipe")}
        className={`flex-1 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors ${
          mode === "recipe"
            ? "bg-white text-green-700 shadow-sm"
            : "text-gray-500 hover:text-gray-700"
        }`}
      >
        레시피 변환
      </button>
    </div>
  );
}
