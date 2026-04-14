import React, { memo } from "react";

const StatusBadge = memo(({ status }) => {
  const statusStyles = {
    NEW: "bg-green-100 text-green-700",
    Viewed: "bg-slate-100 text-slate-600",
    SAVED: "bg-blue-100 text-blue-700",
    Expired: "bg-red-100 text-red-700",
    Hold: "bg-amber-100 text-amber-700",
  };

  return (
    <span
      className={`px-3 py-1 rounded-full text-xs font-medium inline-block ${
        statusStyles[status] || statusStyles.Viewed
      }`}
    >
      {status}
    </span>
  );
});

export default StatusBadge;
