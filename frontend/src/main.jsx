import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import './hooks/usePostHog' // Initialize PostHog

import { GoogleOAuthProvider } from '@react-oauth/google';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={(() => {
      const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
      if (!clientId || clientId === "PLACEHOLDER_CLIENT_ID") {
        console.error("CRITICAL: Google Client ID is missing. Check .env file and ensure VITE_GOOGLE_CLIENT_ID is set.");
        // alert("Google Client ID is missing! Check console."); 
        return "PLACEHOLDER_CLIENT_ID";
      }
      console.log("Google Client ID loaded:", clientId.substring(0, 10) + "...");
      return clientId;
    })()}>
      <App />
    </GoogleOAuthProvider>
  </React.StrictMode>,
)
