import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
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
import "./App.css";

const fuelLabels = {
    P91: "Regular Petrol 91",
    P95: "Premium Petrol 95",
    P98: "Premium Petrol 98",
    DSL: "Automotive Diesel",
};

const fuelColors = {
    P91: "#2563eb",
    P95: "#16a34a",
    P98: "#dc2626",
    DSL: "#f59e0b",
};

function App() {
    const [page, setPage] = useState("overview");

    const [nationalData, setNationalData] = useState([]);
    const [regionalData, setRegionalData] = useState([]);
    const [regionsData, setRegionsData] = useState([]);

    const [citiesData, setCitiesData] = useState([]);
    const [brandData, setBrandData] = useState([]);
    const [brandsData, setBrandsData] = useState([]);

    const [fuelType, setFuelType] = useState("P91");
    const [selectedDate, setSelectedDate] = useState("");
    const [visibleFuels, setVisibleFuels] = useState(["P91", "P95", "P98", "DSL"]);

    const [brandCity, setBrandCity] = useState("AKC");
    const [brandFuelType, setBrandFuelType] = useState("P91");
    const [brandDate, setBrandDate] = useState("");

    useEffect(() => {
        loadCsv("/data/national_weekly.csv", setNationalData);
        loadCsv("/data/fuel_prices_long.csv", setRegionalData);
        loadCsv("/data/regions.csv", setRegionsData);
        loadCsv("/data/cities.csv", setCitiesData);
        loadCsv("/data/brand_city_prices_long.csv", setBrandData);
        loadCsv("/data/brands.csv", setBrandsData);
    }, []);

    function loadCsv(path, setter) {
        Papa.parse(path, {
            download: true,
            header: true,
            skipEmptyLines: true,
            complete: (result) => {
                const cleanedData = result.data.map((row) => {
                    const cleanedRow = {};

                    Object.keys(row).forEach((key) => {
                        const cleanKey = key
                            .replace("\ufeff", "")
                            .replace(/\s+/g, "")
                            .trim();

                        cleanedRow[cleanKey] = row[key];
                    });

                    return cleanedRow;
                });

                setter(cleanedData);
            },
            error: (error) => {
                console.error("CSV loading error:", error);
            },
        });
    }

    const availableDates = useMemo(() => {
        const dates = nationalData
            .map((row) => Object.values(row)[0])
            .filter(Boolean);

        return [...new Set(dates)];
    }, [nationalData]);

    useEffect(() => {
        if (!selectedDate && availableDates.length > 0) {
            setSelectedDate(availableDates[availableDates.length - 1]);
        }
    }, [availableDates, selectedDate]);

    useEffect(() => {
        if (!brandDate && availableDates.length > 0) {
            setBrandDate(availableDates[availableDates.length - 1]);
        }
    }, [availableDates, brandDate]);

    const regionNameMap = useMemo(() => {
        const map = {};

        regionsData.forEach((row) => {
            const values = Object.values(row);
            const code = String(values[0] || "").trim();
            const name = String(values[1] || "").trim();

            if (code && name) {
                map[code] = name;
            }
        });

        return map;
    }, [regionsData]);

    const cityNameMap = useMemo(() => {
        const map = {};

        citiesData.forEach((row) => {
            const values = Object.values(row);

            const cityCode = String(values[0] || "").trim();
            const cityName = String(values[1] || "").trim();
            const regionCode = String(values[2] || "").trim();

            if (cityCode) {
                map[cityCode] = {
                    cityName: cityName || cityCode,
                    regionCode,
                    regionName: regionNameMap[regionCode] || regionCode,
                };
            }
        });

        return map;
    }, [citiesData, regionNameMap]);

    const brandNameMap = useMemo(() => {
        const map = {};

        brandsData.forEach((row) => {
            const values = Object.values(row);

            const brandCode = String(values[0] || "").trim();
            const brandName = String(values[1] || "").trim();

            if (brandCode) {
                map[brandCode] = brandName || brandCode;
            }
        });

        return map;
    }, [brandsData]);

    const nationalChartData = useMemo(() => {
        const grouped = {};

        nationalData.forEach((row) => {
            const values = Object.values(row);

            const date = values[0];
            const code = String(values[1] || "").trim();
            const price = Number(values[2]);

            if (!date || !code || Number.isNaN(price)) {
                return;
            }

            if (!grouped[date]) {
                grouped[date] = { date };
            }

            grouped[date][code] = price;
        });

        return Object.values(grouped);
    }, [nationalData]);

    const regionalChartData = useMemo(() => {
        return regionalData
            .filter((row) => {
                const values = Object.values(row);

                const rowDate = String(values[0] || "").trim();
                const rowFuel = String(values[2] || "").trim();

                return rowDate === selectedDate && rowFuel === fuelType;
            })
            .map((row) => {
                const values = Object.values(row);
                const regionCode = String(values[1] || "").trim();

                return {
                    region: regionCode,
                    regionFullName: regionNameMap[regionCode] || regionCode,
                    price: Number(values[3]),
                };
            })
            .filter((row) => row.region && row.price > 0)
            .sort((a, b) => b.price - a.price);
    }, [regionalData, selectedDate, fuelType, regionNameMap]);

    const brandComparisonData = useMemo(() => {
        return brandData
            .filter((row) => {
                const values = Object.values(row);

                const rowDate = String(values[0] || "").trim();
                const rowCity = String(values[2] || "").trim();
                const rowFuel = String(values[4] || "").trim();

                return (
                    rowDate === brandDate &&
                    rowCity === brandCity &&
                    rowFuel === brandFuelType
                );
            })
            .map((row) => {
                const values = Object.values(row);

                const brandCode = String(values[1] || "").trim();
                const cityCode = String(values[2] || "").trim();
                const regionCode = String(values[3] || "").trim();

                return {
                    brandCode,
                    brandName: brandNameMap[brandCode] || brandCode,
                    cityCode,
                    cityName: cityNameMap[cityCode]?.cityName || cityCode,
                    regionCode,
                    regionName: regionNameMap[regionCode] || regionCode,
                    price: Number(values[5]),
                };
            })
            .filter((row) => row.brandName && row.price > 0)
            .sort((a, b) => b.price - a.price);
    }, [
        brandData,
        brandDate,
        brandCity,
        brandFuelType,
        brandNameMap,
        cityNameMap,
        regionNameMap,
    ]);

    const cityOptions = useMemo(() => {
        return Object.entries(cityNameMap)
            .map(([code, info]) => ({
                code,
                name: info.cityName,
                regionName: info.regionName,
            }))
            .sort((a, b) => a.name.localeCompare(b.name));
    }, [cityNameMap]);

    function toggleFuel(code) {
        setVisibleFuels((current) => {
            if (current.includes(code)) {
                return current.filter((fuel) => fuel !== code);
            }

            return [...current, code];
        });
    }

    function RegionalTooltip({ active, payload }) {
        if (active && payload && payload.length > 0) {
            const data = payload[0].payload;

            return (
                <div className="custom-tooltip">
                    <p>
                        <strong>{data.regionFullName}</strong>
                    </p>
                    <p>Fuel type: {fuelLabels[fuelType]}</p>
                    <p>Date: {selectedDate}</p>
                    <p>Price: ${data.price.toFixed(3)} NZD/L</p>
                </div>
            );
        }

        return null;
    }

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
        <div className="app">
            <header className="hero">
                <h1>NZ Fuel Price Explorer</h1>
            </header>

            <nav className="tabs">
                <button
                    className={page === "overview" ? "active" : ""}
                    onClick={() => setPage("overview")}
                >
                    Overview
                </button>

                <button
                    className={page === "brand" ? "active" : ""}
                    onClick={() => setPage("brand")}
                >
                    Brand Comparison
                </button>
            </nav>

            {page === "overview" && (
                <main className="dashboard">
                    <section className="card">
                        <h2>National Fuel Price Trend</h2>
                        <p className="card-description">
                            Compare national weekly average prices across different fuel
                            types.
                        </p>

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

                        <ResponsiveContainer width="100%" height={420}>
                            <LineChart data={nationalChartData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" minTickGap={30} />
                                <YAxis domain={["auto", "auto"]} />
                                <Tooltip />

                                {visibleFuels.includes("P91") && (
                                    <Line
                                        type="monotone"
                                        dataKey="P91"
                                        name="Regular Petrol 91"
                                        stroke={fuelColors.P91}
                                        strokeWidth={2}
                                        dot={false}
                                        connectNulls
                                    />
                                )}

                                {visibleFuels.includes("P95") && (
                                    <Line
                                        type="monotone"
                                        dataKey="P95"
                                        name="Premium Petrol 95"
                                        stroke={fuelColors.P95}
                                        strokeWidth={2}
                                        dot={false}
                                        connectNulls
                                    />
                                )}

                                {visibleFuels.includes("P98") && (
                                    <Line
                                        type="monotone"
                                        dataKey="P98"
                                        name="Premium Petrol 98"
                                        stroke={fuelColors.P98}
                                        strokeWidth={2}
                                        dot={false}
                                        connectNulls
                                    />
                                )}

                                {visibleFuels.includes("DSL") && (
                                    <Line
                                        type="monotone"
                                        dataKey="DSL"
                                        name="Automotive Diesel"
                                        stroke={fuelColors.DSL}
                                        strokeWidth={2}
                                        dot={false}
                                        connectNulls
                                    />
                                )}
                            </LineChart>
                        </ResponsiveContainer>
                    </section>

                    <section className="card">
                        <h2>Regional Price Comparison</h2>
                        <p className="card-description">
                            Compare regional prices for the selected fuel type and date.
                        </p>

                        <div className="chart-filters">
                            <div className="filter-item">
                                <label>Fuel Type</label>
                                <select
                                    value={fuelType}
                                    onChange={(e) => setFuelType(e.target.value)}
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
                                    value={selectedDate}
                                    onChange={(e) => setSelectedDate(e.target.value)}
                                >
                                    {availableDates.map((date) => (
                                        <option key={date} value={date}>
                                            {date}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <ResponsiveContainer width="100%" height={520}>
                            <BarChart
                                data={regionalChartData}
                                layout="vertical"
                                margin={{ top: 10, right: 30, left: 20, bottom: 10 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis type="number" domain={["auto", "auto"]} />
                                <YAxis
                                    type="category"
                                    dataKey="region"
                                    width={60}
                                    interval={0}
                                />
                                <Tooltip content={<RegionalTooltip />} />
                                <Bar
                                    dataKey="price"
                                    name={`${fuelLabels[fuelType]} regional average`}
                                    fill={fuelColors[fuelType]}
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </section>
                </main>
            )}

            {page === "brand" && (
                <main className="single-page">
                    <section className="card">
                        <h2>Brand Comparison</h2>
                        <p className="card-description">
                            Compare fuel prices between brands in a selected city.
                        </p>

                        <div className="chart-filters">
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
                        </div>

                        {brandComparisonData.length === 0 ? (
                            <p className="card-description">
                                No brand price data is available for this city, fuel type, and
                                date.
                            </p>
                        ) : (
                            <ResponsiveContainer width="100%" height={520}>
                                <BarChart
                                    data={brandComparisonData}
                                    margin={{ top: 10, right: 30, left: 20, bottom: 40 }}
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
                    </section>
                </main>
            )}
        </div>
    );
}

export default App;