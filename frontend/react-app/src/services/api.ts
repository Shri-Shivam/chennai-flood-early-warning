// API service for communicating with the FastAPI backend
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ApiResponse<T> {
  data: T;
  error?: string;
}

// AI#1 Rainfall prediction
interface RainfallFeatures {
  temperature_2m: number;
  relative_humidity_2m: number;
  surface_pressure: number;
  wind_speed_10m: number;
  precipitation: number;
  rain_lag_1h: number;
  rain_lag_3h: number;
  rain_lag_6h: number;
  rain_1h: number;
  rain_3h: number;
  rain_6h: number;
  rain_12h: number;
  rain_24h: number;
  pressure_change_3h: number;
  pressure_change_6h: number;
  humidity_change_3h: number;
  humidity_change_6h: number;
  hour: number;
  month: number;
  day_of_year: number;
}

interface RainfallPredictionResponse {
  model_version: string;
  forecast_horizon: string;
  significant_rainfall_probability: number;
  threshold_note: string;
}

// AI#2 Inundation prediction
interface InundationCellFeatures {
  cell_id: string;
  rain_1h: number;
  rain_3h: number;
  rain_6h: number;
  rain_12h: number;
  rain_24h: number;
  elevation: number;
  slope_degrees: number;
  distance_to_drainage: number;
}

interface InundationRequest {
  cells: InundationCellFeatures[];
}

interface InundationCellResult {
  cell_id: string;
  inundation_risk_probability: number;
}

interface InundationResponse {
  model_version: string;
  results: InundationCellResult[];
  limitation_note: string;
}

// Risk assessment
interface RiskRequest {
  rainfall_features?: RainfallFeatures;
  cells: InundationCellFeatures[];
}

interface CellRiskResult {
  cell_id: string;
  inundation_risk_probability: number;
  risk_class: string;
}

interface RiskResponse {
  rainfall_significant_probability: number | null;
  cells: CellRiskResult[];
  limitation_note: string;
}

// Live inundation prediction (end-to-end pipeline)
interface LiveInundationResponse {
  model_version: string;
  rainfall_probability: number;
  timestamp: string; // ISO string
  limitation_note: string;
  cells: Array<{
    cell_id: string;
    inundation_risk_probability: number;
  }>;
}

// Risk map endpoint
interface RiskMapRequest {
  rainfall_features?: RainfallFeatures;
  cells: InundationCellFeatures[];
}

interface RiskMapResponse {
  cells: Array<{
    cell_id: string;
    inundation_risk_probability: number;
    risk_class: string;
  }>;
  note: string;
}

// Alerts endpoint
interface AlertsRequest {
  cells: CellRiskResult[];
}

interface Alert {
  cell_id: string;
  risk_class: string;
  recommended_actions: Record<string, string[]>;
}

interface AlertsResponse {
  alerts: Alert[];
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async fetchJson<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return {
          data: null as unknown as T,
          error: errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        };
      }

      const data = await response.json();
      return { data };
    } catch (error) {
      return {
        data: null as unknown as T,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // Health check
  async getHealth(): Promise<ApiResponse<{ status: string }>> {
    return this.fetchJson('/health');
  }

  // Model info
  async getModelInfo(): Promise<ApiResponse<{ models: Array<{ name: string; path: string; description: string; feature_names: string[] }> }>> {
    return this.fetchJson('/model-info');
  }

  // AI#1 Rainfall prediction
  async predictRainfall(features: RainfallFeatures): Promise<ApiResponse<RainfallPredictionResponse>> {
    return this.fetchJson<RainfallPredictionResponse>('/predict/rainfall', {
      method: 'POST',
      body: JSON.stringify(features),
    });
  }

  // AI#2 Inundation prediction
  async predictInundation(request: InundationRequest): Promise<ApiResponse<InundationResponse>> {
    return this.fetchJson<InundationResponse>('/predict/inundation', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Risk assessment
  async assessRisk(request: RiskRequest): Promise<ApiResponse<RiskResponse>> {
    return this.fetchJson<RiskResponse>('/predict/risk', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Live inundation prediction (end-to-end pipeline)
  async predictLiveInundation(
    point: { lat: number; lng: number } = { lat: 13.0827, lng: 80.2707 }, // Chennai coordinates
    past_days: number = 2,
    forecast_days: number = 1
  ): Promise<ApiResponse<LiveInundationResponse>> {
    return this.fetchJson<LiveInundationResponse>('/predict/live-inundation', {
      method: 'POST',
      body: JSON.stringify({ point, past_days, forecast_days }),
    });
  }

  // Risk map endpoint
  async getRiskMap(request: RiskMapRequest): Promise<ApiResponse<RiskMapResponse>> {
    return this.fetchJson<RiskMapResponse>('/risk-map', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Alerts endpoint
  async getAlerts(request: AlertsRequest): Promise<ApiResponse<AlertsResponse>> {
    return this.fetchJson<AlertsResponse>('/alerts', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }
}

export const api = new ApiClient(API_BASE_URL);