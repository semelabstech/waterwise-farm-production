import React, { useState, useEffect, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell } from 'recharts'

// Fix default marker icon (Leaflet + Webpack/Vite issue)
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const API = '/api'

function LocationPicker({ position, setPosition }) {
  useMapEvents({
    click(e) { setPosition([e.latlng.lat, e.latlng.lng]) }
  })
  return position ? <Marker position={position} /> : null
}

export default function CropPlannerPage({ appMode, userLocation }) {
  const [mode, setMode] = useState(appMode === 'farmer' ? 'farmer' : 'expert') // 'farmer' or 'expert'
  const [step, setStep] = useState(appMode === 'farmer' ? 2 : 1)
  const [position, setPosition] = useState(appMode === 'farmer' && userLocation ? [userLocation.lat, userLocation.lon] : null)
  const [areaHa, setAreaHa] = useState(10)
  const [plantingMonth, setPlantingMonth] = useState(3)
  const [crops, setCrops] = useState([])
  const [selectedCrops, setSelectedCrops] = useState([])
  const [categories, setCategories] = useState([])
  const [filterCat, setFilterCat] = useState('')
  const [search, setSearch] = useState('')
  const [results, setResults] = useState(null)
  const [climate, setClimate] = useState(null)
  const [loading, setLoading] = useState(false)

  // Load crops
  useEffect(() => {
    fetch(`${API}/crops`).then(r => r.json()).then(data => {
      setCrops(data.crops || [])
      setCategories(data.categories || [])
    }).catch(console.error)
  }, [])

  // Fetch climate when position changes
  useEffect(() => {
    if (position) {
      fetch(`${API}/planner/climate?lat=${position[0]}&lon=${position[1]}`)
        .then(r => r.json())
        .then(data => setClimate(data.climate))
        .catch(console.error)
    }
  }, [position])

  const filtered = useMemo(() => {
    let list = crops
    if (filterCat) list = list.filter(c => c.category === filterCat)
    if (search) {
      const s = search.toLowerCase()
      list = list.filter(c => c.name_en.toLowerCase().includes(s) || c.name_fr.toLowerCase().includes(s))
    }
    return list
  }, [crops, filterCat, search])

  const toggleCrop = (crop) => {
    const exists = selectedCrops.find(c => c.id === crop.id)
    if (exists) {
      setSelectedCrops(selectedCrops.filter(c => c.id !== crop.id))
    } else {
      const remaining = 100 - selectedCrops.reduce((sum, c) => sum + c.percentage, 0)
      const defaultPct = Math.min(remaining, Math.max(10, Math.floor(remaining / 2)))
      setSelectedCrops([...selectedCrops, { ...crop, percentage: defaultPct }])
    }
  }

  const updatePercentage = (id, pct) => {
    setSelectedCrops(selectedCrops.map(c => c.id === id ? { ...c, percentage: Math.max(0, Math.min(100, pct)) } : c))
  }

  const totalPct = selectedCrops.reduce((s, c) => s + c.percentage, 0)

  const computeBudget = async () => {
    if (!position || selectedCrops.length === 0) return
    setLoading(true)
    try {
      const res = await fetch(`${API}/planner/estimate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: position[0], lon: position[1],
          area_ha: areaHa,
          planting_month: plantingMonth,
          crops: selectedCrops.map(c => ({ id: c.id, percentage: c.percentage }))
        })
      })
      const data = await res.json()
      setResults(data)
      setStep(3)
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  const monthNames = ["Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin", "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre"]
  const COLORS = ['#60A5FA', '#34D399', '#F59E0B', '#EF4444', '#A78BFA', '#F472B6', '#38BDF8', '#FB923C', '#4ADE80', '#E879F9']

  // Styles
  const glass = { background: "rgba(30, 41, 59, 0.7)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: "16px", padding: "1.5rem", backdropFilter: "blur(10px)" }
  const inputStyle = { background: "rgba(15, 23, 42, 0.8)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "10px", color: "#F8FAFC", padding: "10px 14px", fontSize: "0.95rem", width: "100%", outline: "none", fontFamily: "Inter, sans-serif" }
  const btnPrimary = { background: "linear-gradient(135deg, #1B5E20, #2E7D32)", color: "white", border: "none", padding: "12px 28px", borderRadius: "12px", fontWeight: "700", fontSize: "1rem", cursor: "pointer", fontFamily: "Inter, sans-serif", transition: "all 0.2s" }
  const btnOutline = { background: "transparent", color: "#81C784", border: "1px solid rgba(76,175,80,0.5)", padding: "12px 28px", borderRadius: "12px", fontWeight: "600", fontSize: "1rem", cursor: "pointer", fontFamily: "Inter, sans-serif" }

  return (
    <div className="page-container fade-in">
      {/* Header Info */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem" }}>
        <div>
          <h2 style={{ fontSize: "2rem", fontWeight: "800", background: "linear-gradient(90deg, #60A5FA, #34D399)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", margin: 0 }}>
            <span style={{ WebkitTextFillColor: "initial", marginRight: "10px" }}>🌍</span>
            {appMode === 'farmer' ? 'Mon Exploitation Agricole' : 'Planificateur Avancé'}
          </h2>
          <p style={{ color: "#94A3B8", margin: "0.5rem 0 0 0" }}>
            {appMode === 'farmer' ? 'Calculez facilement les besoins en eau (données GPS synchronisées).' : 'Analyse détaillée FAO-56 avec coefficients Kc, courbes ETc et calendrier cultural pour toute région.'}
          </p>
        </div>
        {appMode !== 'farmer' && (
        <div style={{ display: "flex", gap: "4px", background: "rgba(15, 23, 42, 0.5)", borderRadius: "12px", padding: "4px", border: "1px solid rgba(255,255,255,0.05)" }}>
          <button onClick={() => { setMode('farmer'); setStep(position ? 2 : 1); }} style={{ ...btnOutline, padding: "8px 20px", fontSize: "0.85rem", background: mode === 'farmer' ? "rgba(76,175,80,0.15)" : "transparent", borderColor: mode === 'farmer' ? "rgba(76,175,80,0.5)" : "transparent", color: mode === 'farmer' ? "#81C784" : "#94A3B8" }}>
            🧑‍🌾 Mode Simplifié
          </button>
          <button onClick={() => setMode('expert')} style={{ ...btnOutline, padding: "8px 20px", fontSize: "0.85rem", background: mode === 'expert' ? "rgba(96,165,250,0.15)" : "transparent", borderColor: mode === 'expert' ? "rgba(96,165,250,0.5)" : "transparent", color: mode === 'expert' ? "#60A5FA" : "#94A3B8" }}>
            🔬 Mode Expert
          </button>
        </div>
        )}
      </div>

      {/* Step Indicators */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "2rem" }}>
        {[{ n: 1, label: "Localisation", icon: "📍" }, { n: 2, label: "Cultures", icon: "🌱" }, { n: 3, label: "Resultats IA", icon: "📊" }]
          .filter(s => !(appMode === 'farmer' && s.n === 1))
          .map(s => (
          <div key={s.n} onClick={() => { if (s.n < step || (s.n === 2 && position) || (s.n === 3 && results)) setStep(s.n) }} style={{
            flex: 1, ...glass, textAlign: "center", cursor: "pointer",
            borderColor: step === s.n ? "rgba(76,175,80,0.5)" : "rgba(255,255,255,0.05)",
            background: step === s.n ? "rgba(76,175,80,0.08)" : glass.background,
            opacity: step >= s.n ? 1 : 0.4, transition: "all 0.3s"
          }}>
            <div style={{ fontSize: "1.5rem" }}>{s.icon}</div>
            <div style={{ fontSize: "0.85rem", fontWeight: "600", color: step === s.n ? "#81C784" : "#94A3B8", marginTop: "4px" }}>Etape {s.n}: {s.label}</div>
          </div>
        ))}
      </div>

      {/* STEP 1: Location */}
      {step === 1 && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 380px", gap: "1.5rem" }}>
          <div style={{ ...glass, padding: 0, overflow: "hidden", height: "450px" }}>
            <MapContainer center={[31.6, -8.0]} zoom={3} style={{ height: "100%", width: "100%" }}>
              <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" attribution='&copy; CartoDB' />
              <LocationPicker position={position} setPosition={setPosition} />
            </MapContainer>
          </div>
          <div style={{ ...glass, display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <h3 style={{ color: "#E2E8F0", margin: 0 }}>📍 Votre Terrain</h3>
            <p style={{ color: "#94A3B8", fontSize: "0.9rem", margin: 0 }}>
              {mode === 'farmer' ? 'Cliquez sur la carte pour indiquer ou se trouve votre terre.' : 'Cliquez pour geopositionner la parcelle. Les donnees climatiques seront estimees automatiquement.'}
            </p>

            {position && (
              <div style={{ background: "rgba(76,175,80,0.08)", padding: "1rem", borderRadius: "12px", border: "1px solid rgba(76,175,80,0.2)" }}>
                <div style={{ fontSize: "0.8rem", color: "#81C784", fontWeight: "600", marginBottom: "0.5rem" }}>Position selectionnee</div>
                <div style={{ color: "#E2E8F0" }}>{position[0].toFixed(4)}, {position[1].toFixed(4)}</div>
                {climate && <div style={{ color: "#94A3B8", fontSize: "0.85rem", marginTop: "4px" }}>Climat: {climate.climate_name} — ET0: {climate.et0_avg} mm/j</div>}
              </div>
            )}

            <div>
              <label style={{ fontSize: "0.85rem", color: "#94A3B8", marginBottom: "6px", display: "block" }}>
                {mode === 'farmer' ? 'Taille de votre terre (hectares)' : 'Surface parcellaire (ha)'}
              </label>
              <input type="number" value={areaHa} onChange={e => setAreaHa(Number(e.target.value))} style={inputStyle} min={0.1} step={0.5} />
            </div>

            {mode === 'expert' && (
              <div>
                <label style={{ fontSize: "0.85rem", color: "#94A3B8", marginBottom: "6px", display: "block" }}>Mois de plantation</label>
                <select value={plantingMonth} onChange={e => setPlantingMonth(Number(e.target.value))} style={inputStyle}>
                  {monthNames.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
                </select>
              </div>
            )}

            {mode === 'expert' && climate && (
              <div style={{ background: "rgba(15,23,42,0.5)", padding: "1rem", borderRadius: "12px", fontSize: "0.8rem", color: "#94A3B8" }}>
                <div style={{ fontWeight: "600", color: "#60A5FA", marginBottom: "6px" }}>Profil Climatique Estime</div>
                <div>Temp moy: {climate.temp_avg}°C | Humidite: {climate.humidity_avg}%</div>
                <div>Rayonnement: {climate.solar_avg} MJ/m²/j | Vent: {climate.wind_avg} m/s</div>
                <div>Precipitations: ~{climate.precip_annual_mm} mm/an</div>
              </div>
            )}

            <button onClick={() => position && setStep(2)} disabled={!position} style={{ ...btnPrimary, opacity: position ? 1 : 0.4, marginTop: "auto" }}>
              Suivant → Choisir les Cultures
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: Crop Selection */}
      {step === 2 && (
        <div>
          <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
            <input placeholder="🔍 Rechercher une culture..." value={search} onChange={e => setSearch(e.target.value)}
              style={{ ...inputStyle, maxWidth: "350px", flex: "1" }} />
            <select value={filterCat} onChange={e => setFilterCat(e.target.value)} style={{ ...inputStyle, maxWidth: "220px" }}>
              <option value="">Toutes les categories</option>
              {categories.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "1rem", marginBottom: "2rem", maxHeight: "400px", overflowY: "auto", padding: "4px" }}>
            {filtered.map(crop => {
              const isSelected = selectedCrops.find(c => c.id === crop.id)
              return (
                <div key={crop.id} onClick={() => toggleCrop(crop)} style={{
                  ...glass, cursor: "pointer", textAlign: "center", padding: "1.2rem 1rem",
                  borderColor: isSelected ? "rgba(76,175,80,0.5)" : "rgba(255,255,255,0.05)",
                  background: isSelected ? "rgba(76,175,80,0.1)" : glass.background,
                  transform: isSelected ? "scale(1.02)" : "scale(1)", transition: "all 0.2s"
                }}>
                  <div style={{ fontSize: "2rem" }}>{crop.icon}</div>
                  <div style={{ fontSize: "0.9rem", fontWeight: "600", color: "#E2E8F0", marginTop: "6px" }}>{crop.name_fr}</div>
                  <div style={{ fontSize: "0.75rem", color: "#64748B", marginTop: "2px" }}>{crop.name_en}</div>
                  <div style={{ fontSize: "0.75rem", color: "#60A5FA", marginTop: "4px" }}>{crop.water_total_mm} mm/saison</div>
                  {isSelected && <div style={{ marginTop: "6px", color: "#81C784", fontWeight: "700", fontSize: "0.8rem" }}>✓ Selectionne</div>}
                </div>
              )
            })}
          </div>

          {selectedCrops.length > 0 && (
            <div style={{ ...glass, marginBottom: "1.5rem" }}>
              <h4 style={{ color: "#E2E8F0", marginBottom: "1rem" }}>Repartition de votre terrain ({areaHa} ha) — Total: {totalPct}%</h4>
              <div style={{ display: "flex", height: "8px", borderRadius: "4px", overflow: "hidden", marginBottom: "1rem", background: "rgba(15,23,42,0.5)" }}>
                {selectedCrops.map((c, i) => (
                  <div key={c.id} style={{ width: `${c.percentage}%`, background: COLORS[i % COLORS.length], transition: "width 0.3s" }} />
                ))}
              </div>
              {selectedCrops.map((c, i) => (
                <div key={c.id} style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "0.8rem" }}>
                  <span style={{ width: "12px", height: "12px", borderRadius: "50%", background: COLORS[i % COLORS.length], flexShrink: 0 }} />
                  <span style={{ flex: 1, color: "#E2E8F0", fontWeight: "500" }}>{c.icon} {c.name_fr}</span>
                  <input type="number" value={c.percentage} onChange={e => updatePercentage(c.id, Number(e.target.value))}
                    style={{ ...inputStyle, width: "80px", textAlign: "center" }} min={1} max={100} />
                  <span style={{ color: "#94A3B8", fontSize: "0.85rem" }}>%</span>
                  {mode === 'expert' && <span style={{ color: "#64748B", fontSize: "0.8rem" }}>({(areaHa * c.percentage / 100).toFixed(1)} ha)</span>}
                  <button onClick={() => setSelectedCrops(selectedCrops.filter(x => x.id !== c.id))} style={{ background: "transparent", border: "none", color: "#EF4444", cursor: "pointer", fontSize: "1.2rem" }}>×</button>
                </div>
              ))}
            </div>
          )}

          <div style={{ display: "flex", gap: "1rem" }}>
            <button onClick={() => setStep(1)} style={btnOutline}>← Retour</button>
            <button onClick={computeBudget} disabled={selectedCrops.length === 0 || loading} style={{ ...btnPrimary, opacity: selectedCrops.length > 0 ? 1 : 0.4 }}>
              {loading ? 'Calcul IA en cours...' : '📊 Calculer le Budget Eau'}
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: Results */}
      {step === 3 && results && (
        <div>
          {/* Summary KPIs */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1.5rem", marginBottom: "2rem" }}>
            {[
              { label: mode === 'farmer' ? "Eau Totale" : "Budget Hydrique Annuel", value: `${(results.grand_total_m3 || 0).toLocaleString()} m³`, color: "#60A5FA" },
              { label: mode === 'farmer' ? "Par Jour" : "Debit Journalier Moyen", value: `${results.avg_daily_m3 || 0} m³/j`, color: "#34D399" },
              { label: "Cultures", value: results.num_crops, color: "#F59E0B" },
              { label: "Surface", value: `${results.total_area_ha} ha`, color: "#A78BFA" },
            ].map((kpi, i) => (
              <div key={i} style={{ ...glass, textAlign: "center" }}>
                <div style={{ fontSize: "0.8rem", color: "#94A3B8", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "0.5rem" }}>{kpi.label}</div>
                <div style={{ fontSize: "2rem", fontWeight: "800", color: kpi.color }}>{kpi.value}</div>
              </div>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: mode === 'expert' ? "1.4fr 1fr" : "1fr", gap: "1.5rem", marginBottom: "2rem" }}>
            {/* Monthly Chart */}
            <div style={glass}>
              <h4 style={{ color: "#E2E8F0", marginBottom: "1rem" }}>
                {mode === 'farmer' ? '💧 Eau necessaire par mois' : '📈 Repartition mensuelle ETc (m³)'}
              </h4>
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={results.aggregated_monthly || []}>
                  <defs>
                    <linearGradient id="waterGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#60A5FA" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#60A5FA" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="month" stroke="#64748B" fontSize={12} />
                  <YAxis stroke="#64748B" fontSize={12} />
                  <Tooltip contentStyle={{ background: "#0F172A", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }} />
                  <Area type="monotone" dataKey="total_m3" stroke="#60A5FA" fill="url(#waterGrad)" strokeWidth={2} name="Eau (m³)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Crop Pie Chart (expert) or simple summary (farmer) */}
            {mode === 'expert' ? (
              <div style={glass}>
                <h4 style={{ color: "#E2E8F0", marginBottom: "1rem" }}>🥧 Repartition par culture</h4>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={(results.crops || []).map((c, i) => ({ name: c.crop.name_fr, value: c.results.total_water_m3, fill: COLORS[i % COLORS.length] }))}
                      cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={3} dataKey="value">
                      {(results.crops || []).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: "#0F172A", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", justifyContent: "center" }}>
                  {(results.crops || []).map((c, i) => (
                    <span key={i} style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "0.75rem", color: "#94A3B8" }}>
                      <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: COLORS[i % COLORS.length] }} />
                      {c.crop.name_fr}
                    </span>
                  ))}
                </div>
              </div>
            ) : (
              <div style={glass}>
                <h4 style={{ color: "#E2E8F0", marginBottom: "1rem" }}>🌱 Vos Cultures</h4>
                {(results.crops || []).map((c, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.8rem 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                    <span style={{ color: "#E2E8F0" }}>{c.crop.icon} {c.crop.name_fr}</span>
                    <span style={{ color: "#60A5FA", fontWeight: "700" }}>{(c.results.total_water_m3 || 0).toLocaleString()} m³</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Expert: Detailed crop table */}
          {mode === 'expert' && (
            <div style={{ ...glass, marginBottom: "2rem", overflowX: "auto" }}>
              <h4 style={{ color: "#E2E8F0", marginBottom: "1rem" }}>📋 Analyse Detaillee par Culture</h4>
              <table className="data-table" style={{ width: "100%" }}>
                <thead>
                  <tr>
                    <th>Culture</th>
                    <th>Surface</th>
                    <th>Kc ini</th>
                    <th>Kc mid</th>
                    <th>Kc end</th>
                    <th>Saison (j)</th>
                    <th>ETc (mm)</th>
                    <th>Volume (m³)</th>
                    <th>Pic (mm/j)</th>
                    <th>Tolerance</th>
                  </tr>
                </thead>
                <tbody>
                  {(results.crops || []).map((c, i) => {
                    const crop = c.crop
                    const r = c.results
                    const origCrop = crops.find(x => x.id === crop.id) || {}
                    return (
                      <tr key={i}>
                        <td style={{ fontWeight: "600" }}>{crop.icon} {crop.name_fr}</td>
                        <td>{c.allocated_area_ha} ha ({c.percentage}%)</td>
                        <td>{origCrop.kc_ini}</td>
                        <td style={{ color: "#60A5FA", fontWeight: "600" }}>{origCrop.kc_mid}</td>
                        <td>{origCrop.kc_end}</td>
                        <td>{r.season_days} j</td>
                        <td>{r.total_water_mm} mm</td>
                        <td style={{ color: "#34D399", fontWeight: "700" }}>{(r.total_water_m3 || 0).toLocaleString()}</td>
                        <td>{r.peak_daily_mm} mm/j</td>
                        <td>
                          <span style={{ padding: "2px 8px", borderRadius: "12px", fontSize: "0.7rem", fontWeight: "600",
                            background: crop.drought_tolerance === 'very_high' ? "rgba(52,211,153,0.15)" : crop.drought_tolerance === 'high' ? "rgba(96,165,250,0.15)" : crop.drought_tolerance === 'medium' ? "rgba(251,191,36,0.15)" : "rgba(239,68,68,0.15)",
                            color: crop.drought_tolerance === 'very_high' ? "#34D399" : crop.drought_tolerance === 'high' ? "#60A5FA" : crop.drought_tolerance === 'medium' ? "#FBB224" : "#EF4444" }}>
                            {crop.drought_tolerance}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Expert: Kc Curves */}
          {mode === 'expert' && results.crops && results.crops.length > 0 && results.crops[0].kc_curve && (
            <div style={{ ...glass, marginBottom: "2rem" }}>
              <h4 style={{ color: "#E2E8F0", marginBottom: "1rem" }}>📈 Courbe Kc — {results.crops[0].crop.name_fr}</h4>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={results.crops[0].kc_curve}>
                  <defs>
                    <linearGradient id="kcGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#34D399" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#34D399" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="day" stroke="#64748B" fontSize={11} label={{ value: "Jour", position: "insideBottom", offset: -5, fill: "#94A3B8" }} />
                  <YAxis stroke="#64748B" fontSize={11} domain={[0, 1.4]} />
                  <Tooltip contentStyle={{ background: "#0F172A", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }}
                    formatter={(v, n) => [v, n === 'kc' ? 'Kc' : n]} labelFormatter={v => `Jour ${v}`} />
                  <Area type="monotone" dataKey="kc" stroke="#34D399" fill="url(#kcGrad)" strokeWidth={2} name="Kc" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Farmer: Simple recommendation */}
          {mode === 'farmer' && (
            <div style={{ ...glass, background: "linear-gradient(135deg, rgba(30, 80, 40, 0.3), rgba(15, 23, 42, 0.8))", border: "1px solid rgba(76,175,80,0.2)", marginBottom: "2rem" }}>
              <h4 style={{ color: "#81C784", marginBottom: "1rem" }}>💡 Conseil pour Votre Exploitation</h4>
              <p style={{ color: "#E2E8F0", fontSize: "1.1rem", lineHeight: 1.6 }}>
                Pour vos <strong>{results.total_area_ha} hectares</strong> avec {results.num_crops} culture(s),
                vous aurez besoin d'environ <strong style={{ color: "#60A5FA" }}>{(results.grand_total_m3 || 0).toLocaleString()} m³ d'eau</strong> par saison.
                Cela represente environ <strong>{results.avg_daily_m3} m³ par jour</strong>.
              </p>
              <p style={{ color: "#94A3B8", fontSize: "0.9rem", marginTop: "1rem" }}>
                Nous recommandons l'irrigation goutte-a-goutte le matin (5h-8h) pour maximiser l'efficacite et reduire l'evaporation.
              </p>
            </div>
          )}

          <div style={{ display: "flex", gap: "1rem" }}>
            <button onClick={() => { setStep(2); setResults(null) }} style={btnOutline}>← Modifier les Cultures</button>
            <button onClick={() => { setStep(1); setResults(null); setSelectedCrops([]); setPosition(null); setClimate(null) }} style={btnOutline}>🔄 Nouveau Calcul</button>
          </div>
        </div>
      )}
    </div>
  )
}
