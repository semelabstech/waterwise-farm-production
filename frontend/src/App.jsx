import { useState, useEffect } from 'react'
import './App.css'
import Sidebar from './components/Sidebar'
import HomePage from './pages/HomePage'
import MapPage from './pages/MapPage'
import StressPage from './pages/StressPage'
import ForecastPage from './pages/ForecastPage'
import RecommendationsPage from './pages/RecommendationsPage'
import ReportPage from './pages/ReportPage'
import IoTPage from './pages/IoTPage'
import CropPlannerPage from './pages/CropPlannerPage'
import LandingPage from './pages/LandingPage'

const API = '/api'

function App() {
  const [page, setPage] = useState('home')
  const [selectedRegion, setSelectedRegion] = useState('souss_massa')
  const [regions, setRegions] = useState([])
  const [overview, setOverview] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [weather, setWeather] = useState(null)
  const [weatherStats, setWeatherStats] = useState(null)
  const [patchData, setPatchData] = useState(null)
  const [recommendations, setRecommendations] = useState(null)
  const [mapZones, setMapZones] = useState(null)
  const [patchId, setPatchId] = useState(0)
  const [loading, setLoading] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())

  const [appMode, setAppMode] = useState('landing') // 'landing', 'farmer', 'engineer'
  const [userLocation, setUserLocation] = useState(null) // { lat, lon, name }
  
  // ... (lines 34-47 unchanged)

  // Load all data when region changes OR mode changes
  useEffect(() => {
    if (appMode === 'landing') return;

    // If we are in farmer mode but don't have location yet, wait
    if (appMode === 'farmer' && !userLocation) return;

    setLoading(true)
    setOverview(null)
    setWeather(null)
    setPatchData(null)
    setPatchId(0)

    let queryParams = `region=${selectedRegion}`
    if (appMode === 'farmer' && userLocation) {
        queryParams = `region=custom&lat=${userLocation.lat}&lon=${userLocation.lon}`
        if (userLocation.name) {
          queryParams += `&name=${encodeURIComponent(userLocation.name)}`
        }
    }

    Promise.all([
      fetch(`${API}/overview?${queryParams}`).then(r => r.json()),
      fetch(`${API}/alerts?${queryParams}`).then(r => r.json()),
      fetch(`${API}/weather?days=90&${queryParams}`).then(r => r.json()),
      fetch(`${API}/weather/stats?${queryParams}`).then(r => r.json()),
      fetch(`${API}/patches/0?${queryParams}`).then(r => r.json()),
      fetch(`${API}/recommendations?${queryParams}`).then(r => r.json()),
      fetch(`${API}/map/zones?${queryParams}`).then(r => r.json()),
    ]).then(([ov, al, wt, ws, pt, rec, mz]) => {
      setOverview(ov)
      setAlerts(al.alerts || [])
      setWeather(wt.data)
      setWeatherStats(ws.current)
      setPatchData(pt)
      setRecommendations(rec)
      setMapZones(mz)
      setLoading(false)
    }).catch(err => {
      console.error('API Error:', err)
      setLoading(false)
    })
  }, [selectedRegion, appMode, userLocation])

  // Load patch data when patchId changes
  useEffect(() => {
    if (patchId > 0 && appMode !== 'landing') {
      let queryParams = `region=${selectedRegion}`
      if (appMode === 'farmer' && userLocation) {
          queryParams = `region=custom&lat=${userLocation.lat}&lon=${userLocation.lon}`
      }
      fetch(`${API}/patches/${patchId}?${queryParams}`)
        .then(r => r.json())
        .then(setPatchData)
    }
  }, [patchId, appMode, selectedRegion, userLocation])

  const handleRegionChange = (e) => {
    setSelectedRegion(e.target.value)
  }

  const formatDate = (d) => {
    return d.toLocaleDateString('fr-FR', {
      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    })
  }

  const formatTime = (d) => {
    return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <h2>Chargement des données...</h2>
        <p>Connexion à la région {regions.find(r => r.key === selectedRegion)?.name || selectedRegion}</p>
      </div>
    )
  }

  const regionInfo = overview?.region || null

  const renderPage = () => {
    switch (page) {
      case 'home': return <HomePage overview={overview} alerts={alerts} onPageChange={setPage} />
      case 'iot': return <IoTPage selectedRegion={selectedRegion} appMode={appMode} userLocation={userLocation} />
      case 'map': return <MapPage zones={mapZones} regionInfo={regionInfo} />
      case 'stress': return <StressPage data={patchData} patchId={patchId} setPatchId={setPatchId} regionInfo={regionInfo} />
      case 'forecast': return <ForecastPage weather={weather} stats={weatherStats} regionInfo={regionInfo} />
      case 'recommendations': return <RecommendationsPage data={recommendations} regionInfo={regionInfo} />
      case 'report': return <ReportPage overview={overview} weather={weather} recommendations={recommendations} regionInfo={regionInfo} />
      case 'planner': return <CropPlannerPage appMode={appMode} userLocation={userLocation} />
      default: return <HomePage overview={overview} alerts={alerts} onPageChange={setPage} />
    }
  }

  if (appMode === 'landing') {
    return (
      <LandingPage 
        onSelectEngineerMode={() => setAppMode('engineer')} 
        onSelectFarmerMode={(lat, lon, name) => {
          setUserLocation({ lat, lon, name });
          setAppMode('farmer');
        }} 
      />
    );
  }

  return (
    <div className="app">
      <Sidebar currentPage={page} onPageChange={setPage} regionInfo={regionInfo} appMode={appMode} setAppMode={setAppMode} />

      <div className="top-header">
        <div className="header-left">
          {appMode === 'engineer' ? (
            <div className="region-selector">
              <label>📍 Région :</label>
              <select className="region-select" value={selectedRegion} onChange={handleRegionChange}>
                {regions.map(r => (
                  <option key={r.key} value={r.key}>{r.name}</option>
                ))}
              </select>
            </div>
          ) : (
            <div className="region-selector" style={{ padding: "0.5rem 1rem", background: "rgba(76,175,80,0.1)", borderRadius: "8px", border: "1px solid rgba(76,175,80,0.3)" }}>
              <label style={{ color: "#81C784", margin: 0, fontWeight: "600" }}>📍 Ma Ferme (GPS)</label>
            </div>
          )}
        </div>

        <div className="header-right">
          {weatherStats && (
            <div className="header-weather">
              <div className="header-weather-item">
                <span>🌡️</span>
                <span className="value">{weatherStats.temp_avg}°C</span>
              </div>
              <div className="header-weather-item">
                <span>💧</span>
                <span className="value">{weatherStats.humidity_avg}%</span>
              </div>
              <div className="header-weather-item">
                <span>🌿</span>
                <span className="value">{weatherStats.et0_avg} mm/j</span>
              </div>
            </div>
          )}
          <div className="header-datetime">
            <div className="date">{formatDate(currentTime)}</div>
            <div>{formatTime(currentTime)}</div>
          </div>
        </div>
      </div>

      <main className="main-content">
        <div className="page-content">
          {renderPage()}
        </div>
      </main>
    </div>
  )
}

export default App
