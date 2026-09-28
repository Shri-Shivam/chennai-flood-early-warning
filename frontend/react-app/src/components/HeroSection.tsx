import React from 'react';

interface HeroSectionProps {
  location: {
    name: string;
    coordinates: { lat: number; lng: number };
  };
  lastUpdated: Date;
}

const HeroSection: React.FC<HeroSectionProps> = ({ location, lastUpdated }) => {
  return (
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-gray-700/50 p-6">
      <div className="flex flex-col items-center text-center space-y-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-primary-600 rounded-full flex items-center justify-center">
            <span className="text-white text-2xl">🌊</span>
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">
              {location.name}
            </h1>
            <p className="text-gray-300 sm:text-lg">
              {location.coordinates.lat.toFixed(4)}°N, {location.coordinates.lng.toFixed(4)}°E
            </p>
          </div>
        </div>
        
        <div className="flex flex-col items-center space-x-4 sm:flex-row sm:space-x-6">
          <div className="text-center">
            <p className="text-sm text-gray-400">Current Conditions</p>
            <p className="text-2xl font-semibold text-white" id="temperature">--°C</p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-400">Humidity</p>
            <p className="text-2xl font-semibold text-white" id="humidity">--%</p>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-400">Wind Speed</p>
            <p className="text-2xl font-semibold text-white" id="windSpeed">-- km/h</p>
          </div>
        </div>
        
        <div className="flex justify-between w-full pt-4 border-t border-gray-700/50">
          <div className="text-left">
            <p className="text-xs text-gray-400">Data Source:</p>
            <p className="text-sm font-mono text-gray-300">Open-Meteo API</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-400">Last Updated:</p>
            <p className="text-sm font-mono text-gray-300">
              {lastUpdated.toLocaleTimeString()} {lastUpdated.toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HeroSection;
