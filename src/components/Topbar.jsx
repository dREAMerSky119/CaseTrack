import { Bell, ChevronDown, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function Topbar({ user, onLogout }) {
  const navigate = useNavigate();
  return <header className="topbar">
    <div className="topbar-context"><span>AICTE / CaseTrack 360</span><span className="context-divider">/</span><strong>Operations workspace</strong></div>
    <div className="topbar-actions">
      <button className="top-search" onClick={() => navigate("/complaints")}><Search size={16} /><span>Search cases, institutions...</span><kbd>⌘ K</kbd></button>
      <button className="icon-button notification" aria-label="Notifications" onClick={() => navigate("/complaints?overdue=true")}><Bell size={18} /><i></i></button>
      <div className="user-menu"><div className="avatar">{user?.initials || "AD"}</div><div className="user-text"><strong>{user?.name || "Demo User"}</strong><span>{user?.role || "Administrator"}</span></div><button className="plain-icon" aria-label="Account menu" onClick={onLogout}><ChevronDown size={16} /></button></div>
    </div>
  </header>;
}
