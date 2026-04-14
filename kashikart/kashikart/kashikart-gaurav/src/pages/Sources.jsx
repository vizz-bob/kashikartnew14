import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
  memo,
} from "react";
import {
  Search,
  Plus,
  ExternalLink,
  Globe,
  Lock,
  RefreshCw,
  Edit,
  Bell,
  X,
} from "lucide-react";
import { EmptyState } from "../components/States";
import { getErrorMessage, requestJson, requestWithRetry } from "../utils/api";
import { useSources } from "../contexts/SourcesContext";

const USE_MOCK_SOURCES = false;
const USE_MOCK_NOTIFICATIONS = false;
const USE_MOCK_KEYWORDS = false;
const SOURCE_ENDPOINTS = {
  list: (size = 200) => `/api/sources/?size=${size}`,
  refresh: (id) => `/api/sources/${id}/refresh`,
};
const NOTIFICATION_ENDPOINTS = {
  list: "/api/notifications/",
};
const KEYWORD_ENDPOINTS = {
  active: "/api/keywords/active",
};

const INITIAL_NOTIFICATIONS = [];

const getStatusColor = (status) => {
  const s = String(status).toLowerCase();
  switch (s) {
    case "active":
      return "bg-green-100 text-green-700";
    case "error":
      return "bg-red-100 text-red-700";
    case "disabled":
      return "bg-gray-100 text-gray-700";
    default:
      return "bg-gray-100 text-gray-700";
  }
};

const SourceRow = memo(function SourceRow({
  source,
  onToggle,
  onRefresh,
  onEdit,
}) {
  return (
    <tr className="hover:bg-gray-50 transition">
      <td className="px-6 py-4 text-sm font-medium text-gray-900">
        {source.name}
      </td>
      <td className="px-6 py-4">
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-[#3c83f6] hover:text-[#2563eb] flex items-center gap-1.5"
        >
          {source.url}
          <ExternalLink size={13} />
        </a>
      </td>
      <td className="px-6 py-4">
        <div className="flex items-center gap-2 text-sm">
          {String(source.login_type).toLowerCase() === "public" ? (
            <>
              <Globe size={16} className="text-gray-500" />
              <span className="text-gray-700">Public</span>
            </>
          ) : (
            <>
              <Lock size={16} className="text-yellow-600" />
              <span className="text-yellow-600 font-medium">Required</span>
            </>
          )}
        </div>
      </td>
      <td className="px-6 py-4">
        <span
          className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium ${getStatusColor(
            source.status
          )}`}
        >
          {source.status}
        </span>
      </td>
      <td className="px-6 py-4 text-sm text-gray-700">
        {source.last_fetch_at ? new Date(source.last_fetch_at).toLocaleString() : "Never"}
      </td>
      <td className="px-6 py-4 text-sm font-semibold text-gray-900">
        {source.total_tenders || 0}
      </td>
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
{(['error', 'warning'].includes(source.status.toLowerCase())) ? (
            <div className="tooltip-group relative inline-flex items-center cursor-not-allowed opacity-50">
              <div className="w-11 h-6 bg-gray-200 rounded-full pointer-events-none"></div>
              <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 px-2 py-1 bg-red-100 text-red-800 text-xs rounded whitespace-nowrap">
                Issues detected. Fix first
              </div>
            </div>
          ) : (
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={source.isEnabled}
                onChange={() => onToggle(source.id)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#3c83f6]"></div>
            </label>
          )}
          <button
            onClick={() => onRefresh(source.id)}
            className="text-gray-500 hover:text-[#3c83f6] transition"
            title="Refresh"
          >
            <RefreshCw size={18} />
          </button>
          <button
            onClick={() => onEdit(source.id)}
            className="text-gray-500 hover:text-[#3c83f6] transition"
            title="Edit"
          >
            <Edit size={18} />
          </button>
        </div>
      </td>
    </tr>
  );
});

export default function Sources() {
  const { sources, toggleSource, fetchSources, loading: sourcesLoading, error: sourcesError } = useSources();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingSource, setEditingSource] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showRefreshToast, setShowRefreshToast] = useState(false);
  const [refreshingSource, setRefreshingSource] = useState("");
  const [keywords, setKeywords] = useState([]);
  const [keywordFilter, setKeywordFilter] = useState("ALL");
  const [stats, setStats] = useState({ active: 0, disabled: 0, errors: 0 });
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS);
  const notificationMenuRef = useRef(null);
  const [formData, setFormData] = useState({
    name: "",
    excelPath: "",
    url: "",
    loginType: "Public",
    scraperType: "html",
    selectorConfig: "",
  });





  // Active keywords for filtering / suggestions
  const fetchKeywords = useCallback(async () => {
    if (USE_MOCK_KEYWORDS) return;
    try {
      const data = await requestWithRetry(() =>
        requestJson(KEYWORD_ENDPOINTS.active)
      );
      if (Array.isArray(data)) {
        setKeywords(data);
      }
    } catch (err) {
      console.error("Failed to fetch keywords:", err);
    }
  }, []);

  useEffect(() => {
    fetchKeywords();
  }, [fetchKeywords]);

  const fetchNotifications = useCallback(async () => {
    if (USE_MOCK_NOTIFICATIONS) return; // TODO BACKEND: mock hata ke API se data aayega
    try {
      setError(null);
      const data = await requestWithRetry(() =>
        requestJson(NOTIFICATION_ENDPOINTS.list)
      );
      setNotifications(
        (data?.items || []).map((n) => ({
          ...n,
          isRead: Boolean(n?.isRead ?? n?.is_read),
        }))
      );
    } catch (err) {
      console.error(err);
      setError(getErrorMessage(err, "Failed to load notifications"));
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

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

  const handleInputChange = useCallback((e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  }, []);


  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      try {
        setLoading(true);
        setError(null);

        const payload = {
          name: formData.name,
          url: formData.url,
          scraper_type: formData.scraperType || 'html',
          selector_config: formData.selectorConfig ? JSON.parse(formData.selectorConfig) : {},
          login_type: formData.loginType.toLowerCase() === 'public' ? 'PUBLIC' : 'REQUIRED',
          is_active: true
        };

        await requestJson("/api/sources/", {
          method: "POST",
          body: JSON.stringify(payload)
        });

        setIsModalOpen(false);
        setFormData({
          name: "",
          excelPath: "",
          url: "",
          loginType: "Public",
          scraperType: "html",
          selectorConfig: "",
        });
        
        // Refresh sources list immediately
        fetchSources?.();
        
        // Delayed refreshes to catch the background fetch result
        setTimeout(() => fetchSources?.(), 2000);
        setTimeout(() => fetchSources?.(), 5000);

      } catch (err) {
        console.error(err);
        setError(getErrorMessage(err, "Failed to add source. Make sure Selector Config is valid JSON."));
      } finally {
        setLoading(false);
      }
    },
    [formData, fetchSources]
  );

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
    setFormData({
      name: "",
      excelPath: "",
      url: "",
      loginType: "Public",
    });
  }, []);

  const handleToggle = useCallback((id) => {
    toggleSource(id);
  }, [toggleSource]);

  const handleRefresh = useCallback(
    async (id) => {
      const source = sources.find((s) => s.id === id);
      if (!source) return;
      setRefreshingSource(source.name);
      setShowRefreshToast(true);

      try {
        setError(null);
        if (!USE_MOCK_SOURCES) {
          await requestWithRetry(() =>
            requestJson(SOURCE_ENDPOINTS.refresh(id), { method: "POST" })
          );
        }
      } catch (err) {
        console.error(err);
        setError(getErrorMessage(err, "Failed to refresh source"));
      }

      setSources((prev) =>
        prev.map((item) =>
          item.id === id
            ? {
                ...item,
                last_fetch_at: new Date().toISOString(),
              }
            : item
        )
      );

      // Refresh sources list from server to get updated tender counts
      setTimeout(() => {
        fetchSources?.();
      }, 1500);

      setTimeout(() => {
        setShowRefreshToast(false);
      }, 3000);

      setTimeout(() => {
        fetchSources?.();
      }, 4000);
    },
    [sources, fetchSources]
  );

  const handleEdit = useCallback(
    (id) => {
      const source = sources.find((s) => s.id === id);
      setEditingSource({
        ...source,
        scraperType: source?.scraper_type || "html",
        selectorConfig: source?.selector_config
          ? JSON.stringify(source.selector_config, null, 2)
          : "",
        loginType:
          String(source?.login_type).toLowerCase() === "public"
            ? "Public"
            : "Required",
      });
      setIsEditModalOpen(true);
    },
    [sources]
  );

  const handleEditSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      try {
        setLoading(true);
        setError(null);

        const payload = {
          name: editingSource.name,
          url: editingSource.url,
          login_type: editingSource.loginType?.toLowerCase() === 'public' ? 'PUBLIC' : 'REQUIRED',
          scraper_type: editingSource.scraperType || 'html',
          selector_config: editingSource.selectorConfig ? JSON.parse(editingSource.selectorConfig) : {},
        };

        await requestJson(`/api/sources/${editingSource.id}`, {
          method: "PATCH",
          body: JSON.stringify(payload)
        });

        setIsEditModalOpen(false);
        setEditingSource(null);
        fetchSources?.();
      } catch (err) {
        console.error(err);
        setError(getErrorMessage(err, "Failed to update source"));
      } finally {
        setLoading(false);
      }
    },
    [editingSource, fetchSources]
  );

  const handleEditInputChange = useCallback((e) => {
    const { name, value } = e.target;
    setEditingSource((prev) => ({
      ...prev,
      [name]: value,
    }));
  }, []);

  const handleCloseEditModal = useCallback(() => {
    setIsEditModalOpen(false);
    setEditingSource(null);
  }, []);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.isRead).length,
    [notifications]
  );

  const isLoading = loading || sourcesLoading;
  const displayError = error || sourcesError;

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

  const safeSources = useMemo(
    () => (Array.isArray(sources) ? sources : []),
    [sources]
  );
  const filteredSources = useMemo(
    () =>
      safeSources.filter((source) => {
        const matchesSearch =
          source.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          source.url.toLowerCase().includes(searchQuery.toLowerCase());

        if (keywordFilter === "ALL") return matchesSearch;

        const kw = keywordFilter.toLowerCase();
        const sourceKeywords = Array.isArray(source.keywords)
          ? source.keywords.map((k) => String(k).toLowerCase())
          : [];

        const keywordHit =
          source.name.toLowerCase().includes(kw) ||
          source.url.toLowerCase().includes(kw) ||
          sourceKeywords.some((k) => k.includes(kw));

        return matchesSearch && keywordHit;
      }),
    [safeSources, searchQuery, keywordFilter]
  );

  return (
    <div className="bg-[#F7FAFC] min-h-full">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-4 sm:px-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">
              Source Management
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Configure and monitor tender data sources
            </p>
          </div>
          <div className="relative" ref={notificationMenuRef}>
            <button
              onClick={handleToggleNotifications}
              className="relative p-1.5 rounded-lg hover:bg-gray-100 transition"
            >
              <Bell size={20} className="text-gray-600" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center font-semibold">
                  {unreadCount}
                </span>
              )}
            </button>

            {showNotifications && (
              <div className="absolute right-0 mt-2 w-72 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
                <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200">
                  <span className="text-sm font-semibold">Notifications</span>
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
                        n.isRead ? "text-gray-500" : "text-gray-900 font-medium"
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

      {isLoading && (
        <div className="mx-4 mt-4 text-sm text-gray-500 flex items-center gap-2 sm:mx-6">
          <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></span>
          Loading sources...
        </div>
      )}
      {displayError && (
        <div className="mx-4 mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm sm:mx-6">
          {displayError}
        </div>
      )}

      {/* Content */}
      <div className="p-4 max-w-[1400px] mx-auto sm:p-6">
        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="text-sm text-gray-600 mb-1">Total Sources</div>
            <div className="text-3xl font-semibold text-gray-900">
              {sources.length}
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="text-sm text-gray-600 mb-1">Active</div>
            <div className="text-3xl font-semibold text-green-600">
              {sources.filter(s => s.isEnabled).length}
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="text-sm text-gray-600 mb-1">Disabled</div>
            <div className="text-3xl font-semibold text-gray-600">
              {sources.filter(s => !s.isEnabled).length}
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <div className="text-sm text-gray-600 mb-1">Errors</div>
            <div className="text-3xl font-semibold text-red-600">
              {sources.filter(s => s.status === 'ERROR').length}
            </div>
          </div>
        </div>

        {/* Search and Add Button */}
        <div className="flex flex-col gap-3 mb-6 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
            <div className="relative w-full sm:w-[360px]">
              <Search
                className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
                size={18}
              />
              <input
                type="text"
                placeholder="Search sources..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="w-full sm:w-56">
              <select
                value={keywordFilter}
                onChange={(e) => setKeywordFilter(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="ALL">All keywords</option>
                {keywords.map((kw) => (
                  <option key={kw} value={kw}>
                    {kw}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-gray-400 mt-1">
                Filter sources by admin keywords
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="bg-[#3c83f6] hover:bg-[#2563eb] text-white px-5 py-2.5 rounded-md flex items-center justify-center gap-2 transition font-medium text-sm whitespace-nowrap w-full md:w-auto"
          >
            <Plus size={18} />
            Add Source
          </button>
        </div>

        {/* Table */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Source
                  </th>
                  <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    URL
                  </th>
                  <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Login
                  </th>
                  <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Last Fetch
                  </th>
                  <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Tenders
                  </th>
                  <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {filteredSources.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8">
                      <EmptyState
                        title="No sources found"
                        message="Add a source or change your search."
                      />
                    </td>
                  </tr>
                ) : (
                  filteredSources.map((source) => (
                    <SourceRow
                      key={source.id}
                      source={source}
                      onToggle={handleToggle}
                      onRefresh={handleRefresh}
                      onEdit={handleEdit}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Add Source Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 backdrop-blur-md">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  Add New Source
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Add a new data source to monitor for tenders.
                </p>
              </div>
              <button
                onClick={handleCloseModal}
                className="text-gray-400 hover:text-gray-600 transition"
              >
                <X size={24} />
              </button>
            </div>

            <div className="p-6">
              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Source Name
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="e.g., SAM.gov"
                    className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Excel Path
                  </label>
                  <input
                    type="text"
                    name="excelPath"
                    value={formData.excelPath}
                    onChange={handleInputChange}
                    placeholder="C:\\path\\to\\file.xlsx"
                    className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    URL
                  </label>
                  <input
                    type="url"
                    name="url"
                    value={formData.url}
                    onChange={handleInputChange}
                    placeholder="https://..."
                    className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Scraper Type
                  </label>
                  <select
                    name="scraperType"
                    value={formData.scraperType}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="html">HTML (CSS Selectors)</option>
                    <option value="portal">Portal / Dynamic Site</option>
                    <option value="api">API (JSON Endpoint)</option>
                    <option value="webscraper_io">Web Scraper.io (Sitemap JSON)</option>
                    <option value="pdf">PDF Parser</option>
                  </select>
                </div>

                {(formData.scraperType === "webscraper_io" || formData.scraperType === "html" || formData.scraperType === "portal" || formData.scraperType === "api") && (
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-2">
                      {formData.scraperType === "html" ? "Selector Config (JSON)" 
                       : formData.scraperType === "portal" ? "Selector Config (CSS Selectors JSON)"
                       : formData.scraperType === "api" ? "API Config (JSON)"
                       : "Web Scraper.io Sitemap (JSON)"}
                    </label>
                    {formData.scraperType === "webscraper_io" && (
                      <p className="text-xs text-gray-500 mb-2">
                        In Chrome Web Scraper.io: open sitemap, click Export Sitemap, copy JSON, and paste here.
                      </p>
                    )}
                    <textarea
                      name="selectorConfig"
                      value={formData.selectorConfig}
                      onChange={handleInputChange}
                      placeholder={formData.scraperType === "html" 
                        ? '{\n  "container_selector": ".tender-item",\n  "selectors": {\n    "title": ".title",\n    "deadline_date": ".date"\n  }\n}'
                        : formData.scraperType === "portal"
                        ? '{\n  "container_selector": ".views-row",\n  "selectors": {\n    "title": "h3 a",\n    "reference_id": ".ref-no"\n  }\n}'
                        : formData.scraperType === "api"
                        ? '{\n  "api_url": "https://api.example.com/tenders",\n  "result_path": "data",\n  "field_mapping": {\n    "title": "bid_description",\n    "reference_id": "id"\n  }\n}'
                        : '{ "_id": "sitemap", ... }'}
                      rows={5}
                      className="w-full px-4 py-2.5 text-sm font-mono border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                )}


                <div>
                  <div className="flex items-center justify-between py-2">
                    <div>
                      <label className="block text-sm font-medium text-gray-900">
                        Requires Login
                      </label>
                      <p className="text-xs text-gray-500 mt-1">
                        Enable if this source requires authentication
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.loginType === "Required"}
                        onChange={(e) =>
                          setFormData((prev) => ({
                            ...prev,
                            loginType: e.target.checked ? "Required" : "Public",
                          }))
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#3c83f6]"></div>
                    </label>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-gray-200">
                <button
                  type="button"
                  onClick={handleCloseModal}
                  className="px-5 py-2.5 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition font-medium"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSubmit}
                  className="px-5 py-2.5 text-sm bg-[#3c83f6] text-white rounded-lg hover:bg-[#2563eb] transition font-medium"
                >
                  Add Source
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Source Modal */}
      {isEditModalOpen && editingSource && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 backdrop-blur-md">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  Edit Source
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Update the source configuration below.
                </p>
              </div>
              <button
                onClick={handleCloseEditModal}
                className="text-gray-400 hover:text-gray-600 transition"
              >
                <X size={24} />
              </button>
            </div>

            <div className="p-6">
              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Source Name
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={editingSource.name}
                    onChange={handleEditInputChange}
                    placeholder="e.g., SAM.gov"
                    className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    URL
                  </label>
                  <input
                    type="url"
                    name="url"
                    value={editingSource.url}
                    onChange={handleEditInputChange}
                    placeholder="https://..."
                    className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Scraper Type
                  </label>
                  <select
                    name="scraperType"
                    value={editingSource.scraperType || "html"}
                    onChange={handleEditInputChange}
                    className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="html">HTML (CSS Selectors)</option>
                    <option value="portal">Portal / Dynamic Site</option>
                    <option value="api">API (JSON Endpoint)</option>
                    <option value="webscraper_io">Web Scraper.io (Sitemap JSON)</option>
                    <option value="pdf">PDF Parser</option>
                  </select>
                </div>

                {(editingSource.scraperType === "webscraper_io" || editingSource.scraperType === "html" || editingSource.scraperType === "portal" || editingSource.scraperType === "api") && (
                  <div>
                    <label className="block text-sm font-medium text-gray-900 mb-2">
                      {editingSource.scraperType === "html" ? "Selector Config (JSON)" 
                       : editingSource.scraperType === "portal" ? "Selector Config (CSS Selectors JSON)"
                       : editingSource.scraperType === "api" ? "API Config (JSON)"
                       : "Web Scraper.io Sitemap (JSON)"}
                    </label>
                    {editingSource.scraperType === "webscraper_io" && (
                      <p className="text-xs text-gray-500 mb-2">
                        In Chrome Web Scraper.io: open sitemap, click Export Sitemap, copy JSON, and paste here.
                      </p>
                    )}
                    <textarea
                      name="selectorConfig"
                      value={editingSource.selectorConfig || ""}
                      onChange={handleEditInputChange}
                      placeholder={editingSource.scraperType === "html" 
                        ? '{\n  "container_selector": ".tender-item",\n  "selectors": {\n    "title": ".title",\n    "deadline_date": ".date"\n  }\n}'
                        : editingSource.scraperType === "portal"
                        ? '{\n  "container_selector": ".views-row",\n  "selectors": {\n    "title": "h3 a"\n  }\n}'
                        : editingSource.scraperType === "api"
                        ? '{\n  "api_url": "https://api.example.com/tenders",\n  "result_path": "data",\n  "field_mapping": {\n    "title": "bid_description",\n    "reference_id": "id"\n  }\n}'
                        : '{ "_id": "sitemap", ... }'}
                      rows={5}
                      className="w-full px-4 py-2.5 text-sm font-mono border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                )}

                <div>
                  <div className="flex items-center justify-between py-2">
                    <div>
                      <label className="block text-sm font-medium text-gray-900">
                        Requires Login
                      </label>
                      <p className="text-xs text-gray-500 mt-1">
                        Enable if this source requires authentication
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editingSource.loginType === "Required"}
                        onChange={(e) =>
                          setEditingSource((prev) => ({
                            ...prev,
                            loginType: e.target.checked ? "Required" : "Public",
                          }))
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#3c83f6]"></div>
                    </label>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-gray-200">
                <button
                  type="button"
                  onClick={handleCloseEditModal}
                  className="px-5 py-2.5 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition font-medium"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleEditSubmit}
                  className="px-5 py-2.5 text-sm bg-[#3c83f6] text-white rounded-lg hover:bg-[#2563eb] transition font-medium"
                >
                  Update Source
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Refresh Toast Notification */}
      {showRefreshToast && (
        <div className="fixed bottom-6 right-6 z-50 bg-gray-800 text-white px-5 py-4 rounded-lg shadow-2xl flex items-center gap-3 animate-slide-up">
          <RefreshCw size={20} className="animate-spin" />
          <div>
            <div className="font-medium">Fetching data</div>
            <div className="text-sm text-gray-300">
              Refreshing data from {refreshingSource}...
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// import React from "react";
// import { useState } from "react";
// import { Search, Plus, ExternalLink, Globe, Lock, RefreshCw, Edit, Bell, X } from "lucide-react";

// export default function Sources() {
//   const [sources, setSources] = useState([
//     {
//       id: 1,
//       name: "SAM.gov",
//       url: "https://sam.gov",
//       login: "Public",
//       status: "Active",
//       lastFetch: "2026-01-01 08:30",
//       tenders: 1247,
//       isPublic: true,
//       isEnabled: true
//     },
//     {
//       id: 2,
//       name: "DOT Portal",
//       url: "https://dot.gov/contracts",
//       login: "Required",
//       status: "Active",
//       lastFetch: "2026-01-01 08:25",
//       tenders: 342,
//       isPublic: false,
//       isEnabled: true
//     },
//     {
//       id: 3,
//       name: "VA Procurement",
//       url: "https://va.gov/procurement",
//       login: "Required",
//       status: "Active",
//       lastFetch: "2026-01-01 08:20",
//       tenders: 189,
//       isPublic: false,
//       isEnabled: true
//     },
//     {
//       id: 4,
//       name: "DHS Contracts",
//       url: "https://dhs.gov/contracts",
//       login: "Required",
//       status: "Active",
//       lastFetch: "2026-01-01 08:15",
//       tenders: 156,
//       isPublic: false,
//       isEnabled: true
//     },
//     {
//       id: 5,
//       name: "EPA Portal",
//       url: "https://epa.gov/contracts",
//       login: "Public",
//       status: "Error",
//       lastFetch: "2025-12-31 22:00",
//       tenders: 98,
//       isPublic: true,
//       isEnabled: false
//     },
//     {
//       id: 6,
//       name: "DOJ Procurement",
//       url: "https://doj.gov/procurement",
//       login: "Required",
//       status: "Active",
//       lastFetch: "2026-01-01 08:10",
//       tenders: 134,
//       isPublic: false,
//       isEnabled: true
//     },
//     {
//       id: 7,
//       name: "DoD Contracts",
//       url: "https://defense.gov/contracts",
//       login: "Required",
//       status: "Active",
//       lastFetch: "2026-01-01 08:05",
//       tenders: 567,
//       isPublic: false,
//       isEnabled: true
//     },
//     {
//       id: 8,
//       name: "NASA Procurement",
//       url: "https://nasa.gov/procurement",
//       login: "Public",
//       status: "Disabled",
//       lastFetch: "2025-12-20 14:00",
//       tenders: 45,
//       isPublic: true,
//       isEnabled: false
//     }
//   ]);

//   const [isModalOpen, setIsModalOpen] = useState(false);
//   const [isEditModalOpen, setIsEditModalOpen] = useState(false);
//   const [editingSource, setEditingSource] = useState(null);
//   const [searchQuery, setSearchQuery] = useState("");
//   const [showRefreshToast, setShowRefreshToast] = useState(false);
//   const [refreshingSource, setRefreshingSource] = useState("");
//   const [formData, setFormData] = useState({
//     name: "",
//     url: "",
//     loginType: "Public"
//   });

//   const getStatusColor = (status) => {
//     switch(status) {
//       case "Active": return "bg-green-100 text-green-700";
//       case "Error": return "bg-red-100 text-red-700";
//       case "Disabled": return "bg-gray-100 text-gray-700";
//       default: return "bg-gray-100 text-gray-700";
//     }
//   };

//   const handleInputChange = (e) => {
//     const { name, value } = e.target;
//     setFormData(prev => ({
//       ...prev,
//       [name]: value
//     }));
//   };

//   const handleSubmit = (e) => {
//     e.preventDefault();

//     const newSource = {
//       id: sources.length + 1,
//       name: formData.name,
//       url: formData.url,
//       login: formData.loginType,
//       status: "Active",
//       lastFetch: new Date().toLocaleString('en-US', {
//         year: 'numeric',
//         month: '2-digit',
//         day: '2-digit',
//         hour: '2-digit',
//         minute: '2-digit',
//         hour12: false
//       }).replace(',', ''),
//       tenders: 0,
//       isPublic: formData.loginType === "Public",
//       isEnabled: true
//     };

//     setSources(prev => [...prev, newSource]);
//     setIsModalOpen(false);
//     setFormData({
//       name: "",
//       url: "",
//       loginType: "Public"
//     });
//   };

//   const handleCloseModal = () => {
//     setIsModalOpen(false);
//     setFormData({
//       name: "",
//       url: "",
//       loginType: "Public"
//     });
//   };

//   const handleToggle = (id) => {
//     setSources(prev => prev.map(source =>
//       source.id === id
//         ? { ...source, isEnabled: !source.isEnabled }
//         : source
//     ));
//   };

//   const handleRefresh = (id) => {
//     const source = sources.find(s => s.id === id);
//     setRefreshingSource(source.name);
//     setShowRefreshToast(true);

//     setSources(prev => prev.map(source =>
//       source.id === id
//         ? {
//             ...source,
//             lastFetch: new Date().toLocaleString('en-US', {
//               year: 'numeric',
//               month: '2-digit',
//               day: '2-digit',
//               hour: '2-digit',
//               minute: '2-digit',
//               hour12: false
//             }).replace(',', '')
//           }
//         : source
//     ));

//     setTimeout(() => {
//       setShowRefreshToast(false);
//     }, 3000);
//   };

//   const handleEdit = (id) => {
//     const source = sources.find(s => s.id === id);
//     setEditingSource({
//       ...source,
//       loginType: source.login
//     });
//     setIsEditModalOpen(true);
//   };

//   const handleEditSubmit = (e) => {
//     e.preventDefault();

//     setSources(prev => prev.map(source =>
//       source.id === editingSource.id
//         ? {
//             ...source,
//             name: editingSource.name,
//             url: editingSource.url,
//             login: editingSource.loginType,
//             isPublic: editingSource.loginType === "Public"
//           }
//         : source
//     ));

//     setIsEditModalOpen(false);
//     setEditingSource(null);
//   };

//   const handleEditInputChange = (e) => {
//     const { name, value } = e.target;
//     setEditingSource(prev => ({
//       ...prev,
//       [name]: value
//     }));
//   };

//   const handleCloseEditModal = () => {
//     setIsEditModalOpen(false);
//     setEditingSource(null);
//   };

//   const filteredSources = sources.filter(source =>
//     source.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
//     source.url.toLowerCase().includes(searchQuery.toLowerCase())
//   );

//   return (
//     <div className="bg-[#F7FAFC] min-h-screen">
//       {/* Header */}
//       <div className="bg-white border-b border-gray-200 px-6 py-4">
//         <div className="flex items-center justify-between">
//           <div>
//             <h1 className="text-2xl font-semibold text-gray-900">Source Management</h1>
//             <p className="text-sm text-gray-500 mt-0.5">Configure and monitor tender data sources</p>
//           </div>
//           <div className="relative">
//             <button className="relative">
//               <Bell size={20} className="text-gray-600" />
//               <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center font-semibold">3</span>
//             </button>
//           </div>
//         </div>
//       </div>

//       {/* Content */}
//       <div className="p-6 max-w-[1400px] mx-auto">
//         {/* Statistics Cards */}
//         <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
//           <div className="bg-white rounded-lg border border-gray-200 p-5">
//             <div className="text-sm text-gray-600 mb-1">Total Sources</div>
//             <div className="text-3xl font-semibold text-gray-900">{sources.length}</div>
//           </div>
//           <div className="bg-white rounded-lg border border-gray-200 p-5">
//             <div className="text-sm text-gray-600 mb-1">Active</div>
//             <div className="text-3xl font-semibold text-green-600">
//               {sources.filter(s => s.status === "Active").length}
//             </div>
//           </div>
//           <div className="bg-white rounded-lg border border-gray-200 p-5">
//             <div className="text-sm text-gray-600 mb-1">Disabled</div>
//             <div className="text-3xl font-semibold text-gray-600">
//               {sources.filter(s => s.status === "Disabled").length}
//             </div>
//           </div>
//           <div className="bg-white rounded-lg border border-gray-200 p-5">
//             <div className="text-sm text-gray-600 mb-1">Errors</div>
//             <div className="text-3xl font-semibold text-red-600">
//               {sources.filter(s => s.status === "Error").length}
//             </div>
//           </div>
//         </div>

//         {/* Search and Add Button */}
//         <div className="flex justify-between gap-3 mb-6">
//           <div className="relative" style={{ width: '400px' }}>
//             <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
//             <input
//               type="text"
//               placeholder="Search sources..."
//               value={searchQuery}
//               onChange={(e) => setSearchQuery(e.target.value)}
//               className="w-full pl-10 pr-4 py-2.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
//             />
//           </div>
//           <button
//             onClick={() => setIsModalOpen(true)}
//             className="bg-[#3c83f6] hover:bg-[#2563eb] text-white px-5 py-2.5 rounded-md flex items-center justify-center gap-2 transition font-medium text-sm whitespace-nowrap"
//           >
//             <Plus size={18} />
//             Add Source
//           </button>
//         </div>

//         {/* Table */}
//         <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
//           <div className="overflow-x-auto">
//             <table className="w-full">
//               <thead className="bg-gray-50 border-b border-gray-200">
//                 <tr>
//                   <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">Source</th>
//                   <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">URL</th>
//                   <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">Login</th>
//                   <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">Status</th>
//                   <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">Last Fetch</th>
//                   <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">Tenders</th>
//                   <th className="text-left px-6 py-3.5 text-xs font-semibold text-gray-700 uppercase tracking-wider">Actions</th>
//                 </tr>
//               </thead>
//               <tbody className="divide-y divide-gray-200 bg-white">
//                 {filteredSources.map((source) => (
//                   <tr key={source.id} className="hover:bg-gray-50 transition">
//                     <td className="px-6 py-4 text-sm font-medium text-gray-900">{source.name}</td>
//                     <td className="px-6 py-4">
//                       <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-sm text-[#3c83f6] hover:text-[#2563eb] flex items-center gap-1.5">
//                         {source.url}
//                         <ExternalLink size={13} />
//                       </a>
//                     </td>
//                     <td className="px-6 py-4">
//                       <div className="flex items-center gap-2 text-sm">
//                         {source.isPublic ? (
//                           <>
//                             <Globe size={16} className="text-gray-500" />
//                             <span className="text-gray-700">Public</span>
//                           </>
//                         ) : (
//                           <>
//                             <Lock size={16} className="text-yellow-600" />
//                             <span className="text-yellow-600 font-medium">Required</span>
//                           </>
//                         )}
//                       </div>
//                     </td>
//                     <td className="px-6 py-4">
//                       <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium ${getStatusColor(source.status)}`}>
//                         {source.status}
//                       </span>
//                     </td>
//                     <td className="px-6 py-4 text-sm text-gray-700">{source.lastFetch}</td>
//                     <td className="px-6 py-4 text-sm font-semibold text-gray-900">{source.tenders}</td>
//                     <td className="px-6 py-4">
//                       <div className="flex items-center gap-3">
//                         {source.status !== "Disabled" && (
//                           <label className="relative inline-flex items-center cursor-pointer">
//                             <input
//                               type="checkbox"
//                               checked={source.isEnabled}
//                               onChange={() => handleToggle(source.id)}
//                               className="sr-only peer"
//                             />
//                             <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#3c83f6]"></div>
//                           </label>
//                         )}
//                         <button
//                           onClick={() => handleRefresh(source.id)}
//                           className="text-gray-500 hover:text-[#3c83f6] transition"
//                           title="Refresh"
//                         >
//                           <RefreshCw size={18} />
//                         </button>
//                         <button
//                           onClick={() => handleEdit(source.id)}
//                           className="text-gray-500 hover:text-[#3c83f6] transition"
//                           title="Edit"
//                         >
//                           <Edit size={18} />
//                         </button>
//                       </div>
//                     </td>
//                   </tr>
//                 ))}
//               </tbody>
//             </table>
//           </div>
//         </div>
//       </div>

//       {/* Add Source Modal */}
//       {isModalOpen && (
//         <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 backdrop-blur-md">
//           <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg">
//             <div className="flex items-center justify-between p-6 border-b border-gray-200">
//               <div>
//                 <h2 className="text-xl font-semibold text-gray-900">Add New Source</h2>
//                 <p className="text-sm text-gray-500 mt-1">Add a new data source to monitor for tenders.</p>
//               </div>
//               <button
//                 onClick={handleCloseModal}
//                 className="text-gray-400 hover:text-gray-600 transition"
//               >
//                 <X size={24} />
//               </button>
//             </div>

//             <div className="p-6">
//               <div className="space-y-5">
//                 <div>
//                   <label className="block text-sm font-medium text-gray-900 mb-2">
//                     Source Name
//                   </label>
//                   <input
//                     type="text"
//                     name="name"
//                     value={formData.name}
//                     onChange={handleInputChange}
//                     placeholder="e.g., SAM.gov"
//                     className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
//                   />
//                 </div>

//                 <div>
//                   <label className="block text-sm font-medium text-gray-900 mb-2">
//                     URL
//                   </label>
//                   <input
//                     type="url"
//                     name="url"
//                     value={formData.url}
//                     onChange={handleInputChange}
//                     placeholder="https://..."
//                     className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
//                   />
//                 </div>

//                 <div>
//                   <div className="flex items-center justify-between py-2">
//                     <div>
//                       <label className="block text-sm font-medium text-gray-900">
//                         Requires Login
//                       </label>
//                       <p className="text-xs text-gray-500 mt-1">Enable if this source requires authentication</p>
//                     </div>
//                     <label className="relative inline-flex items-center cursor-pointer">
//                       <input
//                         type="checkbox"
//                         checked={formData.loginType === "Required"}
//                         onChange={(e) => setFormData(prev => ({
//                           ...prev,
//                           loginType: e.target.checked ? "Required" : "Public"
//                         }))}
//                         className="sr-only peer"
//                       />
//                       <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#3c83f6]"></div>
//                     </label>
//                   </div>
//                 </div>
//               </div>

//               <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-gray-200">
//                 <button
//                   type="button"
//                   onClick={handleCloseModal}
//                   className="px-5 py-2.5 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition font-medium"
//                 >
//                   Cancel
//                 </button>
//                 <button
//                   type="button"
//                   onClick={handleSubmit}
//                   className="px-5 py-2.5 text-sm bg-[#3c83f6] text-white rounded-lg hover:bg-[#2563eb] transition font-medium"
//                 >
//                   Add Source
//                 </button>
//               </div>
//             </div>
//           </div>
//         </div>
//       )}

//       {/* Edit Source Modal */}
//       {isEditModalOpen && editingSource && (
//         <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 backdrop-blur-md">
//           <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg">
//             <div className="flex items-center justify-between p-6 border-b border-gray-200">
//               <div>
//                 <h2 className="text-xl font-semibold text-gray-900">Edit Source</h2>
//                 <p className="text-sm text-gray-500 mt-1">Update the source configuration below.</p>
//               </div>
//               <button
//                 onClick={handleCloseEditModal}
//                 className="text-gray-400 hover:text-gray-600 transition"
//               >
//                 <X size={24} />
//               </button>
//             </div>

//             <div className="p-6">
//               <div className="space-y-5">
//                 <div>
//                   <label className="block text-sm font-medium text-gray-900 mb-2">
//                     Source Name
//                   </label>
//                   <input
//                     type="text"
//                     name="name"
//                     value={editingSource.name}
//                     onChange={handleEditInputChange}
//                     placeholder="e.g., SAM.gov"
//                     className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
//                   />
//                 </div>

//                 <div>
//                   <label className="block text-sm font-medium text-gray-900 mb-2">
//                     URL
//                   </label>
//                   <input
//                     type="url"
//                     name="url"
//                     value={editingSource.url}
//                     onChange={handleEditInputChange}
//                     placeholder="https://..."
//                     className="w-full px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
//                   />
//                 </div>

//                 <div>
//                   <div className="flex items-center justify-between py-2">
//                     <div>
//                       <label className="block text-sm font-medium text-gray-900">
//                         Requires Login
//                       </label>
//                       <p className="text-xs text-gray-500 mt-1">Enable if this source requires authentication</p>
//                     </div>
//                     <label className="relative inline-flex items-center cursor-pointer">
//                       <input
//                         type="checkbox"
//                         checked={editingSource.loginType === "Required"}
//                         onChange={(e) => setEditingSource(prev => ({
//                           ...prev,
//                           loginType: e.target.checked ? "Required" : "Public"
//                         }))}
//                         className="sr-only peer"
//                       />
//                       <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#3c83f6]"></div>
//                     </label>
//                   </div>
//                 </div>
//               </div>

//               <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-gray-200">
//                 <button
//                   type="button"
//                   onClick={handleCloseEditModal}
//                   className="px-5 py-2.5 text-sm border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition font-medium"
//                 >
//                   Cancel
//                 </button>
//                 <button
//                   type="button"
//                   onClick={handleEditSubmit}
//                   className="px-5 py-2.5 text-sm bg-[#3c83f6] text-white rounded-lg hover:bg-[#2563eb] transition font-medium"
//                 >
//                   Update Source
//                 </button>
//               </div>
//             </div>
//           </div>
//         </div>
//       )}

//       {/* Refresh Toast Notification */}
//       {showRefreshToast && (
//         <div className="fixed bottom-6 right-6 z-50 bg-gray-800 text-white px-5 py-4 rounded-lg shadow-2xl flex items-center gap-3 animate-slide-up">
//           <RefreshCw size={20} className="animate-spin" />
//           <div>
//             <div className="font-medium">Fetching data</div>
//             <div className="text-sm text-gray-300">Refreshing data from {refreshingSource}...</div>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }
