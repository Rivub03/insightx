// src/main.jsx
//
// PURPOSE:
//   This is the JavaScript entry point — the first file Vite executes.
//   Its only job is to mount the React application into the <div id="root">
//   element inside index.html.
//
//   Think of it as the bridge between the HTML shell and the React world.
//   You should almost never need to edit this file.

import React    from 'react'
import ReactDOM from 'react-dom/client'
import App      from './App.jsx'

// Import the global CSS file — styles defined here apply to every page
import './index.css'

ReactDOM.createRoot(
  // Find the <div id="root"> in index.html
  document.getElementById('root')
).render(
  // StrictMode runs extra checks in development (not in production builds)
  // It may cause some effects to run twice in dev — this is intentional and expected
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
