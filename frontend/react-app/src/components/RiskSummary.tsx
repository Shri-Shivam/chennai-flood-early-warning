import React from 'react';

interface RiskSummaryProps {
  riskAssessment: {
    rainfall_significant_probability: number | null;
    cells: Array<{
      cell_id: string;
      inundation_risk_probability: number;
      risk_class: string;
    }>;
    limitation_note: string;
  } | null;
  riskMapData: {
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
  } | null;
}

const RiskSummary: React.FC<RiskSummaryProps> = ({ 
  riskAssessment, 
  riskMapData 
}) => {
  if (!riskAssessment && !riskMapData) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
        <h3 className="mb-4 text-lg font-semibold text-white">Flood Risk Summary</h3>
        <p className="text-gray-400">Loading risk assessment data...</p>
      </div>
    );
  }

  // Calculate summary statistics from risk map data
  const highRiskCells = riskMapData?.features.filter(
    (f: any) => f.properties.risk_class === 'HIGH_RISK'
  ).length || 0;
  
  const warningCells = riskMapData?.features.filter(
    (f: any) => f.properties.risk_class === 'WARNING'
  ).length || 0;
  
  const watchCells = riskMapData?.features.filter(
    (f: any) => f.properties.risk_class === 'WATCH'
  ).length || 0;
  
  const normalCells = riskMapData?.features.filter(
    (f: any) => f.properties.risk_class === 'NORMAL'
  ).length || 0;
  
  const totalCells = riskMapData?.features.length || 0;
  
  // Calculate average risk probability
  const avgRiskProbability = riskMapData?.features.reduce(
    (sum: number, f: any) => sum + f.properties.inundation_risk_probability, 0
  ) / totalCells || 0;

  return (
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
      <h3 className="mb-4 text-lg font-semibold text-white">Flood Risk Summary</h3>
      
      {!riskAssessment && !riskMapData ? (
        <p className="text-gray-400">Loading risk assessment data...</p>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
            <div className="text-center">
              <p className="text-sm text-gray-400">Total Areas Monitored</p>
              <p className="text-2xl font-bold text-white">{totalCells}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-400">Average Risk Level</p>
              <p className="text-2xl font-bold text-white">
                {(avgRiskProbability * 100).toFixed(1)}%
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-400">High Risk Zones</p>
              <p className="text-2xl font-bold text-red-500">{highRiskCells}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-400">Warning Zones</p>
              <p className="text-2xl font-bold text-yellow-500">{warningCells}</p>
            </div>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0">
                <div className="w-5 h-5 bg-red-500 rounded-full"></div>
              </div>
              <div>
                <h4 className="font-semibold text-white mb-1">AI#1 Rainfall Prediction</h4>
                <p className="text-gray-300 text-sm">
                  {riskAssessment?.rainfall_significant_probability !== null
                    ? `Probability of ≥20mm rainfall: ${(riskAssessment.rainfall_significant_probability * 100).toFixed(1)}%`
                    : 'Data not available'}
                </p>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0">
                <div className="w-5 h-5 bg-gray-800 rounded-full"></div>
              </div>
              <div>
                <h4 className="font-semibold text-white mb-1">AI#2 Spatial Risk Assessment</h4>
                <p className="text-gray-300 text-sm">
                  {totalCells > 0
                    ? `Analyzing ${totalCells} spatial cells for flood risk`
                    : 'No spatial data available'}
                </p>
              </div>
            </div>
            
            {/* Risk Level Distribution Chart (simplified) */}
            <div className="mt-4">
              <h4 className="font-semibold text-white mb-2">Risk Level Distribution</h4>
              <div className="w-full bg-gray-700/50 rounded-full h-4">
                <div 
                  className="flex h-full"
                  style={{ 
                    width: `${(normalCells / totalCells) * 100}%`,
                    backgroundColor: 'green-400' 
                  }}
                ></div>
                <div 
                  className="flex h-full"
                  style={{ 
                    width: `${(watchCells / totalCells) * 100}%`,
                    backgroundColor: 'blue-400' 
                  }}
                ></div>
                <div 
                  className="flex h-full"
                  style={{ 
                    width: `${(warningCells / totalCells) * 100}%`,
                    backgroundColor: 'yellow-400' 
                  }}
                ></div>
                <div 
                  className="flex h-full"
                  style={{ 
                    width: `${(highRiskCells / totalCells) * 100}%`,
                    backgroundColor: 'red-400' 
                  }}
                ></div>
              </div>
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>Normal</span>
                <span>Watch</span>
                <span>Warning</span>
                <span>High Risk</span>
              </div>
            </div>
            
            <div className="mt-4 pt-4 border-t border-gray-700/50">
              <p className="text-xs text-gray-400 italic">
                {riskAssessment?.limitation_note || 
                 'Models validated on limited historical data. Predictions are probabilistic estimates.'}
              </p>
            </div>
          </>
        )}
      </div>
    );
};

export default RiskSummary;
