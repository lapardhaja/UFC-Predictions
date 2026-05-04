import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { EventDetail } from "./pages/EventDetail";
import { FighterDetail } from "./pages/FighterDetail";
import { Home } from "./pages/Home";
import { ModelStats } from "./pages/ModelStats";

const qc = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <div className="min-h-screen flex flex-col">
          <Navbar />
          <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-8">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/events/:eventId" element={<EventDetail />} />
              <Route path="/fighters/:fighterId" element={<FighterDetail />} />
              <Route path="/model" element={<ModelStats />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
