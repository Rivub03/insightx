// src/App.jsx
//
// PURPOSE:
//   The root React component. Its only job is to define which URL paths
//   show which pages. This is called "routing".
//
// HOW ROUTING WORKS:
//   React Router reads the current URL in the browser's address bar and
//   renders the matching page component. The page never actually reloads —
//   React swaps the component in/out without a full browser refresh.
//
// ROUTES DEFINED:
//   /                    → redirects to /datasources automatically
//   /datasources         → DataSourceListPage (list of saved connections)
//   /datasources/new     → AddDataSourcePage  (the 5-step wizard)

import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

import AddDataSourcePage  from './features/data-sources/pages/AddDataSourcePage.jsx'
import DataSourceListPage from './features/data-sources/pages/DataSourceListPage.jsx'

function App() {
  return (
    // BrowserRouter enables URL-based navigation
    <BrowserRouter>
      <Routes>
        {/* Visiting / sends the user straight to /datasources */}
        <Route path="/" element={<Navigate to="/datasources" replace />} />

        {/* The data sources list page */}
        <Route path="/datasources" element={<DataSourceListPage />} />

        {/* The add-new-datasource wizard */}
        <Route path="/datasources/new" element={<AddDataSourcePage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
