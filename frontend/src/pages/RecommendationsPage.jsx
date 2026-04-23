import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell
} from 'recharts'

export default function RecommendationsPage({ data, regionInfo }) {
  const [tab, setTab] = useState('chart')
  if (!data) return null

  const { recommendations, savings, schedule } = data

  const priorityBadge = (p) => {
    const map = {
      'Basse': 'badge-green',
      'Moyenne': 'badge-yellow',
      'Haute': 'badge-orange',
      'Urgente': 'badge-red',
    }
    return <span className={`badge ${map[p] || 'badge-green'}`}>{p}</span>
  }

  const handleExport = () => {
    const headers = ['zone_id', 'stress_mean', 'priority', 'volume_recommended_mm', 'score']
    const csv = [
      headers.join(','),
      ...recommendations.map(r => headers.map(h => r[h]).join(','))
    ].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `irrigation_${regionInfo?.name || 'plan'}.csv`
    a.click()
  }

  const urgentCount = recommendations?.filter(r => r.priority === 'Urgente' || r.priority === 'Haute').length || 0

  return (
    <div>
      <div className="page-header">
        <h1>💧 Plan d'Irrigation — {regionInfo?.name || 'Maroc'}</h1>
        <p>Recommandations optimisées par analyse satellite, météo et capteurs IoT</p>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-value" style={{
            background:'linear-gradient(135deg, #4CAF50, #81C784)',
            WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent'
          }}>{savings.savings_percent}%</div>
          <div className="kpi-label">💰 Économie d'eau</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{savings.total_precision_mm}</div>
          <div className="kpi-label">Irrigation ciblée (mm)</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value" style={{textDecoration: 'line-through', opacity: 0.5}}>{savings.total_uniform_mm}</div>
          <div className="kpi-label">Irrigation uniforme (mm)</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value" style={{
            background:'linear-gradient(135deg, #42A5F5, #90CAF9)',
            WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent'
          }}>{savings.savings_mm}</div>
          <div className="kpi-label">💧 Eau économisée (mm)</div>
        </div>
      </div>

      {urgentCount > 0 && (
        <div className="interpretation" style={{borderLeftColor: 'var(--red)', background: 'rgba(239,83,80,0.06)', marginBottom: 18}}>
          <strong>⚠ Attention :</strong> {urgentCount} zone(s) nécessitent une irrigation urgente ou haute priorité. 
          Consultez le planning ci-dessous pour les détails.
        </div>
      )}

      <div className="tabs">
        <div className={`tab ${tab === 'chart' ? 'active' : ''}`} onClick={() => setTab('chart')}>📊 Volumes par zone</div>
        <div className={`tab ${tab === 'schedule' ? 'active' : ''}`} onClick={() => setTab('schedule')}>📋 Planning</div>
        <div className={`tab ${tab === 'details' ? 'active' : ''}`} onClick={() => setTab('details')}>📈 Détails</div>
      </div>

      {tab === 'chart' && (
        <div className="card">
          <div className="card-title"><span className="icon">📊</span> Volume d'irrigation recommandé par zone</div>
          <ResponsiveContainer width="100%" height={380}>
            <BarChart data={recommendations} margin={{top:20, right:20, bottom:20, left:0}}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="zone_id" tick={{fontSize:9}} interval={0} angle={-45} textAnchor="end" height={50} />
              <YAxis tick={{fontSize:10}} label={{value:'mm', angle:-90, position:'insideLeft', style:{fontSize:11, fill:'#aaa'}}} />
              <Tooltip
                contentStyle={{background:'#0e1c36', border:'1px solid rgba(255,255,255,0.1)', borderRadius:10}}
                formatter={(val, name, props) => [`${val} mm (${props.payload.priority})`, 'Volume']}
              />
              <ReferenceLine y={30} stroke="#ef5350" strokeDasharray="6 3" label={{value:'Uniforme (30mm)', fill:'#ef5350', fontSize:10, position:'right'}} />
              <Bar dataKey="volume_recommended_mm" radius={[4,4,0,0]} name="Volume">
                {recommendations.map((entry, i) => (
                  <Cell key={i} fill={entry.color} opacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {tab === 'schedule' && (
        <div className="card">
          <div className="card-title"><span className="icon">📋</span> Planning d'irrigation (05:00 – 08:00)</div>
          {schedule.length > 0 ? (
            <table className="data-table">
              <thead>
                <tr><th>Zone</th><th>Heure</th><th>Durée</th><th>Volume</th><th>Priorité</th></tr>
              </thead>
              <tbody>
                {schedule.map((s, i) => (
                  <tr key={i}>
                    <td style={{fontWeight:600}}>Zone {s.zone_id}</td>
                    <td>{s.start_time}</td>
                    <td>{s.duration_min} min</td>
                    <td>{s.volume_mm} mm</td>
                    <td>{priorityBadge(s.priority)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p style={{color:'var(--accent-light)', textAlign:'center', padding:40}}>
              ✅ Aucune irrigation nécessaire aujourd'hui !
            </p>
          )}
        </div>
      )}

      {tab === 'details' && (
        <div className="card">
          <div className="card-title"><span className="icon">📈</span> Détails par zone</div>
          <div style={{overflowX:'auto'}}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Zone</th><th>Stress</th><th>Niveau</th><th>ET0</th>
                  <th>Humidité sol</th><th>Score</th><th>Priorité</th><th>Volume</th>
                </tr>
              </thead>
              <tbody>
                {recommendations.slice(0, 30).map((r, i) => (
                  <tr key={i}>
                    <td style={{fontWeight:600}}>Zone {r.zone_id}</td>
                    <td>{r.stress_mean}</td>
                    <td><span className="badge" style={{background:`${r.color}22`, color:r.color, border:`1px solid ${r.color}44`}}>{r.stress_label}</span></td>
                    <td>{r.et0_predicted}</td>
                    <td>{r.soil_moisture}%</td>
                    <td style={{fontWeight:700}}>{r.score}</td>
                    <td>{priorityBadge(r.priority)}</td>
                    <td style={{fontWeight:600}}>{r.volume_recommended_mm} mm</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div style={{display:'flex', gap:12, marginTop:18}}>
        <button className="btn btn-primary" onClick={handleExport}>
          📥 Exporter CSV
        </button>
        <button className="btn btn-outline" onClick={() => window.print()}>
          🖨️ Imprimer
        </button>
      </div>
    </div>
  )
}
