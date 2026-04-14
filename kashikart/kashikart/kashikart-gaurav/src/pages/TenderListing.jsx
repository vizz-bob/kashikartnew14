import React, {
  useEffect,
  useRef,
  useState,
  useCallback,
  useMemo,
} from "react";
import {
  Search,
  Filter,
  Calendar,
  Eye,
  Bookmark,
  MoreHorizontal,
  ChevronLeft,
  ChevronRight,
  Bell,
  X,
  Building2,
  MapPin,
  Download,
  ExternalLink,
  ChevronDown,
  Check,
} from "lucide-react";
import { EmptyState } from "../components/States";
import { getErrorMessage, requestJson, requestWithRetry } from "../utils/api";
import { useSources } from "../contexts/SourcesContext";
import {
  ensureNotificationPermission,
  notifyNewTenders,
} from "../utils/notifications";
const TENDER_ENDPOINTS = {
  list: "/api/tenders/",
};
const NOTIFICATION_ENDPOINTS = {
  list: "/api/notifications/", // TODO BACKEND: yahi endpoint use hoga
};

const INITIAL_NOTIFICATIONS = [];

function getTenderKeywordsText(tender) {
  if (!tender) return "";
  if (typeof tender.matched_keywords === "string") {
    return tender.matched_keywords.trim();
  }
  if (Array.isArray(tender.keywords)) {
    return tender.keywords.join(", ");
  }
  return "";
}

const StatusBadge = ({ status }) => {
  const s = String(status).toLowerCase();
  const styles = {
    new: "bg-green-100 text-green-700",
    viewed: "bg-gray-100 text-gray-700",
    saved: "bg-blue-100 text-blue-700",
    expired: "bg-red-100 text-red-700",
  };

  return (
    <span
      className={`px-3 py-1 rounded-md text-xs font-medium ${
        styles[s] || "bg-gray-100 text-gray-700"
      }`}
    >
      {status}
    </span>
  );
};

const TenderListing = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("All Status");
  const [selectedSource, setSelectedSource] = useState("All Sources");
  const [showDatePicker, setShowDatePicker] = useState(false);
  // const [startDate, setStartDate] = useState(null);
  // const [endDate, setEndDate] = useState(null);

  const [startDate, setStartDate] = useState(null); // Date | null
  const [endDate, setEndDate] = useState(null); // Date | null
  const [currentMonth, setCurrentMonth] = useState(new Date(2026, 0));
  const [selectedTender, setSelectedTender] = useState(null);
  const [openDropdown, setOpenDropdown] = useState(null);
  const [sourceOpen, setSourceOpen] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS);
  const notificationMenuRef = useRef(null);
  const { activeSourceIds } = useSources();

  const [tenders, setTenders] = useState([]); 
  const tenderIdsRef = useRef(new Set());
  const hasTenderSnapshotRef = useRef(false);

  const getTenderKey = useCallback((tender) => {
    if (!tender) return null;
    return tender.id ?? tender.reference_id ?? tender.code ?? null;
  }, []);

  const pushRealtimeNotifications = useCallback(
    (newItems) => {
      if (!newItems?.length) return;

      // Update in-app notification tray (keep last 25 to avoid unbounded growth)
      setNotifications((prev) => {
        const mapped = newItems.map((t) => ({
          id: `rt-${getTenderKey(t) || Date.now()}`,
          message: `New tender fetched: ${t.title || t.reference_id || "Untitled"}`,
          isRead: false,
        }));
        const next = [...prev, ...mapped];
        return next.slice(-25);
      });

      // OS / desktop notification
      notifyNewTenders(newItems);
    },
    [getTenderKey]
  );

  const fetchTenders = useCallback(async (reason = "manual") => {
    try {
      if (reason === "initial") setLoading(true);
      setError(null);

      const data = await requestWithRetry(() =>
        requestJson(TENDER_ENDPOINTS.list)
      );

      const items = data?.items || [];
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

      setTenders(items);

      if (newlyArrived.length) {
        pushRealtimeNotifications(newlyArrived);
      }
    } catch (err) {
      console.error(err);
      setError(getErrorMessage(err, "Failed to load tenders"));
    } finally {
      if (reason === "initial") {
        setLoading(false);
      }
    }
  }, [getTenderKey, pushRealtimeNotifications]);

  useEffect(() => {
    ensureNotificationPermission();
  }, []);

  useEffect(() => {
    fetchTenders("initial");
  }, [fetchTenders]);

  useEffect(() => {
    const interval = setInterval(() => fetchTenders("realtime"), 20000);
    return () => clearInterval(interval);
  }, [fetchTenders]);

  const fetchNotifications = async () => {
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
  };

  const updateTenderStatus = useCallback(async (tenderId, status) => {
    try {
      const lowerStatus = status.toLowerCase();
      // Local optimistic update
      setTenders((prev) =>
        prev.map((t) => (t.id === tenderId ? { ...t, status: lowerStatus } : t))
      );
      setSelectedTender((prev) =>
        prev?.id === tenderId ? { ...prev, status: lowerStatus } : prev
      );

      // Backend persist
      await requestJson(`/api/tenders/${tenderId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: lowerStatus })
      });
    } catch (err) {
      console.error("Failed to update tender status:", err);
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

  useEffect(() => {
    fetchNotifications();
  }, []);

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

  const clearFilters = useCallback(() => {
    setSearchQuery("");
    setSelectedStatus("All Status");
    setSelectedSource("All Sources");
    setStartDate(null);
    setEndDate(null);
    setShowDatePicker(false);
  }, []);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.isRead).length,
    [notifications]
  );

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

  const hasActiveFilters =
    searchQuery ||
    selectedStatus !== "All Status" ||
    selectedSource !== "All Sources" ||
    startDate ||
    endDate;

  useEffect(() => {
    if (startDate && endDate) {
      setShowDatePicker(false);
    }
  }, [startDate, endDate]);

  const safeTenders = useMemo(
    () => (Array.isArray(tenders) ? tenders : []),
    [tenders, activeSourceIds]
  );
  const activeTenders = useMemo(() => 
    safeTenders.filter(t => !t.source_id || activeSourceIds.has(t.source_id)),
    [safeTenders, activeSourceIds]
  );
  const filteredTenders = useMemo(
    () =>
      activeTenders.filter((tender) => {
        const title = (tender.title || "").toLowerCase();
        const code = (tender.reference_id || tender.code || "").toLowerCase();
        const agency = (tender.agency_name || tender.agency || "").toLowerCase();
        const kwStr = getTenderKeywordsText(tender).toLowerCase();
        const query = searchQuery.toLowerCase();

        const matchesSearch =
          title.includes(query) ||
          code.includes(query) ||
          agency.includes(query) ||
          kwStr.includes(query);

        const currentStatus = String(tender.status).toLowerCase();
        const matchesStatus =
          selectedStatus === "All Status" || currentStatus === selectedStatus.toLowerCase();
          
        const currentSource = tender.source_name || tender.source || "Unknown";
        const matchesSource =
          selectedSource === "All Sources" || currentSource === selectedSource;

        let matchesDate = true;
        if (startDate && endDate && tender.deadline_date) {
            const tenderDeadline = new Date(tender.deadline_date);
            matchesDate = tenderDeadline >= startDate && tenderDeadline <= endDate;
        }

        return matchesSearch && matchesStatus && matchesSource && matchesDate;
      }),
    [
      endDate,
      activeTenders,
      searchQuery,
      selectedSource,
      selectedStatus,
      startDate,
    ]
  );

  const sources = useMemo(
    () => {
      const uniqueSources = new Set(safeTenders.map(t => t.source_name || t.source).filter(Boolean));
      return ["All Sources", ...Array.from(uniqueSources)];
    },
    [safeTenders]
  );
  const statuses = useMemo(
    () => ["All Status", "New", "Viewed", "Saved", "Expired"],
    []
  );

  const getDaysInMonth = (date) => {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (date) => {
    return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
  };

  const monthNames = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  const formatDateString = (date) => {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(
      2,
      "0"
    )}-${String(date.getDate()).padStart(2, "0")}`;
  };

  const renderCalendar = (monthOffset = 0) => {
    const date = new Date(
      currentMonth.getFullYear(),
      currentMonth.getMonth() + monthOffset
    );
    const daysInMonth = getDaysInMonth(date);
    const firstDay = getFirstDayOfMonth(date);
    const days = [];
    const prevMonthDays = getDaysInMonth(
      new Date(date.getFullYear(), date.getMonth() - 1, 1)
    );

    for (let i = firstDay - 1; i >= 0; i--) {
      const day = prevMonthDays - i;
      days.push(
        <div
          key={`prev-${i}`}
          className="text-center py-2 text-sm text-gray-300"
        >
          {day}
        </div>
      );
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const currentDate = new Date(date.getFullYear(), date.getMonth(), day);
      const dateStr = formatDateString(currentDate);
      const isToday = day === 15 && monthOffset === 0;
      // const isStart = startDate === dateStr;
      // const isEnd = endDate === dateStr;
      const isStart =
        startDate && currentDate.toDateString() === startDate.toDateString();
      const isEnd =
        endDate && currentDate.toDateString() === endDate.toDateString();

      // let isInRange = false;
      // if (startDate && endDate) {
      //   const startDateObj = new Date(startDate);
      //   const endDateObj = new Date(endDate);
      //   isInRange = currentDate > startDateObj && currentDate < endDateObj;
      // }

      const isInRange =
        startDate &&
        endDate &&
        currentDate > startDate &&
        currentDate < endDate;

      days.push(
        <button
          key={day}
          onClick={() => {
            if (!startDate || endDate) {
              setStartDate(currentDate);
              setEndDate(null);
            } else if (currentDate < startDate) {
              setEndDate(startDate);
              setStartDate(currentDate);
            } else {
              setEndDate(currentDate);
            }
          }}
          className={`text-center py-2 text-sm rounded-lg transition ${
            isToday
              ? "bg-blue-500 text-white hover:bg-blue-600 font-semibold"
              : isStart || isEnd
              ? "bg-blue-500 text-white font-semibold"
              : isInRange
              ? "bg-blue-100 text-blue-700"
              : "text-gray-700 hover:bg-gray-100"
          }`}
        >
          {day}
        </button>
      );
    }

    return (
      <div className="flex-1">
        <div className="font-semibold text-center mb-3 text-base text-gray-900">
          {monthNames[date.getMonth()]} {date.getFullYear()}
        </div>
        <div className="grid grid-cols-7 gap-1 mb-2">
          {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((day) => (
            <div
              key={day}
              className="text-center text-xs font-medium text-gray-500 py-1"
            >
              {day}
            </div>
          ))}
        </div>
        <div className="grid grid-cols-7 gap-1">{days}</div>
      </div>
    );
  };

  return (
    <div className="min-h-full flex flex-col bg-gray-50">
      <div className="sticky top-0 z-20 bg-gray-50 px-4 pt-4 pb-3 border-b border-gray-200 sm:px-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-800 text-xl">
              Tender Listings
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {filteredTenders.length} tenders found
            </p>
          </div>
          <div className="relative" ref={notificationMenuRef}>
            <button
              onClick={handleToggleNotifications}
              className="relative p-1.5 rounded-lg hover:bg-gray-100 transition"
            >
              <Bell size={18} className="text-gray-500 hover:text-gray-700" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] rounded-full px-1">
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

      {loading && (
        <div className="mx-4 mt-4 text-sm text-gray-500 flex items-center gap-2 sm:mx-6">
          <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></span>
          Loading tenders...
        </div>
      )}
      {error && (
        <div className="mx-4 mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm sm:mx-6">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-auto px-4 py-6 sm:px-6 lg:px-10">
        <div className="bg-white rounded-lg p-3 border border-gray-200 mb-3 shadow-sm">
          <div className="relative mb-3">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by title, agency, reference ID, or keywords..."
              className="w-full py-2 pl-10 pr-4 text-sm text-gray-700 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="flex flex-col gap-3 text-sm text-gray-600 sm:flex-row sm:flex-wrap sm:items-center">
            <div className="flex items-center gap-2">
              <Filter size={14} />
              <span className="text-sm">Filters:</span>
            </div>

            {/* <select 
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="border border-gray-300 rounded-md px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer hover:border-gray-400">
              {statuses.map(status => (
                <option key={status}  value={status} >{status}</option>
              ))}
            </select>  */}

            <div className="relative">
              <button
                onClick={() => setStatusOpen((v) => !v)}
                className="
                  flex items-center justify-between gap-2
                  border border-gray-300 rounded-md
                  px-4 py-2 text-sm text-gray-700
                  min-w-[160px]
                  hover:border-gray-400 hover:bg-gray-50
                  focus:outline-none focus:ring-2 focus:ring-blue-500
                "
              >
                <span>{selectedStatus}</span>
                <ChevronDown className="w-4 h-4 text-gray-500" />
              </button>

              {statusOpen && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setStatusOpen(false)}
                  />

                  <div className="absolute z-20 mt-1 w-full rounded-md border border-gray-200 bg-white shadow-lg">
                    {statuses.map((status) => {
                      const isSelected = status === selectedStatus;

                      return (
                        <button
                          key={status}
                          onClick={() => {
                            setSelectedStatus(status);
                            setStatusOpen(false);
                          }}
                          className={`
                            flex w-full items-center gap-2 px-3 py-2 text-sm
                            transition  rounded hover:bg-blue-500 hover:text-white
                            ${
                              isSelected
                                ? " text-gray-700 font-medium"
                                : "text-gray-700"
                            }
                          `}
                        >
                          <span className="w-4">
                            {isSelected && <Check className="w-4 h-4" />}
                          </span>

                          <span>{status}</span>
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
            </div>

            {/* <select 
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="border border-gray-300 rounded-md px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer hover:border-gray-400"
            >
              {sources.map(source => (
                <option key={source} value={source}>{source}</option>
              ))}
            </select> */}

            <div className="relative">
              <button
                onClick={() => setSourceOpen((v) => !v)}
                className="
                  flex items-center justify-between gap-2
                  border border-gray-300 rounded-md px-4 py-2 text-sm text-gray-700 min-w-[180px] hover:border-gray-400 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <span>{selectedSource}</span>
                <ChevronDown className="w-4 h-4 text-gray-500" />
              </button>

              {sourceOpen && (
                <>
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setSourceOpen(false)}
                  />

                  <div className="absolute z-20 mt-1 w-full rounded-md border border-gray-200 bg-white shadow-lg">
                    {sources.map((source) => {
                      const isSelected = source === selectedSource;

                      return (
                        <button
                          key={source}
                          onClick={() => {
                            setSelectedSource(source);
                            setSourceOpen(false);
                          }}
                          className={`
                            flex w-full items-center gap-2 px-3 py-2 text-sm
                            transition  rounded hover:bg-blue-500 hover:text-white
                            ${
                              isSelected
                                ? "text-gray-700 font-medium"
                                : "text-gray-700"
                            }
                          `}
                        >
                          <span className="w-4">
                            {isSelected && <Check className="w-4 h-4" />}
                          </span>

                          <span>{source}</span>
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
            </div>

            <div className="relative">
              <button
                onClick={() => setShowDatePicker(!showDatePicker)}
                className="flex items-center gap-2 border border-gray-300 px-4 py-2 rounded-md hover:bg-blue-500 hover:text-white transition text-sm font-semibold text-gray-600"
              >
                <Calendar size={14} />
                {startDate && endDate
                  ? `${new Date(startDate).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    })} - ${new Date(endDate).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    })}`
                  : "Date Range"}
              </button>

              {showDatePicker && (
                <div className="absolute top-full left-0 mt-2 bg-white border border-gray-200 rounded-xl shadow-2xl p-4 z-30 w-[580px] max-w-[calc(100vw-2rem)]">
                  <div className="flex justify-between items-center mb-3 pb-3 border-b border-gray-200">
                    <div className="flex items-center gap-3">
                      <Calendar size={16} className="text-gray-600" />
                      <span className="font-semibold text-sm text-gray-900">
                        {startDate
                          ? new Date(startDate).toLocaleDateString("en-US", {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            })
                          : "Select date"}
                      </span>
                      {startDate && endDate && (
                        <>
                          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                            1 active
                          </span>
                          <button
                            onClick={() => {
                              setStartDate(null);
                              setEndDate(null);
                            }}
                            className="text-xs text-blue-600 hover:text-blue-700 hover:underline ml-1"
                          >
                            Clear all
                          </button>
                        </>
                      )}
                    </div>
                    <button
                      onClick={() => setShowDatePicker(false)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <X size={18} />
                    </button>
                  </div>

                  <div className="flex items-center justify-between mb-3">
                    <button
                      onClick={() =>
                        setCurrentMonth(
                          new Date(
                            currentMonth.getFullYear(),
                            currentMonth.getMonth() - 1
                          )
                        )
                      }
                      className="p-1 hover:bg-gray-100 rounded transition"
                    >
                      <ChevronLeft size={18} className="text-gray-600" />
                    </button>
                    <button
                      onClick={() =>
                        setCurrentMonth(
                          new Date(
                            currentMonth.getFullYear(),
                            currentMonth.getMonth() + 1
                          )
                        )
                      }
                      className="p-1 hover:bg-gray-100 rounded transition"
                    >
                      <ChevronRight size={18} className="text-gray-600" />
                    </button>
                  </div>

                  <div className="flex flex-col gap-4 sm:flex-row sm:gap-6">
                    {renderCalendar(0)}
                    {renderCalendar(1)}
                  </div>
                </div>
              )}
            </div>

            <div>
              {hasActiveFilters && (
                <button
                  onClick={clearFilters}
                  className="
                    inline-flex items-center justify-center gap-2
                    whitespace-nowrap text-sm font-medium
                    text-muted-foreground hover:text-foreground
                    hover:bg-blue-400
                    rounded-md px-3 h-9
                    transition-colors
                    focus-visible:outline-none
                    focus-visible:ring-2
                    focus-visible:ring-blue-500
                    focus-visible:ring-offset-2
                    disabled:pointer-events-none disabled:opacity-50
                    [&_svg]:pointer-events-none
                    [&_svg]:size-4
                    [&_svg]:shrink-0
                  "
                >
                  <X className="w-4 h-4 mr-1" />
                  Clear all
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {[
                    "Tender",
                    "Agency",
                    "Source",
                    "Deadline",
                    "Status",
                    "Keywords",
                    "Actions",
                  ].map((h) => (
                    <th
                      key={h}
                      className="text-left px-6 py-3.5 text-sm font-semibold text-gray-600 tracking-wider"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody className="divide-y divide-gray-100">
                {filteredTenders.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8">
                      <EmptyState
                        title="No tenders found"
                        message="Try adjusting filters or check back later."
                      />
                    </td>
                  </tr>
                ) : (
                  filteredTenders.map((tender) => (
                  <tr
                    key={tender.id}
                    className="border-b border-gray-200 hover:bg-gray-50 transition"
                  >
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-gray-900 line-clamp-1">
                          {tender.title}
                        </span>
                        <span className="text-xs text-gray-500 mt-1">
                          {tender.reference_id}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <div className="flex items-center gap-1.5 text-sm text-gray-900">
                          <Building2 size={14} className="text-gray-400" />
                          {tender.agency_name}
                        </div>
                        <div className="flex items-center gap-1.5 text-xs text-gray-500 mt-1">
                          <MapPin size={14} className="text-gray-400" />
                          {tender.agency_location}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {tender.source_name}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-gray-900">
                          {tender.deadline_date ? new Date(tender.deadline_date).toLocaleDateString() : 'N/A'}
                        </span>
                        <span className="text-xs text-gray-500 mt-1">
                          {tender.days_until_deadline !== null ? `${tender.days_until_deadline} days left` : ''}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={tender.status} />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-2">
                        {getTenderKeywordsText(tender).split(',').filter(k => k).slice(0, 2).map((keyword, idx) => (
                          <span
                            key={`${tender.id}-kw-${idx}`}
                            className="bg-gray-100 px-3 py-1 rounded-full text-xs"
                          >
                            {keyword.trim()}
                          </span>
                        ))}
                      </div>
                    </td>

                      <td className="px-6 py-4">
                        <div className="flex gap-3 text-gray-600">
                          <button
                            className="p-1.5 rounded hover:bg-[#2563eb] transition group"
                            onClick={() => {
                              setSelectedTender(tender);
                              if (tender.status?.toLowerCase() === 'new') {
                                updateTenderStatus(tender.id, 'viewed');
                              }
                              openTenderSource(tender);
                            }}
                          >
                            <Eye
                              size={18}
                              strokeWidth={2}
                              className="cursor-pointer text-gray-600 group-hover:text-white"
                            />
                          </button>
                          <button 
                            className={`p-1.5 rounded transition group ${tender.status?.toLowerCase() === 'saved' ? 'bg-blue-100' : 'hover:bg-[#2563eb]'}`}
                            onClick={() => {
                              const nextStatus = tender.status?.toLowerCase() === 'saved' ? 'viewed' : 'saved';
                              updateTenderStatus(tender.id, nextStatus);
                            }}
                          >
                            <Bookmark
                              size={18}
                              strokeWidth={2}
                              className={`cursor-pointer group-hover:text-white ${tender.status?.toLowerCase() === 'saved' ? 'text-blue-600 fill-blue-600' : 'text-gray-600'}`}
                            />
                          </button>
                          <div className="relative">
                            <button
                              onClick={() =>
                                setOpenDropdown(
                                  openDropdown === tender.id ? null : tender.id
                                )
                              }
                              className="p-1.5 rounded hover:bg-[#2563eb] transition group"
                            >
                              <MoreHorizontal
                                size={18}
                                strokeWidth={2}
                                className="cursor-pointer text-gray-600 group-hover:text-white"
                              />
                            </button>
                            {openDropdown === tender.id && (
                              <>
                                <div
                                  className="fixed inset-0 z-10"
                                  onClick={() => setOpenDropdown(null)}
                                />
                                <div className="absolute right-0 top-6 mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-20 py-1">
                                  <button
                                    onClick={() => {
                                      if (tender.source_url) window.open(tender.source_url, '_blank');
                                      setOpenDropdown(null);
                                    }}
                                    className="w-full text-left px-4 py-2 text-sm text-gray-700 rounded hover:bg-blue-500 hover:text-white flex items-center gap-2"
                                  >
                                    <ExternalLink size={14} />
                                    Open Source URL
                                  </button>
                                  <button
                                    onClick={() => {
                                      setSelectedTender(tender);
                                      setOpenDropdown(null);
                                    }}
                                    className="w-full text-left px-4 py-2 text-sm text-gray-700  rounded hover:bg-blue-500 hover:text-white flex items-center gap-2"
                                  >
                                    <Bookmark size={14} />
                                    Save Tender
                                  </button>
                                </div>
                              </>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="flex justify-between items-center mt-4 text-sm text-gray-500">
          <span>
            Showing {filteredTenders.length} of {safeTenders.length} tenders
          </span>
        </div>
      </div>

      {selectedTender && (
        <>
          <div
            className="fixed inset-0 bg-black bg-opacity-30 z-40"
            onClick={() => setSelectedTender(null)}
          />

          <div className="fixed top-0 right-0 h-full w-full sm:w-[500px] bg-white shadow-2xl z-50 overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-start mb-6">
                <StatusBadge status={selectedTender.status} />
                <button
                  onClick={() => setSelectedTender(null)}
                  className="text-gray-400 hover:text-gray-600 transition"
                >
                  <X size={20} />
                </button>
              </div>

              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                {selectedTender.title}
              </h2>
              <p className="text-sm text-gray-500 mb-8">
                {selectedTender.reference_id || selectedTender.code}
              </p>

              <div className="grid grid-cols-2 gap-6 mb-8">
                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <Building2 size={20} className="text-blue-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Agency</p>
                    <p className="text-sm font-semibold text-gray-900">
                      {selectedTender.agency_name || selectedTender.agency}
                    </p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <MapPin size={20} className="text-blue-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Location</p>
                    <p className="text-sm font-semibold text-gray-900">
                      {selectedTender.agency_location || selectedTender.location}
                    </p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-lg bg-green-50 flex items-center justify-center flex-shrink-0">
                    <Calendar size={20} className="text-green-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Published</p>
                    <p className="text-sm font-semibold text-gray-900">
                      {selectedTender.published}
                    </p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                    <Calendar size={20} className="text-blue-600" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Deadline</p>
                    <p className="text-sm font-semibold text-gray-900">
                      {selectedTender.deadline_date ? new Date(selectedTender.deadline_date).toLocaleDateString() : 'N/A'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {selectedTender.days_until_deadline !== null ? `${selectedTender.days_until_deadline} days left` : ''}
                    </p>
                  </div>
                </div>
              </div>

              <div className="mb-8">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-sm font-semibold text-gray-900">
                    Keyword Matches
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {getTenderKeywordsText(selectedTender).split(',').filter(k => k).map((keyword, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1.5 rounded-md bg-blue-50 text-sm font-medium text-blue-700"
                    >
                      {keyword.trim()}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mb-8">
                <h3 className="text-sm font-semibold text-gray-900 mb-3">
                  Description
                </h3>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {selectedTender.description}
                </p>
              </div>

              {selectedTender.attachments &&
                selectedTender.attachments.length > 0 && (
                  <div className="mb-8">
                    <h3 className="text-sm font-semibold text-gray-900 mb-3">
                      Attachments
                    </h3>
                    <div className="space-y-2">
                      {selectedTender.attachments.map((attachment, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-3 rounded-lg bg-red-50 hover:bg-red-100 transition cursor-pointer"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded bg-red-100 flex items-center justify-center">
                              <span className="text-red-600 text-xs font-bold">
                                PDF
                              </span>
                            </div>
                            <div>
                              <p className="text-sm font-medium text-gray-900">
                                {attachment.name}
                              </p>
                              <p className="text-xs text-gray-500">
                                {attachment.size}
                              </p>
                            </div>
                          </div>
                          <Download size={16} className="text-gray-600" />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              <button 
                onClick={() => {
                  if (selectedTender.source_url) window.open(selectedTender.source_url, '_blank');
                }}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold flex items-center justify-center gap-2 transition"
              >
                <ExternalLink size={18} />
                View on {selectedTender.source_name || selectedTender.source || 'Source'}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default TenderListing;
