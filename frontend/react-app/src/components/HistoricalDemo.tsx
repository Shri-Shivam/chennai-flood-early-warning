import React, { useState } from 'react';

interface HistoricalDemoProps {
  location: { lat: number; lng: number };
}

const HistoricalDemo: React.FC<HistoricalDemoProps> = ({ location }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDemoData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Simulate loading historical validation data
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // In a real implementation, this would fetch actual data
    } catch (err) {
      setError('Failed to load historical demonstration data.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDemoData();
  }, [location.lat, location.lng]);

  if (loading) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
        <h3 className="mb-4 text-lg font-semibold text-white">Historical Validation</h3>
        <p className="text-gray-400 text-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto"></div>
          Loading historical data...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
        <h3 className="mb-4 text-lg font-semibold text-white">Historical Validation</h3>
        <p className="text-red-400 text-center">{error}</p>
        <button 
          onClick={loadDemoData}
          className="mt-4 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-500"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
      <h3 className="mb-4 text-lg font-semibold text-white">Historical Validation & Demo</h3>
      
      <div className="space-y-4">
        {/* Demo Notice */}
        <div className="bg-gray-700/50 rounded-lg p-4">
          <h4 className="font-semibold text-white mb-2>Historical Validation Data</h4>
          <p className="text-gray-300">
            This section would demonstrate model performance against historical flood events 
            using validation datasets. In a production implementation, this would show:
          </p>
          <ul className="list-disc list-inset space-y-2 mt-2 text-gray-300">
            <li>Comparison of predicted vs actual flood extents</li>
            <li>Model accuracy, precision, and recall metrics</li>
            <li>Lessons learned from past events</li>
            <li>Temporal analysis of model performance</li>
          </ul>
        </div>
        
        {/* Limitations Notice */}
        <div className="border-t border-gray-700/50 pt-4">
          <h4 className="font-semibold text-white mb-2>Scientific Limitations</h4>
          <p className="text-gray-300 text-sm">
            The AI#1 and AI#2 models have been validated on only two independently verified 
            historical flood episodes. This limited validation means:
          </p>
          <ul className="list-disc list-inset space-y-1 mt-2 text-gray-300 text-sm">
            <li>Model performance may vary with different flood characteristics</li>
            <li>Predictions should be interpreted as probabilistic estimates, not guarantees</li>
            <li>Engineering/demo risk thresholds are used for classification purposes</li>
            <li>Continuous validation with additional events is recommended</li>
          </ul>
          <p className="text-gray-300 text-sm mt-2">
            Always consult official emergency management sources during actual flood events.
          </p>
        </div>
      </div>
    </div>
  );
};

export default HistoricalDemo;
