import React from "react";
import { CustomDrawerContent } from "@/src/features/dashboard/ui/CustomDrawerContent";

// Sidebar component for web
function Sidebar() {
  return (
    <aside style={{ width: 350, background: '#18181b', borderRight: '1px solid #222', overflowY: 'auto' }}>
      <CustomDrawerContent />
    </aside>
  );
}

// Main container for web
function MainContainer({ children }: { children?: React.ReactNode }) {
  return (
    <main style={{ flex: 1, background: '#111', overflowY: 'auto' }}>
      {children}
    </main>
  );
}

export default function AppLayout({ children }: { children?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#111' }}>
      <Sidebar />
      <MainContainer>{children}</MainContainer>
    </div>
  );
}
