import React, {
  useMemo,
  useState,
  useEffect,
  useRef,
  useCallback,
} from "react";
import {
  FileText,
  Target,
  Globe,
  Bell,
  X,
  TrendingUp,
  Search,
  RefreshCw,
  Eye,
  Bookmark,
  MoreHorizontal,
} from "lucide-react";
import { getErrorMessage, requestJson, requestWithRetry } from "../utils/api";
import {
  ensureNotificationPermission,
  notifyNewTenders,
} from "../utils/notifications";

const VALID_TENDER_STATUS = ["new", "viewed", "saved"];
const DASHBOARD_ENDPOINTS = {
  fetch: "/api/dashboard",
  sync: "/api/dashboard/sync",
};
const EMPTY_STATS = {
  newTendersToday: 0,
  keywordMatches: 0,
  activeSources: { active: 0, total: 0 },
  alertsToday: 0,
  trendNewTenders: 0,
  trendKeywords: 0,
};

function getTenderKeywordsText(tender) {
  if (!tender) return "";
  if (typeof tender.matched_keywords === "string") {
    return tender.matched_keywords;
  }
  if (Array.isArray(tender.keywords)) {
    return tender.keywords.join(", ");
  }
  return "";
}

function isValidSearch(value) {
  if (!value) return true;
  if (value.length > 50) return false;
  return /^[a-zA-Z0-9\s.-]+$/.test(value);
}

function safeArray(arr) {
  return Array.isArray(arr) ? arr : [];
}

function safeStatus(status) {
  return VALID_TENDER_STATUS.includes(String(status).toLowerCase()) ? String(status).toLowerCase() : "viewed";
}

function getTenderKey(tender) {
  if (!tender) return null;
  return tender.id ?? tender.reference_id ?? tender.code ?? null;
}

function isValidTender(tender) {
  if (!tender) return false;

  if (typeof tender.title !== "string" || tender.title.trim() === "")
    return false;
    
  // Support both backend (reference_id) and legacy/ui (code)
  const code = tender.reference_id || tender.code;
  if (typeof code !== "string" || code.trim() === "")
    return false;
    
  return true;
}

function computeStatsFromData(stats) {
  if (!stats) return { ...EMPTY_STATS };
  
  // Handle both snake_case (direct stats api) and camelCase (dashboard sync api)
  return {
    newTendersToday: stats.newTendersToday ?? stats.new_tenders_today ?? 0,
    keywordMatches: stats.keywordMatches ?? stats.keyword_matches_today ?? 0,
    activeSources: {
      active: stats.activeSources?.active ?? stats.active_sources ?? 0,
      total: stats.activeSources?.total ?? stats.total_sources ?? 0,
    },
    alertsToday: stats.alertsToday ?? stats.alerts_today ?? 0,
    trendNewTenders: stats.trendNewTenders ?? stats.new_tenders_change ?? 0,
    trendKeywords: stats.trendKeywords ?? stats.keyword_matches_change ?? 0,
  };
}

function formatCountdown(seconds) {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) {
    return "—";
  }
  const safe = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

const Dashboard = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [showNotifications, setShowNotifications] = useState(false);
  const [selectedTender, setSelectedTender] = useState(null);
  const [activeActionsId, setActiveActionsId] = useState(null);

  const [notifications, setNotifications] = useState([]);
  const [tenderList, setTenderList] = useState([]);
  const [topKeywords, setTopKeywords] = useState([]);
  const [sources, setSources] = useState([]);
  const [lastSyncAt, setLastSyncAt] = useState("");
  const [nextSyncIn, setNextSyncIn] = useState("");
  const [syncCountdown, setSyncCountdown] = useState(20 * 60);
  const [stats, setStats] = useState({ ...EMPTY_STATS });
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 5;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const notificationMenuRef = useRef(null);
  const tenderIdsRef = useRef(new Set());
  const hasTenderSnapshotRef = useRef(false);

  const pushRealtimeNotifications = useCallback((newItems) => {
    if (!newItems?.length) return;

    // In-app notification list (keep last 25 entries)
    setNotifications((prev) => {
      const mapped = newItems.map((t) => ({
        id: `rt-${getTenderKey(t) || Date.now()}`,
        message: `New tender fetched: ${t.title || t.reference_id || "Untitled"}`,
        isRead: false,
      }));
      const next = [...prev, ...mapped];
      return next.slice(-25);
    });

    notifyNewTenders(newItems);
  }, []);

  const fetchDashboard = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      console.log("[Dashboard] Starting parallel fetch...");
      const startTime = Date.now();
      
      const requests = [
        { name: "stats", url: "/api/dashboard/stats" },
        { name: "tenders", url: "/api/dashboard/recent-tenders" },
        { name: "sources", url: "/api/dashboard/source-status" },
        { name: "notifications", url: "/api/notifications/" }
      ];

      const [statsData, tendersData, sourcesData, notificationsData] = await Promise.all(
        requests.map(req => 
          requestJson(req.url)
            .then(data => {
              console.log(`[Dashboard] Success: ${req.name} (${Date.now() - startTime}ms)`);
              return data;
            })
            .catch(err => {
              console.error(`[Dashboard] Error: ${req.name}`, err);
              throw err;
            })
        )
      );

      const fallbackTopKeywords = (() => {
        const counts = new Map();
        (Array.isArray(tendersData) ? tendersData : []).forEach((t) => {
          const parts = getTenderKeywordsText(t)
            .split(",")
            .map((k) => k.trim())
            .filter(Boolean);
          parts.forEach((k) => counts.set(k, (counts.get(k) || 0) + 1));
        });
        return Array.from(counts.entries())
          .sort((a, b) => b[1] - a[1])
          .slice(0, 5)
          .map(([keyword, matches]) => ({ keyword, matches }));
      })();

      setStats(statsData);
      setTopKeywords(statsData?.top_keywords?.length ? statsData.top_keywords : fallbackTopKeywords);
      setTenderList(tendersData || []);
      setSources(sourcesData || []);
      setNotifications(
        (notificationsData?.items || []).map((n) => ({
          ...n,
          isRead: Boolean(n?.isRead ?? n?.is_read),
        }))
      );

      const tenderIds = new Set(
        (tendersData || [])
          .map((t) => getTenderKey(t))
          .filter(Boolean)
      );
      tenderIdsRef.current = tenderIds;
      hasTenderSnapshotRef.current = true;

      const nextSyncSeconds = Number(statsData?.next_tender_sync_in_seconds);
      const resolvedNextSync = Number.isFinite(nextSyncSeconds)
        ? nextSyncSeconds
        : 20 * 60;

      setSyncCountdown(resolvedNextSync);
      setNextSyncIn(formatCountdown(resolvedNextSync));
      
      // Update local lastSync meta
      const latestSync = sourcesData.reduce((prev, curr) => {
        if (!curr.last_fetch) return prev;
        const prevDate = prev ? new Date(prev) : new Date(0);
        const currDate = new Date(curr.last_fetch);
        return (currDate > prevDate) ? curr.last_fetch : prev;
      }, "");
      setLastSyncAt(latestSync && latestSync !== "0" ? new Date(latestSync).toLocaleString() : "Never");

    } catch (err) {
      console.error(err);
      setError(getErrorMessage(err, "Failed to load dashboard"));
    } finally {
      setLoading(false);
    }
  }, []);

  const pollRecentTenders = useCallback(async () => {
    try {
      const data = await requestWithRetry(() =>
        requestJson("/api/dashboard/recent-tenders")
      );

      const items = Array.isArray(data) ? data : data?.items || [];
      const ids = new Set(
        items
          .map((t) => getTenderKey(t))
          .filter(Boolean)
      );

      let newlyArrived = [];
      if (hasTenderSnapshotRef.current) {
        newlyArrived = items.filter((t) => {
          const key = getTenderKey(t);
          return key && !tenderIdsRef.current.has(key);
        });
      }

      tenderIdsRef.current = ids;
      hasTenderSnapshotRef.current = true;

      setTenderList(items);

      if (newlyArrived.length) {
        pushRealtimeNotifications(newlyArrived);
      }
    } catch (err) {
      console.error("[Dashboard] Realtime tender poll failed", err);
    }
  }, [pushRealtimeNotifications]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  useEffect(() => {
    ensureNotificationPermission();
  }, []);

  useEffect(() => {
    const interval = setInterval(pollRecentTenders, 20000);
    return () => clearInterval(interval);
  }, [pollRecentTenders]);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.isRead).length,
    [notifications]
  );

  const normalizedSearch = searchQuery.trim().toLowerCase();

  const filteredTenders = useMemo(() => {
    if (!Array.isArray(tenderList)) return [];

    const validTenders = tenderList.filter(isValidTender);
    if (!normalizedSearch) return validTenders;
    if (!isValidSearch(searchQuery)) return validTenders;

    return validTenders.filter((tender) => {
      const title = tender.title?.toLowerCase() || "";
      const code = (tender.reference_id || tender.code || "").toLowerCase();
      const agency = (tender.agency_name || tender.agency || "").toLowerCase();
      const location = (tender.agency_location || tender.location || "").toLowerCase();
      const source = (tender.source_name || tender.source || "").toLowerCase();
      
      const keywords = getTenderKeywordsText(tender).toLowerCase();

      return (
        title.includes(normalizedSearch) ||
        code.includes(normalizedSearch) ||
        agency.includes(normalizedSearch) ||
        location.includes(normalizedSearch) ||
        source.includes(normalizedSearch) ||
        keywords.includes(normalizedSearch)
      );
    });
  }, [tenderList, normalizedSearch, searchQuery]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, tenderList]);

  useEffect(() => {
    const timer = setInterval(() => {
      setSyncCountdown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    setNextSyncIn(formatCountdown(syncCountdown));
    if (syncCountdown === 0) {
      fetchDashboard();
      setSyncCountdown(20 * 60);
    }
  }, [syncCountdown, fetchDashboard]);

  useEffect(() => {
    if (!showNotifications) return;

    const handleClickOutside = (event) => {
      if (
        notificationMenuRef.current &&
        !notificationMenuRef.current.contains(event.target)
      ) {
        setShowNotifications(false);
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setShowNotifications(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [showNotifications]);

  const handleToggleNotifications = useCallback(() => {
    setShowNotifications((prev) => !prev);
  }, []);

  const handleMarkAllRead = useCallback(() => {
    setNotifications((list) => list.map((n) => ({ ...n, isRead: true })));
  }, []);

  const handleClearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const handleNotificationClick = useCallback((id) => {
    setNotifications((list) =>
      list.map((n) => (n.id === id ? { ...n, isRead: true } : n))
    );
  }, []);

  const handleRemoveNotification = useCallback((id) => {
    setNotifications((list) => list.filter((n) => n.id !== id));
  }, []);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(filteredTenders.length / pageSize)),
    [filteredTenders.length, pageSize]
  );
  const safePage = Math.min(currentPage, totalPages);
  const startIndex = (safePage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedTenders = useMemo(
    () => filteredTenders.slice(startIndex, endIndex),
    [filteredTenders, startIndex, endIndex]
  );

  const goToPage = useCallback(
    (page) => {
      const next = Math.min(Math.max(page, 1), totalPages);
      setCurrentPage(next);
    },
    [totalPages]
  );

  const getPageItems = useCallback((total, current) => {
    if (total <= 7) {
      return Array.from({ length: total }, (_, idx) => ({
        type: "page",
        value: idx + 1,
      }));
    }

    const items = [];
    const pushPage = (value) => items.push({ type: "page", value });
    const pushDots = (key) => items.push({ type: "dots", key });

    if (current <= 3) {
      pushPage(1);
      pushPage(2);
      pushPage(3);
      pushDots("end");
      pushPage(total);
      return items;
    }

    if (current >= total - 2) {
      pushPage(1);
      pushDots("start");
      pushPage(total - 2);
      pushPage(total - 1);
      pushPage(total);
      return items;
    }

    pushPage(1);
    pushDots("start");
    pushPage(current - 1);
    pushPage(current);
    pushPage(current + 1);
    pushDots("end");
    pushPage(total);
    return items;
  }, []);

  const pageItems = useMemo(
    () => getPageItems(totalPages, safePage),
    [getPageItems, totalPages, safePage]
  );

  const resolvedStats = useMemo(
    () => computeStatsFromData(stats),
    [stats]
  );

  const getStatusBadgeClasses = (status) => {
    switch (safeStatus(status)) {
      case "new":
        return "bg-green-100 text-green-800";
      case "viewed":
        return "bg-gray-100 text-gray-600";
      case "saved":
        return "bg-blue-100 text-blue-800";
      default:
        return "bg-gray-100 text-gray-600";
    }
  };

  const getDaysLeftClass = (daysText) => {
    const days = parseInt(daysText, 10);
    if (Number.isNaN(days)) return "text-gray-500";
    if (days <= 10) return "text-gray-500";
    if (days <= 30) return "text-gray-500";
    return "text-gray-500";
  };

  const getKeywordBadgeClasses = (color) => {
    switch (color) {
      case "green":
        return "bg-green-100 text-green-800";
      case "red":
        return "bg-red-100 text-red-800";
      case "gray":
        return "bg-gray-100 text-gray-600";
      default:
        return "bg-gray-100 text-gray-600";
    }
  };

  const getSourceDotColor = (status) => {
    switch (String(status).toLowerCase()) {
      case "active":
        return "bg-green-500";
      case "warning":
        return "bg-orange-500";
      case "error":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  };

  const getSourceStatusColor = (status) => {
    switch (String(status).toLowerCase()) {
      case "active":
        return "text-green-600";
      case "warning":
        return "text-orange-600";
      case "error":
        return "text-red-600";
      default:
        return "text-gray-600";
    }
  };

  const updateTenderStatus = useCallback(async (tenderId, status) => {
    try {
      // Local optimistic update
      setTenderList((prev) =>
        prev.map((tender) =>
          tender.id === tenderId ? { ...tender, status: status.toLowerCase() } : tender
        )
      );
      setSelectedTender((prev) =>
        prev?.id === tenderId ? { ...prev, status: status.toLowerCase() } : prev
      );

      // Backend persist
      await requestJson(`/api/tenders/${tenderId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: status.toLowerCase() })
      });
    } catch (err) {
      console.error("Failed to update tender status:", err);
      // Revert or show error if needed, but for now we log it
    }
  }, []);

  const openTenderSource = useCallback((tender) => {
    if (!tender) return;
    const url =
      tender.source_url ||
      tender.url ||
      tender.link ||
      tender.source_link;
    if (url && typeof window !== "undefined") {
      window.open(url, "_blank", "noopener,noreferrer");
    }
  }, []);

  const handleViewTender = useCallback(
    (tender) => {
      const currentStatus = String(tender.status || "").toLowerCase();
      const nextStatus = currentStatus === "saved" ? "saved" : "viewed";
      updateTenderStatus(tender.id, nextStatus);
      setSelectedTender(tender);
      openTenderSource(tender);
    },
    [updateTenderStatus, openTenderSource]
  );

  const handleToggleSave = useCallback(
    (tender) => {
      const currentStatus = String(tender.status || "").toLowerCase();
      const nextStatus = currentStatus === "saved" ? "viewed" : "saved";
      updateTenderStatus(tender.id, nextStatus);
    },
    [updateTenderStatus]
  );

  const handleAttachmentOpen = useCallback((attachment) => {
    if (!attachment) return;
    if (attachment.url) {
      window.open(attachment.url, "_blank", "noopener,noreferrer");
    }
  }, []);

  const handleSyncNow = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const data =
        (await requestWithRetry(() =>
          requestJson(DASHBOARD_ENDPOINTS.sync, { method: "POST" })
        )) || {};

      setNotifications(
        (data.notifications || []).map((n) => ({
          ...n,
          isRead: Boolean(n?.isRead ?? n?.is_read),
        }))
      );
      setTenderList(data.tenders || []);
      setTopKeywords(data.topKeywords || []);
      setSources(data.sources || []);
      setLastSyncAt(data.lastSyncAt || new Date().toLocaleString());
      const nextSyncSeconds = Number(data?.nextTenderSyncSeconds);
      const resolvedNextSync = Number.isFinite(nextSyncSeconds)
        ? nextSyncSeconds
        : 20 * 60;
      setSyncCountdown(resolvedNextSync);
      setNextSyncIn(formatCountdown(resolvedNextSync));
      setStats(
        data.stats ||
          computeStatsFromData(
            data.tenders || tenderList,
            data.sources || sources,
            data.notifications || notifications
          )
      );
    } catch (err) {
      console.error(err);
      setError(getErrorMessage(err, "Failed to sync dashboard"));
    } finally {
      setLoading(false);
    }
  }, [notifications, sources, tenderList]);

  return (
    <div className="min-h-full bg-gray-50">
      {/* Main Content */}
      <div className="overflow-y-auto">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-4 py-3 sm:px-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-800">Dashboard</h2>
              <p className="text-xs text-gray-500">
                Monitor your tender opportunities
              </p>
            </div>

            <div className="flex flex-col md:flex-row md:items-center gap-3 w-full md:w-auto">
              <div className="relative">
                <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500">
                  <Search size={16} />
                </span>
                <input
                  type="text"
                  placeholder="Search tenders..."
                  value={searchQuery}
                  onChange={(e) => {
                    const value = e.target.value;
                    if (isValidSearch(value)) {
                      setSearchQuery(value);
                    }
                  }}
                  className="w-full sm:w-64 pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm font-semibold"
                />
              </div>

              <div className="text-xs text-gray-500">
                Last sync: {lastSyncAt}
              </div>

              <button
                onClick={handleSyncNow}
                disabled={loading}
                className="flex items-center gap-4 px-5 py-1.5 border border-gray-300 rounded-lg bg-white hover:bg-blue-400 text-sm font-semibold disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <RefreshCw size={18} className="text-gray-900 font-bold" />
                Sync Now
              </button>

              <div className="relative" ref={notificationMenuRef}>
                <button
                  onClick={handleToggleNotifications}
                  className="relative p-1.5 border border-gray-300 rounded-lg bg-white hover:bg-gray-50"
                >
                  <Bell size={18} className="text-gray-600" />

                  {stats?.alerts_today > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 text-xs flex items-center justify-center rounded-full bg-red-500 text-white font-bold animate-pulse">
                {stats.alerts_today}
              </span>
            )}
                </button>

                {showNotifications && (
                  <div className="absolute right-0 mt-2 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
                    <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200">
                      <span className="text-sm font-semibold">
                        Notifications
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={handleMarkAllRead}
                          disabled={unreadCount === 0}
                          className={`text-[11px] ${
                            unreadCount === 0
                              ? "text-gray-300 cursor-not-allowed"
                              : "text-blue-600 hover:text-blue-700"
                          }`}
                        >
                          Mark all
                        </button>
                        <button
                          type="button"
                          onClick={handleClearNotifications}
                          disabled={notifications.length === 0}
                          className={`text-[11px] ${
                            notifications.length === 0
                              ? "text-gray-300 cursor-not-allowed"
                              : "text-red-500 hover:text-red-600"
                          }`}
                        >
                          Clear
                        </button>
                      </div>
                    </div>

                    {notifications.length === 0 ? (
                      <div className="px-4 py-3 text-xs text-gray-500 text-center">
                        No notifications
                      </div>
                    ) : (
                      notifications.map((n) => (
                        <div
                          key={n.id}
                          onClick={() => handleNotificationClick(n.id)}
                          className={`flex items-start justify-between gap-2 px-4 py-2 text-xs border-b last:border-b-0 cursor-pointer ${
                            n.isRead
                              ? "text-gray-500"
                              : "text-gray-900 font-medium"
                          }`}
                        >
                          <span className="flex-1">{n.message}</span>
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              handleRemoveNotification(n.id);
                            }}
                            className="text-gray-400 hover:text-red-500"
                            title="Remove notification"
                          >
                            <X size={12} />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Status Banner */}
        <div className="mx-4 mt-4 bg-green-100 border border-green-300 rounded-lg p-4 flex flex-col gap-2 sm:mx-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3 text-green-900">
            <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
            <span className="text-sm font-semibold">
              System is active and monitoring
            </span>
          </div>
          <div className="text-sm text-green-700">
            Next sync in {nextSyncIn}
          </div>
        </div>

        {loading && (
          <div className="mx-4 mt-4 text-sm text-gray-500 flex items-center gap-2 sm:mx-6">
            <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></span>
            Loading dashboard...
          </div>
        )}
        {error && (
          <div className="mx-4 mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm sm:mx-6">
            {error}
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 px-4 md:px-6 mt-6">
          <div className="bg-white border border-gray-200 rounded-lg p-6 flex flex-col justify-center shadow-lg">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Tenders</p>
                <div className="text-3xl font-bold mt-1">
                  {resolvedStats?.newTendersToday ?? 0}
                </div>
                <div className="flex items-center gap-1 text-xs text-green-600 mt-1">
                  <TrendingUp size={12} />
                  {resolvedStats?.trendNewTenders ?? 0}% vs last week
                </div>
              </div>
              <div className="p-2 bg-blue-100 rounded-lg">
                <FileText className="text-blue-600" size={24} />
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6 flex flex-col justify-center shadow-lg">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-500">Keyword Matches</p>
                <div className="text-3xl font-bold mt-1">
                  {resolvedStats?.keywordMatches ?? 0}
                </div>
                <div className="flex items-center gap-1 text-xs text-green-600 mt-1">
                  <TrendingUp size={12} />
                  {resolvedStats?.trendKeywords ?? 0}% vs last week
                </div>
              </div>
              <div className="p-2 bg-green-100 rounded-lg">
                <Search className="text-green-600" size={24} />
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6 flex flex-col justify-center shadow-lg">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-500">Active Sources</p>
                <div className="text-3xl font-bold mt-1">
                  {resolvedStats?.activeSources?.active ?? 0}/
                  {resolvedStats?.activeSources?.total ?? 0}
                </div>
              </div>
              <div className="p-2 bg-indigo-100 rounded-lg">
                <Globe className="text-indigo-600" size={24} />
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg p-6 flex flex-col justify-center shadow-lg">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-gray-500">Notifications</p>
                <div className="text-3xl font-bold mt-1">
                  {resolvedStats?.alertsToday ?? 0}
                </div>
              </div>
              <div className="p-2 bg-orange-100 rounded-lg">
                <Bell className="text-orange-600" size={24} />
              </div>
            </div>
          </div>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 px-4 md:px-6 mt-6">
          {/* Recent Tenders */}
          <div className="lg:col-span-8 bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Recent Tenders
              </h3>

              <span className="text-xs bg-blue-50 text-blue-600 px-3 py-1 rounded-full font-medium">
                {filteredTenders.length} total
              </span>
            </div>

            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-gray-500 text-xs">
                    <tr>
                      <th className="px-5 py-4 text-left font-semibold uppercase">
                        Tender
                      </th>
                      <th className="px-5 py-3 text-left font-semibold uppercase">
                        Agency
                      </th>
                      <th className="px-5 py-3 text-left font-semibold uppercase">
                        Sources
                      </th>
                      <th className="px-5 py-3 text-left font-semibold uppercase">
                        Deadline
                      </th>
                      <th className="px-5 py-3 text-left font-semibold uppercase">
                        Status
                      </th>
                      <th className="px-5 py-3 text-left font-semibold uppercase">
                        Keywords
                      </th>
                      <th className="px-5 py-3 text-left font-semibold uppercase">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedTenders.map((tender) => (
                      <tr
                        key={tender.id}
                        className="border-b border-gray-200 hover:bg-gray-50"
                      >
                        <td className="px-3 py-10">
                          <div className="font-medium text-gray-900 text-sm truncate max-w-xs">
                            {tender.title}
                          </div>
                          <div className="text-xs text-gray-500 mt-0.5">
                            {tender.reference_id}
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          <div className="text-gray-900 text-xs text-semibold">
                            {tender.agency_name}
                          </div>
                          <div className="text-xs text-gray-500 mt-0.5">
                            {tender.agency_location}
                          </div>
                        </td>
                        <td className="px-3 py-2 font-semibold text-xs">
                          {tender.source_name}
                        </td>
                        <td className="px-3 py-2">
                          <div className="font-medium text-xs">
                            {tender.deadline_date ? new Date(tender.deadline_date).toLocaleDateString() : 'N/A'}
                          </div>
                          <div
                            className={`text-xs mt-0.5 ${getDaysLeftClass(
                              tender.days_until_deadline
                            )}`}
                          >
                            {tender.days_until_deadline !== null ? `${tender.days_until_deadline} days left` : ''}
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-xs font-medium uppercase ${getStatusBadgeClasses(
                              tender.status
                            )}`}
                          >
                            {tender.status}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex flex-wrap gap-2">
                            {getTenderKeywordsText(tender).split(',').filter(k => k).map((keyword, idx) => (
                              <span
                                key={`${tender.id}-kw-${idx}`}
                                className="bg-gray-100 px-3 py-1 rounded-full text-xs"
                              >
                                {keyword.trim()}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          <div className="relative flex items-center justify-center gap-3 text-gray-500">
                            <Eye
                              size={16}
                              className="hover:text-gray-900 cursor-pointer"
                              onClick={() => {
                                try {
                                  if (!tender || !tender.id) {
                                    throw new Error("Invalid tender data");
                                  }
                                  handleViewTender(tender);
                                } catch (error) {
                                  console.error(
                                    "Tender selection failed:",
                                    error
                                  );
                                  alert(
                                    "Something went wrong. Please try again."
                                  );
                                }
                              }}
                            />

                            <Bookmark
                              size={16}
                              className="hover:text-gray-900 cursor-pointer"
                              onClick={() => handleToggleSave(tender)}
                            />
                            <MoreHorizontal
                              size={16}
                              className="hover:text-gray-900 cursor-pointer"
                              onClick={() =>
                                setActiveActionsId((prev) =>
                                  prev === tender.id ? null : tender.id
                                )
                              }
                            />
                            {activeActionsId === tender.id && (
                              <div className="absolute mt-10 right-6 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-30">
                                <button
                                  className="w-full text-left px-3 py-2 text-xs hover:bg-gray-50"
                                  onClick={() => {
                                    handleViewTender(tender);
                                    setActiveActionsId(null);
                                  }}
                                >
                                  View details
                                </button>
                                <button
                                  className="w-full text-left px-3 py-2 text-xs hover:bg-gray-50"
                                  onClick={() => {
                                    updateTenderStatus(tender.id, "VIEWED");
                                    setActiveActionsId(null);
                                  }}
                                >
                                  Mark as viewed
                                </button>
                                <button
                                  className="w-full text-left px-3 py-2 text-xs hover:bg-gray-50"
                                  onClick={() => {
                                    updateTenderStatus(tender.id, "NEW");
                                    setActiveActionsId(null);
                                  }}
                                >
                                  Mark as new
                                </button>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {paginatedTenders.length === 0 && (
                      <tr>
                        <td
                          colSpan={7}
                          className="px-4 py-6 text-center text-sm text-gray-500"
                        >
                          No tenders found
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-2 py-4">
              <div className="text-sm text-gray-500 font-medium">
                Showing {filteredTenders.length === 0 ? 0 : startIndex + 1}-
                {Math.min(endIndex, filteredTenders.length)} of{" "}
                {filteredTenders.length} results
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => goToPage(safePage - 1)}
                  disabled={safePage === 1}
                  className="px-3 py-1.5 text-sm shadow-sm rounded border border-gray-200 bg-white hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Prev
                </button>
                <div className="flex items-center gap-1">
                  {pageItems.map((item) => {
                    if (item.type === "dots") {
                      return (
                        <span
                          key={item.key}
                          className="w-8 h-8 text-xs text-gray-500 flex items-center justify-center"
                        >
                          ...
                        </span>
                      );
                    }

                    const page = item.value;
                    return (
                      <button
                        key={page}
                        onClick={() => goToPage(page)}
                        className={`w-8 h-8 text-xs rounded border ${
                          page === safePage
                            ? "bg-indigo-600 text-white border-gray-900"
                            : "bg-white text-gray-700 border-gray-200 hover:bg-gray-50"
                        }`}
                      >
                        {page}
                      </button>
                    );
                  })}
                </div>
                <button
                  onClick={() => goToPage(safePage + 1)}
                  disabled={safePage === totalPages}
                  className="px-3 py-1.5 text-sm shadow-sm rounded border border-gray-200 bg-white hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          </div>

          {/* Top Keywords */}
          <div className="lg:col-span-4 bg-white border border-gray-200 rounded-xl">
            <div className="flex items-center justify-between px-5 py-4 border-b">
              <h3 className="text-lg font-semibold text-gray-900">
                Top Keywords
              </h3>
              <TrendingUp size={16} className="text-gray-400" />
            </div>
            <div className="p-4 space-y-10">
              {topKeywords.map((keyword, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between mb-3"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-gray-500 font-medium text-xs">
                      {idx + 1}.
                    </span>
                    <span className="text-sm font-medium text-gray-900">
                      {keyword.keyword || keyword.name}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700`}
                  >
                    {keyword.matches || keyword.match_count || 0} matches
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Source Status Overview */}
        <div className="px-4 pb-6 mt-4 sm:px-6">
          <div className="bg-white border border-gray-200 rounded-lg">
            <div className="px-4 py-3 border-b border-gray-200">
              <h3 className="text-base font-semibold">
                Source Status Overview
              </h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 p-4">
              {sources.map((source, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 border border-gray-100 rounded-lg hover:bg-gray-50"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-2 h-2 rounded-full ${getSourceDotColor(
                        source.status
                      )}`}
                    ></div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {source.name}
                      </p>
                      <p
                        className={`text-[10px] font-semibold uppercase ${getSourceStatusColor(
                          source.status
                        )}`}
                      >
                        {source.status}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-semibold text-gray-900">
                      {source.tenders_today} new today
                    </p>
                    <p className="text-[10px] text-gray-500">
                      Last:{" "}
                      {source.last_fetch
                        ? new Date(source.last_fetch).toLocaleTimeString()
                        : "Never"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ================= OVERLAY ================= */}
      {selectedTender && (
        <div className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"></div>
      )}

      {selectedTender && (
        <div className="fixed top-0 right-0 h-full w-full sm:w-[420px] bg-white z-50 shadow-2xl transition-transform duration-300">
          {/* Header */}
          <div className="flex items-start justify-between p-5 border-b">
            <div>
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${getStatusBadgeClasses(
                  selectedTender.status
                )}`}
              >
                {selectedTender.status}
              </span>
              <h2 className="text-lg font-semibold mt-2">
                {selectedTender.title}
              </h2>
              <p className="text-xs text-gray-500 mt-1">
                {selectedTender.reference_id || selectedTender.code}
              </p>
            </div>

            <button
              onClick={() => setSelectedTender(null)}
              className="text-gray-400 hover:text-gray-700 text-xl"
            >
              ✕
            </button>
          </div>

          {/* Body */}
          <div className="p-5 space-y-5 text-sm">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500">Agency</p>
                <p className="font-medium">{selectedTender.agency_name || selectedTender.agency}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Location</p>
                <p className="font-medium">{selectedTender.agency_location || selectedTender.location}</p>
              </div>

              <div>
                <p className="text-xs text-gray-500">Source</p>
                <p className="font-medium">{selectedTender.source_name || selectedTender.source}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Deadline</p>
                <p className="font-medium">
                  {selectedTender.deadline_date ? new Date(selectedTender.deadline_date).toLocaleDateString() : 'N/A'}
                </p>
              </div>
            </div>

            {/* Keywords */}
            <div>
              <p className="text-xs text-gray-500 mb-2">Keyword Matches</p>
              <div className="flex flex-wrap gap-2">
                {getTenderKeywordsText(selectedTender).split(',').filter(k => k).map((k, i) => (
                  <span
                    key={`${selectedTender.id}-details-kw-${i}`}
                    className="bg-blue-50 text-blue-600 px-3 py-1 rounded-full text-xs"
                  >
                    {k.trim()}
                  </span>
                ))}
              </div>
            </div>

            {/* Description */}
            <div>
              <p className="text-xs text-gray-500 mb-1">Description</p>
              <p className="text-gray-700 text-sm leading-relaxed line-clamp-6">
                {selectedTender.description || "No description available."}
              </p>
            </div>

            {/* Attachments */}
            <div>
              <p className="text-xs text-gray-500 mb-2">Attachments</p>
              <div className="space-y-2">
                {safeArray(selectedTender.attachments).length === 0 ? (
                  <div className="border border-dashed rounded-lg p-3 text-xs text-gray-500">
                    No attachments available
                  </div>
                ) : (
                  safeArray(selectedTender.attachments).map((attachment) => (
                    <button
                      key={attachment.name}
                      type="button"
                      className="w-full text-left border rounded-lg p-3 text-xs hover:bg-gray-50"
                      onClick={() => handleAttachmentOpen(attachment)}
                    >
                      📎 {attachment.name}
                      {attachment.size ? ` • ${attachment.size}` : ""}
                    </button>
                  ))
                )}
              </div>
            </div>

            {/* Button */}
            {selectedTender.source_url && (
              <a 
                href={selectedTender.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="block w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg text-sm mt-4 text-center"
              >
                View on Source
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
