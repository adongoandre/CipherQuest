import { NavLink, Link, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { clearSessionToken } from '../lib/api'

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

/** Hamburger for narrow screens: three bars that fold into an X while open. */
function NavToggle({
  open,
  controls,
  onToggle,
}: {
  open: boolean
  controls: string
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      className={`nav-toggle${open ? ' is-open' : ''}`}
      aria-label={open ? 'Close menu' : 'Open menu'}
      aria-expanded={open}
      aria-controls={controls}
      onClick={onToggle}
    >
      <span className="nav-toggle-bar" aria-hidden="true" />
      <span className="nav-toggle-bar" aria-hidden="true" />
      <span className="nav-toggle-bar" aria-hidden="true" />
    </button>
  )
}

export function PublicHeader({ guestLabel = 'Playing as guest' }: { guestLabel?: string }) {
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    if (!menuOpen) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [menuOpen])

  return (
    <header className="public-header">
      <div className="public-header-inner">
        <Brand />
        <NavToggle
          open={menuOpen}
          controls="public-nav"
          onToggle={() => setMenuOpen((open) => !open)}
        />
        <nav
          id="public-nav"
          className={`public-nav${menuOpen ? ' is-open' : ''}`}
          aria-label="Main"
        >
          <Link to="/help" onClick={() => setMenuOpen(false)}>
            Help &amp; accessibility
          </Link>
          <Link to="/join" className="guest-pill" onClick={() => setMenuOpen(false)}>
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
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  /** Settings is a footer link in the mockup, not a top-level pill. */
  const settingsActive = pathname.startsWith('/settings')

  useEffect(() => {
    if (!menuOpen) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMenuOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [menuOpen])

  /** Sign out: drop the stored session and go back to the landing page. */
  function signOut() {
    setMenuOpen(false)
    clearSessionToken()
    navigate('/', { replace: true })
  }

  return (
    <div className="app-shell app-shell-split">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>

      <aside className="sidebar">
        <div className="sidebar-bar">
          <Brand to="/home" />
          <NavToggle
            open={menuOpen}
            controls="app-nav-menu"
            onToggle={() => setMenuOpen((open) => !open)}
          />
        </div>

        <div id="app-nav-menu" className={`sidebar-menu${menuOpen ? ' is-open' : ''}`}>
          <nav className="sidebar-nav" aria-label="Main">
            {APP_NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => (isActive ? 'active' : undefined)}
                onClick={() => setMenuOpen(false)}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <NavLink
            to="/settings"
            className={`sidebar-settings${settingsActive ? ' active' : ''}`}
            onClick={() => setMenuOpen(false)}
          >
            Settings
          </NavLink>
          <button type="button" className="sidebar-settings sidebar-logout" onClick={signOut}>
            Log out
          </button>
        </div>
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
