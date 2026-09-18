'use client';

import { AppShell } from '@/components/shell/AppShell';
import { DashboardView } from '@/components/dashboard/DashboardView';

export default function Dashboard() {
  return (
    <AppShell activeView="dashboard">
      <DashboardView />
    </AppShell>
  );
}
