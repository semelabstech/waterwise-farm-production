import { useEffect, useRef } from 'react'

export default function MapPage({ zones, regionInfo }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)

  useEffect(() => {
    if (!zones || !mapRef.current) return

    // Clean up previous map
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove()
      mapInstanceRef.current = null
    }

    const L = window.L
    if (!L) {
      // Load Leaflet from CDN
      const link = document.createElement('link')
      link.rel = 'stylesheet'
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
      document.head.appendChild(link)

      const script = document.createElement('script')
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
      script.onload = () => initMap()
      document.head.appendChild(script)
    } else {
      initMap()
    }

    function initMap() {
      const L = window.L
      const map = L.map(mapRef.current).setView([zones.center.lat, zones.center.lon], 10)
      mapInstanceRef.current = map

      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap',
        maxZoom: 19,
      }).addTo(map)

      // Study area rectangle
      L.rectangle(
        [[zones.bbox.south, zones.bbox.west], [zones.bbox.north, zones.bbox.east]],
        { color: '#4CAF50', weight: 2, fillOpacity: 0.03, dashArray: '8 4' }
      ).addTo(map)

      // Zone markers
      zones.zones.forEach(z => {
        const radius = 8 + z.stress_level * 5
        L.circleMarker([z.lat, z.lon], {
          radius,
          color: z.color,
          fillColor: z.color,
          fillOpacity: 0.55,
          weight: 2,
        }).bindPopup(`
          <div style="font-family:Inter,sans-serif; min-width:200px; line-height:1.7;">
            <b style="font-size:14px; color:#1B5E20;">Zone ${z.id}</b><br/>
            <span style="color:${z.color}; font-weight:600;">● ${z.stress_label}</span><br/>
            🌾 Culture: <b>${z.crop || 'N/A'}</b><br/>
            NDVI: ${z.ndvi}<br/>
            Humidité sol: ${z.moisture}%<br/>
            ${z.needs_irrigation ? '<b style="color:#EF5350;">⚠ Irrigation requise</b>' : '<span style="color:#4CAF50;">✓ Pas d\'irrigation nécessaire</span>'}
          </div>
        `).bindTooltip(`Zone ${z.id}: ${z.stress_label}`, {direction:'top'}).addTo(map)
      })
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [zones])

  const stressLegend = [
    { label: 'Normal', color: '#2E7D32', desc: 'NDVI > 0.5' },
    { label: 'Stress Léger', color: '#F9A825', desc: '0.3 – 0.5' },
    { label: 'Stress Modéré', color: '#EF6C00', desc: '0.2 – 0.3' },
    { label: 'Stress Sévère', color: '#C62828', desc: '< 0.2' },
  ]

  const irrigationCount = zones?.zones?.filter(z => z.needs_irrigation).length || 0
  const totalZones = zones?.zones?.length || 0

  return (
    <div>
      <div className="page-header">
        <h1>🗺️ Carte Interactive — {regionInfo?.name || 'Maroc'}</h1>
        <p>Visualisation des {totalZones} zones agricoles • {irrigationCount} zone(s) nécessitant une irrigation</p>
      </div>

      <div className="map-container">
        <div ref={mapRef} style={{height:'100%', width:'100%'}}></div>
      </div>

      <div className="kpi-grid" style={{marginTop: 18}}>
        {stressLegend.map(s => (
          <div className="card" key={s.label} style={{padding:'12px 18px', display:'flex', alignItems:'center', gap:12, marginBottom: 0}}>
            <div style={{width:13, height:13, borderRadius:'50%', background:s.color, flexShrink:0}}></div>
            <div>
              <div style={{fontWeight:600, fontSize:'0.82rem'}}>{s.label}</div>
              <div style={{fontSize:'0.7rem', color:'var(--text-muted)'}}>NDVI {s.desc}</div>
            </div>
          </div>
        ))}
      </div>

      {regionInfo && (
        <div className="interpretation" style={{marginTop: 18}}>
          <strong>Zone d'étude :</strong> {regionInfo.name} — {regionInfo.description}
        </div>
      )}
    </div>
  )
}
