"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";

// ── Types ─────────────────────────────────────────────────────────────────

export interface NearbyPlace {
  place_id: string;
  name: string;
  vicinity: string;
  lat: number;
  lng: number;
  rating?: number;
  user_ratings_total?: number;
  open_now?: boolean;
  types: string[];
}

interface MapViewProps {
  center: { lat: number; lng: number };
  places: NearbyPlace[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

// ── MapController ─────────────────────────────────────────────────────────
// react-leaflet v4: MapContainer's center prop is init-only (NOT reactive).
// All imperative map updates must go through useMap() in a child component.

interface MapControllerProps {
  center: { lat: number; lng: number };
  selectedPlace: NearbyPlace | null;
}

function MapController({ center, selectedPlace }: MapControllerProps) {
  const map = useMap();

  useEffect(() => {
    map.setView([center.lat, center.lng], map.getZoom());
  }, [center]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (selectedPlace) {
      map.panTo([selectedPlace.lat, selectedPlace.lng]);
    }
  }, [selectedPlace]); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
}

// ── MapView ───────────────────────────────────────────────────────────────

export function MapView({ center, places, selectedId, onSelect }: MapViewProps) {
  const selectedPlace = places.find((p) => p.place_id === selectedId) ?? null;

  return (
    <div className="w-full h-full rounded-xl overflow-hidden border border-glass-border">
      <MapContainer
        center={[center.lat, center.lng]}
        zoom={13}
        style={{ width: "100%", height: "100%", minHeight: "480px" }}
        zoomControl={true}
        scrollWheelZoom={true}
      >
        {/* CartoDB Dark tiles — matches existing navy dark theme */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
        />

        {/* Programmatic center / pan updates */}
        <MapController center={center} selectedPlace={selectedPlace} />

        {/* User location — amber dot, same color as previous Google Maps version */}
        <CircleMarker
          center={[center.lat, center.lng]}
          radius={10}
          pathOptions={{
            fillColor: "#FFB800",
            fillOpacity: 0.95,
            color: "#ffffff",
            weight: 2.5,
          }}
        >
          <Popup>
            <span style={{ fontFamily: "Inter, sans-serif", fontSize: 13, fontWeight: 600 }}>
              Your Location
            </span>
          </Popup>
        </CircleMarker>

        {/* Place markers — cyan/green, same radius & color as the old makePinIcon() */}
        {places.map((place) => {
          if (place.lat == null || place.lng == null) return null;
          const isSelected = place.place_id === selectedId;

          return (
            <CircleMarker
              key={place.place_id}
              center={[place.lat, place.lng]}
              radius={isSelected ? 12 : 8}
              pathOptions={{
                fillColor: isSelected ? "#00FF88" : "#00D4FF",
                fillOpacity: 0.95,
                color: "#ffffff",
                weight: isSelected ? 2.5 : 1.5,
              }}
              eventHandlers={{ click: () => onSelect(place.place_id) }}
            >
              <Popup>
                <div style={{ fontFamily: "Inter, sans-serif", padding: "4px 2px", maxWidth: 200 }}>
                  <strong style={{ fontSize: 13, color: "#0f172a" }}>{place.name}</strong>
                  {place.vicinity && (
                    <div style={{ fontSize: 11, marginTop: 3, color: "#475569" }}>
                      {place.vicinity}
                    </div>
                  )}
                  {place.rating != null && (
                    <div style={{ fontSize: 11, marginTop: 2, color: "#374151" }}>
                      ⭐ {place.rating}
                    </div>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
