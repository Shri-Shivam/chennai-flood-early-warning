import React from 'react';

interface Alert {
  cell_id: string;
  risk_class: string;
  recommended_actions: Record<string, string[]>;
}

interface AlertCenterProps {
  alerts: {
    alerts: Alert[];
  } | null;
}

const AlertCenter: React.FC<AlertCenterProps> = ({ alerts }) => {
  if (!alerts || !alerts.alerts || alerts.alerts.length === 0) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
        <h3 className="mb-4 text-lg font-semibold text-white">Recommended Actions</h3>
        <p className="text-gray-400">No alerts currently active.</p>
      </div>
    );
  }

  const getAlertSeverityColor = (risk_class: string) => {
    switch (risk_class.toUpperCase()) {
      case 'NORMAL': return 'bg-green-500/20 text-green-400';
      case 'WATCH': return 'bg-blue-500/20 text-blue-400';
      case 'WARNING': return 'bg-yellow-500/20 text-yellow-400';
      case 'HIGH_RISK': return 'bg-red-500/20 text-red-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  return (
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-6">
      <h3 className="mb-4 text-lg font-semibold text-white">Recommended Actions</h3>
      
      {alerts.alerts.map((alert, index) => (
        <div key={alert.cell_id} className="mb-4 last:mb-0">
          <div className="flex justify-between items-start mb-2">
            <div className="flex items-center space-x-2">
              <div 
                className={`w-3 h-3 rounded-full 
                  ${alert.risk_class === 'NORMAL' ? 'bg-green-500' :
                    alert.risk_class === 'WATCH' ? 'bg-blue-500' :
                    alert.risk_class === 'WARNING' ? 'bg-yellow-500' :
                    'bg-red-500'}`}
              ></div>
              <div>
                <h4 className="font-semibold text-white">
                  Area {alert.cell_id.slice(-4)} /* Show last 4 chars of cell ID */
                </h4>
                <p className="text-xs text-gray-400">
                  Risk Level: {alert.risk_class.replace('_', ' ')}
                </p>
              </div>
            </div>
            <span className={`px-2 py-0.5 rounded text-xs 
              ${getAlertSeverityColor(alert.risk_class)}`}
            >
              {alert.risk_class.replace('_', ' ')}
            </span>
          </div>
          
          <div className="space-y-3">
            {Object.entries(alert.recommended_actions).map(([role, actions]) => (
              <div key={role} className="border-t border-gray-700/50 pt-3">
                <h4 className="font-semibold text-white mb-2">
                  {role.charAt(0).toUpperCase() + role.slice(1)} /* Capitalize first letter */
                </h4>
                <ul className="list-disc list-inside space-y-1 text-gray-300 text-sm">
                  {actions.map((action, actionIndex) => (
                    <li key={actionIndex}>{action}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      ))}
      
      <div className="mt-4 pt-4 border-t border-gray-700/50">
        <p className="text-xs text-gray-400 italic">
          All actions are recommendations for human decision-makers. 
          No automatic system controls are engaged.
        </p>
      </div>
    </div>
  );
};

export default AlertCenter;
