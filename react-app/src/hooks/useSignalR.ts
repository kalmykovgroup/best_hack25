import { useEffect, useCallback, useState } from 'react';
import { getSignalRService, SignalRService } from '../services/signalr.service';
import { ApiResponse, SearchResultData, SearchProgress } from '../types/api.types';

interface UseSignalROptions {
  hubUrl: string;
  autoConnect?: boolean;
  onMessage?: (response: ApiResponse<SearchResultData>) => void;
  onProgress?: (progress: SearchProgress) => void;
  onError?: (error: Error) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
}

export const useSignalR = (options: UseSignalROptions) => {
  const {
    hubUrl,
    autoConnect = true,
    onMessage,
    onProgress,
    onError,
    onConnected,
    onDisconnected
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [service] = useState<SignalRService>(() => getSignalRService(hubUrl));

  useEffect(() => {
    // Обработчики подключения
    const unsubscribeConnected = service.onConnected(() => {
      setIsConnected(true);
      onConnected?.();
    });

    const unsubscribeDisconnected = service.onDisconnected(() => {
      setIsConnected(false);
      onDisconnected?.();
    });

    // Обработчики сообщений
    const unsubscribeMessage = onMessage ? service.onMessage(onMessage) : () => {};
    const unsubscribeProgress = onProgress ? service.onProgress(onProgress) : () => {};
    const unsubscribeError = onError ? service.onError(onError) : () => {};

    // Автоподключение
    if (autoConnect) {
      service.connect().catch((error) => {
        console.error('[useSignalR] Ошибка подключения:', error);
        onError?.(error);
      });
    }

    // Cleanup
    return () => {
      unsubscribeConnected();
      unsubscribeDisconnected();
      unsubscribeMessage();
      unsubscribeProgress();
      unsubscribeError();
    };
  }, [service, autoConnect, onMessage, onProgress, onError, onConnected, onDisconnected]);

  const searchAddress = useCallback(async (query: string, limit: number, requestId: string) => {
    try {
      await service.searchAddress({ requestId, query, limit });
      return true;
    } catch (error) {
      console.error('[useSignalR] Ошибка searchAddress:', error);
      return false;
    }
  }, [service]);

  const cancelSearch = useCallback(async (requestId: string) => {
    try {
      await service.cancelSearch(requestId);
      return true;
    } catch (error) {
      console.error('[useSignalR] Ошибка cancelSearch:', error);
      return false;
    }
  }, [service]);

  const connect = useCallback(async () => {
    try {
      await service.connect();
    } catch (error) {
      console.error('[useSignalR] Ошибка connect:', error);
      throw error;
    }
  }, [service]);

  const disconnect = useCallback(async () => {
    await service.disconnect();
  }, [service]);

  const checkPythonServiceStatus = useCallback(async () => {
    try {
      return await service.checkPythonServiceStatus();
    } catch (error) {
      console.error('[useSignalR] Ошибка checkPythonServiceStatus:', error);
      return false;
    }
  }, [service]);

  return {
    searchAddress,
    cancelSearch,
    connect,
    disconnect,
    checkPythonServiceStatus,
    isConnected,
    connectionId: service.getConnectionId(),
  };
};
