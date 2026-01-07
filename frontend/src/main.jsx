import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import UmamiAnalytics from '@danielgtmn/umami-react';

import { GoogleOAuthProvider } from '@react-oauth/google';

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
      <UmamiAnalytics
        url="https://a.samhren.dev"
        websiteId="aac51aaa-1826-437b-8001-66232141aa69"
        scriptAttributes={{
          src: "/lib/client.js",
          'data-host-url': "https://a.samhren.dev"
        }}
      />
    </GoogleOAuthProvider>
  </React.StrictMode>,
)
