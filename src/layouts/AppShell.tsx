import { Database, FilePlus2, FileText, FolderOpen, LayoutDashboard, LogOut, Menu, PencilRuler, Settings, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { DisclaimerBanner } from '@/components/DisclaimerBanner'
import { StatusBadge } from '@/components/StatusBadge'
import { Button } from '@/components/ui/Button'
import { useActiveCase } from '@/hooks/active-case-context'
import { useAuth } from '@/hooks/auth-context'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/investigations/new', label: 'New Investigation', icon: FilePlus2 },
  { to: '/cases', label: 'Case Management', icon: FolderOpen },
  { to: '/workspace', label: 'Sketch Workspace', icon: PencilRuler },
  { to: '/datasets', label: 'Dataset and AI Evaluation', icon: Database },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <ul className="flex flex-col gap-1">
      {NAV.map(({ to, label, icon: Icon, ...rest }) => (
        <li key={to}>
          <NavLink
            to={to}
            end={'end' in rest}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                isActive ? 'bg-accent/10 font-medium text-accent' : 'text-muted hover:bg-raised hover:text-ink'
              }`
            }
          >
            <Icon className="size-4 shrink-0" aria-hidden="true" />
            {label}
          </NavLink>
        </li>
      ))}
    </ul>
  )
}

function Brand() {
  return (
    <Link to="/" className="flex items-center gap-2.5 rounded-lg px-1 py-1">
      <span className="grid size-8 place-items-center rounded-lg border border-accent/40 bg-accent/10 text-accent">
        <PencilRuler className="size-4" aria-hidden="true" />
      </span>
      <span className="leading-tight">
        <span className="block text-sm font-semibold text-ink">SketchAssist AI</span>
        <span className="block text-[11px] text-subtle">Version 3.0 · academic prototype</span>
      </span>
    </Link>
  )
}

function ActiveCaseBar() {
  const { activeCase, activeCaseId, loading, clearCase } = useActiveCase()
  return (
    <div className="flex min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-1 text-sm" aria-live="polite">
      <span className="text-xs tracking-wide text-subtle uppercase">Active case</span>
      {activeCase ? (
        <>
          <Link to={`/cases/${activeCase.case_id}`} className="inline-link font-mono text-accent hover:text-accent-strong">
            {activeCase.case_id}
          </Link>
          <span className="max-w-[16rem] truncate text-ink" title={activeCase.title}>
            {activeCase.title}
          </span>
          <StatusBadge status={activeCase.status} />
          <span className="max-w-[26rem] truncate text-xs text-subtle" title={`Investigator: ${activeCase.investigator_name || 'not recorded'}. Witness: ${activeCase.witness_name || 'not recorded'}.`}>
            Investigator <span className="text-muted">{activeCase.investigator_name || 'not recorded'}</span> · Witness <span className="text-muted">{activeCase.witness_name || 'not recorded'}</span>
          </span>
          <Button size="sm" variant="ghost" onClick={clearCase} aria-label="Clear the active case">
            <X className="size-3.5" aria-hidden="true" /> Clear
          </Button>
        </>
      ) : activeCaseId && loading ? (
        <span className="text-muted">Loading…</span>
      ) : (
        <>
          <span className="text-muted">None selected</span>
          <Link to="/cases" className="inline-link text-accent hover:text-accent-strong">
            Choose a case
          </Link>
        </>
      )}
    </div>
  )
}

export function AppShell() {
  const { user, logout } = useAuth()
  const location = useLocation()
  // The mobile menu belongs to the page it was opened on, so it closes by itself after any navigation.
  const [menuPath, setMenuPath] = useState<string | null>(null)
  const menuOpen = menuPath === location.pathname
  const setMenuOpen = (open: boolean) => setMenuPath(open ? location.pathname : null)

  useEffect(() => {
    window.scrollTo?.({ top: 0 })
  }, [location.pathname])

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[17rem_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded-lg focus:bg-accent focus:px-3 focus:py-2 focus:text-accent-ink">
        Skip to main content
      </a>

      <aside className="hidden border-r border-line bg-sidebar lg:sticky lg:top-0 lg:flex lg:h-screen lg:flex-col" aria-label="Sidebar">
        <div className="p-4">
          <Brand />
        </div>
        <nav aria-label="Main" className="flex-1 overflow-y-auto px-3 pb-4">
          <NavLinks />
        </nav>
        <div className="border-t border-line p-4">
          <p className="truncate text-sm font-medium text-ink">{user?.display_name ?? user?.username}</p>
          <p className="mb-3 text-xs text-subtle">{user?.role === 'admin' ? 'Administrator' : 'Investigator'}</p>
          <Button size="sm" icon={LogOut} onClick={logout} className="w-full">
            Sign out
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 border-b border-line bg-bg/95 backdrop-blur">
          <div className="flex items-center gap-3 px-4 py-2.5 lg:px-8">
            <button
              type="button"
              className="rounded-lg p-2 text-muted hover:bg-raised hover:text-ink lg:hidden"
              aria-expanded={menuOpen}
              aria-controls="mobile-nav"
              onClick={() => setMenuOpen(!menuOpen)}
            >
              {menuOpen ? <X className="size-5" aria-hidden="true" /> : <Menu className="size-5" aria-hidden="true" />}
              <span className="sr-only">{menuOpen ? 'Close menu' : 'Open menu'}</span>
            </button>
            <ActiveCaseBar />
          </div>
          {menuOpen ? (
            <nav id="mobile-nav" aria-label="Main (mobile)" className="border-t border-line bg-sidebar px-3 py-3 lg:hidden">
              <NavLinks onNavigate={() => setMenuOpen(false)} />
              <div className="mt-3 flex items-center justify-between gap-3 border-t border-line px-3 pt-3">
                <span className="truncate text-sm text-muted">{user?.display_name ?? user?.username}</span>
                <Button size="sm" icon={LogOut} onClick={logout}>
                  Sign out
                </Button>
              </div>
            </nav>
          ) : null}
        </header>

        <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[84rem] flex-1 px-4 py-6 lg:px-8">
          <Outlet />
        </main>

        <footer className="border-t border-line px-4 py-3 lg:px-8">
          <DisclaimerBanner compact />
        </footer>
      </div>
    </div>
  )
}
