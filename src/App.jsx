import { useEffect, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, DEMO_MODE } from "./services/api";
import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import Dashboard from "./pages/Dashboard";
import Complaints from "./pages/Complaints";
import ComplaintForm from "./pages/ComplaintForm";
import ComplaintDetail from "./pages/ComplaintDetail";
import Institutions from "./pages/Institutions";
import Analytics from "./pages/Analytics";
import Relationships from "./pages/Relationships";
import Login from "./pages/Login";
import Placeholder from "./pages/Placeholder";
import Alerts from "./pages/Alerts";

export default function App() {
  const [user,setUser]=useState(null);const [complaints,setComplaints]=useState([]);const [institutions,setInstitutions]=useState([]);const [loading,setLoading]=useState(true);const [loadError,setLoadError]=useState("");const navigate=useNavigate();const location=useLocation();
  const load=async()=>{setLoading(true);setLoadError("");try{const [u,c,i]=await Promise.all([api.getCurrentUser(),api.getComplaints(),api.getInstitutions()]);setUser(u);setComplaints(c);setInstitutions(i);}catch(e){setLoadError(e.message||"Unable to connect to the backend.");}finally{setLoading(false);}};
  useEffect(()=>{load();},[]);
  useEffect(()=>{const titles={"Overview":"Overview","Complaints":"Complaints","Institutions":"Institutions","Insights & analytics":"Insights & analytics","Related cases":"Related cases"};const p=location.pathname;if(p==="/")document.title="Overview · CaseTrack 360";else if(p.includes("/complaints/new"))document.title="Register complaint · CaseTrack 360";else if(p.startsWith("/complaints/"))document.title="Complaint details · CaseTrack 360";else document.title=`${Object.values(titles).find(t=>p.includes(t.toLowerCase().replaceAll(" ","-")))||"Workspace"} · CaseTrack 360`;},[location.pathname]);
  const login=async(email,password,displayName)=>{setLoadError("");const result=await api.login(email,password,displayName);const [c,i]=await Promise.all([api.getComplaints(),api.getInstitutions()]);setUser(result);setComplaints(c);setInstitutions(i);setLoadError("");navigate("/");};
  const logout=async()=>{await api.logout();setUser(null);navigate("/login");};
  const createComplaint=async(payload)=>{const result=await api.createComplaint(payload);setComplaints(await api.getComplaints());return result;};
  const updateComplaint=async(id,payload)=>{await api.updateComplaint(id,payload);setComplaints(await api.getComplaints());};
  const createInstitution=async(payload)=>{await api.createInstitution(payload);setInstitutions(await api.getInstitutions());};
  if(loading)return <div className="app-loading"><div className="loading-mark">C</div><strong>CaseTrack 360</strong><span>Preparing your workspace…</span></div>;
  if(!user||location.pathname==="/login")return <Login onLogin={login}/>;
  if(loadError)return <div className="connection-error"><h2>Couldn’t load the workspace</h2><p>{loadError}</p><button className="btn btn-primary" onClick={load}>Try again</button><p className="muted">Check that the Flask backend is running at <code>http://127.0.0.1:5000</code> and that the frontend <code>.env</code> points to it.</p></div>;
  return <div className="app-shell"><Sidebar complaintCount={new Set(complaints.filter(c=>c?.id).map(c=>String(c.id))).size}/><div className="main-shell"><Topbar user={user} onLogout={logout}/>{DEMO_MODE&&<div className="demo-topline"><span>DEMO MODE</span> SQLite-backed records · prototype authentication</div>}<main>
    <Routes>
      <Route path="/" element={<Dashboard complaints={complaints} user={user}/>}/>
      <Route path="/complaints" element={<Complaints complaints={complaints}/>}/>
      <Route path="/complaints/new" element={<ComplaintForm institutions={institutions} onCreate={createComplaint}/>}/>
      <Route path="/complaints/:id" element={<ComplaintDetail complaints={complaints} onUpdate={updateComplaint} user={user}/>}/>
      <Route path="/institutions" element={<Institutions institutions={institutions} onCreate={createInstitution}/>}/>
      <Route path="/analytics" element={<Analytics complaints={complaints}/>}/>
      <Route path="/relationships" element={<Relationships complaints={complaints}/>}/>
      <Route path="/settings" element={<Placeholder title="Settings"/>}/>
      <Route path="*" element={<Navigate to="/" replace/>}/>
      <Route path="/alerts" element={<Alerts />} />
    </Routes>
  </main><footer className="app-footer"><span>© 2026 CaseTrack 360 <i>·</i> Prototype</span><span>Built for cross-bureau complaint intelligence</span></footer></div></div>;
}
