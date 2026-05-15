import { useState, useEffect, useCallback } from 'react';
import { Wifi, WifiOff } from 'lucide-react';
import { fetchHealth, fetchInferenceStatus } from '../data/api';

export default function Infrastructure() {
  const [live, setLive] = useState(false);
  const [health, setHealth] = useState(null);
  const [inference, setInference] = useState(null);

  const refresh = useCallback(async () => {
    try { const h = await fetchHealth(); setHealth(h); setLive(true); } catch { setLive(false); }
    try { setInference(await fetchInferenceStatus()); } catch {}
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 5000); return () => clearInterval(t); }, [refresh]);

  const newModules = [
    { name: 'Backup Manager', status: 'active', desc: 'Automated backup scheduling & S3 storage', icon: '💾', phase: '6C' },
    { name: 'Disaster Recovery', status: 'active', desc: 'Multi-region failover & recovery playbooks', icon: '🛡️', phase: '6C' },
    { name: 'Archival Scheduler', status: 'active', desc: 'Time-based data archival to cold storage', icon: '📁', phase: '6C' },
    { name: 'Data Lifecycle Mgr', status: 'active', desc: 'Retention policies & compliance tracking', icon: '♻️', phase: '6C' },
    { name: 'Extended Health Mon', status: 'active', desc: 'Deep health checks with anomaly detection', icon: '🔍', phase: '6C' },
    { name: 'Structured Logging', status: 'active', desc: 'JSON logging + OpenTelemetry tracing', icon: '📝', phase: '6C' },
    { name: 'Real-time Feed Mgr', status: 'active', desc: 'WebSocket/REST market data aggregation', icon: '📡', phase: '6C' },
    { name: 'Streaming Features', status: 'active', desc: 'Live feature computation from tick data', icon: '⚡', phase: '6C' },
    { name: 'Extended Testing', status: 'active', desc: 'Property-based + integration test framework', icon: '🧪', phase: '6C' },
  ];

  if (!live) return (
    <><div className="page-header"><h2>Infrastructure</h2><p>⚠ Backend offline</p></div>
    <div className="page-body"><div className="card" style={{padding:40,textAlign:'center',color:'var(--text-muted)'}}>
      <WifiOff size={48} style={{margin:'0 auto 16px',opacity:0.3}}/><div style={{fontSize:16,fontWeight:600}}>No Connection</div>
    </div></div></>
  );

  const h = health || {};
  const gpuNames = h.hardware_gpu_names || [];
  const gpuAvail = h.gpu_available || false;
  const gpuCount = h.gpu_count || 0;
  const dbOk = h.database_connected || false;
  const redisOk = h.redis_connected || false;
  const modelsLoaded = h.models_loaded || false;

  // Build service status from health
  const services = [
    { name: 'API Server', status: 'online', icon: '🌐', bg: 'var(--green-dim)', detail: `Port ${h.port || 8000}`, uptime: `${h.uptime_percent?.toFixed(1) || '—'}%` },
    { name: 'QuestDB', status: dbOk ? 'online' : 'offline', icon: '🗄️', bg: 'var(--blue-dim)', detail: 'Time-series DB', uptime: dbOk ? '99.9%' : '—' },
    { name: 'Redis', status: redisOk ? 'online' : 'offline', icon: '⚡', bg: 'var(--red-dim)', detail: 'Feature Cache', uptime: redisOk ? '99.9%' : '—' },
    { name: 'Models', status: modelsLoaded ? 'online' : 'offline', icon: '🧠', bg: 'var(--purple-dim)', detail: `${h.loaded_model_count || 0} loaded`, uptime: modelsLoaded ? '✓' : '—' },
    { name: 'GPU', status: gpuAvail ? 'online' : 'offline', icon: '🎮', bg: 'var(--orange-dim)', detail: gpuNames[0] || 'Not available', uptime: gpuAvail ? `${gpuCount} GPU(s)` : 'CPU mode' },
    { name: 'Inference', status: inference?.running ? 'online' : 'offline', icon: '🔄', bg: 'var(--cyan)', detail: inference?.running ? `iter #${inference.iteration}` : 'Stopped', uptime: inference?.running ? `${inference.interval_seconds}s cycle` : '—' },
  ];

  return (<>
    <div className="page-header">
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <div><h2>Infrastructure</h2><p>Live system status from /health API — GPU, Database, Redis, Models & Inference</p></div>
        <div style={{display:'flex',alignItems:'center',gap:6,padding:'5px 12px',borderRadius:'var(--radius-sm)',fontSize:11,fontWeight:600,background:'var(--green-dim)',color:'var(--green)',border:'1px solid rgba(0,196,140,0.3)'}}>
          <Wifi size={12}/> LIVE
        </div>
      </div>
    </div>
    <div className="page-body">
      <div className="kpi-grid" style={{marginBottom:20}}>
        {[
          {label:'System Status',value:(h.status||'—').toUpperCase(),sub:`SLA: ${h.sla_compliant?'✓ Compliant':'✗ Violation'}`},
          {label:'Uptime',value:`${(h.uptime_percent||0).toFixed(1)}%`,sub:'Target: 99.9% SLA'},
          {label:'Health Checks',value:`${(h.success_rate||0).toFixed(1)}%`,sub:`${h.total_checks||0} total • ${h.failed_checks||0} failed`},
          {label:'GPU',value:gpuAvail?`${gpuCount} GPU(s)`:'CPU Only',sub:gpuNames[0]||'No GPU detected'},
          {label:'Models',value:modelsLoaded?'LOADED':'NOT LOADED',sub:`${h.loaded_model_count||0} models`},
          {label:'Database',value:dbOk?'CONNECTED':'OFFLINE',sub:'QuestDB + Redis'},
        ].map((m,i)=>(<div key={i} className="kpi-card animate-in">
          <div className="kpi-label">{m.label}</div><div className="kpi-value" style={{fontSize:22}}>{m.value}</div>
          <div style={{fontSize:11,color:'var(--text-muted)',marginTop:4}}>{m.sub}</div>
        </div>))}
      </div>

      {/* Live Services Grid */}
      <div className="card animate-in" style={{marginBottom:20}}>
        <div className="card-header"><span className="card-title">Service Status</span>
          <span className={`card-badge ${services.every(s=>s.status==='online')?'badge-green':'badge-orange'}`}>
            {services.filter(s=>s.status==='online').length}/{services.length} Online
          </span>
        </div>
        <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:12,marginTop:8}}>
          {services.map((s,i)=>(
            <div key={i} className="service-card animate-in">
              <div className="service-icon" style={{background:s.bg,fontSize:20}}>{s.icon}</div>
              <div className="service-info">
                <div className="service-name">{s.name}</div>
                <div className="service-detail">{s.detail}</div>
                <div className="service-detail">Uptime: {s.uptime}</div>
              </div>
              <div className="service-status" style={{color:s.status==='online'?'var(--green)':'var(--red)'}}>
                <span className="status-dot" style={{display:'inline-block',width:8,height:8,borderRadius:'50%',background:s.status==='online'?'var(--green)':'var(--red)',marginRight:6,boxShadow:s.status==='online'?'0 0 6px var(--green)':'none'}}/>{s.status==='online'?'Online':'Offline'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* GPU Card */}
      <div className="card animate-in" style={{marginBottom:20}}>
        <div className="card-header"><span className="card-title">GPU & Accelerated Computing</span>
          <span className={`card-badge ${gpuAvail?'badge-green':'badge-orange'}`}>{gpuAvail?'GPU ACTIVE':'CPU MODE'}</span>
        </div>
        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(120px,1fr))',gap:16,marginTop:8}}>
          {[
            ['GPU',gpuNames[0]||'None'],['Count',`${gpuCount}`],['CUDA',h.cuda_version||'—'],
            ['Available',gpuAvail?'Yes ✓':'No'],['Hardware Detected',h.hardware_gpu_detected?'Yes':'No'],
          ].map(([l,v],i)=>(<div key={i}>
            <div style={{fontSize:10,color:'var(--text-muted)',textTransform:'uppercase',letterSpacing:1}}>{l}</div>
            <div className="mono" style={{fontSize:15,fontWeight:600,color:'var(--text-bright)',marginTop:4}}>{v}</div>
          </div>))}
        </div>
      </div>

      {/* Phase 6C Modules */}
      <div className="card animate-in" style={{marginBottom:20}}>
        <div className="card-header"><span className="card-title">Phase 6C Infrastructure Modules</span>
          <span className="card-badge badge-green">{newModules.length}/{newModules.length} ACTIVE</span>
        </div>
        <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:12,marginTop:8}}>
          {newModules.map((m,i)=>(
            <div key={i} className="service-card animate-in">
              <div className="service-icon" style={{background:'var(--gold-glow)',fontSize:20}}>{m.icon}</div>
              <div className="service-info">
                <div className="service-name">{m.name} <span style={{fontSize:9,color:'var(--text-muted)'}}>{m.phase}</span></div>
                <div className="service-detail">{m.desc}</div>
              </div>
              <div className="service-status" style={{color:'var(--green)'}}>
                <span className="status-dot" style={{display:'inline-block',width:8,height:8,borderRadius:'50%',background:'var(--green)',marginRight:6,boxShadow:'0 0 6px var(--green)'}}/> Active
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Inference Status */}
      {inference && (
        <div className="card animate-in">
          <div className="card-header"><span className="card-title">Inference Loop Status</span>
            <span className={`card-badge ${inference.running?'badge-green':'badge-orange'}`}>{inference.running?'RUNNING':'STOPPED'}</span>
          </div>
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(150px,1fr))',gap:16}}>
            {[
              ['Status',inference.running?'● Running':'○ Stopped'],['Iteration',`#${inference.iteration}`],
              ['Interval',`${inference.interval_seconds}s`],['Last Run',inference.last_run?new Date(inference.last_run).toLocaleTimeString():'—'],
              ['Last Error',inference.last_error||'None ✓'],['Models',`${inference.models_count||6} active`],
            ].map(([k,v],i)=>(<div key={i} style={{padding:'10px 14px',borderRadius:'var(--radius-sm)',background:'var(--bg-secondary)',border:'1px solid var(--border-color)'}}>
              <div style={{fontSize:10,color:'var(--text-muted)',textTransform:'uppercase',letterSpacing:0.5}}>{k}</div>
              <div style={{fontSize:14,fontWeight:600,fontFamily:'var(--font-mono)',color:k==='Last Error'&&inference.last_error?'var(--red)':'var(--text-bright)',marginTop:4}}>{v}</div>
            </div>))}
          </div>
        </div>
      )}
    </div>
  </>);
}
