// Типы для работы с C# API (GeocodeHub)

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  errorMessage?: string;
  errorCode?: string;
  metadata?: ResponseMetadata;
}

export interface ResponseMetadata {
  requestId: string;
  executionTimeMs: number;
  timestamp: string;
  wasCancelled: boolean;
}

export interface SearchResultData {
  searchedAddress: string;
  objects: AddressObject[];
  totalFound: number;
}

export interface AddressObject {
  locality: string;
  street: string;
  number: string;
  lon: number;
  lat: number;
  score: number;
  additionalInfo?: AddressAdditionalInfo;
}

export interface AddressAdditionalInfo {
  postalCode?: string;
  district?: string;
  fullAddress?: string;
  objectId?: string;
}

export interface GeocodeRequest {
  requestId: string;
  query: string;
  limit: number;
}

export interface SearchProgress {
  requestId: string;
  status: "processing" | "normalizing" | "searching" | "finalizing";
  message: string;
  progressPercent: number;
}

export interface CancelSearchRequest {
  requestId: string;
}
