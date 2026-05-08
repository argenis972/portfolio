import { useState, useEffect } from 'react';

export function useCurrentTime(intervalMs: number = 1000): number {
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    const update = () => setCurrentTime(Date.now());
    update();
    const timer = setInterval(update, intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);

  return currentTime;
}
