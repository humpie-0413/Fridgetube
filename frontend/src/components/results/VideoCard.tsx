import Link from "next/link";
import type { VideoResult } from "@/lib/api";

function formatDuration(seconds: number | null): string {
  if (!seconds) return "";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0)
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatViewCount(count: number | null): string {
  if (!count) return "";
  if (count >= 100_000_000) return `${(count / 100_000_000).toFixed(1)}억회`;
  if (count >= 10_000) return `${(count / 10_000).toFixed(1)}만회`;
  return `${count.toLocaleString()}회`;
}

interface VideoCardProps {
  video: VideoResult;
  showGap: boolean;
  servings: number;
}

export default function VideoCard({ video, showGap, servings }: VideoCardProps) {
  const gap = video.ingredient_gap_estimate;

  return (
    <Link
      href={`/recipe?id=${video.video_id}&servings=${servings}`}
      className="group block overflow-hidden rounded-xl border border-gray-200 bg-white transition-shadow hover:shadow-md"
    >
      {/* 썸네일 */}
      <div className="relative aspect-video bg-gray-100">
        <img
          src={video.thumbnail}
          alt={video.title}
          className="h-full w-full object-cover"
          loading="lazy"
        />
        {video.duration_seconds != null && video.duration_seconds > 0 && (
          <span className="absolute bottom-2 right-2 rounded bg-black/80 px-1.5 py-0.5 text-xs font-medium text-white">
            {formatDuration(video.duration_seconds)}
          </span>
        )}
        {showGap && gap && (
          <span
            className={`absolute left-2 top-2 rounded-full px-2.5 py-1 text-xs font-bold text-white ${
              gap.estimated_missing === 0
                ? "bg-green-500"
                : gap.estimated_missing <= 2
                  ? "bg-yellow-500"
                  : "bg-red-500"
            }`}
          >
            {gap.estimated_missing === 0
              ? "재료 충분"
              : `~${gap.estimated_missing}개 부족`}
          </span>
        )}
      </div>

      {/* 정보 */}
      <div className="p-3">
        <h3 className="line-clamp-2 text-sm font-semibold text-gray-900 transition-colors group-hover:text-green-700">
          {video.title}
        </h3>
        <p className="mt-1 text-xs text-gray-500">{video.channel.name}</p>
        {video.view_count != null && video.view_count > 0 && (
          <p className="mt-0.5 text-xs text-gray-400">
            {formatViewCount(video.view_count)}
          </p>
        )}
      </div>
    </Link>
  );
}
