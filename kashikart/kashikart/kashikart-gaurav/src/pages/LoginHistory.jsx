import React, { useEffect, useMemo, useState, useCallback } from "react";
import {
  Calendar,
  CalendarDays,
  CalendarRange,
  Search,
  ShieldCheck,
  ShieldOff,
  TrendingDown,
  TrendingUp,
  Users,
} from "lucide-react";

const HISTORY_KEY = "loginHistory";
const BLOCKED_KEY = "blockedUsers";

const MOCK_HISTORY = [
  {
    id: "lh-1",
    name: "Gaurav",
    email: "gauravkumar@gmail.com",
    role: "Admin",
    date: "2026-02-03",
    time: "09:12 AM",
    timestamp: 1765108320000,
  },
  {
    id: "lh-2",
    name: "Aman",
    email: "aman@company.com",
    role: "User",
    date: "2026-02-03",
    time: "10:45 AM",
    timestamp: 1765113900000,
  },
  {
    id: "lh-3",
    name: "Neha",
    email: "neha@company.com",
    role: "User",
    date: "2026-02-02",
    time: "06:28 PM",
    timestamp: 1765036080000,
  },
];

const loadHistory = () => {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (Array.isArray(parsed) && parsed.length > 0) return parsed;
  } catch (err) {
    console.error("Failed to load login history:", err);
  }
  return MOCK_HISTORY;
};

const loadBlockedMap = () => {
  try {
    const raw = localStorage.getItem(BLOCKED_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (err) {
    console.error("Failed to load blocked users:", err);
    return {};
  }
};

export default function LoginHistory() {
  const [history, setHistory] = useState(loadHistory);
  const [blockedUsers, setBlockedUsers] = useState(loadBlockedMap);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  useEffect(() => {
    const refresh = () => {
      setHistory(loadHistory());
      setBlockedUsers(loadBlockedMap());
    };

    refresh();
    window.addEventListener("storage", refresh);
    window.addEventListener("loginHistoryUpdated", refresh);
    window.addEventListener("blockedUsersUpdated", refresh);

    return () => {
      window.removeEventListener("storage", refresh);
      window.removeEventListener("loginHistoryUpdated", refresh);
      window.removeEventListener("blockedUsersUpdated", refresh);
    };
  }, []);

  const normalizedSearch = search.trim().toLowerCase();

  const filteredHistory = useMemo(() => {
    const list = Array.isArray(history) ? history : [];

    return list
      .filter((item) => {
        if (!normalizedSearch) return true;
        const haystack = `${item.name} ${item.email} ${item.role}`
          .toLowerCase()
          .trim();
        return haystack.includes(normalizedSearch);
      })
      .filter((item) => {
        if (statusFilter === "All") return true;
        const key = String(item.email || "").toLowerCase();
        const isBlocked = Boolean(blockedUsers[key]);
        return statusFilter === "Blocked" ? isBlocked : !isBlocked;
      })
      .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
  }, [history, normalizedSearch, statusFilter, blockedUsers]);

  const stats = useMemo(() => {
    const list = Array.isArray(history) ? history : [];
    const now = new Date();
    const nowMs = now.getTime();
    const oneDay = 24 * 60 * 60 * 1000;
    const startOfToday = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate()
    ).getTime();
    const startOfYesterday = startOfToday - oneDay;
    const weekAgo = nowMs - 7 * oneDay;
    const prevWeekAgo = nowMs - 14 * oneDay;
    const monthAgo = nowMs - 30 * oneDay;
    const prevMonthAgo = nowMs - 60 * oneDay;

    const countBetween = (from, to) =>
      list.filter((item) => {
        const ts = item.timestamp || 0;
        return ts >= from && ts < to;
      }).length;

    const today = countBetween(startOfToday, nowMs + 1);
    const yesterday = countBetween(startOfYesterday, startOfToday);
    const weekly = countBetween(weekAgo, nowMs + 1);
    const prevWeekly = countBetween(prevWeekAgo, weekAgo);
    const monthly = countBetween(monthAgo, nowMs + 1);
    const prevMonthly = countBetween(prevMonthAgo, monthAgo);

    const uniqueAll = new Set(
      list.map((item) => String(item.email || "").toLowerCase()).filter(Boolean)
    );
    const uniqueMonthly = new Set(
      list
        .filter((item) => (item.timestamp || 0) >= monthAgo)
        .map((item) => String(item.email || "").toLowerCase())
        .filter(Boolean)
    );
    const uniquePrevMonthly = new Set(
      list
        .filter(
          (item) =>
            (item.timestamp || 0) >= prevMonthAgo &&
            (item.timestamp || 0) < monthAgo
        )
        .map((item) => String(item.email || "").toLowerCase())
        .filter(Boolean)
    );

    return {
      today,
      yesterday,
      weekly,
      prevWeekly,
      monthly,
      prevMonthly,
      unique: uniqueAll.size,
      uniqueMonthly: uniqueMonthly.size,
      uniquePrevMonthly: uniquePrevMonthly.size,
    };
  }, [history]);

  const pctChange = useCallback((current, prev) => {
    if (!prev) return null;
    return Math.round(((current - prev) / prev) * 100);
  }, []);

  const renderTrend = useCallback(
    (current, prev, label) => {
      const pct = pctChange(current, prev);
      if (pct === null) {
        return (
          <div className="mt-2 flex items-center gap-2 text-xs">
            <span className="text-gray-500">{label}</span>
            <span className="text-gray-400">—</span>
          </div>
        );
      }

      const isUp = pct >= 0;
      const TrendIcon = isUp ? TrendingUp : TrendingDown;

      return (
        <div className="mt-2 flex items-center gap-2 text-xs">
          <span className="text-gray-500">{label}</span>
          <span
            className={`flex items-center gap-1 font-semibold ${
              isUp ? "text-emerald-600" : "text-red-600"
            }`}
          >
            <TrendIcon size={12} />
            {pct > 0 ? "+" : ""}
            {pct}%
          </span>
        </div>
      );
    },
    [pctChange]
  );

  const toggleBlock = useCallback(
    (email) => {
      const key = String(email || "").toLowerCase();
      if (!key) return;

      const next = { ...blockedUsers, [key]: !blockedUsers[key] };
      setBlockedUsers(next);
      localStorage.setItem(BLOCKED_KEY, JSON.stringify(next));
      window.dispatchEvent(new Event("blockedUsersUpdated"));
    },
    [blockedUsers]
  );

  return (
    <div className="min-h-full bg-gray-50">
      <header className="flex flex-col gap-3 px-4 py-5 border-b bg-white sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Login History</h1>
          <p className="text-sm text-gray-500">
            Track logins and manage user access
          </p>
        </div>
      </header>

      <main className="p-4 sm:p-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">
                  Today Logins
                </p>
                <p className="mt-2 text-3xl font-semibold text-gray-900">
                  {stats.today}
                </p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                <Calendar size={20} />
              </div>
            </div>
            {renderTrend(stats.today, stats.yesterday, "vs yesterday")}
          </div>
          <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">
                  Weekly Logins
                </p>
                <p className="mt-2 text-3xl font-semibold text-gray-900">
                  {stats.weekly}
                </p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                <CalendarDays size={20} />
              </div>
            </div>
            {renderTrend(stats.weekly, stats.prevWeekly, "vs prev 7 days")}
          </div>
          <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">
                  Monthly Logins
                </p>
                <p className="mt-2 text-3xl font-semibold text-gray-900">
                  {stats.monthly}
                </p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-50 text-purple-600">
                <CalendarRange size={20} />
              </div>
            </div>
            {renderTrend(stats.monthly, stats.prevMonthly, "vs prev 30 days")}
          </div>
          <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">
                  Unique Users
                </p>
                <p className="mt-2 text-3xl font-semibold text-gray-900">
                  {stats.unique}
                </p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
                <Users size={20} />
              </div>
            </div>
            {renderTrend(
              stats.uniqueMonthly,
              stats.uniquePrevMonthly,
              "vs prev 30 days"
            )}
          </div>
        </div>

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full sm:max-w-sm">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search name, email, or role..."
              className="w-full rounded-lg border border-gray-200 bg-white px-9 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm"
            >
              <option>All</option>
              <option>Active</option>
              <option>Blocked</option>
            </select>
            {(search || statusFilter !== "All") && (
              <button
                onClick={() => {
                  setSearch("");
                  setStatusFilter("All");
                }}
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        <div className="mt-4 bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="text-left px-5 py-3 font-medium">User</th>
                  <th className="text-left px-5 py-3 font-medium">Email</th>
                  <th className="text-left px-5 py-3 font-medium">Role</th>
                  <th className="text-left px-5 py-3 font-medium">Date</th>
                  <th className="text-left px-5 py-3 font-medium">Time</th>
                  <th className="text-left px-5 py-3 font-medium">Status</th>
                  <th className="text-right px-5 py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredHistory.length === 0 ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-5 py-6 text-center text-gray-500"
                    >
                      No login history found
                    </td>
                  </tr>
                ) : (
                  filteredHistory.map((item) => {
                    const emailKey = String(item.email || "").toLowerCase();
                    const isBlocked = Boolean(blockedUsers[emailKey]);
                    return (
                      <tr
                        key={item.id || `${item.email}-${item.timestamp}`}
                        className="border-t"
                      >
                        <td className="px-5 py-3 font-medium text-gray-900">
                          {item.name || "Unknown"}
                        </td>
                        <td className="px-5 py-3 text-gray-600">
                          {item.email || "—"}
                        </td>
                        <td className="px-5 py-3 text-gray-600">
                          {item.role || "User"}
                        </td>
                        <td className="px-5 py-3 text-gray-600">
                          {item.date || "—"}
                        </td>
                        <td className="px-5 py-3 text-gray-600">
                          {item.time || "—"}
                        </td>
                        <td className="px-5 py-3">
                          <span
                            className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
                              isBlocked
                                ? "bg-red-100 text-red-700"
                                : "bg-green-100 text-green-700"
                            }`}
                          >
                            {isBlocked ? "Blocked" : "Active"}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right">
                          <button
                            onClick={() => toggleBlock(item.email)}
                            className={`inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                              isBlocked
                                ? "bg-green-600 text-white hover:bg-green-700"
                                : "bg-red-600 text-white hover:bg-red-700"
                            }`}
                          >
                            {isBlocked ? (
                              <>
                                <ShieldCheck size={14} />
                                Unblock
                              </>
                            ) : (
                              <>
                                <ShieldOff size={14} />
                                Block
                              </>
                            )}
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
