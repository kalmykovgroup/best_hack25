// SignalR сервис для работы с C# GeocodeHub

import * as signalR from '@microsoft/signalr';
import { logger } from '../utils/logger';
import {
  ApiResponse,
  SearchResultData,
  GeocodeRequest,
  SearchProgress,
  CancelSearchRequest
} from '../types/api.types';

type MessageHandler = (response: ApiResponse<SearchResultData>) => void;
type ProgressHandler = (progress: SearchProgress) => void;
type ErrorHandler = (error: Error) => void;
type ConnectionHandler = () => void;

export class SignalRService {
  private connection: signalR.HubConnection | null = null;
  private hubUrl: string;

  private messageHandlers: Set<MessageHandler> = new Set();
  private progressHandlers: Set<ProgressHandler> = new Set();
  private errorHandlers: Set<ErrorHandler> = new Set();
  private connectedHandlers: Set<ConnectionHandler> = new Set();
  private disconnectedHandlers: Set<ConnectionHandler> = new Set();

  private isManuallyDisconnected = false;

  constructor(hubUrl: string) {
    this.hubUrl = hubUrl;
  }

  async connect(): Promise<void> {
    if (this.connection?.state === signalR.HubConnectionState.Connected) {
      logger.log('[SignalR] Уже подключен');
      return;
    }

    this.isManuallyDisconnected = false;

    this.connection = new signalR.HubConnectionBuilder()
      .withUrl(this.hubUrl, {
        skipNegotiation: false,
        transport: signalR.HttpTransportType.WebSockets | signalR.HttpTransportType.LongPolling
      })
      .withAutomaticReconnect({
        nextRetryDelayInMilliseconds: (retryContext) => {
          // Exponential backoff: 0s, 2s, 10s, 30s
          if (retryContext.previousRetryCount === 0) return 0;
          if (retryContext.previousRetryCount === 1) return 2000;
          if (retryContext.previousRetryCount === 2) return 10000;
          if (retryContext.previousRetryCount === 3) return 30000;
          return null; // Прекратить попытки
        }
      })
      .configureLogging(signalR.LogLevel.Information)
      .build();

    // Обработчики событий от сервера
    this.connection.on('SearchCompleted', (response: ApiResponse<SearchResultData>) => {
      logger.log('[SignalR] SearchCompleted:', response);
      this.messageHandlers.forEach(handler => handler(response));
    });

    this.connection.on('SearchProgress', (progress: SearchProgress) => {
      logger.log('[SignalR] SearchProgress:', progress);
      this.progressHandlers.forEach(handler => handler(progress));
    });

    // Обработчики состояния подключения
    this.connection.onclose((error) => {
      logger.log('[SignalR] Соединение закрыто', error);
      this.disconnectedHandlers.forEach(handler => handler());

      if (!this.isManuallyDisconnected && error) {
        this.notifyError(new Error('SignalR connection closed'));
      }
    });

    this.connection.onreconnecting((error) => {
      logger.log('[SignalR] Переподключение...', error);
      this.disconnectedHandlers.forEach(handler => handler());
    });

    this.connection.onreconnected((connectionId) => {
      logger.log('[SignalR] Переподключено:', connectionId);
      this.connectedHandlers.forEach(handler => handler());
    });

    try {
      await this.connection.start();
      logger.log('[SignalR] Подключено, connectionId:', this.connection.connectionId);
      this.connectedHandlers.forEach(handler => handler());
    } catch (error) {
      logger.error('[SignalR] Ошибка подключения:', error);
      this.notifyError(error as Error);
      throw error;
    }
  }

  async disconnect(): Promise<void> {
    this.isManuallyDisconnected = true;

    if (this.connection) {
      try {
        await this.connection.stop();
        logger.log('[SignalR] Отключено');
      } catch (error) {
        logger.error('[SignalR] Ошибка при отключении:', error);
      }
    }
  }

  async searchAddress(request: GeocodeRequest): Promise<void> {
    if (!this.connection || this.connection.state !== signalR.HubConnectionState.Connected) {
      throw new Error('SignalR not connected');
    }

    try {
      logger.log('[SignalR] Отправка SearchAddress:', request);
      await this.connection.invoke('SearchAddress', request);
    } catch (error) {
      logger.error('[SignalR] Ошибка при вызове SearchAddress:', error);
      throw error;
    }
  }

  async cancelSearch(requestId: string): Promise<void> {
    if (!this.connection || this.connection.state !== signalR.HubConnectionState.Connected) {
      throw new Error('SignalR not connected');
    }

    try {
      const request: CancelSearchRequest = { requestId };
      logger.log('[SignalR] Отправка CancelSearch:', request);
      await this.connection.invoke('CancelSearch', request);
    } catch (error) {
      logger.error('[SignalR] Ошибка при отмене:', error);
      throw error;
    }
  }

  async checkPythonServiceStatus(): Promise<boolean> {
    if (!this.connection || this.connection.state !== signalR.HubConnectionState.Connected) {
      logger.warn('[SignalR] Не подключено, не могу проверить Python сервис');
      return false;
    }

    try {
      const isAvailable = await this.connection.invoke<boolean>('CheckPythonServiceStatus');
      logger.log('[SignalR] Python сервис статус:', isAvailable ? 'Доступен' : 'Недоступен');
      return isAvailable;
    } catch (error) {
      logger.error('[SignalR] Ошибка при проверке Python сервиса:', error);
      return false;
    }
  }

  async checkAddressParserServiceStatus(): Promise<boolean> {
    if (!this.connection || this.connection.state !== signalR.HubConnectionState.Connected) {
      logger.warn('[SignalR] Не подключено, не могу проверить Address Parser сервис');
      return false;
    }

    try {
      const isAvailable = await this.connection.invoke<boolean>('CheckAddressParserServiceStatus');
      logger.log('[SignalR] Address Parser сервис статус:', isAvailable ? 'Доступен' : 'Недоступен');
      return isAvailable;
    } catch (error) {
      logger.error('[SignalR] Ошибка при проверке Address Parser сервиса:', error);
      return false;
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onProgress(handler: ProgressHandler): () => void {
    this.progressHandlers.add(handler);
    return () => this.progressHandlers.delete(handler);
  }

  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }

  onConnected(handler: ConnectionHandler): () => void {
    this.connectedHandlers.add(handler);
    return () => this.connectedHandlers.delete(handler);
  }

  onDisconnected(handler: ConnectionHandler): () => void {
    this.disconnectedHandlers.add(handler);
    return () => this.disconnectedHandlers.delete(handler);
  }

  private notifyError(error: Error): void {
    this.errorHandlers.forEach(handler => handler(error));
  }

  isConnected(): boolean {
    return this.connection?.state === signalR.HubConnectionState.Connected;
  }

  getConnectionState(): signalR.HubConnectionState | undefined {
    return this.connection?.state;
  }

  getConnectionId(): string | null {
    return this.connection?.connectionId || null;
  }
}

// Singleton instance
let signalRInstance: SignalRService | null = null;

export const getSignalRService = (hubUrl?: string): SignalRService => {
  if (!signalRInstance && hubUrl) {
    signalRInstance = new SignalRService(hubUrl);
  }
  if (!signalRInstance) {
    throw new Error('SignalR service не инициализирован. Укажите hubUrl.');
  }
  return signalRInstance;
};
