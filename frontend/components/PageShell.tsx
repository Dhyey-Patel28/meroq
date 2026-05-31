import Link from "next/link";
import type { ReactNode } from "react";

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/ticker", label: "Ticker" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/portfolio", label: "Portfolio" },
];

export function PageShell({ children }: { children: ReactNode }) {
  return (
    <main className="app-shell">
      <nav className="top-nav">
        <Link className="brand" href="/">
          <span className="brand-mark">M</span>
          Meroq
        </Link>
        <div className="nav-links">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href}>
              {item.label}
            </Link>
          ))}
        </div>
      </nav>
      {children}
    </main>
  );
}
