export default function Sidebar({ currentPage, onPageChange, regionInfo, appMode, setAppMode }) {
  const items = [
    { id: 'planner', icon: '🌍', label: 'Planificateur Culture' },
    { id: 'home', icon: '📊', label: 'Tableau de Bord' },
    { id: 'iot', icon: '📡', label: 'Capteurs IoT & IA' },
    { id: 'map', icon: '🗺️', label: 'Carte Interactive' },
    { id: 'stress', icon: '🔬', label: 'Stress Hydrique' },
    { id: 'forecast', icon: '🌤️', label: 'Météo & Prévisions' },
    { id: 'recommendations', icon: '💧', label: "Plan d'Irrigation" },
    { id: 'report', icon: '📄', label: 'Rapport' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h1>🌾 WaterWiseFarm</h1>
        <div className="subtitle">Système Intelligent — Maroc</div>
      </div>

      {regionInfo && (
        <div className="sidebar-region">
          <div className="sidebar-region-name">
            📍 {regionInfo.name}
          </div>
          <div className="sidebar-region-meta">
            <span className="sidebar-region-tag">☀️ {regionInfo.climate}</span>
            <span className="sidebar-region-tag">🌱 {regionInfo.soil}</span>
          </div>
        </div>
      )}

      <nav className="sidebar-nav">
        {items.map(item => (
          <div
            key={item.id}
            className={`nav-item ${currentPage === item.id ? 'active' : ''}`}
            onClick={() => onPageChange(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ))}
      </nav>

      <div style={{ marginTop: "auto", padding: "1rem" }}>
        <button 
          onClick={() => setAppMode('landing')}
          style={{ width: "100%", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", color: "#FCA5A5", padding: "10px", borderRadius: "8px", cursor: "pointer", fontSize: "0.9rem", fontWeight: "600" }}
        >
          🔄 Changer de Mode
        </button>
      </div>

      <div className="sidebar-footer">
        <span>WaterWiseFarm v2.0<br />Maroc 2026</span>
      </div>
    </aside>
  )
}
