import { useState } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine
} from 'recharts'

export default function ForecastPage({ weather, stats, regionInfo }) {
  const [days, setDays] = useState(90)
  if (!weather) return null

  const displayData = weather.slice(-days).map(d => ({
    ...d,
    date: d.date.slice(5, 10),
  }))

  return (
    <div>
      <div className="page-header">
        <h1>🌤️ Météo & Prévisions — {regionInfo?.name || 'Maroc'}</h1>
        <p>Données météorologiques et prévision de l'évapotranspiration (ET0)</p>
      </div>

      {stats && (
        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-value">{stats.temp_avg}°C</div>
            <div className="kpi-label">🌡️ Température moy.</div>
            <div className={`kpi-delta ${stats.temp_delta >= 0 ? 'positive' : 'negative'}`}>
              {stats.temp_delta >= 0 ? '+' : ''}{stats.temp_delta}°C vs moyenne annuelle
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-value">{stats.humidity_avg}%</div>
            <div className="kpi-label">💧 Humidité relative</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-value">{stats.precip_total} mm</div>
            <div className="kpi-label">🌧️ Précipitations (30j)</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-value">{stats.solar_avg}</div>
            <div className="kpi-label">☀️ Radiation (MJ/m²)</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-value">{stats.et0_avg}</div>
            <div className="kpi-label">🌿 ET0 moy. (mm/j)</div>
            <div className={`kpi-delta ${stats.et0_delta >= 0 ? 'negative' : 'positive'}`}>
              {stats.et0_delta >= 0 ? '+' : ''}{stats.et0_delta} vs moyenne annuelle
            </div>
          </div>
        </div>
      )}

      <div className="slider-container">
        <label>Période affichée : {days} jours</label>
        <input type="range" min={30} max={365} value={days} onChange={e => setDays(Number(e.target.value))} />
      </div>

      <div className="card" style={{marginBottom:18}}>
        <div className="card-title"><span className="icon">🌡️</span> Température & Humidité</div>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={displayData}>
            <defs>
              <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef5350" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#ef5350" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="humGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#42A5F5" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#42A5F5" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{fontSize:10}} interval={Math.max(1, Math.floor(days / 15))} />
            <YAxis tick={{fontSize:10}} />
            <Tooltip contentStyle={{background:'#0e1c36', border:'1px solid rgba(255,255,255,0.1)', borderRadius:10}} />
            <Legend wrapperStyle={{fontSize:12}} />
            <Area type="monotone" dataKey="temperature" stroke="#ef5350" fill="url(#tempGrad)" strokeWidth={2} name="Temp. (°C)" />
            <Area type="monotone" dataKey="humidity" stroke="#42A5F5" fill="url(#humGrad)" strokeWidth={1.5} name="Humidité (%)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-title"><span className="icon">🌧️</span> Précipitations</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={displayData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{fontSize:10}} interval={Math.max(1, Math.floor(days / 12))} />
              <YAxis tick={{fontSize:10}} />
              <Tooltip contentStyle={{background:'#0e1c36', border:'1px solid rgba(255,255,255,0.1)', borderRadius:10}} />
              <Bar dataKey="precipitation" fill="#42A5F5" opacity={0.7} radius={[2,2,0,0]} name="Pluie (mm)" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="card-title"><span className="icon">🌿</span> Évapotranspiration (ET0)</div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={displayData}>
              <defs>
                <linearGradient id="et0Grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#66BB6A" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#66BB6A" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{fontSize:10}} interval={Math.max(1, Math.floor(days / 12))} />
              <YAxis tick={{fontSize:10}} />
              <Tooltip contentStyle={{background:'#0e1c36', border:'1px solid rgba(255,255,255,0.1)', borderRadius:10}} />
              <ReferenceLine y={5} stroke="#ef5350" strokeDasharray="6 3" label={{value:'Seuil critique', fill:'#ef5350', fontSize:10}} />
              <Area type="monotone" dataKey="et0" stroke="#66BB6A" fill="url(#et0Grad)" strokeWidth={2.5} name="ET0 (mm/j)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {regionInfo && (
        <div className="interpretation">
          <strong>Contexte climatique :</strong> La région {regionInfo.name} est caractérisée par un climat {regionInfo.climate?.toLowerCase()}. 
          {stats && stats.et0_avg > 5
            ? ` Avec un ET0 moyen de ${stats.et0_avg} mm/j, la demande évaporative est élevée — l'irrigation doit compenser les pertes.`
            : ` Avec un ET0 moyen de ${stats?.et0_avg || '—'} mm/j, la demande évaporative est modérée.`
          }
        </div>
      )}
    </div>
  )
}
