import { useState } from "react";
import { ArrowLeft, Save } from "lucide-react";
import { useNavigate } from "react-router-dom";

const initial = { institutionId:"", institution:"", title:"", description:"", category:"Infrastructure", received:new Date().toISOString().slice(0,10), priority:"Medium", frequency:"First Reported", bureau:"Infrastructure Cell", official:"", status:"Open", due:"", score:35, related:false, notes:"" };
export default function ComplaintForm({ institutions, onCreate }) {
  const [form,setForm]=useState(initial); const [error,setError]=useState(""); const [saving,setSaving]=useState(false); const navigate=useNavigate();
  const update=(key,value)=>setForm(old=>({...old,[key]:value}));
  const submit=async e=>{e.preventDefault();setError("");if(!form.institutionId||!form.title.trim()||!form.description.trim()){setError("Select an institution and enter a title and description.");return;}const institution=institutions.find(i=>i.id===form.institutionId);setSaving(true);try{const result=await onCreate({...form,institution:institution?.name||"",official:form.official||"Unassigned"});navigate(`/complaints/${result.id}`);}catch(err){setError(err.message||"Could not save the complaint.");}finally{setSaving(false);}};
  return <div className="page-content narrow-page"><button className="back-link" onClick={()=>navigate("/complaints")}><ArrowLeft size={15}/> Back to complaints</button><div className="page-heading"><div><div className="eyebrow">CASE MANAGEMENT / NEW RECORD</div><h1>Register complaint</h1><p>Create a case record and capture its initial triage details.</p></div></div>
    <form className="panel form-panel" onSubmit={submit}><div className="form-section-title"><span className="form-section-number">01</span><div><h2>Complaint information</h2><p>Provide the core details supplied for this complaint.</p></div></div>
      <div className="form-grid"><label className="field full"><span>Institution <b>*</b></span><select value={form.institutionId} onChange={e=>update("institutionId",e.target.value)} required><option value="">Select an institution</option>{institutions.map(i=><option value={i.id} key={i.id}>{i.name} · {i.id}</option>)}</select></label>
      <label className="field full"><span>Complaint title <b>*</b></span><input value={form.title} onChange={e=>update("title",e.target.value)} placeholder="Briefly describe the issue" required maxLength="160"/></label>
      <label className="field full"><span>Description <b>*</b></span><textarea rows="4" value={form.description} onChange={e=>update("description",e.target.value)} placeholder="Record the complaint details and relevant context..." required/></label>
      <label className="field"><span>Category <b>*</b></span><select value={form.category} onChange={e=>update("category",e.target.value)}>{["Infrastructure","Faculty","Examination","Student Grievance","Institutional Compliance","Other"].map(x=><option key={x}>{x}</option>)}</select></label>
      <label className="field"><span>Date received <b>*</b></span><input type="date" value={form.received} onChange={e=>update("received",e.target.value)} required/></label></div>
      <div className="form-section-title spaced"><span className="form-section-number">02</span><div><h2>Triage & assignment</h2><p>Priority and frequency are separate assessments.</p></div></div>
      <div className="form-grid"><label className="field"><span>Priority <b>*</b></span><select value={form.priority} onChange={e=>update("priority",e.target.value)}>{["Low","Medium","High","Critical"].map(x=><option key={x}>{x}</option>)}</select><small>Set by an authorised official; not automatically based on frequency.</small></label>
      <label className="field"><span>Frequency classification</span><select value={form.frequency} onChange={e=>update("frequency",e.target.value)}>{["First Reported","Recurring","Repeated Pattern","Under Review"].map(x=><option key={x}>{x}</option>)}</select></label>
      <label className="field"><span>Bureau / cell <b>*</b></span><select value={form.bureau} onChange={e=>update("bureau",e.target.value)}>{["Infrastructure Cell","Academic Cell","Compliance Bureau","Student Grievance Cell","Other"].map(x=><option key={x}>{x}</option>)}</select></label>
      <label className="field"><span>Assigned official</span><input value={form.official} onChange={e=>update("official",e.target.value)} placeholder="Name or leave unassigned"/></label>
      <label className="field"><span>Status</span><select value={form.status} onChange={e=>update("status",e.target.value)}>{["Open","In Progress","Pending","Resolved","Closed"].map(x=><option key={x}>{x}</option>)}</select></label>
      <label className="field"><span>Due date</span><input type="date" value={form.due} onChange={e=>update("due",e.target.value)}/></label>
      <label className="field full"><span>Internal notes</span><textarea rows="3" value={form.notes} onChange={e=>update("notes",e.target.value)} placeholder="Optional notes visible to authorised staff"/></label></div>
      {error&&<div className="form-error">{error}</div>}<div className="form-actions"><button type="button" className="btn btn-secondary" onClick={()=>navigate("/complaints")}>Cancel</button><button className="btn btn-primary" disabled={saving}>{saving?"Saving...":<><Save size={15}/> Save complaint</>}</button></div>
      <p className="form-disclaimer">Complaint records are saved to the connected Flask API and SQLite database when demo mode is disabled.</p>
    </form>
  </div>;
}
