import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
  memo,
} from "react";
import { Bell, BellOff, Plus, Pencil, Trash2, X } from "lucide-react";
import { EmptyState } from "../components/States";
import { getErrorMessage, requestJson, requestWithRetry } from "../utils/api";

const USE_MOCK_KEYWORDS = false;
const USE_MOCK_NOTIFICATIONS = false;
const KEYWORD_ENDPOINTS = {
  list: "/api/keywords/",
};
const NOTIFICATION_ENDPOINTS = {
  list: "/api/notifications/", // TODO BACKEND: yahi endpoint use hoga
};

const INITIAL_NOTIFICATIONS = [];

const initialCategories = [
  "Information Technology",
  "Construction",
  "Healthcare",
  "Environmental",
  "Services",
  "Other",
];

const getPriorityClasses = (priority) => {
  const p = Number(priority) || 0;
  if (p >= 9) return "bg-red-100 text-red-600";
  if (p >= 6) return "bg-yellow-100 text-yellow-700";
  return "bg-green-100 text-green-600";
};

const KeywordRow = memo(function KeywordRow({
  item,
  index,
  onToggleAlert,
  onEdit,
  onDelete,
}) {
  return (
    <div className="grid grid-cols-6 px-6 py-4 items-center border-t border-gray-100 text-sm">
      <div className="font-medium text-gray-900">{item.keyword}</div>
      <div>
        <span className="px-3 py-1 rounded-full bg-gray-100 text-gray-700 text-xs">
          {item.category}
        </span>
      </div>
      <div>
        <span
          className={`px-3 py-1 rounded-full text-xs ${getPriorityClasses(
            item.priority
          )}`}
        >
            {`p${item.priority}`}
        </span>
      </div>
      <div>
        {item.enable_alerts !== false ? (
          <div
            onClick={() => onToggleAlert(index)}
            className="w-9 h-9 rounded-lg bg-green-100 flex items-center justify-center cursor-pointer hover:bg-green-200 transition-colors"
          >
            <Bell className="w-4 h-4 text-green-600" />
          </div>
        ) : (
          <div
            onClick={() => onToggleAlert(index)}
            className="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center cursor-pointer hover:bg-gray-200 transition-colors"
          >
            <BellOff className="w-4 h-4 text-gray-400" />
          </div>
        )}
      </div>
      <div className="text-gray-600">{item.created_at ? new Date(item.created_at).toLocaleDateString() : 'N/A'}</div>
      <div className="flex justify-end gap-4">
        <Pencil
          className="w-4 h-4 text-gray-500 cursor-pointer hover:text-blue-500"
          onClick={() => onEdit(item, index)}
        />
        <Trash2
          className="w-4 h-4 text-red-500 cursor-pointer hover:text-red-600"
          onClick={() => onDelete(index)}
        />
      </div>
    </div>
  );
});

export default function Keywords() {
  const [keywords, setKeywords] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [alertsEnabled, setAlertsEnabled] = useState(true);
  const [editingKeyword, setEditingKeyword] = useState(null);
  const [editForm, setEditForm] = useState({
    keyword: "",
    category: "",
    priority: 5,
    alerts: true,
  });
  const [searchTerm, setSearchTerm] = useState("");
  const [newKeyword, setNewKeyword] = useState({
    keyword: "",
    category: "Information Technology",
    priority: 5,
  });
  const [categories, setCategories] = useState(initialCategories);
  const [showCategoryInput, setShowCategoryInput] = useState(false);
  const [newCategoryInput, setNewCategoryInput] = useState("");
  const [showEditCategoryInput, setShowEditCategoryInput] = useState(false);
  const [editCategoryInput, setEditCategoryInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS);
  const notificationMenuRef = useRef(null);

  const fetchKeywords = useCallback(async () => {
    if (USE_MOCK_KEYWORDS) return;
    try {
      setLoading(true);
      setError(null);

      const data = await requestWithRetry(() =>
        requestJson(KEYWORD_ENDPOINTS.list)
      );

      setKeywords(data?.items || []);
      
      // Optionally fetch categories if API provides them separately or extract them
      // In this setup, categories are usually fixed or can be fetched from /api/keywords/categories
    } catch (err) {
      console.error(err);
      setError(getErrorMessage(err, "Failed to load keywords"));
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchCategories = useCallback(async () => {
    if (USE_MOCK_KEYWORDS) return;
    try {
      const data = await requestJson("/api/keywords/categories");
      if (data?.all) {
        setCategories(data.all);
      }
    } catch (err) {
      console.error("Failed to fetch categories:", err);
    }
  }, []);

  useEffect(() => {
    fetchKeywords();
    fetchCategories();
  }, [fetchKeywords, fetchCategories]);

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

  const handleEdit = useCallback((item, index) => {
    setEditingKeyword(index);
    setEditForm({
      keyword: item.keyword,
      category: item.category,
      priority: Number(item.priority) || 5,
      alerts: item.enable_alerts,
    });
    setShowEditCategoryInput(false);
    setEditCategoryInput("");
    setShowEditModal(true);
  }, []);

  const handleAdd = useCallback(async () => {
    if (newKeyword.keyword.trim() === "") return;
    if (newKeyword.category.trim() === "") return;

    try {
      setLoading(true);
      setError(null);

      const pr = Number(newKeyword.priority) || 5;
      const payload = {
        keyword: newKeyword.keyword.trim(),
        category: newKeyword.category,
        priority: `p${pr}`,
        enable_alerts: alertsEnabled
      };

      await requestJson("/api/keywords/", {
        method: "POST",
        body: JSON.stringify(payload)
      });

      setNewKeyword({
        keyword: "",
        category: categories[0] || "Information Technology",
        priority: 5,
      });
      setAlertsEnabled(true);
      setShowCategoryInput(false);
      setNewCategoryInput("");
      setShowModal(false);
      fetchKeywords();
      fetchCategories();
    } catch (err) {
      console.error(err);
      setError(getErrorMessage(err, "Failed to add keyword"));
    } finally {
      setLoading(false);
    }
  }, [alertsEnabled, categories, fetchCategories, fetchKeywords, newKeyword]);

  const handleUpdate = useCallback(async () => {
    if (!editForm.keyword.trim()) return;
    const item = keywords[editingKeyword];
    if (!item) return;

    try {
      setLoading(true);
      setError(null);

      const pr = Number(editForm.priority) || 5;
      const payload = {
        keyword: editForm.keyword.trim(),
        category: editForm.category,
        priority: `p${pr}`,
        enable_alerts: editForm.alerts
      };

      await requestJson(`/api/keywords/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload)
      });

      setShowEditModal(false);
      setEditingKeyword(null);
      fetchKeywords();
      fetchCategories();
    } catch (err) {
      console.error(err);
      setError(getErrorMessage(err, "Failed to update keyword"));
    } finally {
      setLoading(false);
    }
  }, [editForm, editingKeyword, fetchCategories, fetchKeywords, keywords]);

  const handleDelete = useCallback(
    async (index) => {
      const item = keywords[index];
      if (!item) return;

      if (!window.confirm(`Are you sure you want to delete "${item.keyword}"?`)) return;

      try {
        setLoading(true);
        setError(null);

        await requestJson(`/api/keywords/${item.id}`, {
          method: "DELETE"
        });

        fetchKeywords();
      } catch (err) {
        console.error(err);
        setError(getErrorMessage(err, "Failed to delete keyword"));
      } finally {
        setLoading(false);
      }
    },
    [fetchKeywords, keywords]
  );

  const toggleAlert = useCallback(
    async (index) => {
      const item = keywords[index];
      if (!item) return;

      const nextAlertValue = !item.enable_alerts;

      try {
        // Optimistic update
        setKeywords(prev => prev.map((k, i) => i === index ? { ...k, enable_alerts: nextAlertValue } : k));

        await requestJson(`/api/keywords/${item.id}`, {
          method: "PATCH",
          body: JSON.stringify({ enable_alerts: nextAlertValue })
        });
      } catch (err) {
        console.error(err);
        // Revert on failure
        setKeywords(prev => prev.map((k, i) => i === index ? { ...k, enable_alerts: !nextAlertValue } : k));
      }
    },
    [keywords]
  );

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

  const addCategory = useCallback(
    (value) => {
      const trimmed = value.trim();
      if (!trimmed) return;
      if (!categories.includes(trimmed)) {
        setCategories([...categories, trimmed]);
      }
      return trimmed;
    },
    [categories]
  );

  const removeCategory = useCallback(
    (value) => {
      const trimmed = value.trim();
      if (!trimmed) return;
      if (!categories.includes(trimmed)) return;
      if (categories.length <= 1) return;

      const remaining = categories.filter((category) => category !== trimmed);
      const fallback = remaining.includes("Other") ? "Other" : remaining[0];

      setCategories(remaining);
      setKeywords(
        keywords.map((item) =>
          item.category === trimmed ? { ...item, category: fallback } : item
        )
      );

      if (newKeyword.category === trimmed) {
        setNewKeyword({ ...newKeyword, category: fallback });
      }

      if (editForm.category === trimmed) {
        setEditForm({ ...editForm, category: fallback });
      }

      setShowCategoryInput(false);
      setNewCategoryInput("");
      setShowEditCategoryInput(false);
      setEditCategoryInput("");
    },
    [categories, editForm, keywords, newKeyword]
  );

  // Filter keywords based on search term
  const safeKeywords = useMemo(
    () => (Array.isArray(keywords) ? keywords : []),
    [keywords]
  );
  const safeCategories = useMemo(
    () => (Array.isArray(categories) ? categories : []),
    [categories]
  );
  const filteredKeywords = useMemo(
    () =>
      safeKeywords.filter(
        (item) =>
          (item.keyword || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
          (item.category || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
          String(item.priority ? `p${item.priority}` : "").toLowerCase().includes(searchTerm.toLowerCase())
      ),
    [safeKeywords, searchTerm]
  );

  return (
    <div className="flex flex-col min-h-full bg-gray-50">
      <div className="sticky top-0 z-40 bg-gray-50 border-b border-gray-200">
        <div className="px-4 py-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              Keyword Management
            </h1>
            <p className="text-sm text-gray-500">
              Configure keywords for intelligent tender matching
            </p>
          </div>
          <div className="relative" ref={notificationMenuRef}>
            <button
              onClick={handleToggleNotifications}
              className="relative p-1.5 rounded-lg hover:bg-gray-100 transition"
            >
              <Bell className="w-6 h-6 text-gray-600" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 text-xs bg-red-500 text-white rounded-full px-1.5">
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
        <div className="px-4 pb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <input
            placeholder="Search keywords..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:w-72"
          />
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium"
          >
            <Plus size={16} />
            Add Keyword
          </button>
        </div>
      </div>

      {loading && (
        <div className="mx-4 mt-4 text-sm text-gray-500 flex items-center gap-2 sm:mx-8">
          <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full"></span>
          Loading keywords...
        </div>
      )}
      {error && (
        <div className="mx-4 mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm sm:mx-8">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <div className="min-w-[720px]">
              <div className="grid grid-cols-6 px-6 py-3 text-sm text-gray-500 font-medium bg-gray-50">
                <div>Keyword</div>
                <div>Category</div>
                <div>Priority</div>
                <div>Alerts</div>
                <div>Created</div>
                <div className="text-right">Actions</div>
              </div>

              {filteredKeywords.length > 0 ? (
                filteredKeywords.map((item) => {
                  const originalIndex = safeKeywords.indexOf(item);
                  return (
                    <KeywordRow
                      key={originalIndex}
                      item={item}
                      index={originalIndex}
                      onToggleAlert={toggleAlert}
                      onEdit={handleEdit}
                      onDelete={handleDelete}
                    />
                  );
                })
              ) : (
                <div className="px-6 py-8">
                  <EmptyState
                    title="No keywords found"
                    message="Add a keyword or change your search."
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {showModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm"
          style={{ backgroundColor: "rgba(0, 0, 0, 0.2)" }}
        >
          <div className="bg-white w-full max-w-lg rounded-xl p-6 shadow-xl">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-lg font-semibold">Add New Keyword</h2>
                <p className="text-sm text-gray-500">
                  Add a new keyword to monitor for matching tenders.
                </p>
              </div>
              <X
                className="cursor-pointer text-gray-400"
                onClick={() => {
                  setShowModal(false);
                  setAlertsEnabled(true);
                  setShowCategoryInput(false);
                  setNewCategoryInput("");
                }}
              />
            </div>
            <div className="mt-5 space-y-4">
              <div>
                <label className="text-sm font-medium">Keyword</label>
                <input
                  value={newKeyword.keyword}
                  onChange={(e) =>
                    setNewKeyword({ ...newKeyword, keyword: e.target.value })
                  }
                  placeholder="Enter keyword..."
                  className="w-full mt-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Category</label>
                  <button
                    type="button"
                    onClick={() => removeCategory(newKeyword.category)}
                    disabled={!newKeyword.category || categories.length <= 1}
                    className={`inline-flex items-center gap-1 text-xs ${
                      !newKeyword.category || categories.length <= 1
                        ? "text-gray-300 cursor-not-allowed"
                        : "text-red-500 hover:text-red-600"
                    }`}
                    title="Remove selected category"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Remove
                  </button>
                </div>
                <select
                  value={newKeyword.category}
                  onChange={(e) => {
                    const selected = e.target.value;
                    if (selected === "__add_new__") {
                      setShowCategoryInput(true);
                      setNewKeyword({ ...newKeyword, category: "" });
                      return;
                    }
                    setShowCategoryInput(false);
                    setNewCategoryInput("");
                    setNewKeyword({ ...newKeyword, category: selected });
                  }}
                  className="w-full mt-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {safeCategories.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                  <option value="__add_new__">+ Add new category</option>
                </select>
                {showCategoryInput && (
                  <div className="mt-2 flex gap-2">
                    <input
                      value={newCategoryInput}
                      onChange={(e) => setNewCategoryInput(e.target.value)}
                      placeholder="New category name"
                      className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        const added = addCategory(newCategoryInput);
                        if (added) {
                          setNewKeyword({ ...newKeyword, category: added });
                          setShowCategoryInput(false);
                          setNewCategoryInput("");
                        }
                      }}
                      className="px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm"
                    >
                      Add
                    </button>
                  </div>
                )}
              </div>
              <div>
                <label className="text-sm font-medium">Priority</label>
                <select
                  value={newKeyword.priority}
                  onChange={(e) =>
                    setNewKeyword({ ...newKeyword, priority: Number(e.target.value) })
                  }
                  className="w-full mt-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {[...Array(11)].map((_, i) => {
                    const val = 11 - i;
                    return (
                      <option key={val} value={val}>
                        Priority {val}
                      </option>
                    );
                  })}
                </select>
              </div>
              <div className="flex items-center justify-between pt-2">
                <span className="text-base font-medium text-gray-900">
                  Enable Alerts
                </span>
                <button
                  type="button"
                  onClick={() => setAlertsEnabled(!alertsEnabled)}
                  className={`w-11 h-6 rounded-full relative transition ${
                    alertsEnabled ? "bg-blue-500" : "bg-gray-300"
                  }`}
                >
                  <div
                    className={`w-5 h-5 bg-white rounded-full absolute top-0.5 transition ${
                      alertsEnabled ? "right-0.5" : "left-0.5"
                    }`}
                  />
                </button>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => {
                  setShowModal(false);
                  setAlertsEnabled(true);
                  setNewKeyword({
                    keyword: "",
                    category: "Information Technology",
        priority: 5,
                  });
                  setShowCategoryInput(false);
                  setNewCategoryInput("");
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm"
              >
                Add Keyword
              </button>
            </div>
          </div>
        </div>
      )}

      {showEditModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm"
          style={{ backgroundColor: "rgba(0, 0, 0, 0.2)" }}
        >
          <div className="bg-white w-full max-w-lg rounded-xl p-6 shadow-xl">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-lg font-semibold">Edit Keyword</h2>
                <p className="text-sm text-gray-500">
                  Update the keyword configuration below.
                </p>
              </div>
              <X
                className="cursor-pointer text-gray-400"
                onClick={() => {
                  setShowEditModal(false);
                  setEditingKeyword(null);
                  setShowEditCategoryInput(false);
                  setEditCategoryInput("");
                }}
              />
            </div>
            <div className="mt-5 space-y-4">
              <div>
                <label className="text-sm font-medium">Keyword</label>
                <input
                  value={editForm.keyword}
                  onChange={(e) =>
                    setEditForm({ ...editForm, keyword: e.target.value })
                  }
                  placeholder="Enter keyword..."
                  className="w-full mt-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
              <div>
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Category</label>
                  <button
                    type="button"
                    onClick={() => removeCategory(editForm.category)}
                    disabled={!editForm.category || categories.length <= 1}
                    className={`inline-flex items-center gap-1 text-xs ${
                      !editForm.category || categories.length <= 1
                        ? "text-gray-300 cursor-not-allowed"
                        : "text-red-500 hover:text-red-600"
                    }`}
                    title="Remove selected category"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Remove
                  </button>
                </div>
                <select
                  value={editForm.category}
                  onChange={(e) => {
                    const selected = e.target.value;
                    if (selected === "__add_new__") {
                      setShowEditCategoryInput(true);
                      setEditForm({ ...editForm, category: "" });
                      return;
                    }
                    setShowEditCategoryInput(false);
                    setEditCategoryInput("");
                    setEditForm({ ...editForm, category: selected });
                  }}
                  className="w-full mt-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {safeCategories.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                  <option value="__add_new__">+ Add new category</option>
                </select>
                {showEditCategoryInput && (
                  <div className="mt-2 flex gap-2">
                    <input
                      value={editCategoryInput}
                      onChange={(e) => setEditCategoryInput(e.target.value)}
                      placeholder="New category name"
                      className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        const added = addCategory(editCategoryInput);
                        if (added) {
                          setEditForm({ ...editForm, category: added });
                          setShowEditCategoryInput(false);
                          setEditCategoryInput("");
                        }
                      }}
                      className="px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm"
                    >
                      Add
                    </button>
                  </div>
                )}
              </div>
              <div>
                <label className="text-sm font-medium">Priority</label>
                <select
                  value={editForm.priority}
                  onChange={(e) =>
                    setEditForm({ ...editForm, priority: Number(e.target.value) })
                  }
                  className="w-full mt-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {[...Array(11)].map((_, i) => {
                    const val = 11 - i;
                    return (
                      <option key={val} value={val}>
                        Priority {val}
                      </option>
                    );
                  })}
                </select>
              </div>
              <div className="flex items-center justify-between pt-2">
                <span className="text-base font-medium text-gray-900">
                  Enable Alerts
                </span>
                <button
                  type="button"
                  onClick={() =>
                    setEditForm({ ...editForm, alerts: !editForm.alerts })
                  }
                  className={`w-11 h-6 rounded-full relative transition ${
                    editForm.alerts ? "bg-blue-500" : "bg-gray-300"
                  }`}
                >
                  <div
                    className={`w-5 h-5 bg-white rounded-full absolute top-0.5 transition ${
                      editForm.alerts ? "right-0.5" : "left-0.5"
                    }`}
                  />
                </button>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => {
                  setShowEditModal(false);
                  setEditingKeyword(null);
                  setShowEditCategoryInput(false);
                  setEditCategoryInput("");
                }}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdate}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm"
              >
                Update Keyword
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// import React, { useState } from "react";
// import { Bell, BellOff, Plus, Pencil, Trash2, X } from "lucide-react";

// const keywordsData = [
//   { keyword: "IT Infrastructure", category: "Information Technology", priority: "High", alerts: true, created: "11/1/2025" },
//   { keyword: "Cybersecurity", category: "Information Technology", priority: "High", alerts: true, created: "11/1/2025" },
//   { keyword: "Construction", category: "Construction", priority: "Medium", alerts: true, created: "11/5/2025" },
//   { keyword: "Healthcare", category: "Healthcare", priority: "High", alerts: true, created: "11/10/2025" },
//   { keyword: "Environmental", category: "Environmental", priority: "Low", alerts: false, created: "11/15/2025" },
//   { keyword: "Software Development", category: "Information Technology", priority: "High", alerts: true, created: "11/20/2025" },
//   { keyword: "Facility Management", category: "Services", priority: "Medium", alerts: true, created: "12/1/2025" },
//   { keyword: "Medical Equipment", category: "Healthcare", priority: "Medium", alerts: true, created: "12/5/2025" }
// ];

// export default function Keywords() {
//   const [keywords, setKeywords] = useState(keywordsData);
//   const [showModal, setShowModal] = useState(false);
//   const [showEditModal, setShowEditModal] = useState(false);
//   const [alertsEnabled, setAlertsEnabled] = useState(true);
//   const [editingKeyword, setEditingKeyword] = useState(null);
//   const [editForm, setEditForm] = useState({ keyword: "", category: "", priority: "", alerts: true });

//   const handleEdit = (item, index) => {
//     setEditingKeyword(index);
//     setEditForm({ keyword: item.keyword, category: item.category, priority: item.priority, alerts: item.alerts });
//     setShowEditModal(true);
//   };

//   const handleUpdate = () => {
//     const updatedKeywords = [...keywords];
//     updatedKeywords[editingKeyword] = { ...updatedKeywords[editingKeyword], ...editForm };
//     setKeywords(updatedKeywords);
//     setShowEditModal(false);
//     setEditingKeyword(null);
//   };

//   const handleDelete = (index) => {
//     setKeywords(keywords.filter((_, i) => i !== index));
//   };

//   return (
//     <div className="flex flex-col h-screen bg-gray-50">
//       <div className="sticky top-0 z-40 bg-gray-50 border-b border-gray-200">
//         <div className="px-8 py-5 flex items-center justify-between">
//           <div>
//             <h1 className="text-xl font-semibold text-gray-900">Keyword Management</h1>
//             <p className="text-sm text-gray-500">Configure keywords for intelligent tender matching</p>
//           </div>
//           <div className="relative">
//             <Bell className="w-6 h-6 text-gray-600" />
//             <span className="absolute -top-1 -right-1 text-xs bg-red-500 text-white rounded-full px-1.5">3</span>
//           </div>
//         </div>
//         <div className="px-8 pb-4 flex items-center justify-between">
//           <input placeholder="Search keywords..." className="w-72 px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
//           <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium">
//             <Plus size={16} />
//             Add Keyword
//           </button>
//         </div>
//       </div>

//       <div className="flex-1 overflow-y-auto px-8 py-6">
//         <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
//           <div className="grid grid-cols-6 px-6 py-3 text-sm text-gray-500 font-medium bg-gray-50">
//             <div>Keyword</div>
//             <div>Category</div>
//             <div>Priority</div>
//             <div>Alerts</div>
//             <div>Created</div>
//             <div className="text-right">Actions</div>
//           </div>

//           {keywords.map((item, i) => (
//             <div key={i} className="grid grid-cols-6 px-6 py-4 items-center border-t border-gray-100 text-sm">
//               <div className="font-medium text-gray-900">{item.keyword}</div>
//               <div>
//                 <span className="px-3 py-1 rounded-full bg-gray-100 text-gray-700 text-xs">{item.category}</span>
//               </div>
//               <div>
//                 <span className={`px-3 py-1 rounded-full text-xs ${item.priority === "High" ? "bg-red-100 text-red-600" : item.priority === "Medium" ? "bg-yellow-100 text-yellow-700" : "bg-green-100 text-green-600"}`}>{item.priority}</span>
//               </div>
//               <div>
//                 {item.alerts ? (
//                   <div className="w-9 h-9 rounded-lg bg-green-100 flex items-center justify-center">
//                     <Bell className="w-4 h-4 text-green-600" />
//                   </div>
//                 ) : (
//                   <div className="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center">
//                     <BellOff className="w-4 h-4 text-gray-400" />
//                   </div>
//                 )}
//               </div>
//               <div className="text-gray-600">{item.created}</div>
//               <div className="flex justify-end gap-4">
//                 <Pencil className="w-4 h-4 text-gray-500 cursor-pointer hover:text-blue-500" onClick={() => handleEdit(item, i)} />
//                 <Trash2 className="w-4 h-4 text-red-500 cursor-pointer hover:text-red-600" onClick={() => handleDelete(i)} />
//               </div>
//             </div>
//           ))}
//         </div>
//       </div>

//       {showModal && (
//         <div className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm" style={{backgroundColor: 'rgba(0, 0, 0, 0.2)'}}>
//           <div className="bg-white w-full max-w-lg rounded-xl p-6 shadow-xl">
//             <div className="flex justify-between items-start">
//               <div>
//                 <h2 className="text-lg font-semibold">Add New Keyword</h2>
//                 <p className="text-sm text-gray-500">Add a new keyword to monitor for matching tenders.</p>
//               </div>
//               <X className="cursor-pointer text-gray-400" onClick={() => { setShowModal(false); setAlertsEnabled(true); }} />
//             </div>
//             <div className="mt-5 space-y-4">
//               <div>
//                 <label className="text-sm font-medium">Keyword</label>
//                 <input placeholder="Enter keyword..." className="w-full mt-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
//               </div>
//               <div>
//                 <label className="text-sm font-medium">Category</label>
//                 <select className="w-full mt-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
//                   <option>Information Technology</option>
//                   <option>Construction</option>
//                   <option>Healthcare</option>
//                   <option>Environmental</option>
//                   <option>Services</option>
//                   <option>Other</option>
//                 </select>
//               </div>
//               <div>
//                 <label className="text-sm font-medium">Priority</label>
//                 <select className="w-full mt-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
//                   <option>High</option>
//                   <option>Medium</option>
//                   <option>Low</option>
//                 </select>
//               </div>
//               <div className="flex items-center justify-between pt-2">
//                 <span className="text-base font-medium text-gray-900">Enable Alerts</span>
//                 <button type="button" onClick={() => setAlertsEnabled(!alertsEnabled)} className={`w-11 h-6 rounded-full relative transition ${alertsEnabled ? "bg-blue-500" : "bg-gray-300"}`}>
//                   <div className={`w-5 h-5 bg-white rounded-full absolute top-0.5 transition ${alertsEnabled ? "right-0.5" : "left-0.5"}`} />
//                 </button>
//               </div>
//             </div>
//             <div className="flex justify-end gap-3 mt-6">
//               <button onClick={() => { setShowModal(false); setAlertsEnabled(true); }} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
//               <button className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm">Add Keyword</button>
//             </div>
//           </div>
//         </div>
//       )}

//       {showEditModal && (
//         <div className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm" style={{backgroundColor: 'rgba(0, 0, 0, 0.2)'}}>
//           <div className="bg-white w-full max-w-lg rounded-xl p-6 shadow-xl">
//             <div className="flex justify-between items-start">
//               <div>
//                 <h2 className="text-lg font-semibold">Edit Keyword</h2>
//                 <p className="text-sm text-gray-500">Update the keyword configuration below.</p>
//               </div>
//               <X className="cursor-pointer text-gray-400" onClick={() => { setShowEditModal(false); setEditingKeyword(null); }} />
//             </div>
//             <div className="mt-5 space-y-4">
//               <div>
//                 <label className="text-sm font-medium">Keyword</label>
//                 <input value={editForm.keyword} onChange={(e) => setEditForm({...editForm, keyword: e.target.value})} placeholder="Enter keyword..." className="w-full mt-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" />
//               </div>
//               <div>
//                 <label className="text-sm font-medium">Category</label>
//                 <select value={editForm.category} onChange={(e) => setEditForm({...editForm, category: e.target.value})} className="w-full mt-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
//                   <option>Information Technology</option>
//                   <option>Construction</option>
//                   <option>Healthcare</option>
//                   <option>Environmental</option>
//                   <option>Services</option>
//                   <option>Other</option>
//                 </select>
//               </div>
//               <div>
//                 <label className="text-sm font-medium">Priority</label>
//                 <select value={editForm.priority} onChange={(e) => setEditForm({...editForm, priority: e.target.value})} className="w-full mt-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
//                   <option>High</option>
//                   <option>Medium</option>
//                   <option>Low</option>
//                 </select>
//               </div>
//               <div className="flex items-center justify-between pt-2">
//                 <span className="text-base font-medium text-gray-900">Enable Alerts</span>
//                 <button type="button" onClick={() => setEditForm({...editForm, alerts: !editForm.alerts})} className={`w-11 h-6 rounded-full relative transition ${editForm.alerts ? "bg-blue-500" : "bg-gray-300"}`}>
//                   <div className={`w-5 h-5 bg-white rounded-full absolute top-0.5 transition ${editForm.alerts ? "right-0.5" : "left-0.5"}`} />
//                 </button>
//               </div>
//             </div>
//             <div className="flex justify-end gap-3 mt-6">
//               <button onClick={() => { setShowEditModal(false); setEditingKeyword(null); }} className="px-4 py-2 border border-gray-300 rounded-lg text-sm">Cancel</button>
//               <button onClick={handleUpdate} className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm">Update Keyword</button>
//             </div>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// }
