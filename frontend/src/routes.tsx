import React from 'react';
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';

// Layouts
import AppLayout from '@/components/layout/AppLayout';

// Pages
import DashboardPage from '@/pages/DashboardPage';
import ComparePage from '@/pages/ComparePage';
import VisualizationsPage from '@/pages/VisualizationsPage';
import NotFoundPage from '@/pages/NotFoundPage';

// Legacy Components (to be migrated to full pages)
import ProjectionAdjuster from '@/components/projectionadjuster';
import ScenarioManager from '@/components/scenariomanager';
import TeamAdjuster from '@/components/teamadjuster';
import DraftDayTool from '@/components/draftdaytool';

// Define routes
const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <DashboardPage />
      },
      {
        path: 'players',
        element: <ProjectionAdjuster />
      },
      {
        path: 'scenarios',
        element: <ScenarioManager />
      },
      {
        path: 'teams',
        element: <TeamAdjuster />
      },
      {
        path: 'compare',
        element: <ComparePage />
      },
      {
        path: 'visualizations',
        element: <VisualizationsPage />
      },
      {
        path: 'settings',
        element: <div className="container mx-auto p-6">
          <h1 className="text-3xl font-bold mb-4">Settings</h1>
          <p>This page is under construction.</p>
        </div>
      },
      {
        path: 'draft',
        element: <DraftDayTool />
      },
      {
        path: '*',
        element: <NotFoundPage />
      }
    ]
  }
]);

const Routes: React.FC = () => {
  return <RouterProvider router={router} />;
};

export default Routes;