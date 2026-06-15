import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";
import NZRegionMap from "./NZRegionMap";

function OverviewPage({
    fuelLabels,
    fuelColors,
    visibleFuels,
    toggleFuel,
    nationalChartData,
    selectedRegion,
    setSelectedRegion,
    selectedCity,
    setSelectedCity,
    cityNameMap,
    filteredCityOptions,
    trendSummary,
    nationalComparison,
    formatPrice,
    formatDifference,
    formatPercent,
    activeTrendData,
}) {
    return (
        <main className="dashboard">
            <div className="overview-grid">
                <section className="card">
                    <h2>National Fuel Price Trend</h2>

                    <div className="checkbox-group">
                        {Object.entries(fuelLabels).map(([code, label]) => (
                            <label
                                key={code}
                                className={`checkbox-item ${visibleFuels.includes(code) ? "" : "unchecked"
                                    }`}
                            >
                                <input
                                    type="checkbox"
                                    checked={visibleFuels.includes(code)}
                                    onChange={() => toggleFuel(code)}
                                />

                                <span
                                    className="fuel-color-dot"
                                    style={{ backgroundColor: fuelColors[code] }}
                                ></span>

                                {label}
                            </label>
                        ))}
                    </div>

                    <ResponsiveContainer width="100%" height={360}>
                        <LineChart data={nationalChartData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="date" minTickGap={30} />
                            <YAxis domain={["auto", "auto"]} />
                            <Tooltip />

                            {Object.keys(fuelLabels)
                                .filter((code) => visibleFuels.includes(code))
                                .map((code) => (
                                    <Line
                                        key={code}
                                        type="monotone"
                                        dataKey={code}
                                        name={fuelLabels[code]}
                                        stroke={fuelColors[code]}
                                        strokeWidth={2}
                                        dot={false}
                                        connectNulls
                                    />
                                ))}
                        </LineChart>
                    </ResponsiveContainer>
                </section>

                <section className="card">
                    <h2>NZ Map</h2>

                    <NZRegionMap
                        selectedRegion={selectedRegion}
                        onRegionSelect={setSelectedRegion}
                    />

                    <div className="selected-region-box">
                        <strong>Selected region: </strong>
                        {selectedRegion || "No region selected"}

                        {selectedRegion && (
                            <button
                                className="clear-button"
                                onClick={() => setSelectedRegion(null)}
                            >
                                Clear selection
                            </button>
                        )}
                    </div>
                </section>
            </div>

            {selectedRegion && (
                <section className="card region-trend-card">
                    <h2>
                        {selectedCity
                            ? `${cityNameMap[selectedCity]?.cityName || selectedCity} Fuel Price Trend`
                            : `${selectedRegion} Fuel Price Trend`}
                    </h2>

                    <div className="chart-filters">
                        <div className="filter-item">
                            <label>City</label>
                            <select
                                value={selectedCity}
                                onChange={(e) => setSelectedCity(e.target.value)}
                            >
                                <option value="">Region average</option>

                                {filteredCityOptions.map((city) => (
                                    <option key={city.code} value={city.code}>
                                        {city.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {trendSummary && (
                        <div className="summary-grid">
                            <div className="summary-card">
                                <span className="summary-label">Latest P91</span>
                                <strong>{formatPrice(trendSummary.latestP91)}</strong>
                                <span className="summary-date">{trendSummary.latestDate}</span>
                            </div>

                            <div className="summary-card">
                                <span className="summary-label">Latest Diesel</span>
                                <strong>{formatPrice(trendSummary.latestDiesel)}</strong>
                                <span className="summary-date">{trendSummary.latestDate}</span>
                            </div>

                            <div className="summary-card">
                                <span className="summary-label">Average P91</span>
                                <strong>{formatPrice(trendSummary.averageP91)}</strong>
                                <span className="summary-date">Over selected period</span>
                            </div>

                            <div className="summary-card">
                                <span className="summary-label">Records</span>
                                <strong>{trendSummary.records}</strong>
                                <span className="summary-date">Time points</span>
                            </div>
                        </div>
                    )}

                    {nationalComparison && (
                        <div className="national-comparison-panel">
                            <h3>Compared with National Average</h3>

                            <div className="comparison-grid">
                                <div className="summary-card">
                                    <span className="summary-label">P91 vs National</span>
                                    <strong>
                                        {formatDifference(nationalComparison.P91?.difference)}
                                    </strong>
                                    <span className="summary-date">
                                        {formatPercent(
                                            nationalComparison.P91?.percentDifference
                                        )}{" "}
                                        on {nationalComparison.date}
                                    </span>
                                </div>

                                <div className="summary-card">
                                    <span className="summary-label">Diesel vs National</span>
                                    <strong>
                                        {formatDifference(nationalComparison.DSL?.difference)}
                                    </strong>
                                    <span className="summary-date">
                                        {formatPercent(
                                            nationalComparison.DSL?.percentDifference
                                        )}{" "}
                                        on {nationalComparison.date}
                                    </span>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTrendData.length === 0 ? (
                        <p className="card-description">
                            No fuel price data is available for this selection.
                        </p>
                    ) : (
                        <ResponsiveContainer width="100%" height={420}>
                            <LineChart data={activeTrendData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" minTickGap={30} />
                                <YAxis domain={["auto", "auto"]} />
                                <Tooltip />

                                {Object.keys(fuelLabels).map((code) => (
                                    <Line
                                        key={code}
                                        type="monotone"
                                        dataKey={code}
                                        name={fuelLabels[code]}
                                        stroke={fuelColors[code]}
                                        strokeWidth={2}
                                        dot={false}
                                        connectNulls
                                    />
                                ))}
                            </LineChart>
                        </ResponsiveContainer>
                    )}
                </section>
            )}
        </main>
    );
}

export default OverviewPage;