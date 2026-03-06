"use client";

interface ServingsSliderProps {
  value: number;
  onChange: (value: number) => void;
}

export default function ServingsSlider({
  value,
  onChange,
}: ServingsSliderProps) {
  return (
    <div className="flex items-center gap-3">
      <label className="whitespace-nowrap text-sm font-medium text-gray-700">
        인원수
      </label>
      <button
        onClick={() => onChange(Math.max(1, value - 1))}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-gray-300 text-gray-500 transition-colors hover:border-green-500 hover:text-green-600"
        aria-label="인원수 줄이기"
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
        </svg>
      </button>
      <input
        type="range"
        min={1}
        max={10}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-2 w-full cursor-pointer appearance-none rounded-full bg-gray-200 accent-green-600"
      />
      <button
        onClick={() => onChange(Math.min(10, value + 1))}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-gray-300 text-gray-500 transition-colors hover:border-green-500 hover:text-green-600"
        aria-label="인원수 늘리기"
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      </button>
      <span className="min-w-[3.5rem] text-center text-sm font-semibold text-green-700">
        {value}인분
      </span>
    </div>
  );
}
