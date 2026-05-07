"use client";

import { useState } from "react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import HeatmapView from "@/components/views/HeatmapView";
import OverviewView from "@/components/views/OverviewView";
import ForecastView from "@/components/views/ForecastView";
import VPPView from "@/components/views/VPPView";
import SitesView from "@/components/views/SitesView";
import AlertsView from "@/components/views/AlertsView";
import AgentsView from "@/components/views/AgentsView";

export default function Home() {
  const [currentView, setCurrentView] = useState("overview");

  return (
    <DashboardLayout view={currentView} setView={setCurrentView}>
      {currentView === "overview" && <OverviewView />}
      {currentView === "heatmap" && <HeatmapView />}
      {currentView === "forecast" && <ForecastView />}
      {currentView === "vpp" && <VPPView />}
      {currentView === "sites" && <SitesView />}
      {currentView === "alerts" && <AlertsView />}
      {currentView === "agents" && <AgentsView />}
    </DashboardLayout>
  );
}
