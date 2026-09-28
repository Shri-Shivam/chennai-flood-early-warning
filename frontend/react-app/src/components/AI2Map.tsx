import React from 'react';

interface RiskMapData {
  type: string;
  features: Array<{
    type: string;
    properties: {
      cell_id: string;
      inundation_risk_probability: number;
      risk_class: string;
      [key: string]: any;
    };
    geometry: {
      type: string;
      coordinates: number[][][];
    };
  }>;
}

interface AI2MapProps {
  riskMapData: RiskMapData | null;
}

const AI2Map: React.FC<AI2MapProps> = ({ riskMapData }) => {
  if (!riskMapData) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
        <h3 className="mb-2 text-lg font-semibold text-white">Live Flood Risk Map (AI#2)</h3>
        <p className="text-gray-400 text-center py-8">Loading risk map data...</p>
      </div>
    );
  }

  // Count risk levels for display
  const riskCounts = riskMapData.features.reduce((acc: any, feature: any) => {
    const riskClass = feature.properties.risk_class || 'NORMAL';
    acc[riskClass] = (acc[riskClass] || 0) + 1;
    return acc;
  }, {});

  const total = riskMapData.features.length;

  return (
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
      <div className="space-y-4">
        <h3 className="mb-2 text-lg font-semibold text-white">Live Flood Risk Map (AI#2)</h3>

        {/* Map Placeholder */}
        <div className="h-96 w-full bg-gray-900 rounded-lg overflow-hidden relative">
          {/* In a real implementation, this would contain the actual map */}
          <div className="absolute inset-0 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4"></div>
              <p className="text-sm">Loading flood risk map...</p>
              <p className="text-xs text-gray-400 mt-2">
                {total} spatial cells being monitored
              </p>
            </div>
          </div>
        </div>

        {/* Risk Legend */}
        <div className="grid gap-2 sm:grid-cols-2">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-green-500 rounded"></div>
            <span className="text-xs text-gray-300">Normal ({riskCounts.NORMAL || 0} cells)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-blue-500 rounded"></div>
            <span className="text-xs text-gray-300">Watch ({riskCounts.WATCH || 0} cells)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-yellow-500 rounded"></div>
            <span className="text-xs text-gray-300">Warning ({riskCounts.WARNING || 0} cells)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-red-500 rounded"></div>
            <span className="text-xs text-gray-300">High Risk ({riskCounts.HIGH_RISK || 0} cells)</span>
          </div>
        </div>

        {/* Map Controls */}
        <div className="flex justify-between items-center pt-3 border-t border-gray-700/50">
          <div className="flex items-center space-x-3">
            <button
              className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded"
            >
              Zoom In
            </button>
            <button
              className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded"
            >
              Zoom Out
            </button>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-400">Live Data</span>
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          </div>
        </div>

        <p className="text-xs text-gray-400 mt-2 italic">
          Note: For production use with large GeoJSON datasets (>{' '}>70k cells), a performant geospatial renderer like deck.gl or Mapbox GL would be used instead of this simplified placeholder.
        </p>
      </div>
    </div>
  );
};

export default AI2Map;