import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { requestJson, requestWithRetry } from '../utils/api';

const SourcesContext = createContext();

export function SourcesProvider({ children }) {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeSourceIds, setActiveSourceIds] = useState(new Set());

  const SOURCE_ENDPOINTS = {
    list: '/api/sources/',
  };

  const fetchSources = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await requestWithRetry(() => requestJson(SOURCE_ENDPOINTS.list));
      const sourceItems = Array.isArray(data) ? data : data?.items || [];
      setSources(sourceItems.map(s => ({
        ...s,
        status: String(s.status || '').toUpperCase(),
        isEnabled: Boolean(s.is_active),
      })));
      const activeIds = new Set(sourceItems.filter(s => s.is_active).map(s => s.id));
      setActiveSourceIds(activeIds);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []); // ESLint happy - no violation

  const toggleSource = useCallback(async (id) => {
    try {
      const source = sources.find(s => s.id === id);
      if (!source || ['ERROR', 'WARNING'].includes(source.status)) return;

      const updatedSource = await requestJson(`/api/sources/${id}/toggle`, { method: 'POST' });
      setSources(prev => prev.map(s => s.id === id ? updatedSource : s));
      const updatedActiveIds = new Set(sources.filter(s => s.id !== id || updatedSource.is_active).map(s => s.id));
      setActiveSourceIds(updatedActiveIds);
    } catch (err) {
      console.error(err);
    }
  }, [sources]);

  useEffect(() => {
    fetchSources();
    const interval = setInterval(fetchSources, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, [fetchSources]);

  return (
    <SourcesContext.Provider value={{
      sources,
      activeSourceIds,
      loading,
      error,
      fetchSources,
      toggleSource,
    }}>
      {children}
    </SourcesContext.Provider>
  );
}

export const useSources = () => {
  const context = useContext(SourcesContext);
  if (!context) throw new Error('useSources must be within SourcesProvider');
  return context;
};
