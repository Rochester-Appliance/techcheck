import { clsx } from "clsx";

export interface YouTubeVideo {
  video_id: string;
  title: string;
  thumbnail_url: string;
  channel_name: string;
  view_count: string;
  duration: string;
  published_at: string;
}

interface VideoCardProps {
  video: YouTubeVideo;
}

const VideoCard = ({ video }: VideoCardProps) => {
  const youtubeUrl = `https://www.youtube.com/watch?v=${video.video_id}`;

  return (
    <a
      href={youtubeUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="video-card"
      aria-label={`Watch ${video.title} on YouTube`}
    >
      <div className="video-card-thumbnail">
        {video.thumbnail_url ? (
          <img
            src={video.thumbnail_url}
            alt={video.title}
            loading="lazy"
            decoding="async"
          />
        ) : (
          <div className="video-card-placeholder">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="48"
              height="48"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
          </div>
        )}
        {video.duration && (
          <span className="video-card-duration">{video.duration}</span>
        )}
        <div className="video-card-play-overlay">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      </div>
      <div className="video-card-info">
        <h5 className="video-card-title" title={video.title}>
          {video.title}
        </h5>
        <div className="video-card-meta">
          <span className="video-card-channel">{video.channel_name}</span>
          <span className="video-card-stats">
            {video.view_count}
            {video.published_at && ` • ${video.published_at}`}
          </span>
        </div>
      </div>
    </a>
  );
};

interface VideoCardSkeletonProps {
  count?: number;
}

export const VideoCardSkeleton = ({ count = 3 }: VideoCardSkeletonProps) => {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="video-card video-card-skeleton">
          <div className="video-card-thumbnail skeleton-pulse" />
          <div className="video-card-info">
            <div className="skeleton-line skeleton-pulse" style={{ width: "90%" }} />
            <div className="skeleton-line skeleton-pulse" style={{ width: "60%" }} />
          </div>
        </div>
      ))}
    </>
  );
};

interface VideoCardGridProps {
  videos: YouTubeVideo[];
  loading?: boolean;
  error?: string | null;
  fallbackQuery?: string;
}

export const VideoCardGrid = ({
  videos,
  loading = false,
  error = null,
  fallbackQuery,
}: VideoCardGridProps) => {
  if (loading) {
    return (
      <div className="video-card-grid">
        <VideoCardSkeleton count={3} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="video-card-error">
        <p className="muted">{error}</p>
        {fallbackQuery && (
          <a
            href={`https://www.youtube.com/results?search_query=${encodeURIComponent(fallbackQuery)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-link"
          >
            Search on YouTube →
          </a>
        )}
      </div>
    );
  }

  if (videos.length === 0) {
    return (
      <div className="video-card-empty">
        <p className="muted">No video tutorials found.</p>
        {fallbackQuery && (
          <a
            href={`https://www.youtube.com/results?search_query=${encodeURIComponent(fallbackQuery)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-link"
          >
            Search on YouTube →
          </a>
        )}
      </div>
    );
  }

  return (
    <div className="video-card-grid">
      {videos.map((video) => (
        <VideoCard key={video.video_id} video={video} />
      ))}
    </div>
  );
};

export default VideoCard;

