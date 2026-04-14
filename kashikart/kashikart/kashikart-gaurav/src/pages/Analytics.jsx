import React, {
  useEffect,
  useRef,
  useState,
  useCallback,
  useMemo,
  memo,
} from "react";
import { getErrorMessage, requestJson, requestWithRetry } from "../utils/api";

import {
  Bell,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  BarChart3,
  ExternalLink,
  X,
  Search,
} from "lucide-react";

const NotificationItem = memo(function NotificationItem({
  notification,
  onClick,
  onRemove,
}) {
  return (
    <div
      onClick={() => onClick(notification.id)}
      className={`px-4 py-3 border-b last:border-b-0 flex gap-3 ${
        !notification.is_read ? "bg-blue-50" : ""
      }`}
    >
      <div className="mt-1">
        {notification.type === "success" && (
          <CheckCircle className="text-green-600" size={18} />
        )}
        {notification.type === "warning" && (
          <AlertTriangle className="text-yellow-500" size={18} />
        )}
        {!["success", "warning"].includes(notification.type) && (
          <AlertTriangle className="text-gray-400" size={18} />
        )}
      </div>

      <div className="flex-1">
        <p className="text-sm text-gray-800">
          {notification.message || "No message available"}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          {notification.time || "Just now"}
        </p>
      </div>
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          onRemove(notification.id);
        }}
        className="text-gray-400 hover:text-red-500 transition"
      >
        <X size={16} />
      </button>
    </div>
  );
});

export default function AnalyticsDashboard() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const notificationMenuRef = useRef(null);

  // Real data states
  const [stats, setStats] = useState([
    { value: "--", title: "Total Tenders (30 d)", icon: <TrendingUp className="text-blue-600 shadow-sm" />, bg: "bg-blue-100" },
    { title: "Keyword Matches", value: "--", icon: <BarChart3 className="text-green-600 shadow-sm" />, bg: "bg-green-100" },
    { title: "Fetch Success Rate", value: "--", icon: <CheckCircle className="text-blue-600 shadow-sm" />, bg: "bg-blue-100" },
    { title: "Source Errors", value: "--", icon: <AlertTriangle className="text-yellow-500 shadow-sm" />, bg: "bg-yellow-100" },
  ]);
  const [tenderSources, setTenderSources] = useState([]);
  const [tenderCategories, setTenderCategories] = useState([]);
  const [lastSync, setLastSync] = useState(null);

  const fetchAnalyticsData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch all data in parallel 
      const [dashboardStats, sourcesData, systemLogs, notifData] = await Promise.all([
        requestWithRetry(() => requestJson("/api/dashboard/stats")),
        requestWithRetry(() => requestJson("/api/sources/")),
        requestWithRetry(() => requestJson("/api/system-logs/")).catch(() => ({ items: [], stats: {} })),
        requestWithRetry(() => requestJson("/api/notifications/")).catch(() => ({ items: [] })),
      ]);

      if (notifData?.items) {
        setNotifications(notifData.items);
      }

      // Build stats cards with real data
      const totalTenders = dashboardStats?.new_tenders_today ?? 0;
      const keywordMatches = dashboardStats?.keyword_matches_today ?? 0;
      
      const logStats = systemLogs?.stats || {};
      const totalLogs = (logStats.Success || 0) + (logStats.Warning || 0) + (logStats.Error || 0) + (logStats.Info || 0);
      const successRate = totalLogs > 0
        ? ((logStats.Success || 0) / totalLogs * 100).toFixed(1) + "%"
        : "N/A";
      const errorCount = logStats.Error || 0;

      setStats([
        { value: String(totalTenders), title: "Total Tenders (30 d)", icon: <TrendingUp className="text-blue-600 shadow-sm" />, bg: "bg-blue-100" },
        { title: "Keyword Matches", value: String(keywordMatches), icon: <BarChart3 className="text-green-600 shadow-sm" />, bg: "bg-green-100" },
        { title: "Fetch Success Rate", value: successRate, icon: <CheckCircle className="text-blue-600 shadow-sm" />, bg: "bg-blue-100" },
        { title: "Source Errors", value: String(errorCount), icon: <AlertTriangle className="text-yellow-500 shadow-sm" />, bg: "bg-yellow-100" },
      ]);

      // Build source chart from sources API data
      const sources = Array.isArray(sourcesData?.items) ? sourcesData.items : (Array.isArray(sourcesData) ? sourcesData : []);
      if (sources.length > 0) {
        const maxTenders = Math.max(...sources.map(s => s.total_tenders || 0), 1);
        setTenderSources(sources.map(s => ({
          name: s.name,
          value: Math.round(((s.total_tenders || 0) / maxTenders) * 100) || 5, // min 5% for visibility
          count: s.total_tenders || 0,
        })));
      }

      // Build keyword category chart from top_keywords
      const topKeywords = dashboardStats?.top_keywords || [];
      if (topKeywords.length > 0) {
        const maxMatches = Math.max(...topKeywords.map(k => k.matches || 0), 1);
        setTenderCategories(topKeywords.map(k => ({
          name: k.keyword,
          value: Math.round(((k.matches || 0) / maxMatches) * 100) || 5,
          count: k.matches || 0,
        })));
      }

      // Last sync from sources
      if (sources.length > 0) {
        const lastFetches = sources
          .filter(s => s.last_fetch_at)
          .map(s => new Date(s.last_fetch_at));
        if (lastFetches.length > 0) {
          const latest = new Date(Math.max(...lastFetches));
          setLastSync(latest.toLocaleString());
        }
      }

    } catch (err) {
      console.error("Analytics fetch failed:", err);
      setError(getErrorMessage(err, "Failed to load analytics data."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalyticsData();
  }, [fetchAnalyticsData]);

  const handleRefreshData = useCallback(() => {
    fetchAnalyticsData();
  }, [fetchAnalyticsData]);

  useEffect(() => {
    if (!open) return;

    const handleClickOutside = (event) => {
      if (
        notificationMenuRef.current &&
        !notificationMenuRef.current.contains(event.target)
      ) {
        setOpen(false);
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.is_read).length,
    [notifications]
  );

  const handleToggleNotifications = useCallback(() => {
    setOpen((prev) => !prev);
  }, []);

  const markAllRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const handleNotificationClick = useCallback((id) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    );
  }, []);

  const handleRemoveNotification = useCallback((id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  return (
    <div className="min-h-full bg-gray-50">
      {/* HEADER */}
      <header className="flex flex-col gap-3 px-4 py-4 border-b sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-800">
            Analytics & Insights
          </h1>
          <p className="text-sm text-gray-500">
            Performance metrics and data overview
          </p>
        </div>
        <div className="relative" ref={notificationMenuRef}>
          <button onClick={handleToggleNotifications} className="relative">
            <Bell className="text-gray-600" />

            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 text-xs flex items-center justify-center rounded-full bg-red-500 text-white">
                {unreadCount}
              </span>
            )}
          </button>

          {/* DROPDOWN */}
          {open && (
            <div className="absolute right-0 mt-3 w-80 bg-white border rounded-xl shadow-lg z-50">
              {/* HEADER */}
              <div className="flex items-center justify-between px-4 py-3 border-b">
                <p className="font-semibold text-gray-800">Notifications</p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={markAllRead}
                    disabled={unreadCount === 0}
                    className={`text-xs ${
                      unreadCount === 0
                        ? "text-gray-300 cursor-not-allowed"
                        : "text-blue-600 hover:underline"
                    }`}
                  >
                    Mark all
                  </button>
                  <button
                    onClick={clearNotifications}
                    disabled={notifications.length === 0}
                    className={`text-xs ${
                      notifications.length === 0
                        ? "text-gray-300 cursor-not-allowed"
                        : "text-red-500 hover:underline"
                    }`}
                  >
                    Clear
                  </button>
                </div>
              </div>

              {/* LIST */}
              <div className="max-h-64 overflow-y-auto">
                {notifications.length === 0 ? (
                  <p className="text-sm text-gray-500 text-center py-6">
                    No notifications
                  </p>
                ) : (
                  notifications.map((n) => (
                    <NotificationItem
                      key={n.id}
                      notification={n}
                      onClick={handleNotificationClick}
                      onRemove={handleRemoveNotification}
                    />
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </header>

      {loading && (
        <div className="mx-4 mt-4 text-sm text-gray-500 flex items-center gap-2 sm:mx-6">
          <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></span>
          Loading analytics...
        </div>
      )}
      {error && (
        <div className="mx-4 mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm sm:mx-6">
          {error}
        </div>
      )}

      <main className="p-4 space-y-6 sm:p-6">
        {/* STATUS BAR */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white border rounded-xl p-7 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="p-2 bg-green-100 rounded-lg">
              <CheckCircle className="text-green-600" />
            </div>
            <div>
              <p className="font-medium text-gray-800">
                System Active
                <span className="ml-2 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                  Online
                </span>
              </p>
              <p className="text-xs text-gray-500">
                Last data sync: {lastSync || "Not available"}
              </p>
            </div>
          </div>
          <button 
            onClick={handleRefreshData}
            className="flex items-center gap-2 px-4 py-2 text-sm border rounded-md hover:bg-blue-300 font-semibold bg-gray-50"
          >
            <RefreshCw size={16} />
            Refresh Data
          </button>
        </div>

        {/* STATS */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((item, i) => (
            <div
              key={i}
              className="bg-white border rounded-lg p-4 flex items-center gap-4 shadow-lg"
            >
              <div className={`p-2 rounded-md ${item.bg}`}>{item.icon}</div>

              <div>
                <p className="text-lg font-bold text-gray-800">
                  {item.value ?? "--"}
                </p>
                <p className="text-sm text-gray-500">
                  {item.title ?? "Unknown"}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* CHARTS */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* SOURCE */}
          <div className="bg-gray-50 border rounded-lg p-4">
            <h3 className="font-medium text-gray-800 mb-4">
              Tenders by Source
            </h3>

            {tenderSources.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-6">No source data available</p>
            ) : (
              tenderSources.map((source, i) => (
                <div key={i} className="mb-3">
                  <div className="flex justify-between mb-1">
                    <p className="text-sm text-gray-600">{source.name}</p>
                    <span className="text-xs text-gray-500">{source.count} tenders</span>
                  </div>

                  <div className="h-2 bg-gray-100 rounded">
                    <div
                      className="h-2 bg-blue-600 rounded"
                      style={{ width: `${source.value}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>

          {/* CATEGORY / KEYWORDS */}
          <div className="bg-gray-50 border rounded-lg p-4">
            <h3 className="font-medium text-gray-800 mb-4">
              Top Keyword Matches
            </h3>

            {tenderCategories.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-6">No keyword data available</p>
            ) : (
              tenderCategories.map((category, i) => (
                <div key={i} className="mb-3">
                  <div className="flex justify-between mb-1">
                    <p className="text-sm text-gray-600">{category.name}</p>
                    <span className="text-xs text-gray-500">
                      {category.count} matches
                    </span>
                  </div>

                  <div className="h-2 bg-gray-100 rounded">
                    <div
                      className="h-2 bg-green-600 rounded"
                      style={{ width: `${category.value}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
