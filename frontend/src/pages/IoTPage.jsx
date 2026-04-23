import React, { useState, useEffect } from 'react'

export default function IoTPage({ selectedRegion, appMode, userLocation }) {
  const [sensors, setSensors] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let queryParams = `region=${selectedRegion}`
    if (appMode === 'farmer' && userLocation) {
        queryParams = `region=custom&lat=${userLocation.lat}&lon=${userLocation.lon}`
    }
    fetch(`/api/iot?${queryParams}`)
      .then(res => res.json())
      .then(data => {
        setSensors(data.sensors || [])
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }, [selectedRegion, appMode, userLocation])

  if (loading) {
    return <div className="page-container"><div className="loading-spinner"></div></div>
  }

  const anomalousSensors = sensors.filter(s => s.is_anomaly)
  const normalSensors = sensors.filter(s => !s.is_anomaly)

  return (
    <div className="page-container fade-in" style={{ animation: "fadeIn 0.5s ease-out" }}>
      <div className="page-header" style={{
        background: "linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
        padding: "2rem",
        borderRadius: "16px",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.2)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(255, 255, 255, 0.05)",
        marginBottom: "2rem"
      }}>
        <div>
          <h2 style={{ fontSize: "2.2rem", fontWeight: "800", background: "linear-gradient(90deg, #60A5FA, #34D399)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", margin: "0 0 0.5rem 0" }}>
            <span style={{ WebkitTextFillColor: "initial", marginRight: "10px" }}>📡</span>Réseau IoT & Intelligence Artificielle
          </h2>
          <p style={{ color: "#94A3B8", fontSize: "1.1rem", margin: 0, maxWidth: "800px" }}>
            Surveillance micro-climatique continue. Le moteur Autoencodeur LSTM analyse chaque flux de capteur en temps réel pour détecter les anomalies structurelles, matérielles, ou climatiques.
          </p>
        </div>
      </div>

      <div className="kpi-grid" style={{ marginBottom: "3rem", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "1.5rem" }}>
        <div className="kpi-card" style={{ background: "rgba(30, 41, 59, 0.5)", border: "1px solid rgba(255, 255, 255, 0.05)", borderRadius: "16px", padding: "1.5rem", boxShadow: "0 4px 6px rgba(0,0,0,0.1)" }}>
          <div className="kpi-title" style={{ color: "#94A3B8", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "0.5rem" }}>Total Capteurs Actifs</div>
          <div className="kpi-value" style={{ fontSize: "2.5rem", fontWeight: "700", color: "#F8FAFC" }}>{sensors.length}</div>
        </div>
        <div className="kpi-card error-card" style={{ 
          background: anomalousSensors.length > 0 ? "rgba(220, 38, 38, 0.1)" : "rgba(30, 41, 59, 0.5)", 
          border: anomalousSensors.length > 0 ? "1px solid rgba(239, 68, 68, 0.3)" : "1px solid rgba(255, 255, 255, 0.05)", 
          borderRadius: "16px", padding: "1.5rem", boxShadow: anomalousSensors.length > 0 ? "0 4px 20px rgba(220, 38, 38, 0.15)" : "0 4px 6px rgba(0,0,0,0.1)" }}>
          <div className="kpi-title" style={{ color: anomalousSensors.length > 0 ? "#FCA5A5" : "#94A3B8", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "0.5rem" }}>
            Anomalies Détectées (Score IA)
          </div>
          <div className="kpi-value" style={{ fontSize: "2.5rem", fontWeight: "700", color: anomalousSensors.length > 0 ? "#EF4444" : "#F8FAFC" }}>
            {anomalousSensors.length}
          </div>
        </div>
      </div>

      <h3 style={{ marginBottom: "1.5rem", fontSize: "1.5rem", fontWeight: "600", color: "#E2E8F0" }}>Matrice des Capteurs</h3>
      
      {sensors.length === 0 ? (
        <div style={{ background: "rgba(30, 41, 59, 0.5)", padding: "3rem", borderRadius: "16px", textAlign: "center", color: "#94A3B8" }}>
          Aucune donnée télémétrique disponible pour ce secteur.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1.5rem" }}>
          {sensors.map((sensor, idx) => {
            const isCritical = sensor.soil_moisture < 20;
            const isAnomaly = sensor.is_anomaly;
            
            return (
              <div key={idx} style={{
                background: "rgba(30, 41, 59, 0.7)",
                borderRadius: "16px",
                border: "1px solid rgba(255, 255, 255, 0.05)",
                borderTop: `4px solid ${isAnomaly ? '#EF4444' : isCritical ? '#F59E0B' : '#10B981'}`,
                padding: "1.5rem",
                position: "relative",
                overflow: "hidden",
                transition: "transform 0.2s, box-shadow 0.2s",
                boxShadow: isAnomaly ? "0 4px 24px rgba(239, 68, 68, 0.15)" : "0 4px 12px rgba(0,0,0,0.05)",
                transform: isAnomaly ? "scale(1.02)" : "scale(1)",
                animation: isAnomaly ? "pulse-border 2s infinite" : "none"
              }}>
                {isAnomaly && (
                  <div style={{ position: "absolute", top: 0, right: 0, bottom: 0, left: 0, background: "radial-gradient(circle at top right, rgba(239, 68, 68, 0.1), transparent 70%)", pointerEvents: "none" }} />
                )}
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.2rem', position: "relative" }}>
                  <h4 style={{ margin: 0, fontSize: "1.2rem", fontWeight: "600", color: "#F8FAFC", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span>🖲️</span> {sensor.sensor_id}
                  </h4>
                  {isAnomaly ? (
                    <span style={{ background: "rgba(239, 68, 68, 0.2)", color: "#FCA5A5", padding: "0.3rem 0.8rem", borderRadius: "999px", fontSize: "0.75rem", fontWeight: "700", border: "1px solid rgba(239, 68, 68, 0.4)", display: "flex", alignItems: "center", gap: "0.3rem" }}>
                      <span className="pulse-dot" style={{ width: "6px", height: "6px", background: "#EF4444", borderRadius: "50%", display: "inline-block" }}></span>
                      ANOMALIE
                    </span>
                  ) : (
                    <span style={{ color: "#94A3B8", fontSize: "0.85rem", background: "rgba(15, 23, 42, 0.5)", padding: "0.3rem 0.6rem", borderRadius: "8px" }}>
                      ⏱️ {new Date(sensor.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  )}
                </div>
                
                <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginBottom: "1.5rem" }}>
                  <div style={{ fontSize: "2.8rem", fontWeight: "800", color: isCritical ? '#F59E0B' : '#38BDF8', letterSpacing: "-1px" }}>
                    {sensor.soil_moisture.toFixed(1)}<span style={{ fontSize: "1.5rem", color: "rgba(255,255,255,0.4)" }}>%</span>
                  </div>
                  <div style={{ color: "#94A3B8", fontSize: "0.9rem", fontWeight: "500", textTransform: "uppercase", letterSpacing: "1px" }}>
                    Hydratation
                  </div>
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: "1rem", borderTop: "1px solid rgba(255, 255, 255, 0.05)" }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem" }}>
                    <span style={{ fontSize: "0.75rem", color: "#64748B", textTransform: "uppercase", letterSpacing: "1px" }}>Profondeur</span>
                    <span style={{ fontSize: "0.9rem", color: "#E2E8F0", fontWeight: "600" }}>{sensor.depth_cm} cm</span>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem", textAlign: "right" }}>
                    <span style={{ fontSize: "0.75rem", color: "#64748B", textTransform: "uppercase", letterSpacing: "1px" }}>Reconstruction Loss</span>
                    <span style={{ fontSize: "0.9rem", color: isAnomaly ? "#FCA5A5" : "#34D399", fontWeight: "600", fontFamily: "monospace" }}>
                      {sensor.anomaly_score ? sensor.anomaly_score.toFixed(3) : '0.000'}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
