import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * React hook for polling an API endpoint with automatic fallback to mock data.
 *
 * @param {Function} apiFn - async function that returns data from API
 * @param {*} mockFallback - fallback data when API is unreachable
 * @param {number} intervalMs - polling interval (0 = no polling)
 * @returns {{ data, loading, error, live, refresh }}
 */
export function useApi(apiFn, mockFallback = null, intervalMs = 0) {
  const [data, setData] = useState(mockFallback);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [live, setLive] = useState(false);
  const mountedRef = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const result = await apiFn();
      if (mountedRef.current) {
        setData(result);
        setLive(true);
        setError(null);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err.message);
        setLive(false);
        if (mockFallback !== null) setData(mockFallback);
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [apiFn, mockFallback]);

  useEffect(() => {
    mountedRef.current = true;
    refresh();

    let timer;
    if (intervalMs > 0) {
      timer = setInterval(refresh, intervalMs);
    }

    return () => {
      mountedRef.current = false;
      if (timer) clearInterval(timer);
    };
  }, [refresh, intervalMs]);

  return { data, loading, error, live, refresh };
}

/**
 * Hook specifically for connection status — polls /health every 5s.
 */
export function useConnectionStatus() {
  const [connected, setConnected] = useState(false);
  const [healthData, setHealthData] = useState(null);

  useEffect(() => {
    let mounted = true;

    const check = async () => {
      try {
        const res = await fetch('http://localhost:8000/health');
        if (res.ok && mounted) {
          const data = await res.json();
          setConnected(true);
          setHealthData(data);
        }
      } catch {
        if (mounted) {
          setConnected(false);
          setHealthData(null);
        }
      }
    };

    check();
    const timer = setInterval(check, 5000);

    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  return { connected, healthData };
}
