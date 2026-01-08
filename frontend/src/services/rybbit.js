/**
 * Safe wrapper for Rybbit analytics
 * Queues calls until Rybbit script is loaded
 */

const pendingCalls = [];
let isReady = false;

function executeCall(method, args) {
    if (window.rybbit && window.rybbit[method]) {
        window.rybbit[method](...args);
    }
}

function queueOrExecute(method, args) {
    if (isReady && window.rybbit) {
        executeCall(method, args);
    } else {
        pendingCalls.push({ method, args });
    }
}

function flushQueue() {
    isReady = true;
    while (pendingCalls.length > 0) {
        const { method, args } = pendingCalls.shift();
        executeCall(method, args);
    }
}

// Wait for Rybbit to be ready
if (typeof window !== 'undefined') {
    if (window.rybbit) {
        isReady = true;
    } else {
        const checkInterval = setInterval(() => {
            if (window.rybbit) {
                clearInterval(checkInterval);
                flushQueue();
            }
        }, 100);
        // Stop checking after 10 seconds
        setTimeout(() => clearInterval(checkInterval), 10000);
    }
}

const rybbit = {
    identify: (userId, traits = {}) => {
        queueOrExecute('identify', [String(userId), traits]);
    },

    track: (eventName, properties = {}) => {
        queueOrExecute('event', [eventName, properties]);
    },

    pageview: () => {
        queueOrExecute('pageview', []);
    },

    clearUserId: () => {
        queueOrExecute('clearUserId', []);
    },

    setTraits: (traits) => {
        queueOrExecute('setTraits', [traits]);
    }
};

export default rybbit;
