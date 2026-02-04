import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import NotFound from "./pages/NotFound";
import ServerService from "./pages/ServerService";
import AuthGuard from "./components/AuthGurad";
import { Home } from "./pages/Home";
import { brain } from './brain';
import { useEffect } from "react";
import { VoiceControls } from "./components/VoiceControls";


const queryClient = new QueryClient();

function App() {
  useEffect(() => {
    brain.initialize();
  }, []);

  return (

    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <VoiceControls />
        <Toaster />
        <Sonner
          theme="dark"
          toastOptions={{
            className: "glass-panel border-jarvis-cyan/30",
          }}
        />
        <BrowserRouter>
          <Routes>
            <Route path="/services" element={<ServerService />} />

            <Route element={<AuthGuard />}>
              <Route path="/login" element={<Login />} />
              <Route path="/" element={<Dashboard />}>
                <Route index element={<Home />} />
              </Route>
            </Route>

            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );

}

export default App;
