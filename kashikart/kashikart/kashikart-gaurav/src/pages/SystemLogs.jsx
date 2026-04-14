import React, { useMemo, useState, useEffect, useCallback } from "react";
import { EmptyState } from "../components/States";
import { getErrorMessage, requestJson, requestWithRetry } from "../utils/api";
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Info,
  Search,
  Filter,
  Download,
  Trash2,
  Bell,
  RefreshCw
} from "lucide-react";

const VALID_STATUS = ["Success", "Warning", "Error", "Info"];
const SYSTEM_LOGS_ENDPOINTS = {
  list: "/api/system-logs/",
  clear: "/api/system-logs/",
};

function parseDateTime(createdAt) {
  if (!createdAt) return { date: "", time: "" };
  try {
    const date = new Date(createdAt);
    const dateStr = date.toISOString().slice(0, 10);
    const timeStr = date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
    return { date: dateStr, time: timeStr };
  } catch {
    return { date: "", time: "" };
  }
}

function isValidStatus(status) {
  return VALID_STATUS.includes(status);
}

function isValidLog(log) {
  if (!log || typeof log !== 'object') return false;
  if (!isValidStatus(log.status)) return false;
  if (typeof log.message !== "string" || log.message.trim() === "") return false;
  if (typeof log.source !== "string" || log.source.trim() === "") return false;
  // created_at or date validation for backend logs
  if (!log.created_at && !log.date) return false;
  return true;
}

function getLocalDateOnly(dateOrCreatedAt, time) {
  try {
    let dateStr = dateOrCreatedAt;
    if (dateOrCreatedAt && dateOrCreatedAt.includes('T')) {
      dateStr = dateOrCreatedAt.slice(0, 10);
    }
    const d = new Date(`${dateStr}T${time || "00:00:00"}`);
    return d.toISOString().slice(0, 10);
  } catch {
    return "";
  }
}

export default function SystemLogs() {
  const [logs, setLogs] = useState([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All Status");
  const [selectedDate, setSelectedDate] = useState("");
  const [notifications, setNotifications] = useState([]);
  const [openNotif, setOpenNotif] = useState(false);
  const [toast, setToast] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 25;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [backendStats, setBackendStats] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);

      const [data, notifData] = await Promise.all([
        requestWithRetry(() => requestJson(SYSTEM_LOGS_ENDPOINTS.list)),
        requestWithRetry(() => requestJson("/api/notifications/")).catch(() => ({ items: [] }))
      ]);

      const items = Array.isArray(data) ? data : (data?.items || []);
      
      // Transform backend logs to expected format
      const transformedLogs = items.map(log => ({
        ...log,
        ...(log.created_at ? parseDateTime(log.created_at) : {}),
        status: log.status || 'Info'
      })).filter(isValidLog);
      
      setLogs(transformedLogs);
      setLastRefresh(new Date().toLocaleTimeString());

      if (data?.stats) {
        setBackendStats(data.stats);
      }

      if (notifData?.items) {
        setNotifications(notifData.items);
      }
    } catch (err) {
      console.error(err);
      setError(getErrorMessage(err, "Failed to load system logs"));
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh every 5 minutes (300000 ms)
  useEffect(() => {
    fetchLogs(); // Initial load
    
    const interval = setInterval(() => {
      fetchLogs();
    }, 300000); // 5 minutes

    return () => clearInterval(interval);
  }, []);

  if (!Array.isArray(logs)) {
    return (
      <div className="w-full bg-white px-6 py-10 text-sm text-red-700">
        Unable to load system logs. Please try again.
      </div>
    );
  }

  const filteredLogs = useMemo(() => {
    try {
      const safeSearch = search.trim().toLowerCase();
      const safeStatus = statusFilter === "All Status" ? "All Status" : statusFilter;

      return logs
        .filter(isValidLog)
        .filter((log) => {
          if (!safeSearch) return true;
          const source = log.source?.toLowerCase() || "";
          const message = log.message?.toLowerCase() || "";
          return source.includes(safeSearch) || message.includes(safeSearch);
        })
        .filter((log) => {
          const matchStatus = safeStatus === "All Status" || log.status === safeStatus;
          const logDate = log.date || (log.created_at ? parseDateTime(log.created_at).date : "");
          const matchDate = !selectedDate || getLocalDateOnly(logDate, log.time) === selectedDate;
          return matchStatus && matchDate;
        });
    } catch (err) {
      console.error("Error filtering logs:", err);
      return [];
    }
  }, [logs, search, statusFilter, selectedDate]);

  const exportableLogs = useMemo(() => {
    return filteredLogs.filter(isValidLog);
  }, [filteredLogs]);

  const exportLogs = useCallback(() => {
    try {
      setError(null);
      if (exportableLogs.length === 0) {
        alert("No valid logs to export");
        return;
      }
      setLoading(true);

      const blob = new Blob([JSON.stringify(exportableLogs, null, 2)], {
        type: "application/json",
      });

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `system-logs-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export logs:", err);
      setError("Failed to export logs. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [exportableLogs]);

  const stats = useMemo(() => {
    if (backendStats) return backendStats;
    const validLogs = logs.filter(isValidLog);
    const count = (s) => validLogs.filter((l) => l.status === s).length;
    return {
      Success: count("Success"),
      Warning: count("Warning"),
      Error: count("Error"),
      Info: count("Info"),
    };
  }, [logs, backendStats]);

  const clearAll = useCallback(async () => {
    try {
      // TODO: Implement backend clear endpoint when available
      setLogs([]);
      setToast({ message: "Logs cleared locally", status: "Info" });
      setTimeout(() => setToast(null), 3000);
    } catch (err) {
      console.error(err);
    }
  }, []);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.is_read).length,
    [notifications]
  );

  const handleToggleNotifications = useCallback(() => {
    setOpenNotif((prev) => !prev);
  }, []);

  useEffect(() => {
    setCurrentPage(1);
  }, [search, statusFilter, selectedDate]);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(filteredLogs.length / pageSize)),
    [filteredLogs.length, pageSize]
  );
  const safePage = Math.min(currentPage, totalPages);
  const startIndex = (safePage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedLogs = useMemo(
    () => filteredLogs.slice(startIndex, endIndex),
    [filteredLogs, startIndex, endIndex]
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
      pushPage(1); pushPage(2); pushPage(3); pushDots("end"); pushPage(total); return items;
    }
    if (current >= total - 2) {
      pushPage(1); pushDots("start"); pushPage(total - 2); pushPage(total - 1); pushPage(total); return items;
    }

    pushPage(1); pushDots("start"); pushPage(current - 1); pushPage(current); pushPage(current + 1); pushDots("end"); pushPage(total);
    return items;
  }, []);

  const pageItems = useMemo(
    () => getPageItems(totalPages, safePage),
    [getPageItems, totalPages, safePage]
  );

  return (
    <div className="w-full bg-white">
      {/* Header */}
      <header className="w-full bg-white px-4 md:px-8 py-6 flex flex-col sm:flex-row gap-4 sm:justify-between sm:items-center">
        <div>
          <h1 className="text-2xl font-semibold text-gray-800">System Logs</h1>
          <p className="text-sm text-gray-500 mt-1">
            Monitor system activity and troubleshoot issues
            {lastRefresh && (
              <>
                {" "}• Last refresh: <span className="font-mono text-xs">{lastRefresh}</span>
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={fetchLogs} 
            disabled={loading}
            className="flex items-center gap-1 text-sm bg-blue-500 hover:bg-blue-600 text-white px-3 py-2 rounded-lg transition disabled:opacity-50"
            title="Refresh logs"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
          <button onClick={handleToggleNotifications} className="relative p-2">
            <Bell className="text-gray-600" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 text-xs flex items-center justify-center rounded-full bg-red-500 text-white font-bold animate-pulse">
                {unreadCount}
              </span>
            )}
          </button>
        </div>
      </header>

      {openNotif && (
        <div className="absolute right-6 top-20 w-80 bg-white border border-gray-200 rounded-xl shadow-lg z-50">
          <div className="px-4 py-3 font-semibold text-gray-700 border-b">Notifications</div>
          {notifications.length === 0 ? (
            <div className="p-4 text-sm text-gray-500">No notifications</div>
          ) : (
            <ul className="max-h-64 overflow-y-auto">
              {notifications.map((n) => (
                <li key={n.id} className={`px-4 py-3 border-b last:border-none ${!n.is_read ? "bg-blue-50" : ""}`}>
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-sm font-medium">{n.status}</div>
                      <div className="text-xs text-gray-500">{n.source} • {n.date}</div>
                      <div className="text-sm text-gray-700 mt-1">{n.message || "No details available"}</div>
                    </div>
                    {!n.is_read && (
                      <button
                        onClick={() => setNotifications((prev) => prev.map((x) => x.id === n.id ? { ...x, is_read: true } : x))}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Mark
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Content */}
      <main className="bg-[#f7fbfb] px-4 md:px-8 pb-8 pt-6 w-full">
        {loading && (
          <div className="mb-6 text-sm text-gray-500 flex items-center gap-2">
            <RefreshCw className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full" />
            Loading system logs...
          </div>
        )}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5 mb-8">
          <StatCard icon={<CheckCircle className="text-green-500" />} value={stats.Success} label="Success" bg="bg-green-50" />
          <StatCard icon={<AlertTriangle className="text-yellow-500" />} value={stats.Warning} label="Warnings" bg="bg-yellow-50" />
          <StatCard icon={<XCircle className="text-red-500" />} value={stats.Error} label="Errors" bg="bg-red-50" />
          <StatCard icon={<Info className="text-blue-500" />} value={stats.Info} label="Info" bg="bg-blue-50" />
        </div>

        {/* Filter Bar */}
        <div className="mb-8">
          <div className="flex flex-col lg:flex-row lg:items-center gap-5">
            <div className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg px-4 py-3 w-full lg:w-[280px]">
              <Search size={18} className="text-gray-400" />
              <input
                placeholder="Search sources..."
                className="outline-none bg-transparent text-sm w-full"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            <select
              className="bg-white hover:bg-gray-50 border border-gray-200 rounded-lg px-3 py-3 text-sm w-full lg:w-[180px]"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option>All Status</option>
              <option>Success</option>
              <option>Warning</option>
              <option>Error</option>
              <option>Info</option>
            </select>

            <div className="flex items-center justify-center gap-2 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg px-5 py-3 text-sm w-full lg:w-auto">
              <Filter size={18} className="text-gray-500" />
              <input
                type="date"
                className="outline-none text-sm bg-transparent"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
              />
            </div>

            <div className="flex flex-col sm:flex-row gap-4 lg:ml-auto w-full lg:w-auto">
              <button
                onClick={exportLogs}
                className="flex items-center justify-center gap-2 bg-white border border-gray-300 rounded-lg px-5 py-3 text-sm shadow-sm hover:bg-gray-50 transition"
              >
                <Download size={18} />
                Export
              </button>
              <button
                onClick={clearAll}
                className="flex items-center justify-center gap-2 bg-white border border-gray-300 rounded-lg px-5 py-3 text-sm text-red-600 shadow-sm hover:bg-red-50 transition"
              >
                <Trash2 size={18} />
                Clear All
              </button>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="max-h-[520px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="hidden md:table-header-group bg-gray-50 text-gray-600">
                <tr>
                  <th className="text-left px-6 py-4 font-medium">Timestamp</th>
                  <th className="text-left px-7 py-4 font-medium">Source</th>
                  <th className="text-center px-10 py-4 font-medium">Status</th>
                  <th className="text-left px-20 py-4 font-medium">Message</th>
                </tr>
              </thead>
              <tbody>
                {paginatedLogs.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-8">
                      <EmptyState
                        title="No logs found"
                        message="Try adjusting filters or check back later. Logs auto-refresh every 5 minutes."
                      />
                    </td>
                  </tr>
                ) : (
                  paginatedLogs.map((log, i) => (
                    <tr
                      key={`${log.id || i}-${log.source}-${i}`}
                      className="border-t md:table-row flex flex-col md:flex-row px-4 py-3 md:p-0 hover:bg-gray-50 transition"
                    >
                      <td className="px-6 py-3 text-gray-500 whitespace-nowrap">
                        <span className="md:hidden font-semibold text-gray-600">Timestamp:&nbsp;</span>
                        <span>{log.date}</span>
                        <span className="ml-4">{log.time}</span>
                      </td>
                      <td className="px-6 py-3 font-medium text-gray-800 text-left">
                        <span className="md:hidden font-semibold text-gray-600">Source:&nbsp;</span>
                        {log.source}
                      </td>
                      <td className="px-6 py-3 text-center">
                        <span className="md:hidden font-semibold text-gray-600">Status:&nbsp;</span>
                        <StatusBadge status={log.status} />
                      </td>
                      <td className="px-6 py-3 text-gray-600">
                        <span className="md:hidden font-semibold text-gray-600">Message:&nbsp;</span>
                        {log.message || "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-4">
            <div className="text-sm text-gray-500 font-medium">
              Showing {filteredLogs.length === 0 ? 0 : startIndex + 1}-
              {Math.min(endIndex, filteredLogs.length)} of {filteredLogs.length} results
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
                {pageItems.map((item) => (
                  item.type === "dots" ? (
                    <span key={item.key} className="w-8 h-8 text-xs text-gray-500 flex items-center justify-center">...</span>
                  ) : (
                    <button
                      key={item.value}
                      onClick={() => goToPage(item.value)}
                      className={`w-8 h-8 text-xs rounded border ${
                        item.value === safePage
                          ? "bg-indigo-600 text-white border-gray-900"
                          : "bg-white text-gray-700 border-gray-200 hover:bg-gray-50"
                      }`}
                    >
                      {item.value}
                    </button>
                  )
                ))}
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
        )}
      </main>

      {toast && (
        <div className="fixed bottom-6 right-6 bg-white border shadow-lg rounded-lg px-4 py-3 flex gap-3 items-start z-50">
          <div>
            <div className="font-semibold text-sm">{toast.status}</div>
            <div className="text-xs text-gray-600">{toast.message}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, value, label, bg }) {
  return (
    <div className="bg-white rounded-xl p-4 flex items-center gap-4 shadow-sm border border-gray-100">
      <div className={`p-3 rounded ${bg}`}>{icon}</div>
      <div>
        <div className="text-lg font-semibold text-gray-800">{value}</div>
        <div className="text-sm text-gray-500">{label}</div>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    Success: "bg-green-100 text-green-600",
    Warning: "bg-yellow-100 text-yellow-600",
    Error: "bg-red-100 text-red-600",
    Info: "bg-blue-100 text-blue-600",
  };

  return (
    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${map[status] || "bg-gray-100 text-gray-600"}`}>
      {status === "Success" && <CheckCircle size={14} />}
      {status === "Warning" && <AlertTriangle size={14} />}
      {status === "Error" && <XCircle size={14} />}
      {status === "Info" && <Info size={14} />}
      {status}
    </span>
  );
}

