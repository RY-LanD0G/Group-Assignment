import { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";

function NZRegionMap({ selectedRegion, onRegionSelect }) {
    const [regions, setRegions] = useState(null);

    useEffect(() => {
        fetch("/data/nz_regions.geojson")
            .then((response) => response.json())
            .then((data) => setRegions(data))
            .catch((error) => console.error("Failed to load GeoJSON:", error));
    }, []);

    function getRegionName(feature) {
        return feature.properties.REGC2025_V1_00_NAME;
    }

    function cleanRegionName(regionName) {
        return String(regionName || "")
            .replace(" Region", "")
            .trim();
    }

    function normalizeRegionName(name) {
        return String(name || "")
            .replace(" Region", "")
            .replace("ū", "u")
            .replace("Ū", "U")
            .replace("-", " ")
            .trim()
            .toLowerCase();
    }

    function isSelectedFeature(feature) {
        const geoJsonName = getRegionName(feature);
        const cleanedName = cleanRegionName(geoJsonName);

        return (
            normalizeRegionName(selectedRegion) === normalizeRegionName(geoJsonName) ||
            normalizeRegionName(selectedRegion) === normalizeRegionName(cleanedName)
        );
    }

    function regionStyle(feature) {
        const isSelected = isSelectedFeature(feature);

        return {
            color: isSelected ? "#dc2626" : "#333333",
            weight: isSelected ? 4 : 1,
            fillColor: isSelected ? "#f97316" : "#4f8cff",
            fillOpacity: isSelected ? 0.8 : 0.45,
        };
    }

    function onEachRegion(feature, layer) {
        const geoJsonName = getRegionName(feature);
        const cleanedName = cleanRegionName(geoJsonName);

        layer.bindTooltip(geoJsonName);

        layer.on({
            click: () => {
                onRegionSelect(cleanedName);
            },
            mouseover: (e) => {
                const isSelected = isSelectedFeature(feature);

                e.target.setStyle({
                    weight: isSelected ? 4 : 3,
                    fillOpacity: isSelected ? 0.85 : 0.65,
                });
            },
            mouseout: (e) => {
                e.target.setStyle(regionStyle(feature));
            },
        });
    }

    if (!regions) {
        return <p>Loading map...</p>;
    }

    return (
        <div className="region-map-container">
            <MapContainer
                center={[-41.2, 172.8]}
                zoom={5}
                style={{ height: "100%", width: "100%" }}
            >
                <TileLayer
                    attribution="&copy; OpenStreetMap contributors"
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />

                <GeoJSON
                    key={selectedRegion || "all-regions"}
                    data={{
                        ...regions,
                        features: regions.features.filter(
                            (feature) =>
                                feature.properties.REGC2025_V1_00_NAME !== "Area Outside Region"
                        ),
                    }}
                    style={regionStyle}
                    onEachFeature={onEachRegion}
                />
            </MapContainer>
        </div>
    );
}

export default NZRegionMap;