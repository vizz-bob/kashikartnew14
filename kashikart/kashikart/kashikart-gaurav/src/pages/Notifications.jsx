import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
  memo,
} from "react";
import { Bell, Mail, Trash2, Clock, Plus, X } from "lucide-react";
import { getErrorMessage, requestJson, requestWithRetry } from "../utils/api";

const USE_MOCK_NOTIFICATIONS = false; // Connected to backend API
const NOTIFICATION_ENDPOINTS = {
  settings: "/api/notifications/settings",
  list: "/api/notifications/", // TODO BACKEND: yahi endpoint use hoga
};

const PRIMARY_BLUE = "#3B82F6";

const INITIAL_NOTIFICATIONS = [];

export default function Notifications() {
  const [desktop, setDesktop] = useState(true);
  const [email, setEmail] = useState(true);
  const [silent, setSilent] = useState(true);
  const [emailList, setEmailList] = useState([]);
  const [newEmail, setNewEmail] = useState("");
  const [startTime, setStartTime] = useState("22:00");
  const [endTime, setEndTime] = useState("07:00");
  const [showSaveNotification, setShowSaveNotification] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS);
  const notificationMenuRef = useRef(null);

  const safeEmailList = useMemo(
    () => (Array.isArray(emailList) ? emailList : []),
    [emailList]
  );

  const fetchSettings = useCallback(async () => {
    if (USE_MOCK_NOTIFICATIONS) return; // TODO BACKEND: mock delete karke API call enable hoga
    try {
      setLoading(true);
      setError(null);

      const data = await requestWithRetry(() =>
        requestJson(NOTIFICATION_ENDPOINTS.settings)
      );

      if (!data || typeof data !== "object") {
        throw new Error("Invalid notification settings");
      }

      setDesktop(Boolean(data.desktop));
      setEmail(Boolean(data.email ?? data.enable_email));
      setSilent(Boolean(data.silent ?? data.enable_silent_hours));
      if (Array.isArray(data.emailList ?? data.email_recipients)) {
        setEmailList(data.emailList ?? data.email_recipients);
      }
      if (typeof (data.startTime ?? data.silent_start_time) === "string") {
        setStartTime(data.startTime ?? data.silent_start_time);
      }
      if (typeof (data.endTime ?? data.silent_end_time) === "string") {
        setEndTime(data.endTime ?? data.silent_end_time);
      }
      if (typeof data.enable_desktop === "boolean") {
        setDesktop(data.enable_desktop);
      }
    } catch (err) {
      console.error(err);
      setError(getErrorMessage(err, "Failed to load notification settings"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const fetchNotifications = useCallback(async () => {
    if (USE_MOCK_NOTIFICATIONS) return; // TODO BACKEND: mock hata ke API se data aayega
    try {
      setError(null);
      const data = await requestWithRetry(() =>
        requestJson(NOTIFICATION_ENDPOINTS.list)
      );
      const notificationItems = Array.isArray(data) ? data : data?.items;
      if (!Array.isArray(notificationItems)) {
        throw new Error("Invalid notifications format from server");
      }
      setNotifications(
        notificationItems.map((n) => ({
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

  const handleAddEmail = useCallback(() => {
    if (newEmail.trim() && newEmail.includes("@")) {
      setEmailList([...emailList, newEmail.trim()]);
      setNewEmail("");
    }
  }, [emailList, newEmail]);

  const handleRemoveEmail = useCallback(
    (indexToRemove) => {
      setEmailList(emailList.filter((_, index) => index !== indexToRemove));
    },
    [emailList]
  );

  const handleSaveChanges = useCallback(() => {
    setError(null);
    setShowSaveNotification(true);
    setTimeout(() => {
      setShowSaveNotification(false);
    }, 3000);
    if (USE_MOCK_NOTIFICATIONS) return;
    setLoading(true);
    requestWithRetry(() =>
      requestJson(NOTIFICATION_ENDPOINTS.settings, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enable_desktop: desktop,
          enable_email: email,
          enable_silent_hours: silent,
          email_recipients: safeEmailList,
          silent_start_time: startTime,
          silent_end_time: endTime,
        }),
      })
    )
      .catch((err) => {
        console.error(err);
        setError(getErrorMessage(err, "Failed to save settings"));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [desktop, email, endTime, safeEmailList, silent, startTime]);

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

  return (
    <div className="relative bg-[#F8FAFC] min-h-full">
      {/* STICKY HEADER */}
      <div className="sticky top-0 z-20 bg-[#F8FAFC]">
        <div className="flex flex-col gap-4 px-4 py-6 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <div>
            <h1 className="text-xl font-semibold text-[#0F172A]">
              Notification Settings
            </h1>
            <p className="text-sm text-[#64748B]">
              Configure how you receive alerts
            </p>
          </div>

          {/* Bell + badge */}
          <div className="relative" ref={notificationMenuRef}>
            <button
              onClick={handleToggleNotifications}
              className="relative p-1.5 rounded-lg hover:bg-gray-100 transition"
            >
              <Bell size={20} className="text-[#0F172A]" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-[#EF4444] text-[10px] font-medium text-white">
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
        <div className="h-px bg-[#E2E8F0]" />
      </div>

      {loading && (
        <div className="mx-4 mt-4 text-sm text-gray-500 flex items-center gap-2 sm:mx-8">
          <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></span>
          Loading notification settings...
        </div>
      )}
      {error && (
        <div className="mx-4 mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm sm:mx-8">
          {error}
        </div>
      )}

      {/* CONTENT — CENTERED */}
      <div className="px-4 py-6 flex justify-center sm:px-8">
        <div className="w-full max-w-[880px] space-y-6">
          {/* Desktop Notifications */}
          <Card>
            <Row
              icon={<Bell size={18} />}
              title="Desktop Notifications"
              desc="Receive real-time browser notifications when new tenders match your keywords"
            >
              <Toggle checked={desktop} onChange={setDesktop} />
            </Row>
          </Card>

          {/* Email Notifications */}
          <Card>
            <Row
              icon={<Mail size={18} />}
              title="Email Notifications"
              desc="Send alert emails to the specified recipients"
            >
              <Toggle checked={email} onChange={setEmail} />
            </Row>

            <p className="mt-4 mb-2 text-sm font-medium text-[#0F172A]">
              Email Recipients
            </p>

            <div className="flex flex-col gap-2 mb-3 sm:flex-row">
              <input
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAddEmail()}
                placeholder="Add email address..."
                className="flex-1 rounded-md border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:ring-2"
                style={{ "--tw-ring-color": PRIMARY_BLUE }}
              />
              <button
                onClick={handleAddEmail}
                className="rounded-md px-3 text-white hover:opacity-90"
                style={{ backgroundColor: PRIMARY_BLUE }}
              >
                <Plus size={18} />
              </button>
            </div>

            {safeEmailList.map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between rounded-lg bg-[#F9FAFB] px-4 py-2.5 mb-2"
              >
                <span className="text-sm text-[#0F172A] font-normal">
                  {item}
                </span>
                <Trash2
                  size={16}
                  className="cursor-pointer text-[#94A3B8] hover:text-red-500"
                  onClick={() => handleRemoveEmail(index)}
                />
              </div>
            ))}
          </Card>

          {/* Alert Triggers */}
          <Card>
            <h3 className="font-medium text-[#0F172A] mb-1">Alert Triggers</h3>
            <p className="text-sm text-[#64748B] mb-4">
              Choose which events trigger notifications
            </p>

            {[
              "New tender published",
              "Keyword match found",
              "Deadline approaching (7 days)",
              "System errors or fetch failures",
            ].map((label, i) => (
              <label
                key={label}
                className="flex items-center gap-3 py-1 text-sm text-[#0F172A]"
              >
                <input
                  type="checkbox"
                  defaultChecked={i !== 3}
                  className="h-4 w-4"
                  style={{ accentColor: PRIMARY_BLUE }}
                />
                {label}
              </label>
            ))}
          </Card>

          {/* Silent Hours */}
          <Card>
            <Row
              icon={<Clock size={18} />}
              title="Silent Hours"
              desc="Pause notifications during specified hours"
            >
              <Toggle checked={silent} onChange={setSilent} />
            </Row>

            <div className="mt-4 grid grid-cols-2 gap-4">
              <FigmaTimeInput
                label="Start Time"
                value={startTime}
                onChange={setStartTime}
              />
              <FigmaTimeInput
                label="End Time"
                value={endTime}
                onChange={setEndTime}
              />
            </div>
          </Card>

          <button
            onClick={handleSaveChanges}
            className="w-full rounded-md py-3 text-sm font-medium text-white"
            style={{ backgroundColor: PRIMARY_BLUE }}
          >
            ✓ Save Changes
          </button>
        </div>
      </div>

      {/* Save Notification Toast */}
      {showSaveNotification && (
        <div className="fixed bottom-4 right-4 bg-white rounded-lg shadow-lg p-4 flex items-start gap-3 w-[calc(100vw-2rem)] max-w-[320px] z-50 border border-gray-200 sm:bottom-8 sm:right-8">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-100">
            <svg
              className="w-5 h-5 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <div className="flex-1">
            <h4 className="font-semibold text-sm text-[#0F172A]">
              Settings saved
            </h4>
            <p className="text-sm text-[#64748B] mt-0.5">
              Your notification preferences have been updated.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- UI HELPERS ---------- */

const Card = memo(function Card({ children }) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-[0_1px_2px_rgba(16,24,40,0.05),0_1px_3px_rgba(16,24,40,0.1)]">
      {children}
    </div>
  );
});

const Row = memo(function Row({ icon, title, desc, children }) {
  return (
    <div className="flex items-center gap-4">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-500">
        {icon}
      </div>
      <div className="flex-1">
        <h3 className="font-medium text-[#0F172A]">{title}</h3>
        <p className="text-sm text-[#64748B]">{desc}</p>
      </div>
      {children}
    </div>
  );
});

const Toggle = memo(function Toggle({ checked, onChange }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className="relative h-6 w-11 rounded-full transition"
      style={{ backgroundColor: checked ? PRIMARY_BLUE : "#CBD5E1" }}
    >
      <span
        className={`absolute left-1 top-1 h-4 w-4 rounded-full bg-white transition ${
          checked ? "translate-x-5" : ""
        }`}
      />
    </button>
  );
});

const FigmaTimeInput = memo(function FigmaTimeInput({
  label,
  value,
  onChange,
}) {
  const [isEditing, setIsEditing] = useState(false);
  const inputRef = React.useRef(null);

  const handleClockClick = () => {
    setIsEditing(true);
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus();
        inputRef.current.showPicker?.();
      }
    }, 0);
  };

  const handleTimeChange = (e) => {
    onChange(e.target.value);
    setIsEditing(false);
  };

  return (
    <div>
      <p className="mb-1 text-sm text-[#64748B]">{label}</p>
      <div className="relative flex items-center justify-between rounded-md border border-[#E2E8F0] bg-white px-3 py-2">
        {isEditing ? (
          <input
            ref={inputRef}
            type="time"
            value={value}
            onChange={handleTimeChange}
            onBlur={() => setIsEditing(false)}
            className="text-sm text-[#0F172A] outline-none w-full"
          />
        ) : (
          <>
            <span className="text-sm text-[#0F172A]">{value}</span>
            <Clock
              size={16}
              className="text-[#94A3B8] cursor-pointer hover:text-[#64748B]"
              onClick={handleClockClick}
            />
          </>
        )}
      </div>
    </div>
  );
});
