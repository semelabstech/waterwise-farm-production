import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

export default function ReportPage({ overview, weather, recommendations, regionInfo }) {
  if (!overview || !regionInfo) return null

  const { kpis, stress_distribution } = overview
  const today = new Date().toLocaleDateString('fr-FR', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  })

  const pieData = stress_distribution
    ? Object.entries(stress_distribution).map(([label, info]) => ({
        name: label,
        value: info.percentage,
        color: info.color,
      }))
    : []

  const handlePrint = () => window.print()

  const handleExportCSV = () => {
    if (!recommendations?.recommendations) return
    const recs = recommendations.recommendations
    const headers = ['zone_id', 'stress_mean', 'stress_label', 'priority', 'volume_recommended_mm', 'score']
    const csv = [
      headers.join(','),
      ...recs.map(r => headers.map(h => r[h]).join(','))
    ].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `rapport_irrigation_${regionInfo.name}_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
  }

  // Weather summary (last 30 days)
  const last30 = weather?.slice(-30) || []
  const avgTemp = last30.length > 0 ? (last30.reduce((s, d) => s + d.temperature, 0) / last30.length).toFixed(1) : '—'
  const totalPrecip = last30.length > 0 ? last30.reduce((s, d) => s + d.precipitation, 0).toFixed(1) : '—'
  const avgEt0 = last30.length > 0 ? (last30.reduce((s, d) => s + d.et0, 0) / last30.length).toFixed(2) : '—'

  return (
    <div>
      <div className="report-header">
        <h1>📄 Rapport d'Irrigation — {regionInfo.name}</h1>
        <p>{today}</p>
      </div>

      {/* Summary Stats */}
      <div className="report-summary-grid">
        <div className="report-stat">
          <div className="value">{kpis.water_savings}%</div>
          <div className="label">Économie d'eau réalisée</div>
        </div>
        <div className="report-stat">
          <div className="value">{kpis.patches_analyzed}</div>
          <div className="label">Zones analysées</div>
        </div>
        <div className="report-stat">
          <div className="value">{kpis.severe_zones}</div>
          <div className="label">Zones en stress sévère</div>
        </div>
        <div className="report-stat">
          <div className="value">{kpis.avg_et0}</div>
          <div className="label">ET0 moyen (mm/j)</div>
        </div>
        <div className="report-stat">
          <div className="value">{kpis.savings_mm}</div>
          <div className="label">Eau économisée (mm)</div>
        </div>
        <div className="report-stat">
          <div className="value">{kpis.num_sensors}</div>
          <div className="label">Capteurs IoT actifs</div>
        </div>
      </div>

      {/* Region Details */}
      <div className="report-section">
        <div className="card">
          <div className="card-title"><span className="icon">📍</span> Informations de la Région</div>
          <table className="data-table">
            <tbody>
              <tr><td style={{color:'var(--text-secondary)', width: '200px'}}>Région</td><td style={{fontWeight: 600}}>{regionInfo.name}</td></tr>
              <tr><td style={{color:'var(--text-secondary)'}}>Climat</td><td>{regionInfo.climate}</td></tr>
              <tr><td style={{color:'var(--text-secondary)'}}>Type de sol</td><td>{regionInfo.soil}</td></tr>
              <tr><td style={{color:'var(--text-secondary)'}}>Cultures principales</td><td>{regionInfo.crops?.join(', ')}</td></tr>
              <tr><td style={{color:'var(--text-secondary)'}}>Description</td><td>{regionInfo.description}</td></tr>
              <tr><td style={{color:'var(--text-secondary)'}}>Coordonnées</td><td>{regionInfo.center?.lat}°N, {regionInfo.center?.lon}°E</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Stress + Weather */}
      <div className="grid-2 report-section">
        <div className="card">
          <div className="card-title"><span className="icon">🎯</span> Distribution du Stress</div>
          {pieData.length > 0 && (
            <div className="chart-container">
              <ResponsiveContainer width="55%" height={200}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={45} outerRadius={80} paddingAngle={3} dataKey="value" stroke="none">
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{background:'#0e1c36', border:'1px solid rgba(255,255,255,0.1)', borderRadius:10, fontSize:'0.8rem'}} formatter={(val) => [`${val}%`, '']} />
                </PieChart>
              </ResponsiveContainer>
              <div className="pie-legend">
                {pieData.map((entry, i) => (
                  <div className="pie-legend-item" key={i}>
                    <div className="pie-legend-dot" style={{background: entry.color}}></div>
                    <span style={{color: 'var(--text-secondary)', fontSize: '0.78rem'}}>{entry.name}</span>
                    <span className="pie-legend-value">{entry.value}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title"><span className="icon">🌤️</span> Résumé Météo (30 derniers jours)</div>
          <table className="data-table">
            <tbody>
              <tr><td style={{color:'var(--text-secondary)'}}>Température moyenne</td><td style={{fontWeight: 600}}>{avgTemp}°C</td></tr>
              <tr><td style={{color:'var(--text-secondary)'}}>Précipitations totales</td><td style={{fontWeight: 600}}>{totalPrecip} mm</td></tr>
              <tr><td style={{color:'var(--text-secondary)'}}>ET0 moyen</td><td style={{fontWeight: 600}}>{avgEt0} mm/j</td></tr>
              <tr><td style={{color:'var(--text-secondary)'}}>Humidité sol moyenne</td><td style={{fontWeight: 600}}>{kpis.avg_moisture}%</td></tr>
            </tbody>
          </table>

          <div className="interpretation" style={{marginTop: 14}}>
            <strong>Conclusion :</strong> {kpis.water_savings > 50 
              ? `L'irrigation de précision a permis une économie exceptionnelle de ${kpis.water_savings}% d'eau par rapport à l'irrigation uniforme.`
              : `L'irrigation de précision a permis une économie de ${kpis.water_savings}% d'eau. Des optimisations supplémentaires sont possibles.`
            }
          </div>
        </div>
      </div>

      {/* Irrigation Schedule */}
      {recommendations?.schedule && recommendations.schedule.length > 0 && (
        <div className="report-section">
          <div className="card">
            <div className="card-title"><span className="icon">📋</span> Planning d'Irrigation Recommandé</div>
            <table className="data-table">
              <thead>
                <tr><th>Zone</th><th>Heure</th><th>Durée</th><th>Volume</th><th>Priorité</th></tr>
              </thead>
              <tbody>
                {recommendations.schedule.map((s, i) => (
                  <tr key={i}>
                    <td style={{fontWeight:600}}>Zone {s.zone_id}</td>
                    <td>{s.start_time}</td>
                    <td>{s.duration_min} min</td>
                    <td>{s.volume_mm} mm</td>
                    <td><span className={`badge ${
                      s.priority === 'Urgente' ? 'badge-red' : 
                      s.priority === 'Haute' ? 'badge-orange' : 
                      s.priority === 'Moyenne' ? 'badge-yellow' : 'badge-green'
                    }`}>{s.priority}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Bilan Hydrique */}
      <div className="report-section">
        <div className="card">
          <div className="card-title"><span className="icon">💰</span> Bilan Hydrique</div>
          <div className="grid-3" style={{gap: 12}}>
            <div className="report-stat" style={{marginBottom: 0}}>
              <div className="value" style={{fontSize: '1.4rem'}}>{recommendations?.savings?.total_precision_mm || '—'}</div>
              <div className="label">Irrigation ciblée (mm)</div>
            </div>
            <div className="report-stat" style={{marginBottom: 0}}>
              <div className="value" style={{fontSize: '1.4rem', opacity: 0.5, textDecoration: 'line-through'}}>{recommendations?.savings?.total_uniform_mm || '—'}</div>
              <div className="label">Irrigation uniforme (mm)</div>
            </div>
            <div className="report-stat" style={{marginBottom: 0}}>
              <div className="value" style={{fontSize: '1.4rem'}}>{recommendations?.savings?.savings_mm || '—'}</div>
              <div className="label">Eau économisée (mm)</div>
            </div>
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div style={{display:'flex', gap:12, marginTop:10}}>
        <button className="btn btn-primary" onClick={handlePrint}>
          🖨️ Imprimer / PDF
        </button>
        <button className="btn btn-outline" onClick={handleExportCSV}>
          📥 Exporter CSV
        </button>
      </div>
    </div>
  )
}
