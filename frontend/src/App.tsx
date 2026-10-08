import { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { Home } from "./pages/Home";
import { HowItWorks } from "./pages/HowItWorks";
import { ReviewDocument, ReviewStart } from "./pages/Review";
import { SampleReview, SamplesIndex } from "./pages/Samples";
import { SERVER_LABELS, ServerProvider, useServer } from "./server";

const TITLES: [RegExp, string][] = [
  [/^\/review/, "Review a lease"],
  [/^\/samples/, "Sample reviews"],
  [/^\/how-it-works/, "How it works"],
];

export default function App() {
  return (
    <ServerProvider>
      <Shell />
    </ServerProvider>
  );
}

function Shell() {
  const { pathname, hash } = useLocation();

  // A new page starts at the top (or at its #section), with its own tab title.
  useEffect(() => {
    const target = hash ? document.getElementById(hash.slice(1)) : null;
    if (target) target.scrollIntoView();
    else window.scrollTo(0, 0);
    const title = TITLES.find(([pattern]) => pattern.test(pathname))?.[1];
    document.title = title ? `${title} · LeaseLens` : "LeaseLens · Understand your rental agreement";
  }, [pathname, hash]);

  return (
    <div className="app-shell">
      <SiteHeader />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/review" element={<ReviewStart />} />
          <Route path="/review/:documentId" element={<ReviewDocument />} />
          <Route path="/samples" element={<SamplesIndex />} />
          <Route path="/samples/:slug" element={<SampleReview />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <SiteFooter />
    </div>
  );
}

function SiteHeader() {
  const { state } = useServer();
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => setMenuOpen(false), [pathname]);

  return (
    <header className="topbar">
      <Link className="brand" to="/" aria-label="LeaseLens home">
        <span className="brand-mark">L</span>
        <span>LeaseLens</span>
      </Link>
      <button
        className="menu-toggle"
        aria-label="Menu"
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen((open) => !open)}
      >
        {menuOpen ? "×" : "☰"}
      </button>
      <nav className={`site-nav ${menuOpen ? "site-nav-open" : ""}`}>
        <NavLink to="/samples">Samples</NavLink>
        <NavLink to="/how-it-works">How it works</NavLink>
        {pathname.startsWith("/review") && (
          <span className={`status ${state === "ready" ? "status-ready" : "status-waiting"}`}>
            <i />
            {SERVER_LABELS[state]}
          </span>
        )}
        <NavLink to="/review" className="primary-button nav-cta">
          Review my lease
        </NavLink>
      </nav>
    </header>
  );
}

function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div>
          <Link className="brand" to="/">
            <span className="brand-mark">L</span>
            <span>LeaseLens</span>
          </Link>
          <p>
            AI-assisted review of Indian rental agreements. Information only, not legal advice.
          </p>
        </div>
        <nav aria-label="Footer">
          <Link to="/review">Review a lease</Link>
          <Link to="/samples">Sample reviews</Link>
          <Link to="/how-it-works">How it works</Link>
          <Link to="/how-it-works#privacy">Privacy</Link>
          <a href="https://github.com/Rishi-Is-Cool/leaselens-india" target="_blank" rel="noreferrer">
            Source on GitHub
          </a>
        </nav>
      </div>
    </footer>
  );
}

function NotFound() {
  return (
    <div className="page page-narrow">
      <section className="card server-notice">
        <h2>Page not found</h2>
        <Link className="primary-button" to="/">
          Go to the home page
        </Link>
      </section>
    </div>
  );
}
