import {
  LayoutDashboard,
  FileText,
  Search,
  Database,
  Bell,
  BarChart3,
} from "lucide-react";

export const sidebarMenu = [
  { name: "Dashboard", icon: LayoutDashboard, path: "/" },
  { name: "Tenders", icon: FileText, path: "/tenders" },
  { name: "Keywords", icon: Search, path: "/keywords" },
  { name: "Sources", icon: Database, path: "/sources" },
  { name: "Notifications", icon: Bell, path: "/notifications" },
  { name: "Analytics", icon: BarChart3, path: "/analytics" },
  { name: "System Logs", icon: FileText, path: "/system-logs" },
];
