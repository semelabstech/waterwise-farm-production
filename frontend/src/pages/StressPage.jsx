import { useRef, useEffect } from 'react'

function HeatmapCanvas({ data, colorMap, title, width = 256, height = 256 }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    if (!data || !canvasRef.current) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const rows = data.length
    const cols = data[0].length
    canvas.width = cols
    canvas.height = rows

    const imageData = ctx.createImageData(cols, rows)
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        const idx = (y * cols + x) * 4
        const val = data[y][x]
        const [r, g, b] = colorMap(val)
        imageData.data[idx] = r
        imageData.data[idx + 1] = g
        imageData.data[idx + 2] = b
        imageData.data[idx + 3] = 255
      }
    }
    ctx.putImageData(imageData, 0, 0)
  }, [data, colorMap])

  return (
    <div>
      <div style={{fontSize:'0.82rem', fontWeight:600, marginBottom:8, color:'var(--text-primary)'}}>
        {title}
      </div>
      <div className="heatmap-container">
        <canvas ref={canvasRef} style={{width:'100%', height:'auto'}}></canvas>
      </div>
    </div>
  )
}

const ndviColorMap = (v) => {
  const t = Math.max(0, Math.min(1, (v + 0.2) / 1.0))
  return [Math.round((1 - t) * 200), Math.round(t * 200 + 55), 30]
}

const ndmiColorMap = (v) => {
  const t = Math.max(0, Math.min(1, (v + 0.3) / 0.8))
  return [Math.round((1 - t) * 180), Math.round(100 + t * 100), Math.round(t * 255)]
}

const stressColorMap = (v) => {
  const colors = {
    0: [46, 125, 50],
    1: [249, 168, 37],
    2: [239, 108, 0],
    3: [198, 40, 40],
  }
  return colors[Math.round(v)] || colors[0]
}

export default function StressPage({ data, patchId, setPatchId, regionInfo }) {
  if (!data) return null

  const totalPatches = data.total_patches || 20
  const statsEntries = data.stats ? Object.entries(data.stats) : []
  const score = data.stress_score || 0

  let scoreClass = 'badge-green'
  let scoreText = 'Situation normale'
  if (score >= 0.5) { scoreClass = 'badge-red'; scoreText = 'Intervention nécessaire' }
  else if (score >= 0.3) { scoreClass = 'badge-yellow'; scoreText = 'Surveillance requise' }

  const severePercent = data.stats?.['Stress Sévère']?.percentage || 0
  const moderatePercent = data.stats?.['Stress Modéré']?.percentage || 0
  const normalPercent = data.stats?.['Normal']?.percentage || 0

  return (
    <div>
      <div className="page-header">
        <h1>🔬 Stress Hydrique — {regionInfo?.name || 'Analyse'}</h1>
        <p>Détection automatique du stress par analyse d'images satellite multibandes</p>
      </div>

      <div className="slider-container">
        <label>Zone d'analyse : {patchId + 1} sur {totalPatches}</label>
        <input
          type="range"
          min={0}
          max={Math.min(totalPatches - 1, 19)}
          value={patchId}
          onChange={e => setPatchId(Number(e.target.value))}
        />
      </div>

      <div className="grid-3">
        <HeatmapCanvas data={data.ndvi} colorMap={ndviColorMap} title="🛰️ Végétation (NDVI)" />
        <HeatmapCanvas data={data.ndmi} colorMap={ndmiColorMap} title="💧 Teneur en eau (NDMI)" />
        <HeatmapCanvas data={data.mask} colorMap={stressColorMap} title="🎯 Carte de Stress" />
      </div>

      <div className="interpretation">
        <strong>Analyse :</strong> {(() => {
          if (severePercent > 5) return `⚠ ${severePercent}% de cette zone est en stress sévère et ${moderatePercent}% en stress modéré. Les cultures nécessitent une irrigation immédiate ciblée.`
          if (moderatePercent > 15) return `${moderatePercent}% de la zone montre des signes de stress modéré. Une augmentation de l'irrigation est recommandée dans les prochaines 24h.`
          return `${normalPercent}% de la végétation est en bonne santé. La situation hydrique est favorable dans cette zone.`
        })()}
      </div>

      <div className="grid-2" style={{marginTop: 18}}>
        <div className="card">
          <div className="card-title"><span className="icon">📊</span> Distribution du stress</div>
          {statsEntries.map(([label, info]) => (
            <div key={label} style={{marginBottom: 12}}>
              <div style={{display:'flex', justifyContent:'space-between', marginBottom:4}}>
                <div className="legend-item" style={{marginBottom:0}}>
                  <div className="legend-dot" style={{background: info.color}}></div>
                  <span className="legend-label">{label}</span>
                </div>
                <span style={{fontWeight:700, fontSize:'0.85rem'}}>{info.percentage}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-bar-fill" style={{
                  width: `${info.percentage}%`,
                  background: `linear-gradient(90deg, ${info.color}, ${info.color}aa)`,
                }}></div>
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card-title"><span className="icon">📋</span> Informations de la zone</div>
          <table className="data-table">
            <tbody>
              <tr><td style={{color:'var(--text-secondary)'}}>Zone</td><td>{patchId + 1} / {totalPatches}</td></tr>
              <tr><td style={{color:'var(--text-secondary)'}}>Résolution</td><td>256 × 256 pixels (10m)</td></tr>
              <tr><td style={{color:'var(--text-secondary)'}}>Indice NDVI</td><td>{data.ndvi_range?.[0]} — {data.ndvi_range?.[1]}</td></tr>
              <tr><td style={{color:'var(--text-secondary)'}}>Indice NDMI</td><td>{data.ndmi_range?.[0]} — {data.ndmi_range?.[1]}</td></tr>
              <tr>
                <td style={{color:'var(--text-secondary)'}}>État global</td>
                <td><span className={`badge ${scoreClass}`}>{scoreText}</span></td>
              </tr>
              {regionInfo && (
                <>
                  <tr><td style={{color:'var(--text-secondary)'}}>Région</td><td>{regionInfo.name}</td></tr>
                  <tr><td style={{color:'var(--text-secondary)'}}>Climat</td><td>{regionInfo.climate}</td></tr>
                </>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
