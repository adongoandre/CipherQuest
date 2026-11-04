import { useEffect } from 'react'
import { NavLink, Route, Routes, useParams } from 'react-router-dom'

import { AppLayout, PublicLayout } from './components/Layout'
import { AdminPage } from './pages/Admin'
import { CipherPage } from './pages/Cipher'
import { CompetePage } from './pages/Compete'
import { FriendsPage } from './pages/Friends'
import { HelpPage } from './pages/Help'
import { HomePage } from './pages/Home'
import { JoinPage } from './pages/Join'
import { LandingPage } from './pages/Landing'
import { LearnPage, LessonPage } from './pages/Learn'
import { LeaderboardsPage } from './pages/Leaderboards'
import { MissionPage } from './pages/Mission'
import { MissionsPage } from './pages/Missions'
import { PlayPage, RoomPage } from './pages/Play'
import { ProfilePage } from './pages/Profile'
import { ProgressPage } from './pages/Progress'
import { SettingsPage } from './pages/Settings'
import { api } from './lib/api'

function trackLandingView(): void {
  api.track('landing_view').catch(() => {
    /* analytics must never block or break the page */
  })
}

export default function App() {
  useEffect(trackLandingView, [])

  return (
    <Routes>
      {/* Public shell: brand header, How it works, Help, guest pill */}
      <Route
        path="/"
        element={
          <PublicLayout>
            <LandingPage />
          </PublicLayout>
        }
      />
      <Route
        path="/missions"
        element={
          <PublicLayout>
            <MissionsPage />
          </PublicLayout>
        }
      />
      <Route
        path="/missions/:slug"
        element={
          <PublicLayout>
            <MissionRoute />
          </PublicLayout>
        }
      />
      <Route
        path="/help"
        element={
          <PublicLayout>
            <HelpPage />
          </PublicLayout>
        }
      />
      <Route
        path="/join"
        element={
          <PublicLayout>
            <JoinPage />
          </PublicLayout>
        }
      />
      <Route
        path="/admin"
        element={
          <PublicLayout guestLabel="Admin session">
            <AdminPage />
          </PublicLayout>
        }
      />

      {/* Signed-in shell: sidebar with gold active pill */}
      <Route
        path="/home"
        element={
          <AppLayout>
            <HomePage />
          </AppLayout>
        }
      />
      <Route
        path="/play"
        element={
          <AppLayout>
            <PlayPage />
          </AppLayout>
        }
      />
      <Route
        path="/rooms/:code"
        element={
          <AppLayout>
            <RoomPage />
          </AppLayout>
        }
      />
      <Route
        path="/learn"
        element={
          <AppLayout>
            <LearnPage />
          </AppLayout>
        }
      />
      <Route
        path="/learn/:slug/:step"
        element={
          <AppLayout>
            <LessonPage />
          </AppLayout>
        }
      />
      <Route
        path="/compete"
        element={
          <AppLayout>
            <CompetePage />
          </AppLayout>
        }
      />
      <Route
        path="/compete/leaderboards"
        element={
          <AppLayout>
            <LeaderboardsPage />
          </AppLayout>
        }
      />
      <Route
        path="/friends"
        element={
          <AppLayout>
            <FriendsPage />
          </AppLayout>
        }
      />
      <Route
        path="/profile"
        element={
          <AppLayout>
            <ProfilePage />
          </AppLayout>
        }
      />
      <Route
        path="/settings"
        element={
          <AppLayout>
            <SettingsPage />
          </AppLayout>
        }
      />
      <Route
        path="/cipher"
        element={
          <AppLayout>
            <CipherPage />
          </AppLayout>
        }
      />
      <Route
        path="/progress"
        element={
          <AppLayout>
            <ProgressPage />
          </AppLayout>
        }
      />

      <Route
        path="*"
        element={
          <PublicLayout>
            <NotFoundPage />
          </PublicLayout>
        }
      />
    </Routes>
  )
}

/**
 * Remounting on the slug keeps every stage, hint and score in a fresh state
 * when the player jumps between missions.
 */
function MissionRoute() {
  const { slug } = useParams()
  return <MissionPage key={slug} />
}

function NotFoundPage() {
  return (
    <div className="prose">
      <p className="eyebrow">404</p>
      <h1>That page is not part of this case file.</h1>
      <p className="muted">The address may have changed, or the mission has not been written yet.</p>
      <NavLink className="btn btn-primary" to="/">
        Back to CipherQuest
      </NavLink>
    </div>
  )
}