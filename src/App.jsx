import { useEffect, useMemo, useState } from "react";
import Papa from "papaparse";
import OverviewPage from "./components/OverviewPage";
import BrandComparisonPage from "./components/BrandComparisonPage";
import LocationComparisonPage from "./components/LocationComparisonPage";
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

const brandColors = {
    BP: "#2563eb",
    MOBIL: "#16a34a",
    Z: "#E10600",
    CAL: "#FF8C00",
    NPD: "#7B2CBF",
    GAS: "#00A3E0",
    GULL: "#111827",
    ALLIED: "#C026D3",
};

const personaLabels = {
    everyday: "Everyday Driver",
    truck: "Truck Driver",
    fleet: "Fleet Manager",
};

function App() {
    const [persona, setPersona] = useState(null);
    const [page, setPage] = useState("overview");

    const [selectedRegion, setSelectedRegion] = useState(null);
    const [selectedCity, setSelectedCity] = useState("");

    const [nationalData, setNationalData] = useState([]);
    const [regionalData, setRegionalData] = useState([]);
    const [regionsData, setRegionsData] = useState([]);
    const [citiesData, setCitiesData] = useState([]);
    const [cityFuelData, setCityFuelData] = useState([]);
    const [brandData, setBrandData] = useState([]);
    const [brandsData, setBrandsData] = useState([]);

    const [visibleFuels, setVisibleFuels] = useState(["P91", "P95", "P98", "DSL"]);

    const [brandCity, setBrandCity] = useState("AKC");
    const [brandFuelType, setBrandFuelType] = useState("P91");
    const [brandDate, setBrandDate] = useState("");
    const [brandViewMode, setBrandViewMode] = useState("snapshot");
    const [visibleBrands, setVisibleBrands] = useState([]);

    useEffect(() => {
        loadCsv("/data/national_weekly.csv", setNationalData);
        loadCsv("/data/fuel_prices_long.csv", setRegionalData);
        loadCsv("/data/regions.csv", setRegionsData);
        loadCsv("/data/cities.csv", setCitiesData);
        loadCsv("/data/city_fuel_prices_long.csv", setCityFuelData);
        loadCsv("/data/brand_city_prices_long.csv", setBrandData);
        loadCsv("/data/brands.csv", setBrandsData);
    }, []);

    useEffect(() => {
        setSelectedCity("");
    }, [selectedRegion]);

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

    function normalizeRegionName(name) {
        return String(name || "")
            .replace(" Region", "")
            .replace("ū", "u")
            .replace("Ū", "U")
            .replace("-", " ")
            .trim()
            .toLowerCase();
    }

    function formatPrice(value) {
        if (value === null || value === undefined || Number.isNaN(value)) {
            return "N/A";
        }

        return `$${Number(value).toFixed(3)}/L`;
    }

    function formatDifference(value) {
        if (value === null || value === undefined || Number.isNaN(value)) {
            return "N/A";
        }

        const sign = value > 0 ? "+" : "";
        return `${sign}$${Number(value).toFixed(3)}/L`;
    }

    function formatPercent(value) {
        if (value === null || value === undefined || Number.isNaN(value)) {
            return "N/A";
        }

        const sign = value > 0 ? "+" : "";
        return `${sign}${Number(value).toFixed(1)}%`;
    }

    const availableDates = useMemo(() => {
        const dates = nationalData
            .map((row) => Object.values(row)[0])
            .filter(Boolean);

        return [...new Set(dates)];
    }, [nationalData]);

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

    const nationalPriceByDate = useMemo(() => {
        const map = {};

        nationalChartData.forEach((row) => {
            if (row.date) {
                map[row.date] = row;
            }
        });

        return map;
    }, [nationalChartData]);

    const selectedRegionTrendData = useMemo(() => {
        if (!selectedRegion) {
            return [];
        }

        const grouped = {};

        regionalData.forEach((row) => {
            const values = Object.values(row);

            const date = String(values[0] || "").trim();
            const regionCode = String(values[1] || "").trim();
            const fuelCode = String(values[2] || "").trim();
            const price = Number(values[3]);

            const regionFullName = regionNameMap[regionCode] || regionCode;

            const isSelectedRegion =
                normalizeRegionName(regionFullName) === normalizeRegionName(selectedRegion);

            if (!date || !fuelCode || Number.isNaN(price) || !isSelectedRegion) {
                return;
            }

            if (!grouped[date]) {
                grouped[date] = { date };
            }

            grouped[date][fuelCode] = price;
        });

        return Object.values(grouped);
    }, [regionalData, selectedRegion, regionNameMap]);

    const selectedCityTrendData = useMemo(() => {
        if (!selectedCity) {
            return [];
        }

        const grouped = {};

        cityFuelData.forEach((row) => {
            const values = Object.values(row);

            const date = String(values[0] || "").trim();
            const cityCode = String(values[1] || "").trim();
            const fuelCode = String(values[3] || "").trim();
            const price = Number(values[4]);

            if (!date || cityCode !== selectedCity || !fuelCode || Number.isNaN(price)) {
                return;
            }

            if (!grouped[date]) {
                grouped[date] = { date };
            }

            grouped[date][fuelCode] = price;
        });

        return Object.values(grouped);
    }, [cityFuelData, selectedCity]);

    const activeTrendData = selectedCity ? selectedCityTrendData : selectedRegionTrendData;

    const trendSummary = useMemo(() => {
        if (!activeTrendData || activeTrendData.length === 0) {
            return null;
        }

        const latest = activeTrendData[activeTrendData.length - 1];

        const p91Values = activeTrendData
            .map((row) => Number(row.P91))
            .filter((value) => !Number.isNaN(value));

        const averageP91 =
            p91Values.length > 0
                ? p91Values.reduce((sum, value) => sum + value, 0) / p91Values.length
                : null;

        return {
            latestDate: latest.date,
            latestP91: latest.P91,
            latestDiesel: latest.DSL,
            averageP91,
            records: activeTrendData.length,
        };
    }, [activeTrendData]);

    const nationalComparison = useMemo(() => {
        if (!activeTrendData || activeTrendData.length === 0) {
            return null;
        }

        const latestLocal = activeTrendData[activeTrendData.length - 1];
        const latestDate = latestLocal.date;
        const nationalForDate = nationalPriceByDate[latestDate];

        if (!nationalForDate) {
            return null;
        }

        function compareFuel(fuelCode) {
            const localPrice = Number(latestLocal[fuelCode]);
            const nationalPrice = Number(nationalForDate[fuelCode]);

            if (Number.isNaN(localPrice) || Number.isNaN(nationalPrice)) {
                return null;
            }

            const difference = localPrice - nationalPrice;
            const percentDifference =
                nationalPrice !== 0 ? (difference / nationalPrice) * 100 : null;

            return {
                localPrice,
                nationalPrice,
                difference,
                percentDifference,
            };
        }

        return {
            date: latestDate,
            P91: compareFuel("P91"),
            DSL: compareFuel("DSL"),
        };
    }, [activeTrendData, nationalPriceByDate]);

    const cityOptions = useMemo(() => {
        return Object.entries(cityNameMap)
            .map(([code, info]) => ({
                code,
                name: info.cityName,
                regionCode: info.regionCode,
                regionName: info.regionName,
            }))
            .sort((a, b) => a.name.localeCompare(b.name));
    }, [cityNameMap]);

    const regionOptions = useMemo(() => {
        return Object.entries(regionNameMap)
            .map(([code, name]) => ({
                code,
                name,
            }))
            .filter((region) => region.name !== "Area Outside Region")
            .sort((a, b) => a.name.localeCompare(b.name));
    }, [regionNameMap]);

    const filteredCityOptions = useMemo(() => {
        if (!selectedRegion) {
            return [];
        }

        return cityOptions.filter((city) => {
            return normalizeRegionName(city.regionName) === normalizeRegionName(selectedRegion);
        });
    }, [cityOptions, selectedRegion]);

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

    const brandTrendData = useMemo(() => {
        const grouped = {};

        brandData.forEach((row) => {
            const values = Object.values(row);

            const rowDate = String(values[0] || "").trim();
            const brandCode = String(values[1] || "").trim();
            const rowCity = String(values[2] || "").trim();
            const rowFuel = String(values[4] || "").trim();
            const price = Number(values[5]);

            if (
                !rowDate ||
                !brandCode ||
                rowCity !== brandCity ||
                rowFuel !== brandFuelType ||
                Number.isNaN(price)
            ) {
                return;
            }

            if (!grouped[rowDate]) {
                grouped[rowDate] = { date: rowDate };
            }

            grouped[rowDate][brandCode] = price;
        });

        return Object.values(grouped);
    }, [brandData, brandCity, brandFuelType]);

    const brandTrendSeries = useMemo(() => {
        const brandCodes = new Set();

        brandData.forEach((row) => {
            const values = Object.values(row);

            const brandCode = String(values[1] || "").trim();
            const rowCity = String(values[2] || "").trim();
            const rowFuel = String(values[4] || "").trim();

            if (brandCode && rowCity === brandCity && rowFuel === brandFuelType) {
                brandCodes.add(brandCode);
            }
        });

        return Array.from(brandCodes).sort();
    }, [brandData, brandCity, brandFuelType]);

    useEffect(() => {
        if (brandTrendSeries.length > 0) {
            setVisibleBrands(brandTrendSeries);
        }
    }, [brandTrendSeries]);

    function handlePersonaSelect(selectedPersona) {
        setPersona(selectedPersona);
        setSelectedRegion(null);
        setSelectedCity("");

        if (selectedPersona === "everyday") {
            setPage("overview");
            setVisibleFuels(["P91", "P95", "DSL"]);
        }

        if (selectedPersona === "truck") {
            setPage("overview");
            setVisibleFuels(["DSL"]);
            setBrandFuelType("DSL");
        }

        if (selectedPersona === "fleet") {
            setPage("brand");
            setVisibleFuels(["P91", "P95", "P98", "DSL"]);
        }
    }

    function resetPersona() {
        setPersona(null);
        setPage("overview");
        setSelectedRegion(null);
        setSelectedCity("");
        setVisibleFuels(["P91", "P95", "P98", "DSL"]);
    }

    function toggleFuel(code) {
        setVisibleFuels((current) => {
            if (current.includes(code)) {
                return current.filter((fuel) => fuel !== code);
            }

            return [...current, code];
        });
    }

    function toggleBrand(code) {
        setVisibleBrands((current) => {
            if (current.includes(code)) {
                return current.filter((brand) => brand !== code);
            }

            return [...current, code];
        });
    }

    if (!persona) {
        return (
            <div className="landing-page">
                <section className="landing-card">
                    <h1>NZ Fuel Price Explorer</h1>
                    <p className="landing-subtitle">
                        Choose a user type to customise the dashboard view.
                    </p>

                    <div className="persona-grid">
                        <button
                            className="persona-card"
                            onClick={() => handlePersonaSelect("everyday")}
                        >
                            <h2>Everyday Driver</h2>
                            <p>
                                Focus on local city prices and common fuel types for daily driving.
                            </p>
                        </button>

                        <button
                            className="persona-card"
                            onClick={() => handlePersonaSelect("truck")}
                        >
                            <h2>Truck Driver</h2>
                            <p>
                                Focus on Diesel prices and regional price changes across New Zealand.
                            </p>
                        </button>

                        <button
                            className="persona-card"
                            onClick={() => handlePersonaSelect("fleet")}
                        >
                            <h2>Fleet Manager</h2>
                            <p>
                                Compare regions, cities, and brands to support fuel cost decisions.
                            </p>
                        </button>
                    </div>
                </section>
            </div>
        );
    }

    return (
        <div className="app">
            <header className="hero">
                <h1>NZ Fuel Price Explorer</h1>
                <p>
                    Current view: <strong>{personaLabels[persona]}</strong>
                    <button className="change-persona-button" onClick={resetPersona}>
                        Change user type
                    </button>
                </p>
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

                <button
                    className={page === "location" ? "active" : ""}
                    onClick={() => setPage("location")}
                >
                    Location Comparison
                </button>
            </nav>

            {page === "overview" && (
                <OverviewPage
                    fuelLabels={fuelLabels}
                    fuelColors={fuelColors}
                    visibleFuels={visibleFuels}
                    toggleFuel={toggleFuel}
                    nationalChartData={nationalChartData}
                    selectedRegion={selectedRegion}
                    setSelectedRegion={setSelectedRegion}
                    selectedCity={selectedCity}
                    setSelectedCity={setSelectedCity}
                    cityNameMap={cityNameMap}
                    filteredCityOptions={filteredCityOptions}
                    trendSummary={trendSummary}
                    nationalComparison={nationalComparison}
                    formatPrice={formatPrice}
                    formatDifference={formatDifference}
                    formatPercent={formatPercent}
                    activeTrendData={activeTrendData}
                />
            )}

            {page === "brand" && (
                <BrandComparisonPage
                    fuelLabels={fuelLabels}
                    fuelColors={fuelColors}
                    brandColors={brandColors}
                    brandViewMode={brandViewMode}
                    setBrandViewMode={setBrandViewMode}
                    brandCity={brandCity}
                    setBrandCity={setBrandCity}
                    brandFuelType={brandFuelType}
                    setBrandFuelType={setBrandFuelType}
                    brandDate={brandDate}
                    setBrandDate={setBrandDate}
                    availableDates={availableDates}
                    cityOptions={cityOptions}
                    brandComparisonData={brandComparisonData}
                    brandTrendData={brandTrendData}
                    brandTrendSeries={brandTrendSeries}
                    visibleBrands={visibleBrands}
                    toggleBrand={toggleBrand}
                    brandNameMap={brandNameMap}
                />
            )}

            {page === "location" && (
                <LocationComparisonPage
                    fuelLabels={fuelLabels}
                    regionalData={regionalData}
                    cityFuelData={cityFuelData}
                    nationalPriceByDate={nationalPriceByDate}
                    availableDates={availableDates}
                    regionOptions={regionOptions}
                    cityOptions={cityOptions}
                    regionNameMap={regionNameMap}
                    cityNameMap={cityNameMap}
                    formatPrice={formatPrice}
                    formatDifference={formatDifference}
                    formatPercent={formatPercent}
                />
            )}
        </div>
    );
}

export default App;