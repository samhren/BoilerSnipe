const pendingCalls = [];
const MAX_PENDING_CALLS = 50;
const READY_CHECK_INTERVAL_MS = 100;
const READY_CHECK_TIMEOUT_MS = 10000;

let readyCheck = null;
let errorTrackingEnabled = false;

function executeCall(method, args) {
  const fn = window.rybbit?.[method];
  if (typeof fn === 'function') {
    fn(...args);
    return true;
  }

  return false;
}

function flushQueue() {
  while (pendingCalls.length > 0) {
    const call = pendingCalls.shift();
    if (!executeCall(call.method, call.args)) {
      pendingCalls.unshift(call);
      return;
    }
  }

  if (readyCheck) {
    clearInterval(readyCheck);
    readyCheck = null;
  }
}

function startReadyCheck() {
  if (readyCheck || typeof window === 'undefined') return;

  readyCheck = window.setInterval(flushQueue, READY_CHECK_INTERVAL_MS);
  window.setTimeout(() => {
    if (readyCheck) {
      clearInterval(readyCheck);
      readyCheck = null;
    }
    pendingCalls.length = 0;
  }, READY_CHECK_TIMEOUT_MS);
}

function call(method, ...args) {
  if (typeof window === 'undefined') return;
  if (executeCall(method, args)) return;

  if (pendingCalls.length < MAX_PENDING_CALLS) {
    pendingCalls.push({ method, args });
  }
  startReadyCheck();
}

const rybbit = {
  identify(userId, email) {
    if (userId == null || !email) return;
    call('identify', String(userId), { email });
  },

  event(eventName, properties = {}) {
    call('event', eventName, properties);
  },

  clearUserId() {
    call('clearUserId');
  },

  enableErrorTracking() {
    if (typeof window === 'undefined' || errorTrackingEnabled) return;
    errorTrackingEnabled = true;

    window.addEventListener('error', (event) => {
      const error = event.error instanceof Error
        ? event.error
        : new Error(event.message || 'Unknown browser error');

      call('error', error, {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      });
    });

    window.addEventListener('unhandledrejection', (event) => {
      const error = event.reason instanceof Error
        ? event.reason
        : new Error(String(event.reason ?? 'Unhandled promise rejection'));

      call('error', error, { type: 'unhandledrejection' });
    });
  },
};

export default rybbit;
