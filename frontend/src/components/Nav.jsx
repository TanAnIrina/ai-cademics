import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Nav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <nav className="nav">
      <div className="container">
        <NavLink to="/" className="brand">
          <span className="brand-mark">🎓</span>
          <span className="brand-name">
            AI&#8209;<em>cademics</em>
          </span>
        </NavLink>

        <div className="nav-links">
          <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
            Classrooms
          </NavLink>
          <NavLink
            to="/history"
            className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
          >
            History
          </NavLink>
          {user ? (
            <div className="row" style={{ gap: 10, marginLeft: 6 }}>
              <span className="tag" title={`Signed in as ${user.role}`}>
                {user.display_name} · {user.role}
              </span>
              <button className="btn ghost sm" onClick={handleLogout}>
                Sign out
              </button>
            </div>
          ) : (
            <NavLink to="/login" className="btn primary sm" style={{ marginLeft: 6 }}>
              Sign in
            </NavLink>
          )}
        </div>
      </div>
    </nav>
  );
}
