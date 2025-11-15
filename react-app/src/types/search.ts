// Типы для поисковых запросов и ответов

export interface SearchRequest {
  type: 'search';
  requestId: string;
  query: string;
  timestamp: number;
}

export interface SearchResponse {
  type: 'search_result';
  requestId: string;
  results: MapObject[];
  timestamp: number;
}

export interface MapObject {
  id: string;
  name: string;
  description?: string;
  coordinates: {
    lat: number;
    lng: number;
  };
  type?: string;
  [key: string]: any; // Дополнительные поля
}

export interface ErrorResponse {
  type: 'error';
  requestId?: string;
  message: string;
  code?: string;
}

export type WebSocketMessage = SearchRequest | SearchResponse | ErrorResponse;
