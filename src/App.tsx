import React from 'react';
import { Layout } from './components/Layout';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AlgorithmPage from './pages/AlgorithmPage';
import FunctionPage from './pages/FunctionPage';
import DebuggerPage from './pages/DebuggerPage';
import DataStructuresPage from './pages/DataStructuresPage';
import DevelopmentToolsPage from './pages/DevelopmentToolsPage';
import ProgrammingLanguagesPage from './pages/ProgrammingLanguagesPage';
import HomePage from './pages/HomePage';
import BibliographyPage from './pages/BibliographyPage';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/algorithms" element={<AlgorithmPage />} />
          <Route path="/functions" element={<FunctionPage />} />
          <Route path="/debuggers" element={<DebuggerPage />} />
          <Route path="/data-structures" element={<DataStructuresPage />} />
          <Route path="/development-tools" element={<DevelopmentToolsPage />} />
          <Route path="/programming-languages" element={<ProgrammingLanguagesPage />} />
          <Route path="/bibliography" element={<BibliographyPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;