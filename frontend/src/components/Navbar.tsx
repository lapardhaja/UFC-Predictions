import { Link, NavLink } from "react-router-dom";

const link = "text-zinc-400 hover:text-blood transition";

export function Navbar() {
  return (
    <header className="border-b border-zinc-800 bg-black/60 backdrop-blur sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
        <Link to="/" className="font-bold tracking-tight text-lg">
          <span className="text-blood">UFC</span>
          <span className="text-zinc-100 ml-1">Predictor</span>
        </Link>
        <nav className="flex gap-6 text-sm font-medium">
          <NavLink to="/" className={({ isActive }) => (isActive ? "text-blood" : link)} end>
            Events
          </NavLink>
          <NavLink to="/model" className={({ isActive }) => (isActive ? "text-blood" : link)}>
            Model
          </NavLink>
        </nav>
      </div>
    </header>
  );
}
