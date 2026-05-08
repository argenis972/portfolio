interface SkeletonProps {
  className?: string;
}

export default function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-app-surface-hover rounded-md ${className}`}
      aria-hidden="true"
    />
  );
}
