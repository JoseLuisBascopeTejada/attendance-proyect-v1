import { Routes, Route } from 'react-router-dom';
import { Layout } from './pages/Layout';
import { Dashboard } from './pages/Dashboard';
import { Register } from './pages/Register';
import { Recognize } from './pages/Recognize';
import { RecognizeGroup } from './pages/RecognizeGroup';

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/register" element={<Register />} />
        <Route path="/recognize" element={<Recognize />} />
        <Route path="/recognize-group" element={<RecognizeGroup />} />
      </Route>
    </Routes>
  );
}

export default App;
