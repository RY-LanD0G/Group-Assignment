import {
    LineChart,
    Line,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";

function BrandComparisonPage({
    fuelLabels,
    fuelColors,
    brandColors,
    brandViewMode,
    setBrandViewMode,
    brandCity,
    setBrandCity,
    brandFuelType,
    setBrandFuelType,
    brandDate,
    setBrandDate,
    availableDates,
    cityOptions,
    brandComparisonData,
    brandTrendData,
    brandTrendSeries,
    visibleBrands,
    toggleBrand,
    brandNameMap,
}) {
    function BrandTooltip({ active, payload }) {
        if (active && payload && payload.length > 0) {
            const data = payload[0].payload;

            return (
                <div className="custom-tooltip">
                    <p>
                        <strong>{data.brandName}</strong>
                    </p>
                    <p>City: {data.cityName}</p>
                    <p>Region: {data.regionName}</p>
                    <p>Fuel type: {fuelLabels[brandFuelType]}</p>
                    <p>Date: {brandDate}</p>
                    <p>Price: ${data.price.toFixed(3)} NZD/L</p>
                </div>
            );
        }

        return null;
    }

    return (
        <main className="single-page">
            <section className="card">
                <h2>Brand Comparison</h2>

                <div className="chart-filters">
                    <div className="filter-item">
                        <label>View</label>
                        <select
                            value={brandViewMode}
                            onChange={(e) => setBrandViewMode(e.target.value)}
                        >
                            <option value="snapshot">Snapshot comparison</option>
                            <option value="trend">Trend over time</option>
                        </select>
                    </div>

                    <div className="filter-item">
                        <label>City</label>
                        <select
                            value={brandCity}
                            onChange={(e) => setBrandCity(e.target.value)}
                        >
                            {cityOptions.map((city) => (
                                <option key={city.code} value={city.code}>
                                    {city.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="filter-item">
                        <label>Fuel Type</label>
                        <select
                            value={brandFuelType}
                            onChange={(e) => setBrandFuelType(e.target.value)}
                        >
                            <option value="P91">Regular Petrol 91</option>
                            <option value="P95">Premium Petrol 95</option>
                            <option value="P98">Premium Petrol 98</option>
                            <option value="DSL">Automotive Diesel</option>
                        </select>
                    </div>

                    {brandViewMode === "snapshot" && (
                        <div className="filter-item">
                            <label>Date</label>
                            <select
                                value={brandDate}
                                onChange={(e) => setBrandDate(e.target.value)}
                            >
                                {availableDates.map((date) => (
                                    <option key={date} value={date}>
                                        {date}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}
                </div>

                {brandViewMode === "snapshot" && (
                    <>
                        {brandComparisonData.length === 0 ? (
                            <p className="card-description">
                                No brand price data is available for this city, fuel type,
                                and date.
                            </p>
                        ) : (
                            <ResponsiveContainer width="100%" height={520}>
                                <BarChart
                                    data={brandComparisonData}
                                    margin={{
                                        top: 10,
                                        right: 30,
                                        left: 20,
                                        bottom: 40,
                                    }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="brandName" />
                                    <YAxis domain={["auto", "auto"]} />
                                    <Tooltip content={<BrandTooltip />} />
                                    <Bar
                                        dataKey="price"
                                        name={`${fuelLabels[brandFuelType]} price`}
                                        fill={fuelColors[brandFuelType]}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </>
                )}

                {brandViewMode === "trend" && (
                    <>
                        {brandTrendSeries.length > 0 && (
                            <div className="checkbox-group">
                                {brandTrendSeries.map((brandCode) => (
                                    <label
                                        key={brandCode}
                                        className={`checkbox-item ${visibleBrands.includes(brandCode) ? "" : "unchecked"
                                            }`}
                                    >
                                        <input
                                            type="checkbox"
                                            checked={visibleBrands.includes(brandCode)}
                                            onChange={() => toggleBrand(brandCode)}
                                        />

                                        <span
                                            className="fuel-color-dot"
                                            style={{
                                                backgroundColor:
                                                    brandColors[brandCode] || "#64748b",
                                            }}
                                        ></span>

                                        {brandNameMap[brandCode] || brandCode}
                                    </label>
                                ))}
                            </div>
                        )}

                        {brandTrendData.length === 0 || brandTrendSeries.length === 0 ? (
                            <p className="card-description">
                                No brand trend data is available for this city and fuel type.
                            </p>
                        ) : (
                            <ResponsiveContainer width="100%" height={520}>
                                <LineChart data={brandTrendData}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="date" minTickGap={30} />
                                    <YAxis domain={["auto", "auto"]} />
                                    <Tooltip />

                                    {brandTrendSeries
                                        .filter((brandCode) =>
                                            visibleBrands.includes(brandCode)
                                        )
                                        .map((brandCode) => (
                                            <Line
                                                key={brandCode}
                                                type="monotone"
                                                dataKey={brandCode}
                                                name={brandNameMap[brandCode] || brandCode}
                                                stroke={brandColors[brandCode] || "#64748b"}
                                                strokeWidth={2}
                                                dot={false}
                                                connectNulls
                                            />
                                        ))}
                                </LineChart>
                            </ResponsiveContainer>
                        )}
                    </>
                )}
            </section>
        </main>
    );
}

export default BrandComparisonPage;