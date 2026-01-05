import { createContext, useContext, useEffect } from 'react';
import posthog from 'posthog-js';
import { useLocation } from 'react-router-dom';

// Initialize PostHog
const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY;

if (POSTHOG_KEY) {
  posthog.init(POSTHOG_KEY, {
    api_host: "https://e.boilersnipe.com",
    ui_url: "https://us.posthog.com",
    capture_pageview: false, // We'll capture manually for SPA
    capture_pageleave: true,
    persistence: 'localStorage',
    autocapture: true,
    session_recording: {
      maskAllInputs: false,
      maskInputOptions: {
        password: true,
      },
    },
  });
}

const PostHogContext = createContext(null);

export const PostHogProvider = ({ children }) => {
  const location = useLocation();

  // Capture page views on route change
  useEffect(() => {
    if (POSTHOG_KEY) {
      posthog.capture('$pageview', {
        $current_url: window.location.href,
        path: location.pathname,
      });
    }
  }, [location.pathname]);

  return (
    <PostHogContext.Provider value={posthog}>
      {children}
    </PostHogContext.Provider>
  );
};

// Hook to use PostHog
export const usePostHog = () => {
  return useContext(PostHogContext);
};

// Helper functions for common tracking events
export const trackEvent = (eventName, properties = {}) => {
  if (POSTHOG_KEY) {
    posthog.capture(eventName, properties);
  }
};

export const identifyUser = (userId, properties = {}) => {
  if (POSTHOG_KEY) {
    posthog.identify(userId, properties);
  }
};

export const resetUser = () => {
  if (POSTHOG_KEY) {
    posthog.reset();
  }
};

// Pre-defined event names for consistency
export const EVENTS = {
  // Auth events
  LOGIN_ATTEMPTED: 'login_attempted',
  LOGIN_SUCCESS: 'login_success',
  LOGIN_FAILED: 'login_failed',
  REGISTER_ATTEMPTED: 'register_attempted',
  REGISTER_SUCCESS: 'register_success',
  REGISTER_FAILED: 'register_failed',
  LOGOUT: 'logout',

  // Search events
  SEARCH_PERFORMED: 'search_performed',
  SEARCH_NO_RESULTS: 'search_no_results',
  SEARCH_RESULTS_SHOWN: 'search_results_shown',

  // Course tracking events
  COURSE_TRACK_CLICKED: 'course_track_clicked',
  COURSE_TRACKED: 'course_tracked',
  COURSE_TRACK_FAILED: 'course_track_failed',
  COURSE_UNTRACKED: 'course_untracked',

  // Notification settings
  NOTIFICATION_TOGGLE: 'notification_toggle',
  NOTIFY_ON_OPEN_CHANGED: 'notify_on_open_changed',
  NOTIFY_ON_CLOSE_CHANGED: 'notify_on_close_changed',

  // Navigation events
  NAV_CLICK: 'nav_click',
  CTA_CLICK: 'cta_click',
  MOBILE_MENU_TOGGLE: 'mobile_menu_toggle',

  // Dashboard events
  DASHBOARD_LOADED: 'dashboard_loaded',
  ADD_COURSE_CLICKED: 'add_course_clicked',

  // Error events
  API_ERROR: 'api_error',
  VALIDATION_ERROR: 'validation_error',
};

export default posthog;
