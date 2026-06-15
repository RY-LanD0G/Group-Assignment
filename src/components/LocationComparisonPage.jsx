import { useEffect, useMemo, useState } from "react";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Cell,
    ResponsiveContainer,
    ReferenceLine,
} from "recharts";

function LocationComparisonPage({
    fuelLabels,
    regionalData,
    cityFuelData,
    nationalPriceByDate,
    availableDates,
    regionOptions,
    cityOptions,
    regionNameMap,
    cityNameMap,
    formatPrice,
    formatDifference,
    formatPercent,
}) {
    const [comparisonFuelType, setComparisonFuelType] = useState("P91");
    const [comparisonDate, setComparisonDate] = useState("");
    const [selectedLocations, setSelectedLocations] = useState([]);
    const [expandedRegions, setExpandedRegions] = useState({});

    useEffect(() => {
        if (!comparisonDate && availableDates.length > 0) {
            setComparisonDate(availableDates[availableDates.length - 1]);
        }
    }, [availableDates, comparisonDate]);

    function getLocationKey(location) {
        return `${location.type}:${location.code}`;
    }

    function isLocationSelected(type, code) {
        return selectedLocations.some(
            (location) => location.type === type && location.code === code
        );
    }

    function toggleLocation(type, code) {
        setSelectedLocations((current) => {
            const exists = current.some(
                (location) => location.type === type && location.code === code
            );

            if (exists) {
                return current.filter(
                    (location) => !(location.type === type && location.code === code)
                );
            }

            return [...current, { type, code }];
        });
    }

    function clearSelection() {
        setSelectedLocations([]);
    }

    function toggleRegionExpand(regionCode) {
        setExpandedRegions((current) => ({
            ...current,
            [regionCode]: !current[regionCode],
        }));
    }

    function expandAllRegions() {
        const allExpanded = {};

        regionOptions.forEach((region) => {
            allExpanded[region.code] = true;
        });

        setExpandedRegions(allExpanded);
    }

    function collapseAllRegions() {
        setExpandedRegions({});
    }

    function getDifferenceColor(difference) {
        if (difference === null || difference === undefined || Number.isNaN(difference)) {
            return "#64748b";
        }

        if (difference < -0.03) {
            return "#16a34a";
        }

        if (difference > 0.03) {
            return "#dc2626";
        }

        return "#f59e0b";
    }

    const nationalAveragePrice = useMemo(() => {
        const price = Number(nationalPriceByDate[comparisonDate]?.[comparisonFuelType]);

        if (Number.isNaN(price)) {
            return null;
        }

        return price;
    }, [nationalPriceByDate, comparisonDate, comparisonFuelType]);

    const groupedLocationOptions = useMemo(() => {
        return regionOptions.map((region) => {
            const citiesInRegion = cityOptions
                .filter((city) => city.regionCode === region.code)
                .sort((a, b) => a.name.localeCompare(b.name));

            return {
                region,
                cities: citiesInRegion,
            };
        });
    }, [regionOptions, cityOptions]);

    const comparisonData = useMemo(() => {
        if (!comparisonDate || selectedLocations.length === 0) {
            return [];
        }

        const nationalPrice = Number(nationalPriceByDate[comparisonDate]?.[comparisonFuelType]);
        const rows = [];

        selectedLocations.forEach((location) => {
            if (location.type === "region") {
                const matchedRow = regionalData.find((row) => {
                    const values = Object.values(row);

                    const date = String(values[0] || "").trim();
                    const regionCode = String(values[1] || "").trim();
                    const fuelCode = String(values[2] || "").trim();

                    return (
                        date === comparisonDate &&
                        regionCode === location.code &&
                        fuelCode === comparisonFuelType
                    );
                });

                if (!matchedRow) {
                    return;
                }

                const values = Object.values(matchedRow);
                const price = Number(values[3]);

                if (Number.isNaN(price)) {
                    return;
                }

                const difference = Number.isNaN(nationalPrice)
                    ? null
                    : price - nationalPrice;

                const percentDifference =
                    !Number.isNaN(nationalPrice) && nationalPrice !== 0
                        ? (difference / nationalPrice) * 100
                        : null;

                rows.push({
                    id: getLocationKey(location),
                    type: "Region average",
                    code: location.code,
                    name: `${regionNameMap[location.code] || location.code} avg`,
                    price,
                    nationalPrice,
                    difference,
                    percentDifference,
                    color: getDifferenceColor(difference),
                });
            }

            if (location.type === "city") {
                const matchedRow = cityFuelData.find((row) => {
                    const values = Object.values(row);

                    const date = String(values[0] || "").trim();
                    const cityCode = String(values[1] || "").trim();
                    const fuelCode = String(values[3] || "").trim();

                    return (
                        date === comparisonDate &&
                        cityCode === location.code &&
                        fuelCode === comparisonFuelType
                    );
                });

                if (!matchedRow) {
                    return;
                }

                const values = Object.values(matchedRow);
                const price = Number(values[4]);

                if (Number.isNaN(price)) {
                    return;
                }

                const difference = Number.isNaN(nationalPrice)
                    ? null
                    : price - nationalPrice;

                const percentDifference =
                    !Number.isNaN(nationalPrice) && nationalPrice !== 0
                        ? (difference / nationalPrice) * 100
                        : null;

                rows.push({
                    id: getLocationKey(location),
                    type: "City",
                    code: location.code,
                    name: cityNameMap[location.code]?.cityName || location.code,
                    price,
                    nationalPrice,
                    difference,
                    percentDifference,
                    color: getDifferenceColor(difference),
                });
            }
        });

        return rows.sort((a, b) => a.price - b.price);
    }, [
        comparisonDate,
        comparisonFuelType,
        selectedLocations,
        regionalData,
        cityFuelData,
        nationalPriceByDate,
        regionNameMap,
        cityNameMap,
    ]);

    const selectedAverageInfo = useMemo(() => {
        if (comparisonData.length === 0) {
            return null;
        }

        const prices = comparisonData
            .map((row) => Number(row.price))
            .filter((price) => !Number.isNaN(price));

        if (prices.length === 0) {
            return null;
        }

        const selectedAverage =
            prices.reduce((sum, price) => sum + price, 0) / prices.length;

        const nationalAverage = nationalAveragePrice;

        const difference =
            nationalAverage !== null && nationalAverage !== undefined
                ? selectedAverage - nationalAverage
                : null;

        const percentDifference =
            nationalAverage !== null && nationalAverage !== undefined && nationalAverage !== 0
                ? (difference / nationalAverage) * 100
                : null;

        return {
            selectedAverage,
            nationalAverage,
            difference,
            percentDifference,
            count: prices.length,
        };
    }, [comparisonData, nationalAveragePrice]);

    function LocationTooltip({ active, payload }) {
        if (active && payload && payload.length > 0) {
            const data = payload[0].payload;

            return (
                <div className="custom-tooltip">
                    <p>
                        <strong>{data.name}</strong>
                    </p>
                    <p>Type: {data.type}</p>
                    <p>Fuel type: {fuelLabels[comparisonFuelType]}</p>
                    <p>Date: {comparisonDate}</p>
                    <p>Price: {formatPrice(data.price)}</p>
                    <p>National average: {formatPrice(data.nationalPrice)}</p>
                    <p>
                        Difference: {formatDifference(data.difference)} (
                        {formatPercent(data.percentDifference)})
                    </p>
                </div>
            );
        }

        return null;
    }

    return (
        <main className="single-page">
            <section className="card">
                <h2>Location Comparison</h2>

                <div className="chart-filters">
                    <div className="filter-item">
                        <label>Fuel Type</label>
                        <select
                            value={comparisonFuelType}
                            onChange={(e) => setComparisonFuelType(e.target.value)}
                        >
                            <option value="P91">Regular Petrol 91</option>
                            <option value="P95">Premium Petrol 95</option>
                            <option value="P98">Premium Petrol 98</option>
                            <option value="DSL">Automotive Diesel</option>
                        </select>
                    </div>

                    <div className="filter-item">
                        <label>Date</label>
                        <select
                            value={comparisonDate}
                            onChange={(e) => setComparisonDate(e.target.value)}
                        >
                            {availableDates.map((date) => (
                                <option key={date} value={date}>
                                    {date}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                <div className="location-selection-panel">
                    <div className="location-selection-header">
                        <h3>Select regions or cities to compare</h3>

                        <div className="location-selection-actions">
                            <button onClick={expandAllRegions}>Expand all</button>
                            <button onClick={collapseAllRegions}>Collapse all</button>
                            <button onClick={clearSelection}>Clear all</button>
                        </div>
                    </div>

                    <div className="region-group-grid">
                        {groupedLocationOptions.map(({ region, cities }) => {
                            const isExpanded = !!expandedRegions[region.code];

                            return (
                                <div key={region.code} className="region-group-card">
                                    <div className="region-group-header">
                                        <label
                                            className={`location-checkbox region-average-option ${isLocationSelected("region", region.code)
                                                    ? "selected"
                                                    : ""
                                                }`}
                                        >
                                            <input
                                                type="checkbox"
                                                checked={isLocationSelected(
                                                    "region",
                                                    region.code
                                                )}
                                                onChange={() =>
                                                    toggleLocation("region", region.code)
                                                }
                                            />
                                            {region.name} avg
                                        </label>

                                        <button
                                            className="region-expand-button"
                                            onClick={() => toggleRegionExpand(region.code)}
                                        >
                                            {isExpanded ? "Hide cities" : "Show cities"}
                                        </button>
                                    </div>

                                    {isExpanded && (
                                        <div className="city-option-list">
                                            {cities.length === 0 ? (
                                                <span className="no-city-text">
                                                    No city data
                                                </span>
                                            ) : (
                                                cities.map((city) => (
                                                    <label
                                                        key={city.code}
                                                        className={`location-checkbox ${isLocationSelected("city", city.code)
                                                                ? "selected"
                                                                : ""
                                                            }`}
                                                    >
                                                        <input
                                                            type="checkbox"
                                                            checked={isLocationSelected(
                                                                "city",
                                                                city.code
                                                            )}
                                                            onChange={() =>
                                                                toggleLocation("city", city.code)
                                                            }
                                                        />
                                                        {city.name}
                                                    </label>
                                                ))
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {selectedAverageInfo && (
                    <div className="comparison-summary-grid">
                        <div className="summary-card">
                            <span className="summary-label">Selected average</span>
                            <strong>{formatPrice(selectedAverageInfo.selectedAverage)}</strong>
                            <span className="summary-date">
                                {selectedAverageInfo.count} selected locations
                            </span>
                        </div>

                        <div className="summary-card">
                            <span className="summary-label">National average</span>
                            <strong>{formatPrice(selectedAverageInfo.nationalAverage)}</strong>
                            <span className="summary-date">{comparisonDate}</span>
                        </div>

                        <div className="summary-card">
                            <span className="summary-label">Average vs National</span>
                            <strong>{formatDifference(selectedAverageInfo.difference)}</strong>
                            <span className="summary-date">
                                {formatPercent(selectedAverageInfo.percentDifference)}
                            </span>
                        </div>
                    </div>
                )}

                <div className="comparison-legend">
                    <span>
                        <span className="legend-dot cheap"></span>
                        Below national average
                    </span>

                    <span>
                        <span className="legend-dot mid"></span>
                        Close to national average
                    </span>

                    <span>
                        <span className="legend-dot expensive"></span>
                        Above national average
                    </span>
                </div>

                {comparisonData.length === 0 ? (
                    <p className="card-description">
                        Select one or more regions or cities to compare fuel prices.
                    </p>
                ) : (
                    <ResponsiveContainer width="100%" height={520}>
                        <BarChart
                            data={comparisonData}
                            layout="vertical"
                            margin={{ top: 45, right: 40, left: 80, bottom: 10 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis type="number" domain={["auto", "auto"]} />
                            <YAxis
                                type="category"
                                dataKey="name"
                                width={150}
                                interval={0}
                            />
                            <Tooltip content={<LocationTooltip />} />

                            {nationalAveragePrice !== null && (
                                <ReferenceLine
                                    x={nationalAveragePrice}
                                    stroke="#111827"
                                    strokeDasharray="4 4"
                                    label={{
                                        value: "National avg",
                                        position: "insideTop",
                                        fill: "#111827",
                                        fontSize: 12,
                                    }}
                                />
                            )}

                            <Bar dataKey="price" name="Fuel price">
                                {comparisonData.map((entry) => (
                                    <Cell key={entry.id} fill={entry.color} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                )}
            </section>
        </main>
    );
}

export default LocationComparisonPage;