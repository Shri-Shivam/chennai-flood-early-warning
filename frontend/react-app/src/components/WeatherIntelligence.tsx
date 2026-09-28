import React from 'react';

interface WeatherIntelligenceProps {
  weatherData: Record<string, number> | null;
  rainfallPrediction: {
    model_version: string;
    significant_rainfall_probability: number;
    forecast_horizon: string;
    threshold_note: string;
  } | null;
}

const WeatherIntelligence: React.FC<WeatherIntelligenceProps> = ({ 
  weatherData, 
  rainfallPrediction 
}) => {
  // Extract key weather metrics from the features
  const getWeatherValue = (key: string, defaultValue: string = '--') => {
    if (!weatherData) return defaultValue;
    const value = weatherData[key];
    return typeof value === 'number' ? value.toFixed(1) : defaultValue;
  };

  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
      {/* Current Weather Card */}
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-4">
        <h3 className="mb-2 text-lg font-semibold text-white">Current Weather</h3>
        <div className="space-y-2">
          <div className="flex justify-between text-gray-300">
            <span>Temperature:</span>
            <span id="current-temp">{getWeatherValue('temperature_2m')}°C</span>
          </div>
          <div className="flex justify-between text-gray-300">
            <span>Humidity:</span>
            <span id="current-humidity">{getWeatherValue('relative_humidity_2m')}%</span>
          </div>
          <div className="flex justify-between text-gray-300">
            <span>Wind Speed:</span>
            <span id="current-wind">{getWeatherValue('wind_speed_10m')} km/h</span>
          </div>
          <div className="flex justify-between text-gray-300">
            <span>Pressure:</span>
            <span id="current-pressure">{getWeatherValue('surface_pressure')} hPa</span>
          </div>
          <div className="flex justify-between text-gray-300">
            <span>Precipitation:</span>
            <span id="current-precip">{getWeatherValue('precipitation')} mm</span>
          </div>
        </div>
      </div>
      
      {/* AI#1 Rainfall Intelligence Card */}
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-4">
        <h3 className="mb-2 text-lg font-semibold text-white">Rainfall Intelligence (AI#1)</h3>
        {rainfallPrediction ? (
          <>
            <div className="space-y-3">
              <div className="flex justify-between text-gray-300">
                <span>Significant Rainfall Probability:</span>
                <span className="font-mono">
                  {(rainfallPrediction.significant_rainfall_probability * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <div 
                  className={`w-3 h-3 rounded-full 
                    ${rainfallPrediction.significant_rainfall_probability >= 0.5 
                      ? 'bg-red-500' 
                      : rainfallPrediction.significant_rainfall_probability >= 0.3 
                        ? 'bg-yellow-500' 
                        : 'bg-green-500'}`}
                ></div>
                <span className="text-sm">
                  {rainfallPrediction.significant_rainfall_probability >= 0.5 
                    ? 'High Risk' 
                    : rainfallPrediction.significant_rainfall_probability >= 0.3 
                      ? 'Moderate Risk' 
                      : 'Low Risk'}
                </span>
              </div>
              <p className="text-xs text-gray-400">
                Probability of ≥20mm rainfall in next 6 hours
              </p>
              <p className="text-xs text-gray-400 italic">
                {rainfallPrediction.threshold_note}
              </p>
            </div>
          </>
        ) : (
          <p className="text-gray-400">Loading rainfall prediction...</p>
        )}
      </div>
      
      {/* Hourly Forecast Card */}
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-4 col-span-2 sm:col-span-1 lg:col-span-2">
        <h3 className="mb-2 text-lg font-semibold text-white">Hourly Forecast</h3>
        <div className="space-x-4 overflow-x-auto">
          {/* In a real implementation, we'd map over hourly forecast data */}
          <div className="min-w-[100px] flex flex-col items-center space-y-2">
            <p className="text-xs text-gray-400">Now</p>
            <p className="text-white font-mono">{getWeatherValue('temperature_2m')}°C</p>
            <p className="text-xs text-gray-300">{getWeatherValue('precipitation')}mm</p>
          </div>
          <div className="min-w-[100px] flex flex-col items-center space-y-2">
            <p className="text-xs text-gray-400">+1h</p>
            <p className="text-white font-mono">--°C</p>
            <p className="text-xs text-gray-300">--mm</p>
          </div>
          <div className="min-w-[100px] flex flex-col items-center space-y-2">
            <p className="text-xs text-gray-400">+2h</p>
            <p className="text-white font-mono">--°C</p>
            <p className="text-xs text-gray-300">--mm</p>
          </div>
          <div className="min-w-[100px] flex flex-col items-center space-y-2">
            <p className="text-xs text-gray-400">+3h</p>
            <p className="text-white font-mono">--°C</p>
            <p className="text-xs text-gray-300">--mm</p>
          </div>
        </div>
      </div>
      
      {/* Daily Forecast Card */}
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-4 lg:col-span-2">
        <h3 className="mb-2 text-lg font-semibold text-white">Daily Outlook</h3>
        <div className="space-y-3">
          <div className="flex justify-between text-gray-300">
            <span>Today's High:</span>
            <span className="font-mono">--°C</span>
          </div>
          <div className="flex justify-between text-gray-300">
            <span>Today's Low:</span>
            <span className="font-mono">--°C</span>
          </div>
          <div className="flex justify-between text-gray-300">
            <span>Rain Chance:</span>
            <span className="font-mono">--%</span>
          </div>
          <div className="flex justify-between text-gray-300">
            <span>Rain Amount:</span>
            <span className="font-mono">--mm</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WeatherIntelligence;
