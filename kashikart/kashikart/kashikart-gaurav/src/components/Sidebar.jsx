import React, { useEffect, useRef, useState, useCallback, useMemo, memo } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  LayoutDashboard,
  FileText,
  Search,
  Globe,
  Bell,
  BarChart3,
  ScrollText,
  Settings,
  LogOut,
  History,
} from "lucide-react";




// export default function Sidebar({
//   headerTitle = "Tender Intel",
//   headerSubtitle = "Intelligent System",
// }) {
const Sidebar = memo(function Sidebar({
  isOpen,
  setIsOpen,
  collapsed = false,
  headerTitle = "Tender Intel",
  headerSubtitle = "Intelligent System",
}) {
  const { isAdmin, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [profilePhoto, setProfilePhoto] = useState(null);
  const profileName = user?.name || localStorage.getItem("profileName") || "User";
  const profileEmail = user?.email || localStorage.getItem("profileEmail") || "";
  const [headerTitleText, setHeaderTitleText] = useState(headerTitle);
  const [headerSubtitleText, setHeaderSubtitleText] = useState(headerSubtitle);
  const [sidebarLogo, setSidebarLogo] = useState(null);
  const logoInputRef = useRef(null);

  const menu = useMemo(() => [
    { name: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
    { name: "Tenders", path: "/tenders", icon: FileText },
    { name: "Keywords", path: "/keywords", icon: Search },
    { name: "Sources", path: "/sources", icon: Globe },
    ...(isAdmin ? [{ name: "Notifications", path: "/notifications", icon: Bell }] : []),
    { name: "Analytics", path: "/analytics", icon: BarChart3 },
    { name: "System Logs", path: "/system-logs", icon: ScrollText },
    ...(isAdmin ? [{ name: "Login History", path: "/login-history", icon: History }] : []),
  ], [isAdmin]);

  useEffect(() => {
    const storedPhoto = localStorage.getItem("profilePhoto");
    if (storedPhoto) setProfilePhoto(storedPhoto);
  }, []);

  const handleProfilePhotoUpdate = useCallback(() => {
    const storedPhoto = localStorage.getItem("profilePhoto");
    setProfilePhoto(storedPhoto || null);
  }, []);

  useEffect(() => {
    window.addEventListener("profilePhotoUpdated", handleProfilePhotoUpdate);
    window.addEventListener("storage", handleProfilePhotoUpdate);
    return () => {
      window.removeEventListener("profilePhotoUpdated", handleProfilePhotoUpdate);
      window.removeEventListener("storage", handleProfilePhotoUpdate);
    };
  }, [handleProfilePhotoUpdate]);

  useEffect(() => {
    const storedTitle = localStorage.getItem("sidebarHeaderTitle") || headerTitle;
    const storedSubtitle = localStorage.getItem("sidebarHeaderSubtitle") || headerSubtitle;
    setHeaderTitleText(storedTitle);
    setHeaderSubtitleText(storedSubtitle);
  }, []);

  useEffect(() => {
    const storedLogo = localStorage.getItem("sidebarHeaderLogo");
    setSidebarLogo(storedLogo || null);
  }, []);

  const handleEditHeader = useCallback(() => {
    const nextTitle = window.prompt("Sidebar title", headerTitleText);
    if (nextTitle !== null) {
      const trimmedTitle = nextTitle.trim();
      const finalTitle = trimmedTitle || headerTitle;
      setHeaderTitleText(finalTitle);
      localStorage.setItem("sidebarHeaderTitle", finalTitle);
    }

    const nextSubtitle = window.prompt("Sidebar subtitle", headerSubtitleText);
    if (nextSubtitle !== null) {
      const trimmedSubtitle = nextSubtitle.trim();
      const finalSubtitle = trimmedSubtitle || headerSubtitle;
      setHeaderSubtitleText(finalSubtitle);
      localStorage.setItem("sidebarHeaderSubtitle", finalSubtitle);
    }
  }, [headerTitleText, headerSubtitleText]);

  const handleProfileToggle = useCallback(() => {
    if (location.pathname === "/profile") {
      navigate("/dashboard");
      return;
    }
    navigate("/profile");
  }, [location.pathname, navigate]);

  const triggerLogoPicker = useCallback(() => {
    logoInputRef.current?.click();
  }, []);

  const handleLogoChange = useCallback((event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) return;

    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result;
      if (typeof result !== "string") return;
      setSidebarLogo(result);
      localStorage.setItem("sidebarHeaderLogo", result);
    };
    reader.readAsDataURL(file);
  }, []);

  return (
    <>
      {isOpen && (
        <div
          onClick={() => setIsOpen(false)}
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
        />
      )}
      <aside
        className={`
    fixed inset-y-0 left-0 z-50
    h-screen w-64 bg-[#0b1222] text-white flex flex-col
    transition-transform duration-300
    ${isOpen ? "translate-x-0" : "-translate-x-full"}
    md:translate-x-0
    ${collapsed ? "md:w-20" : "md:w-64"}
  `}
      >
        <div
          className={`border-b border-white/10 ${
            collapsed ? "px-4 py-5" : "px-6 py-5"
          }`}
        >
          <div
            className={`flex items-center ${
              collapsed ? "justify-center" : "gap-3"
            }`}
          >
            <button
              type="button"
              onClick={triggerLogoPicker}
              className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#4f8cff] to-[#2563eb] flex items-center justify-center shadow-md overflow-hidden"
              aria-label="Change sidebar logo"
              title="Change logo"
            >
              {sidebarLogo ? (
                <img
                  src={sidebarLogo}
                  alt="Sidebar logo"
                  className="w-full h-full object-cover"
                />
              ) : (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M13 2L3 14H11L9 22L21 10H13V2Z"
                    fill="none"
                    stroke="#ffffff"
                    strokeWidth="2"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                  />
                </svg>
              )}
            </button>
            <input
              ref={logoInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleLogoChange}
            />

            {!collapsed && (
              <button
                type="button"
                onClick={handleEditHeader}
                className="text-left hover:text-red-400 transition"
                aria-label="Edit sidebar header"
              >
                <p className="text-[15px] font-semibold tracking-wide">
                  {headerTitleText}
                </p>
                <p className="text-[12px] text-gray-400">
                  {headerSubtitleText}
                </p>
              </button>
            )}
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {menu.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.name}
                to={item.path}
                onClick={() => setIsOpen(false)}
                className={({ isActive }) =>
                  `
                group flex items-center rounded-xl transition-all
                ${
                  collapsed ? "justify-center px-2 py-2.5" : "gap-3 px-4 py-2.5"
                }
                ${
                  isActive
                    ? "bg-[#1e2a44] shadow-[inset_0_0_0_1px_rgba(79,140,255,0.25)]"
                    : "text-gray-300 hover:bg-white/5"
                }
                `
                }
                title={collapsed ? item.name : undefined}
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      size={18}
                      strokeWidth={1.9}
                      className={
                        isActive
                          ? "text-[#4f8cff] drop-shadow-sm"
                          : "text-gray-400 group-hover:text-[#4f8cff]"
                      }
                    />
                    {!collapsed && (
                      <span
                        className={`text-[14px] font-medium ${
                          isActive ? "text-white" : ""
                        }`}
                      >
                        {item.name}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        <div className="p-4 border-t border-white/10">
          <button
            onClick={handleProfileToggle}
            className={`flex items-center w-full hover:bg-white/5 p-2 rounded-xl transition ${
              collapsed ? "justify-center" : "gap-3"
            }`}
            title={collapsed ? `${profileName}` : undefined}
          >
            {profilePhoto ? (
              <img
                src={profilePhoto}
                alt="Profile"
                className="w-9 h-9 rounded-full object-cover shadow"
              />
            ) : (
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#4f8cff] to-[#2563eb] flex items-center justify-center text-white font-semibold shadow">
                {profileName.charAt(0).toUpperCase()}
              </div>
            )}
            {!collapsed && (
              <div className="text-left">
                <p className="text-sm font-medium">{profileName}</p>
                <p className="text-xs text-gray-400">{profileEmail}</p>
              </div>
            )}
          </button>

          <div
            className={`flex items-center mt-4 px-2 text-[12px] text-gray-400 ${
              collapsed ? "justify-center" : "justify-center"
            }`}
          >
            <button
              onClick={() => {
                localStorage.removeItem("kashikart_token");
                localStorage.removeItem("access_token");
                localStorage.removeItem("profileName");
                localStorage.removeItem("profileEmail");
                localStorage.removeItem("profilePhoto");
                navigate("/login");
              }}
              className={`flex items-center hover:text-red-400 transition ${
                collapsed ? "gap-0" : "gap-1"
              }`}
              title={collapsed ? "Logout" : undefined}
            >
              <LogOut size={14} />
              {!collapsed && "Logout"}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
});

export default Sidebar;
