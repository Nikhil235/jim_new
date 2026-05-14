import { infraServices, gpuInfo, executionEngine, healthMonitor } from '../data/mockData';

export default function Infrastructure() {
  return (
    <>
      <div className="page-header">
        <h2>Infrastructure</h2>
        <p>Docker services, GPU/RAPIDS, Health Monitor, C++ engine & SLA tracking</p>
      </div>
      <div className="page-body">
        {/* Health Monitor KPIs */}
        <div className="kpi-grid" style={{ marginBottom: 20 }}>
          {[
            { label: 'System Status', value: healthMonitor.overallStatus.toUpperCase(), sub: `SLA: ${healthMonitor.slaCompliant ? '✓ Compliant' : '✗ Violation'}` },
            { label: 'Uptime', value: `${healthMonitor.uptimePercent}%`, sub: `Target: 99.9% SLA` },
            { label: 'CPU Usage', value: `${healthMonitor.system.cpuPercent}%`, sub: 'System average' },
            { label: 'Memory', value: `${healthMonitor.system.memoryPercent}%`, sub: 'Virtual memory' },
            { label: 'Disk', value: `${healthMonitor.system.diskPercent}%`, sub: 'Storage used' },
            { label: 'Health Checks', value: `${healthMonitor.successRate}%`, sub: `${healthMonitor.totalChecks} total • ${healthMonitor.failedChecks} failed` },
          ].map((m, i) => (
            <div key={i} className="kpi-card animate-in">
              <div className="kpi-label">{m.label}</div>
              <div className="kpi-value" style={{ fontSize: 22 }}>{m.value}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{m.sub}</div>
            </div>
          ))}
        </div>

        {/* GPU Card */}
        <div className="card animate-in" style={{ marginBottom: 20 }}>
          <div className="card-header">
            <span className="card-title">GPU & Accelerated Computing</span>
            <span className="card-badge badge-green">{gpuInfo.pytorch ? 'PyTorch CUDA ✓' : 'CPU Only'}</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 16, marginTop: 8 }}>
            {[['GPU', gpuInfo.name], ['VRAM', gpuInfo.vram], ['CUDA', gpuInfo.cudaVersion], ['Driver', gpuInfo.driver], ['Compute Cap', gpuInfo.computeCapability], ['Utilization', `${gpuInfo.utilization}%`], ['Temperature', `${gpuInfo.temperature}°C`]].map(([l, v], i) => (
              <div key={i}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>{l}</div>
                <div className="mono" style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-bright)', marginTop: 4 }}>{v}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>GPU Utilization</span>
              <span className="mono" style={{ fontSize: 11 }}>{gpuInfo.utilization}%</span>
            </div>
            <div className="progress-bar" style={{ height: 8 }}>
              <div className="progress-fill" style={{ width: `${gpuInfo.utilization}%`, background: 'linear-gradient(90deg, var(--green), var(--gold-primary))' }} />
            </div>
          </div>
          <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12 }}>
            {[['RAPIDS cuDF', gpuInfo.rapids, '100x DataFrames'], ['CuPy', gpuInfo.cupy, 'GPU arrays'], ['cuSignal', gpuInfo.cusignal, 'Signal processing'], ['cuDNN', gpuInfo.cudnn, 'Deep learning']].map(([name, available, desc], i) => (
              <div key={i} style={{ padding: 10, background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: available ? 'var(--green)' : 'var(--text-muted)' }}>{available ? '✓' : '✗'} {name}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="grid-2" style={{ marginBottom: 16 }}>
          {/* Endpoint Latency */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Endpoint Latency Monitor</span>
              <span className="card-badge badge-blue">SLA TRACKING</span>
            </div>
            <table className="data-table">
              <thead><tr><th>Endpoint</th><th>p50</th><th>p95</th><th>p99</th><th>Samples</th></tr></thead>
              <tbody>
                {healthMonitor.latencyEndpoints.map((e, i) => (
                  <tr key={i}>
                    <td className="mono" style={{ fontSize: 12, color: 'var(--gold-primary)' }}>{e.endpoint}</td>
                    <td className="mono" style={{ color: 'var(--green)' }}>{e.p50}ms</td>
                    <td className="mono" style={{ color: 'var(--orange)' }}>{e.p95}ms</td>
                    <td className="mono" style={{ color: 'var(--red)' }}>{e.p99}ms</td>
                    <td className="mono">{e.samples}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ marginTop: 12, borderTop: '1px solid var(--border-color)', paddingTop: 12 }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Service Health</div>
              {healthMonitor.services.map((s, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-color)' }}>
                  <span style={{ fontSize: 12 }}>{s.name}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className="mono" style={{ fontSize: 11 }}>{s.latencyMs}ms</span>
                    <span style={{ color: s.status === 'healthy' ? 'var(--green)' : 'var(--red)', fontSize: 11, fontWeight: 600 }}>{s.status === 'healthy' ? '✓' : '✗'} {s.status.toUpperCase()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* C++ Engine */}
          <div className="card animate-in">
            <div className="card-header"><span className="card-title">C++ Execution Engine</span><span className="card-badge badge-green">COMPILED</span></div>
            {executionEngine.cppEngine.components.map((c, i) => (
              <div key={i} style={{ padding: '12px 0', borderBottom: i < executionEngine.cppEngine.components.length - 1 ? '1px solid var(--border-color)' : 'none' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)' }}>{c.name}</span>
                  <span className="card-badge badge-green" style={{ fontSize: 9 }}>{c.status.toUpperCase()}</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{c.desc}</div>
              </div>
            ))}
            <div style={{ marginTop: 12, padding: '10px 0', borderTop: '1px solid var(--border-color)', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
              {[
                { label: 'P50', value: `${executionEngine.cppEngine.latency.p50}µs`, color: 'var(--green)' },
                { label: 'P95', value: `${executionEngine.cppEngine.latency.p95}µs`, color: 'var(--orange)' },
                { label: 'P99', value: `${executionEngine.cppEngine.latency.p99}µs`, color: 'var(--red)' },
              ].map((l, i) => (
                <div key={i} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{l.label}</div>
                  <div className="mono" style={{ fontSize: 16, fontWeight: 700, color: l.color }}>{l.value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Docker Services */}
        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Docker Services</span>
            <span className="card-badge badge-green">{infraServices.filter(s => s.status === 'online').length}/{infraServices.length} Online</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 8 }}>
            {infraServices.map((s, i) => (
              <div key={i} className="service-card animate-in">
                <div className="service-icon" style={{ background: s.bg, fontSize: 20 }}>{s.icon}</div>
                <div className="service-info">
                  <div className="service-name">{s.name} <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>v{s.version}</span></div>
                  <div className="service-detail">:{s.port} • {s.detail}</div>
                  <div className="service-detail">Memory: {s.memory} • Uptime: {s.uptime}</div>
                </div>
                <div className="service-status" style={{ color: s.status === 'online' ? 'var(--green)' : 'var(--red)' }}>
                  <span className="status-dot" style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: s.status === 'online' ? 'var(--green)' : 'var(--red)', marginRight: 6, boxShadow: s.status === 'online' ? '0 0 6px var(--green)' : 'none' }} />
                  {s.status === 'online' ? 'Online' : 'Offline'}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
