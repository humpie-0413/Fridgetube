"use client";

export default function OfflinePage() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-4">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gray-100">
        <svg
          className="h-8 w-8 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M18.364 5.636a9 9 0 11-12.728 0M12 9v4m0 4h.01"
          />
        </svg>
      </div>
      <h2 className="mt-4 text-lg font-bold text-gray-900">
        오프라인 상태에요
      </h2>
      <p className="mt-2 text-center text-sm text-gray-500">
        인터넷 연결을 확인한 후 다시 시도해주세요.
      </p>
      <button
        onClick={() => window.location.reload()}
        className="mt-6 rounded-xl bg-green-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-green-700"
      >
        새로고침
      </button>
    </div>
  );
}
