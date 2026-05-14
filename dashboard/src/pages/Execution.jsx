import { executionEngine } from '../data/mockData';

export default function Execution() {
  const { cppEngine, recentOrders } = executionEngine;

  return (
    <>
      <div className="page-header">
        <h2>Execution Engine</h2>
        <p>C++ low-latency order routing, IBKR integration & latency monitoring</p>
      </div>
      <div className="page-body">
        {/* Connection Status */}
        <div className="kpi-grid" style={{ marginBottom: 20 }}>
          {[
            { label: 'Status', value: executionEngine.status.toUpperCase(), sub: `Broker: ${executionEngine.broker.toUpperCase()}` },
            { label: 'Mode', value: executionEngine.mode.toUpperCase(), sub: 'Port: 7497 (Paper)' },
            { label: 'Order Type', value: executionEngine.orderType.toUpperCase(), sub: 'Never market orders' },
            { label: 'Algorithm', value: executionEngine.algo.toUpperCase(), sub: `Max slip: ${executionEngine.maxSlippageBps} bps` },
          ].map((m, i) => (
            <div key={i} className="kpi-card animate-in">
              <div className="kpi-label">{m.label}</div>
              <div className="kpi-value" style={{ fontSize: 22 }}>{m.value}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{m.sub}</div>
            </div>
          ))}
        </div>

        <div className="grid-2" style={{ marginBottom: 16 }}>
          {/* C++ Engine Components */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">C++ Engine Components</span>
              <span className="card-badge badge-green">{cppEngine.compiled ? 'COMPILED' : 'NOT BUILT'}</span>
            </div>
            {cppEngine.components.map((c, i) => (
              <div key={i} style={{ padding: '14px 0', borderBottom: i < cppEngine.components.length - 1 ? '1px solid var(--border-color)' : 'none' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-bright)' }}>{c.name}</span>
                  <span className="card-badge badge-green" style={{ fontSize: 9 }}>{c.status.toUpperCase()}</span>
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{c.desc}</div>
              </div>
            ))}
            <div style={{ marginTop: 12, padding: '12px 0', borderTop: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>Build Info</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {[['Build System', 'CMake 3.20+'], ['Compiler', 'MSVC / GCC / Clang'], ['Target', 'order_router_demo'], ['Platform', 'Cross-platform']].map(([k, v], i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{k}</span>
                    <span className="mono" style={{ fontSize: 11 }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Latency Monitoring */}
          <div className="card animate-in">
            <div className="card-header">
              <span className="card-title">Latency Monitor</span>
              <span className="card-badge badge-blue">REAL-TIME</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginTop: 8 }}>
              {[
                { label: 'P50', value: cppEngine.latency.p50, color: 'var(--green)' },
                { label: 'P95', value: cppEngine.latency.p95, color: 'var(--orange)' },
                { label: 'P99', value: cppEngine.latency.p99, color: 'var(--red)' },
              ].map((l, i) => (
                <div key={i} style={{ textAlign: 'center', padding: 16, background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>{l.label}</div>
                  <div className="mono" style={{ fontSize: 28, fontWeight: 700, color: l.color, marginTop: 4 }}>{l.value}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{cppEngine.latency.unit}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>IBKR Connection</div>
              {[
                ['Host', executionEngine.ibkr.host],
                ['Port', executionEngine.ibkr.port],
                ['Client ID', executionEngine.ibkr.clientId],
                ['Max Latency', `${executionEngine.maxSlippageBps * 100} µs`],
              ].map(([k, v], i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border-color)' }}>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{k}</span>
                  <span className="mono" style={{ fontSize: 12, color: 'var(--text-bright)' }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent Orders */}
        <div className="card animate-in">
          <div className="card-header">
            <span className="card-title">Recent Orders</span>
            <span className="card-badge badge-gold">{recentOrders.length} orders</span>
          </div>
          <table className="data-table">
            <thead>
              <tr><th>ID</th><th>Time</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Type</th><th>Price</th><th>Latency</th><th>Status</th></tr>
            </thead>
            <tbody>
              {recentOrders.map(o => (
                <tr key={o.id}>
                  <td className="mono" style={{ fontSize: 11 }}>{o.id}</td>
                  <td className="mono" style={{ fontSize: 12 }}>{o.time}</td>
                  <td style={{ fontSize: 12 }}>{o.symbol}</td>
                  <td><span style={{ color: o.side === 'BUY' ? 'var(--green)' : 'var(--red)', fontWeight: 600, fontSize: 12 }}>{o.side}</span></td>
                  <td className="mono">{o.qty}</td>
                  <td style={{ fontSize: 12 }}>{o.type}</td>
                  <td className="mono">${o.price.toFixed(2)}</td>
                  <td className="mono" style={{ color: o.latency < 20 ? 'var(--green)' : o.latency < 50 ? 'var(--orange)' : 'var(--red)' }}>{o.latency}µs</td>
                  <td><span className={`card-badge ${o.status === 'filled' ? 'badge-green' : o.status === 'cancelled' ? 'badge-red' : 'badge-orange'}`}>{o.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
