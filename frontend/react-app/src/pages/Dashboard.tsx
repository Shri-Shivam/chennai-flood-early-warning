import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import HeroSection from '../components/HeroSection';
import WeatherIntelligence from '../components/WeatherIntelligence';
import RiskSummary from '../components/RiskSummary';
import AI2Map from '../components/AI2Map';
import RiskExplanation from '../components/RiskExplanation';
import AlertCenter from '../components/AlertCenter';
import HistoricalDemo from '../components/HistoricalDemo';

const Dashboard: React.FC = () => {
  const [location, setLocation] = useState<{ lat: number; lng: number }>({ lat: 13.0827, lng: 80.2707 }); // Chennai coordinates
  const [weatherData, setWeatherData] = useState<any>(null);
  const [rainfallPrediction, setRainfallPrediction] = useState<any>(null);
  const [riskAssessment, setRiskAssessment] = useState<any>(null);
  const [riskMapData, setRiskMapData] = useState<any>(null);
  const [alerts, setAlerts] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useType<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch live weather and run the full pipeline
      const liveInundationResponse = await api.predictLiveInundation({
        point: location,
        past_days: 2,
        forecast_days: 1
      });

      if (liveInundationResponse.data) {
        // Update rainfall prediction (AI#1) from live inundation response
        setRainfallPrediction({
          model_version: liveInundationResponse.data.model_version,
          significant_rainfall_probability: liveInundationResponse.data.rainfall_probability,
          forecast_horizon: "next 6 hours",
          threshold_note: liveInundationResponse.data.limitation_note
        });

        // Prepare risk assessment using live inundation response data
        // We need to add risk_class to each cell based on inundation probability
        const riskAssessmentData = {
          rainfall_significant_probability: liveInundationResponse.data.rainfall_probability,
          cells: liveInundationResponse.data.cells.map((cell: any) => ({
            cell_id: cell.cell_id,
            inundation_risk_probability: cell.inundation_risk_probability,
            // Calculate risk class using the same thresholds as backend
            risk_class: calculateRiskClass(cell.inundation_risk_probability)
          })),
          limitation_note: liveInundationResponse.data.limitation_note
        };
        setRiskAssessment(riskAssessmentData);

        // Prepare risk map data for RiskSummary and AI2Map components
        // For now, we'll provide the cells data without geometry since:
        // 1. RiskSummary doesn't use geometry for its calculations
        // 2. AI2Map is currently a placeholder component
        // In a future implementation with a proper map renderer, we would join with spatial features
        const riskMapDataForSummary = {
          type: "FeatureCollection",
          features: liveInundationResponse.data.cells.map((cell: any) => ({
            type: "Feature",
            properties: {
              cell_id: cell.cell_id,
              inundation_risk_probability: cell.inundation_risk_probability,
              risk_class: calculateRiskClass(cell.inundation_risk_probability)
            },
            geometry: {
              type: "Point",
              coordinates: [0, 0] // Placeholder - actual geometry would come from spatial features
            }
          }))
        };
        setRiskMapData(riskMapDataForSummary);

        // Get alerts based on the risk assessment
        if (riskAssessmentData.cells && riskAssessmentData.cells.length > 0) {
          const alertsResponse = await api.getAlerts({
            cells: riskAssessmentData.cells.map((cell: any) => ({
              cell_id: cell.cell_id,
              inundation_risk_probability: cell.inundation_risk_probability,
              risk_class: cell.risk_class
            }))
          });

          if (alertsResponse.data) {
            setAlerts(alertsResponse.data);
          }
        }

        // Note: We don't have access to the detailed weather features (temperature, humidity, etc.)
        // from the live inundation response, so we leave weatherData as null
        // The UI will show "Unavailable" for these fields rather than fake data
        setWeatherData(null);
      }
    } catch (err) {
      setError('Failed to load data. Please try again later.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Helper function to calculate risk class from inundation probability
  // Using the same thresholds as the backend (from src/services/risk_engine.py)
  const calculateRiskClass = (probability: number): string => {
    if (probability >= 0.60) return 'HIGH_RISK';
    if (probability >= 0.30) return 'WARNING';
    if (probability >= 0.10) return 'WATCH';
    return 'NORMAL';
  };

  useEffect(() => {
    fetchData();

    // Set up interval for periodic updates (every 5 minutes)
    const intervalId = setInterval(fetchData, 5 * 60 * 1000);

    return () => clearInterval(intervalId);
  }, [location]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="mt-2 text-gray-600">Loading flood intelligence data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-red-50">
        <div className="text-center">
          <p className="text-red-600">{error}</p>
          <button
            onClick={fetchData}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <HeroSection
        location={{ name: "Chennai, India", coordinates: location }}
        lastUpdated={new Date()} // Would come from API in real implementation
      />

      {/* Weather Intelligence Section */}
      <WeatherIntelligence
        weatherData={weatherData}
        rainfallPrediction={rainfallPrediction}
      />

      {/* Risk Summary Section */}
      <RiskSummary
        riskAssessment={riskAssessment}
        riskMapData={riskMapData}
      />

      {/* Main Content Area (Two Columns) */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-8">
        {/* Left Column: Spatial Focus */}
        <section className="space-y-6">
          <AI2Map
            riskMapData={riskMapData}
          />
          <RiskExplanation
            riskAssessment={riskAssessment}
            weatherData={weatherData}
          />
        </section>

        {/* Right Column: Explanatory Focus */}
        <section className="space-y-6">
          <AlertCenter
            alerts={alerts}
          />
          <HistoricalDemo
            location={location}
          />
        </section>
      </div>
    </div>
  );
};

export default Dashboard;