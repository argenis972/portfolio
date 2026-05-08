import React, { useReducer, useCallback, useMemo } from 'react';
import { type LogLevel, type LogEntry } from '../types/logs';
import { type Incident } from '../types/incidents';
import { LogContext, type LogContextValue } from './LogContextInternal';

interface LogState {
  entries: LogEntry[];
  incidents: Incident[];
}

type LogAction =
  | { type: 'ADD'; entry: LogEntry }
  | { type: 'ADD_INCIDENT'; incident: Incident }
  | { type: 'SET_INCIDENTS'; incidents: Incident[] }
  | { type: 'CLEAR' };

const MAX_ENTRIES = 100;

const INCIDENT_TTL_MS = 2 * 60 * 1000;

function logReducer(state: LogState, action: LogAction): LogState {
  switch (action.type) {
    case 'ADD': {
      const next = [...state.entries, action.entry];
      if (next.length > MAX_ENTRIES) next.splice(0, next.length - MAX_ENTRIES);
      return { ...state, entries: next };
    }
    case 'ADD_INCIDENT': {
      return { ...state, incidents: [action.incident, ...state.incidents].slice(0, 5) };
    }
    case 'SET_INCIDENTS': {
      return { ...state, incidents: action.incidents };
    }
    case 'CLEAR':
      return { ...state, entries: [], incidents: [] };
    default:
      return state;
  }
}

let _counter = 0;

export function LogProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(logReducer, { entries: [], incidents: [] });

  // Cleanup expired incidents every second
  React.useEffect(() => {
    const t = setInterval(() => {
      const now = Date.now();
      const filtered = state.incidents.filter((i) => now - i.startedAt < i.ttl + 5000);
      if (filtered.length !== state.incidents.length) {
        dispatch({ type: 'SET_INCIDENTS', incidents: filtered });
      }
    }, 1000);
    return () => clearInterval(t);
  }, [state.incidents]);

  const addEntry = useCallback((level: LogLevel, message: string, requestId?: string) => {
    const entry: LogEntry = {
      id: `log-${Date.now()}-${++_counter}`,
      timestamp: new Date(),
      level,
      message,
      requestId,
    };
    dispatch({ type: 'ADD', entry });
  }, []);

  const addIncident = useCallback((type: string, labelKey: string, details?: Pick<Incident, 'impactPct' | 'durationMs' | 'origin'>) => {
    const incident: Incident = {
      id: Math.random().toString(36).slice(2),
      type,
      labelKey,
      startedAt: Date.now(),
      ttl: INCIDENT_TTL_MS,
      impactPct: details?.impactPct,
      durationMs: details?.durationMs,
      origin: details?.origin ?? 'synthetic',
    };
    dispatch({ type: 'ADD_INCIDENT', incident });
  }, []);

  const initialized = React.useRef(false);
  React.useEffect(() => {
    if (!initialized.current) {
      initialized.current = true;
      const sessionId = Math.random().toString(36).substring(2, 10);
      addEntry('INFO', `system.init status=BOOT session_id=${sessionId} request_id=boot-${sessionId} trace_id=trace-boot-${sessionId}`);
      setTimeout(() => {
        addEntry('INFO', `health.check status=UP db=CONNECTED session_id=${sessionId} request_id=boot-${sessionId} trace_id=trace-boot-${sessionId}`);
      }, 800);
    }
  }, [addEntry]);

  const clear = useCallback(() => dispatch({ type: 'CLEAR' }), []);

  const value: LogContextValue = useMemo(() => ({
    entries: state.entries,
    incidents: state.incidents,
    addEntry,
    addIncident,
    clear
  }), [
    state.entries,
    state.incidents,
    addEntry,
    addIncident,
    clear,
  ]);

  return <LogContext.Provider value={value}>{children}</LogContext.Provider>;
}
