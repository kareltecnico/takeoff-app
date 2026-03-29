import { createBrowserRouter, Navigate } from 'react-router-dom'

import { AppShell } from '../components/layout/AppShell'
import { EditorRoute } from '../components/layout/EditorRoute'
import { ProtectedRoute } from '../components/layout/ProtectedRoute'
import { LoginPage } from '../features/auth/LoginPage'
import { NewTakeoffPage } from '../features/projects/NewTakeoffPage'
import { ProjectsPage } from '../features/projects/ProjectsPage'
import { TakeoffDetailPage } from '../features/takeoffs/TakeoffDetailPage'
import { VersionDetailPage } from '../features/takeoffs/VersionDetailPage'
import { VersionHistoryPage } from '../features/takeoffs/VersionHistoryPage'

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/projects" replace />,
      },
      {
        path: 'projects',
        element: <ProjectsPage />,
      },
      {
        path: 'projects/new-takeoff',
        element: (
          <EditorRoute>
            <NewTakeoffPage />
          </EditorRoute>
        ),
      },
      {
        path: 'takeoffs/:takeoffId',
        element: <TakeoffDetailPage />,
      },
      {
        path: 'takeoffs/:takeoffId/versions',
        element: <VersionHistoryPage />,
      },
      {
        path: 'versions/:versionId',
        element: <VersionDetailPage />,
      },
    ],
  },
])
