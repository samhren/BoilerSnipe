import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import rybbit from "@rybbit/js";
import { GoogleOAuthProvider } from '@react-oauth/google';

const initApp = async () => {
  // Initialize Rybbit Analytics
  try {
    await rybbit.init({
      analyticsHost: "https://backend-production-f68f.up.railway.app/api",
      siteId: "1",
    });
  } catch (error) {
    console.error("Rybbit Analytics initialization failed:", error);
  }

  ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
      <GoogleOAuthProvider clientId={(() => {
        const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
        if (!clientId || clientId === "PLACEHOLDER_CLIENT_ID") {
          console.error("CRITICAL: Google Client ID is missing. Check .env file and ensure VITE_GOOGLE_CLIENT_ID is set.");
          return "PLACEHOLDER_CLIENT_ID";
        }
        return clientId;
      })()}>
        <App />
      </GoogleOAuthProvider>
    </React.StrictMode>,
  )
};

initApp();
