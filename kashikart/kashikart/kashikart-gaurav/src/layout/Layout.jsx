import { useState, useMemo, useCallback, memo } from "react";
import { useLocation } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Footer from "../components/Footer";
import { Menu } from "lucide-react";

const Layout = memo(function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  const pageTitleMap = {
    "/dashboard": "Dashboard",
    "/analytics": "Analytics",
    "/system-logs": "System Logs",
    "/sources": "Sources",
    "/notifications": "Notifications",
    "/tenders": "Tenders",
    "/keywords": "Keywords",
    "/login-history": "Login History",
  };

  const pageTitle = useMemo(
    () => pageTitleMap[location.pathname] || "Dashboard",
    [location.pathname]
  );

  const handleOpenSidebar = useCallback(() => {
    setSidebarOpen(true);
  }, []);

  const handleToggleCollapse = useCallback(() => {
    setCollapsed((p) => !p);
  }, []);

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/*  SIDEBAR */}
      <Sidebar
        isOpen={sidebarOpen}
        setIsOpen={setSidebarOpen}
        collapsed={collapsed}
      />

      {/* MAIN AREA */}
      <div
        className={`flex min-h-screen flex-1 flex-col transition-all duration-300
        ${collapsed ? "md:ml-20" : "md:ml-64"}
      `}
      >
        {/* HEADER */}
        <header className="sticky top-0 z-40 bg-white border-b px-4 py-3 flex items-center gap-3">
          {/*  MOBILE HAMBURGER */}
          <button className="md:hidden" onClick={handleOpenSidebar}>
            <Menu />
          </button>

          {/* DESKTOP COLLAPSE */}
          <button className="hidden md:block" onClick={handleToggleCollapse}>
            <Menu />
          </button>

          <h1 className="text-lg font-semibold text-gray-800">{pageTitle}</h1>
        </header>

        {/* <main */}
        <main className="flex-1 min-w-0">{children}</main>
        <Footer />
      </div>
    </div>
  );
});

export default Layout;

// import { useState } from "react";
// import { useLocation } from "react-router-dom";
// import Sidebar from "../components/Sidebar";
// import { Menu } from "lucide-react";

// export default function DashboardLayout({ children }) {
//   const [sidebarOpen, setSidebarOpen] = useState(false);
//   const [collapsed, setCollapsed] = useState(false);

//   const location = useLocation();

//   //  ROUTE → TITLE MAP
//   const pageTitleMap = {
//     "/": "Dashboard",
//     "/analytics": "Analytics",
//     "/system-logs": "System Logs",
//     "/sources": "Sources",
//     "/notifications": "Notifications",
//   };

//   const pageTitle = pageTitleMap[location.pathname] || "Dashboard";

//   return (
//     <div className="flex min-h-screen bg-gray-50">
//       {/* SIDEBAR */}
//       <Sidebar
//         isOpen={sidebarOpen}
//         setIsOpen={setSidebarOpen}
//         collapsed={collapsed}
//       />

//       {/* MAIN AREA */}
//       <div
//         className={`flex-1 transition-all duration-300
//         ${collapsed ? "md:ml-20" : "md:ml-64"}
//       `}
//       >
//         {/*  FIXED HEADER */}
//         <header className="sticky top-0 z-40 bg-white border-b px-4 py-3 flex items-center justify-between">
//           <div className="flex items-center gap-3">
//             {/* MOBILE MENU */}
//             <button className="md:hidden" onClick={() => setSidebarOpen(true)}>
//               <Menu />
//             </button>

//             {/* DESKTOP COLLAPSE */}
//             <button
//               className="hidden md:block"
//               onClick={() => setCollapsed((p) => !p)}
//             >
//               <Menu />
//             </button>

//             {/*  DYNAMIC TITLE */}
//             <h1 className="text-lg font-semibold text-gray-800">{pageTitle}</h1>
//           </div>
//         </header>

//         {/* PAGE CONTENT */}
//         <main>{children}</main>
//       </div>
//     </div>
//   );
// }
