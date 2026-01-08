/**
 * Safe wrapper for Rybbit analytics
 */
const rybbit = {
    /**
     * Identify a user
     * @param {string} userId - The user's unique ID
     * @param {Object} traits - User traits (email, name, etc.)
     */
    identify: (userId, traits = {}) => {
        if (window.rybbit) {
            window.rybbit.identify(userId, traits);
        }
    },

    /**
     * Track a custom event
     * @param {string} eventName - Name of the event
     * @param {Object} properties - Event properties
     */
    track: (eventName, properties = {}) => {
        if (window.rybbit) {
            window.rybbit.event(eventName, properties);
        }
    },

    /**
     * Track a page view
     */
    pageview: () => {
        if (window.rybbit) {
            window.rybbit.pageview();
        }
    },

    /**
     * Clear user identification
     */
    clearUserId: () => {
        if (window.rybbit) {
            window.rybbit.clearUserId();
        }
    },

    /**
     * Update user traits
     * @param {Object} traits - New traits to merge
     */
    setTraits: (traits) => {
        if (window.rybbit) {
            window.rybbit.setTraits(traits);
        }
    }
};

export default rybbit;
