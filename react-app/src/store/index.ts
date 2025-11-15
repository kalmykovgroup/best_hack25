import { configureStore } from '@reduxjs/toolkit';
import searchReducer from './slices/searchSlice';

export const store = configureStore({
  reducer: {
    search: searchReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Игнорируем actions с функциями (для SignalR callbacks)
        ignoredActions: ['search/initializeConnection/pending'],
        ignoredPaths: ['search.config'],
      },
    }),
});

// Типы для TypeScript
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
