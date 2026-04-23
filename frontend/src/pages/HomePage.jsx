import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

export default function HomePage({ overview, alerts, onPageChange }) {
  if (!overview) return null
  const { kpis, stress_distribution, region } = overview

  // Prepare pie data
  const pieData = stress_distribution
    ? Object.entries(stress_distribution).map(([label, info]) => ({
        name: label,
        value: info.percentage,
        color: info.color,
      }))
    : []

  return (
    <div>
      <div className="page-header">
        <h1>📊 Tableau de Bord</h1>
        <p>Vue d'ensemble de la situation agricole — {region?.name}</p>
      </div>

      {/* Region Info Card */}
      {region && (
        <div className="region-info-card">
          <div className="region-info-left">
            <h2>📍 {region.name}</h2>
            <p>{region.description}</p>
            <div className="region-tags">
              <span className="region-tag"><span className="tag-icon">☀️</span> {region.climate}</span>
              <span className="region-tag"><span className="tag-icon">🌱</span> {region.soil}</span>
              {region.crops?.map((c, i) => (
                <span className="region-tag" key={i}><span className="tag-icon">🌾</span> {c}</span>
              ))}
            </div>
          </div>
          <div className="region-info-right">
            <div className="region-stat">
              <span className="region-stat-label">Capteurs IoT</span>
              <span className="region-stat-value">{kpis.num_sensors}</span>
            </div>
            <div className="region-stat">
              <span className="region-stat-label">Zones analysées</span>
              <span className="region-stat-value">{kpis.patches_analyzed}</span>
            </div>
            <div className="region-stat">
              <span className="region-stat-label">Horizon prévision</span>
              <span className="region-stat-value">{kpis.forecast_horizon}h</span>
            </div>
          </div>
        </div>
      )}

      {/* Main KPIs */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-value" style={{
            background: 'linear-gradient(135deg, #4CAF50, #81C784)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
          }}>{kpis.water_savings}%</div>
          <div className="kpi-label">💰 Économie d'eau réalisée</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{kpis.avg_et0}</div>
          <div className="kpi-label">🌡️ ET0 moyen (mm/j)</div>
          <div className={`kpi-delta ${kpis.last_7d_et0 > kpis.avg_et0 ? 'negative' : 'positive'}`}>
            {kpis.last_7d_et0 > kpis.avg_et0 ? '↑' : '↓'} {kpis.last_7d_et0} mm/j (7 derniers jours)
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value" style={{
            background: kpis.severe_zones > 0 
              ? 'linear-gradient(135deg, #ef5350, #e57373)' 
              : 'linear-gradient(135deg, #4CAF50, #81C784)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'
          }}>{kpis.severe_zones}</div>
          <div className="kpi-label">🚨 Zones en stress sévère</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{kpis.avg_moisture}%</div>
          <div className="kpi-label">💧 Humidité sol moyenne</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value" style={{fontSize: '1.5rem'}}>{kpis.next_irrigation}</div>
          <div className="kpi-label">⏰ Prochaine irrigation</div>
        </div>
      </div>

      {/* Alerts */}
      {alerts && alerts.length > 0 && (
        <div className="card" style={{padding: '18px 22px'}}>
          <div className="card-title"><span className="icon">🔔</span> Alertes & Notifications</div>
          <div className="alerts-grid">
            {alerts.map((alert, i) => (
              <div key={i} className={`alert-card ${alert.type}`} onClick={() => onPageChange(alert.page)}>
                <div className="alert-icon">{alert.icon}</div>
                <div className="alert-content">
                  <div className="alert-title">{alert.title}</div>
                  <div className="alert-message">{alert.message}</div>
                </div>
                <button className="alert-action" onClick={(e) => { e.stopPropagation(); onPageChange(alert.page); }}>
                  {alert.action} →
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Bottom row: Stress Distribution + Quick Actions */}
      <div className="grid-7030">
        <div className="card">
          <div className="card-title"><span className="icon">🎯</span> Distribution du Stress Hydrique</div>
          {pieData.length > 0 && (
            <div className="chart-container">
              <ResponsiveContainer width="60%" height={240}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={95}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                  >
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: '#0e1c36',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: 10,
                      fontSize: '0.8rem',
                    }}
                    formatter={(val) => [`${val}%`, '']}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="pie-legend">
                {pieData.map((entry, i) => (
                  <div className="pie-legend-item" key={i}>
                    <div className="pie-legend-dot" style={{ background: entry.color }}></div>
                    <span style={{ color: 'var(--text-secondary)' }}>{entry.name}</span>
                    <span className="pie-legend-value">{entry.value}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="interpretation">
            <strong>Interprétation :</strong> {(() => {
              const severe = stress_distribution?.['Stress Sévère']?.percentage || 0
              const moderate = stress_distribution?.['Stress Modéré']?.percentage || 0
              const normal = stress_distribution?.['Normal']?.percentage || 0
              if (severe > 5) return `Alerte : ${severe}% de la zone est en stress sévère. Action immédiate recommandée pour les cultures de ${region?.crops?.[0] || 'la zone'}.`
              if (moderate > 15) return `Surveillance nécessaire : ${moderate}% de stress modéré détecté. Ajustez l'irrigation dans les prochaines 24h.`
              return `Situation favorable : ${normal}% de la zone est en bonne santé. Continuez l'irrigation de précision.`
            })()}
          </div>
        </div>

        <div>
          <div className="card">
            <div className="card-title"><span className="icon">⚡</span> Actions Rapides</div>
            <div className="quick-actions" style={{gridTemplateColumns: '1fr'}}>
              <button className="quick-action-btn" onClick={() => onPageChange('recommendations')}>
                <span className="qa-icon">💧</span> Voir Plan d'Irrigation
              </button>
              <button className="quick-action-btn" onClick={() => onPageChange('map')}>
                <span className="qa-icon">🗺️</span> Ouvrir la Carte
              </button>
              <button className="quick-action-btn" onClick={() => onPageChange('stress')}>
                <span className="qa-icon">🔬</span> Analyser le Stress
              </button>
              <button className="quick-action-btn" onClick={() => onPageChange('forecast')}>
                <span className="qa-icon">🌤️</span> Voir la Météo
              </button>
              <button className="quick-action-btn" onClick={() => onPageChange('report')}>
                <span className="qa-icon">📄</span> Générer un Rapport
              </button>
            </div>
          </div>

          {/* Water savings summary */}
          <div className="card">
            <div className="card-title"><span className="icon">💰</span> Bilan Hydrique</div>
            <div className="region-stat" style={{marginBottom: 8}}>
              <span className="region-stat-label">Irrigation précision</span>
              <span className="region-stat-value" style={{color: 'var(--accent-light)'}}>{kpis.total_precision_mm} mm</span>
            </div>
            <div className="region-stat" style={{marginBottom: 8}}>
              <span className="region-stat-label">Irrigation uniforme</span>
              <span className="region-stat-value" style={{color: 'var(--text-secondary)', textDecoration: 'line-through'}}>{kpis.total_uniform_mm} mm</span>
            </div>
            <div className="region-stat">
              <span className="region-stat-label" style={{fontWeight: 600}}>Eau économisée</span>
              <span className="region-stat-value" style={{color: '#81C784', fontSize: '1.1rem'}}>{kpis.savings_mm} mm</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
