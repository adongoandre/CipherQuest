import { NavLink, Link, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

/**
 * Two shells, matching the mockups:
 *
 *  - the public header (brand, How it works, Help & accessibility, guest pill)
 *    wraps landing, mission flow, join and the admin editor;
 *  - the app layout (sidebar: Home, Play, Learn, Compete, Friends, Profile,
 *    with Settings pinned at the bottom) wraps every signed-in screen.
 */

const APP_NAV = [
  { to: '/home', label: 'Home' },
  { to: '/play', label: 'Play' },
  { to: '/learn', label: 'Learn' },
  { to: '/compete', label: 'Compete' },
  { to: '/friends', label: 'Friends' },
  { to: '/profile', label: 'Profile' },
]

function Brand({ to = '/' }: { to?: string }) {
  return (
    <NavLink to={to} className="brand" aria-label="CipherQuest home">
      Cipher<span className="brand-gold">Quest</span>
    </NavLink>
  )
}

export function PublicHeader({ guestLabel = 'Playing as guest' }: { guestLabel?: string }) {
  return (
    <header className="public-header">
      <div className="public-header-inner">
        <Brand />
        <nav className="public-nav" aria-label="Main">
          <Link to="/help">Help &amp; accessibility</Link>
          <Link to="/join" className="guest-pill">
            {guestLabel}
          </Link>
        </nav>
      </div>
    </header>
  )
}

export function PublicLayout({
  children,
  guestLabel,
}: {
  children: ReactNode
  guestLabel?: string
}) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <PublicHeader guestLabel={guestLabel} />
      <main className="site-main public-main" id="main">
        {children}
      </main>
      <footer className="public-footer">
        <p>
          Classical ciphers are for learning and fun. They are not safe for protecting real
          secrets. We collect only anonymous play data to improve the game.
        </p>
        <p className="public-footer-links">
          <Link to="/help">Privacy</Link>
          <Link to="/help">Accessibility</Link>
        </p>
      </footer>
    </div>
  )
}

export function AppLayout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()

  /** Settings is a footer link in the mockup, not a top-level pill. */
  const settingsActive = pathname.startsWith('/settings')

  return (
    <div className="app-shell app-shell-split">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>

      <aside className="sidebar">
        <Brand to="/home" />
        <nav className="sidebar-nav" aria-label="Main">
          {APP_NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? 'active' : undefined)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <NavLink
          to="/settings"
          className={`sidebar-settings${settingsActive ? ' active' : ''}`}
        >
          Settings
        </NavLink>
      </aside>

      <main className="app-main" id="main">
        {children}
      </main>
    </div>
  )
}

/** Page title + subtitle used across every app screen. */
export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="page-header">
      <h1>{title}</h1>
      {subtitle ? <p className="muted">{subtitle}</p> : null}
    </header>
  )
}
