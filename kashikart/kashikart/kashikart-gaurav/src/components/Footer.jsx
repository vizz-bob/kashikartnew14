import React, { memo } from "react";

const Footer = memo(function Footer() {
  return (
    <footer className="mt-auto border-t border-[#E2E8F0] bg-white px-4 py-3 text-center text-xs text-[#64748B] sm:px-6">
      © 2026 Tender Intel · All rights reserved
    </footer>
  );
});

export default Footer;
