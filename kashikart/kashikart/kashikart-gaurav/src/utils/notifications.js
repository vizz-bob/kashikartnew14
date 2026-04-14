// Lightweight helpers for desktop/browser notifications.
// Keeps all Notification API handling in one place to avoid repeated permission prompts.

function isNotificationSupported() {
  return typeof window !== "undefined" && "Notification" in window;
}

function notifyViaElectron(payload) {
  if (typeof window === "undefined") return false;
  if (window.electronAPI?.notifyTender) {
    window.electronAPI.notifyTender(payload);
    return true;
  }
  return false;
}

export async function ensureNotificationPermission() {
  // In Electron, the renderer may not require permission; allow silent success.
  if (typeof window !== "undefined" && window.electronAPI?.notifyTender) {
    return true;
  }

  if (!isNotificationSupported()) return false;

  if (Notification.permission === "granted") return true;
  if (Notification.permission === "denied") return false;

  const result = await Notification.requestPermission();
  return result === "granted";
}

export function showDesktopNotification({
  title = "New update",
  body = "",
  tag = "realtime-update",
  silent = false,
  icon = "/vite.svg",
} = {}) {
  if (isNotificationSupported() && Notification.permission === "granted") {
    try {
      new Notification(title, {
        body,
        tag,
        renotify: true,
        silent,
        icon,
      });
      return true;
    } catch (err) {
      console.error("Failed to show desktop notification", err);
      // fallthrough to electron
    }
  }

  // Fallback to Electron main-process notification if available.
  return notifyViaElectron({ title, body, silent });
}

export function notifyNewTenders(newTenders = []) {
  if (!Array.isArray(newTenders) || newTenders.length === 0) return false;

  const first = newTenders[0];
  const title =
    newTenders.length === 1
      ? "New tender fetched"
      : `${newTenders.length} new tenders fetched`;

  const body =
    newTenders.length === 1
      ? first?.title || first?.reference_id || "New tender available"
      : [
          first?.title || first?.reference_id || "New tender available",
          `${newTenders.length - 1} more incoming`,
        ].join(" • ");

  return showDesktopNotification({
    title,
    body,
    tag: "tenders-realtime",
  });
}
