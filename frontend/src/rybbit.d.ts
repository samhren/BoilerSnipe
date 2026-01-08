interface Rybbit {
    /**
     * Tracks a page view
     */
    pageview: () => void;
    /**
     * Tracks a custom event
     * @param name Name of the event
     * @param properties Optional properties for the event
     */
    event: (name: string, properties?: Record<string, any>) => void;
    /**
     * Sets a custom user ID for tracking logged-in users
     * @param userId The user ID to set (will be stored in localStorage)
     * @param traits Optional user metadata (email, name, custom fields)
     */
    identify: (userId: string, traits?: Record<string, unknown>) => void;
    /**
     * Updates traits for the currently identified user
     * @param traits User metadata to merge with existing traits
     */
    setTraits: (traits: Record<string, unknown>) => void;
    /**
     * Clears the stored user ID
     */
    clearUserId: () => void;
    /**
     * Returns the currently set user ID, or null if none is set
     */
    getUserId: () => string | null;
}

interface Window {
    rybbit?: Rybbit;
}
