import React from 'react';

interface RiskExplanationProps {
  riskAssessment: {
    rainfall_significant_probability: number | null;
    cells: Array<{
      cell_id: string;
      inundation_risk_probability: number;
      risk_class: string;
    }>;
    limitation_note: string;
  } | null;
  weatherData: Record<string, number> | null;
}

const RiskExplanation: React.FC<RiskExplanationProps> = ({ 
  riskAssessment, 
  weatherData 
}) => {
  if (!riskAssessment) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
        <h3 className="mb-4 text-lg font-semibold text-white">Risk Explanation</h3>
        <p className="text-gray-400">Loading risk assessment data...</p>
      </div>
    );
  }

  // Determine overall risk level based on the highest risk cell
  const getOverallRiskLevel = (cells: any[]) => {
    if (!cells || cells.length === 0) return 'NORMAL';
    
    const riskLevels: Record<string, number> = {
      'NORMAL': 0,
      'WATCH': 1,
      'WARNING': 2,
      'HIGH_RISK': 3
    };
    
    let maxRisk = 0;
    cells.forEach(cell => {
      const riskLevel = riskLevels[cell.risk_class] || 0;
      if (riskLevel > maxRisk) maxRisk = riskLevel;
    });
    
    return Object.keys(riskLevels).find(key => riskLevels[key] === maxRisk) || 'NORMAL';
  };

  const overallRiskLevel = getOverallRiskLevel(riskAssessment.cells);
  
  // Get contributing factors
  const getContributingFactors = () => {
    const factors: string[] = [];
    
    if (weatherData) {
      if (weatherData['precipitation'] && weatherData['precipitation'] > 5) {
        factors.push('Heavy recent precipitation');
      }
      if (weatherData['relative_humidity_2m'] && weatherData['relative_humidity_2m'] > 80) {
        factors.push('High atmospheric humidity');
      }
      if (weatherData['wind_speed_10m'] && weatherData['wind_speed_10m'] > 15) {
        factors.push('Strong wind patterns');
      }
    }
    
    // Always include these as they're part of the model
    factors.push('Regional topography and drainage patterns');
    factors.push('Historical flood patterns in the area');
    
    return factors;
  };

  const contributingFactors = getContributingFactors();
  
  // Get risk description based on level
  const getRiskDescription = (level: string) => {
    switch (level) {
      case 'NORMAL':
        return 'Current conditions indicate normal flood risk levels. Routine monitoring is sufficient.';
      case 'WATCH':
        return 'Elevated flood risk detected. Increased vigilance and monitoring of vulnerable areas recommended.';
      case 'WARNING':
        return 'Significant flood risk identified. Preparatory measures should be considered for at-risk communities.';
      case 'HIGH_RISK':
        return 'High flood risk probability. Immediate attention and potential preventive actions advised.';
      default:
        return 'Risk level assessment unavailable.';
    }
  };

  return (
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
      <h3 className="mb-4 text-lg font-semibold text-white">Risk Explanation</h3>
      
      <div className="space-y-5">
        {/* Current Risk Level */}
        <div className="text-center">
          <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium 
            ${overallRiskLevel === 'NORMAL' ? 'bg-green-500/20 text-green-400' :
              overallRiskLevel === 'WATCH' ? 'bg-blue-500/20 text-blue-400' :
              overallRiskLevel === 'WARNING' ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-red-500/20 text-red-400'}`}
          >
            Risk Level: {overallRiskLevel.replace('_', ' ')}
          </div>
          <p className="mt-2 text-sm text-gray-300">
            {getRiskDescription(overallRiskLevel)}
          </p>
        </div>
        
        {/* Contributing Factors */}
        <div>
          <h4 className="font-semibold text-white mb-2">Contributing Factors</h4>
          <ul className="list-disc list-inside space-y-1 text-gray-300 text-sm">
            {contributingFactors.map((factor, index) => (
              <li key={index}>{factor}</li>
            ))}
          </ul>
        </div>
        
        {/* Model Information */}
        <div className="border-t border-gray-700/50 pt-4">
          <h4 className="font-semibold text-white mb-2">Model Information</h4>
          <p className="text-gray-300 text-sm">
            <strong>AI#1 Model:</strong> {riskAssessment.rainfall_significant_probability !== null 
              ? `Active (v${'unknown'})` 
              : 'Inactive'}
          </p>
          <p className="text-gray-300 text-sm">
            <strong>AI#2 Model:</strong> Active (baseline production)
          </p>
          <p className="text-gray-300 text-sm">
            <strong>Spatial Resolution:</strong> {riskAssessment.cells.length > 0 
              ? `${riskAssessment.cells.length} cells` 
              : 'Unknown'}
          </p>
        </div>
        
        {/* Limitations */}
        <div className="border-t border-gray-700/50 pt-4">
          <h4 className="font-semibold text-white mb-2">Scientific Limitations</h4>
          <p className="text-gray-300 text-sm italic">
            {riskAssessment.limitation_note}
          </p>
          <p className="text-gray-300 text-sm mt-1">
            Risk classification thresholds are engineering/demo values and 
            have not been independently validated against additional flood events.
          </p>
        </div>
      </div>
    </div>
  );
};

export default RiskExplanation;
