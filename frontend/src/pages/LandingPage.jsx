import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.3.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.3.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.3.1/images/marker-shadow.png',
});

function MapPicker({ position, onPositionChange }) {
  useMapEvents({
    async click(e) {
      const lat = e.latlng.lat;
      const lon = e.latlng.lng;
      onPositionChange([lat, lon]);

      // Reverse Geocoding to get a friendly name
      try {
        const resp = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
        const data = await resp.json();
        if (data && data.display_name) {
          const parts = data.display_name.split(',');
          const name = parts.length > 1 ? `${parts[0]}, ${parts[1]}` : parts[0];
          window.dispatchEvent(new CustomEvent('locationDetected', { detail: { name, lat, lon } }));
        }
      } catch (err) {
        console.warn("Reverse geocoding failed:", err);
      }
    },
  });
  return position ? <Marker position={position} /> : null;
}

export default function LandingPage({ onSelectEngineerMode, onSelectFarmerMode }) {
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [mapPosition, setMapPosition] = useState([31.62, -7.99]); // Default to Marrakech
  const [showMap, setShowMap] = useState(false);
  const [locationName, setLocationName] = useState("");

  useEffect(() => {
    const handleLocation = (e) => {
      if (e.detail?.name) {
        setLocationName(e.detail.name);
      }
    };
    window.addEventListener('locationDetected', handleLocation);
    return () => window.removeEventListener('locationDetected', handleLocation);
  }, []);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery) return;
    setLoading(true);
    setErrorMsg("");
    try {
      const resp = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}`);
      const data = await resp.json();
      if (data && data.length > 0) {
        const { lat, lon, display_name } = data[0];
        const newPos = [parseFloat(lat), parseFloat(lon)];
        setMapPosition(newPos);
        // Shorten the name (take first two parts if available)
        const parts = display_name.split(',');
        const shortName = parts.length > 1 ? `${parts[0]}, ${parts[1]}` : parts[0];
        setLocationName(shortName);
        setShowMap(true);
      } else {
        setErrorMsg("📍 Lieu introuvable. Essayez avec un nom de ville ou de village.");
      }
    } catch (err) {
      setErrorMsg("⚠️ Erreur de connexion au service de recherche.");
    } finally {
      setLoading(false);
    }
  };

  const requestGPS = () => {
    setLoading(true);
    setErrorMsg("");
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          setLoading(false);
          const { latitude, longitude } = position.coords;
          setMapPosition([latitude, longitude]);
          setShowMap(true);
          
          // Try to get actual name
          try {
            const resp = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`);
            const data = await resp.json();
            const name = data.display_name ? data.display_name.split(',')[0] : "Ma position";
            setLocationName(`📍 ${name}`);
          } catch(e) {
            setLocationName("📍 Ma position actuelle");
          }
        },
        (error) => {
          console.warn("GPS failed, showing search instead:", error);
          setErrorMsg("❌ GPS inaccessible (bloqué par Windows ou Navigateur). Veuillez utiliser la recherche ci-après.");
          setLoading(false);
        },
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
      );
    } else {
      setErrorMsg("❌ Votre navigateur ne supporte pas le GPS.");
      setLoading(false);
    }
  };

  const wrapperStyle = {
    display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
    minHeight: "100vh", width: "100vw", background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
    color: "#f8fafc", fontFamily: "Inter, sans-serif", padding: "2rem"
  };

  const titleStyle = {
    fontSize: "3rem", fontWeight: "800", marginBottom: "1rem",
    background: "linear-gradient(90deg, #60A5FA, #34D399)",
    WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", textAlign: "center"
  };

  return (
    <div style={wrapperStyle}>
      <h1 style={titleStyle}>WaterWiseFarm</h1>
      <p style={{ color: "#94a3b8", fontSize: "1.2rem", maxWidth: "600px", textAlign: "center", marginBottom: "3rem" }}>
        Optimisez vos ressources hydriques avec l'IA agricole de pointe.
      </p>

      <div style={{ display: "flex", gap: "2rem", maxWidth: "1200px", width: "100%", flexWrap: "wrap", justifyContent: "center" }}>
        
        {/* Mode Agriculteur (GPS/Manual) */}
        <div style={{
          flex: "1", minWidth: "350px", background: "rgba(30, 41, 59, 0.7)", borderRadius: "24px",
          padding: "2rem", textAlign: "center", backdropFilter: "blur(10px)", border: "1px solid rgba(255,255,255,0.05)",
          display: "flex", flexDirection: "column"
        }}>
          <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🧑‍🌾</div>
          <h2 style={{ color: "#34D399", marginBottom: "1rem" }}>Mode Agriculteur</h2>
          <p style={{ color: "#94A3B8", fontSize: "0.95rem", lineHeight: "1.6", marginBottom: "1.5rem" }}>
            Localisez votre exploitation pour obtenir des recommandations d'irrigation sur-mesure.
          </p>

          {!showMap ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              <button 
                onClick={requestGPS}
                style={{ background: "#22c55e", color: "white", padding: "12px", borderRadius: "10px", border: "none", fontWeight: "700", cursor: "pointer" }}
              >
                {loading ? "Recherche..." : "📍 Utiliser mon GPS"}
              </button>
              
              <div style={{ position: "relative" }}>
                <div style={{ height: "1px", background: "rgba(255,255,255,0.1)", margin: "1rem 0" }}></div>
                <span style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", background: "#1e293b", padding: "0 10px", fontSize: "0.8rem", color: "#64748b" }}>OU</span>
              </div>

              <form onSubmit={handleSearch} style={{ display: "flex", gap: "5px" }}>
                <input 
                  type="text" 
                  placeholder="Rechercher ma ville (ex: Marrakech)"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ flex: 1, padding: "10px", borderRadius: "8px", background: "#0f172a", border: "1px solid #334155", color: "white" }}
                />
                <button type="submit" style={{ padding: "0 15px", borderRadius: "8px", background: "#3b82f6", color: "white", border: "none", cursor: "pointer" }}>🔍</button>
              </form>
              {errorMsg && <div style={{ color: "#ef4444", fontSize: "0.85rem", marginTop: "5px" }}>{errorMsg}</div>}
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column" }}>
              <div style={{ background: "rgba(52, 211, 153, 0.1)", padding: "10px", borderRadius: "8px", marginBottom: "1rem", fontSize: "0.85rem", color: "#34D399", border: "1px solid rgba(52, 211, 153, 0.2)" }}>
                {locationName || "📍 Position sélectionnée"}
              </div>
              <div style={{ height: "200px", width: "100%", borderRadius: "12px", overflow: "hidden", marginBottom: "1rem" }}>
                <MapContainer center={mapPosition} zoom={13} style={{ height: "100%", width: "100%" }}>
                  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                  <MapPicker position={mapPosition} onPositionChange={setMapPosition} />
                </MapContainer>
              </div>
              <div style={{ display: "flex", gap: "10px" }}>
                <button 
                  onClick={() => setShowMap(false)}
                  style={{ flex: 1, background: "transparent", color: "#94a3b8", padding: "10px", borderRadius: "8px", border: "1px solid #334155", cursor: "pointer" }}
                >
                  Annuler
                </button>
                <button 
                  onClick={() => onSelectFarmerMode(mapPosition[0], mapPosition[1], locationName)}
                  style={{ flex: 2, background: "#22c55e", color: "white", padding: "10px", borderRadius: "8px", border: "none", fontWeight: "700", cursor: "pointer" }}
                >
                  Valider mon Terrain ✅
                </button>
              </div>
              <p style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "10px" }}>Vous pouvez affiner la position en cliquant sur la carte.</p>
            </div>
          )}
        </div>

        {/* Mode Ingénieur */}
        <div style={{
          flex: "1", minWidth: "350px", background: "rgba(30, 41, 59, 0.7)", borderRadius: "24px",
          padding: "2rem", textAlign: "center", backdropFilter: "blur(10px)", border: "1px solid rgba(255,255,255,0.05)",
          display: "flex", flexDirection: "column"
        }}>
          <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🏗️</div>
          <h2 style={{ color: "#60A5FA", marginBottom: "1rem" }}>Mode Ingénieur</h2>
          <p style={{ color: "#94A3B8", fontSize: "0.95rem", lineHeight: "1.6", marginBottom: "1.5rem" }}>
            Analyse globale et gestion multisites sur l'ensemble du réseau météorologique et IoT.
          </p>
          <button 
            onClick={onSelectEngineerMode}
            style={{ marginTop: "auto", background: "linear-gradient(135deg, #1e3a8a, #3b82f6)", color: "white", padding: "15px", borderRadius: "12px", border: "none", fontWeight: "700", cursor: "pointer", fontSize: "1.1rem" }}
          >
            Accéder au Dashboard Global
          </button>
        </div>

      </div>

      <footer style={{ marginTop: "4rem", color: "#475569", fontSize: "0.9rem" }}>
        WaterWiseFarm © 2026 — Système de Précision Hydrique
      </footer>
    </div>
  );
}

