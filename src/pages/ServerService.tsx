import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { JarvisButton } from "@/components/ui/JarvisButton";
import { JarvisInput } from "@/components/ui/JarvisInput";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { ParticleField } from "@/components/ParticleField";
import { ScanLines } from "@/components/ScanLines";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Server, RefreshCw, ArrowRight } from "lucide-react";

type DiscoveredService = {
  id: string;
  name?: string;
  host?: string;
  port?: number;
  addresses: string[];
  txt?: Record<string, string>;
  updatedAt?: string;
};

export default function ServerService() {
  const [services, setServices] = useState<DiscoveredService[]>([]);
  const [loading, setLoading] = useState(false);
  // default to no filter so the UI shows all discovered servers by default
  const [filter, setFilter] = useState<string>("");
  const [selectedServer, setSelectedServer] = useState<string | null>(() => localStorage.getItem('jarvis:selectedServer'));
  const navigate = useNavigate();

  const selectServer = (s: DiscoveredService) => {
    const addr = s.addresses && s.addresses[0];
    const host = addr || s.host;
    const port = s.port;
    if (!host || !port) return alert("No host/port available");
    const url = `http://${host}:${port}`;
    localStorage.setItem('jarvis:selectedServer', url);
    setSelectedServer(url);
    toast.success('Server selected', { description: url });
    navigate('/login');
  };

  const clearSelection = () => {
    localStorage.clear();
    setSelectedServer(null);
  };

  const fetchList = async () => {
    setLoading(true);
    try {
      const q = filter ? `?name=${encodeURIComponent(filter)}` : "";
      const res = await fetch(`/api/servers${q}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setServices(data);
    } catch (e) {
      console.error("Failed to fetch services", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchList();
    const id = setInterval(fetchList, 2000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      <ParticleField />
      <ScanLines />

      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `
            linear-gradient(hsl(185 100% 50% / 0.03) 1px, transparent 1px),
            linear-gradient(90deg, hsl(185 100% 50% / 0.03) 1px, transparent 1px)
          `,
          backgroundSize: "50px 50px",
        }}
      />

      {/* Radial glow */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <motion.div
          className="w-[500px] h-[500px] rounded-full"
          style={{
            background: "radial-gradient(circle, hsl(185 100% 50% / 0.1) 0%, transparent 70%)",
          }}
          animate={{
            scale: [1, 1.05, 1],
            opacity: [0.5, 0.9, 0.5],
          }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="relative z-10 w-full max-w-2xl px-4"
      >
        <GlassPanel variant="glow" className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl font-orbitron font-bold glow-text">J.A.R.V.I.S Servers</h2>
              <p className="text-sm text-muted-foreground mt-1 font-rajdhani tracking-widest">Select a server to connect</p>
              <div className="mt-2 text-xs text-muted-foreground flex items-center gap-2">
                <div>Selected: <strong className="ml-1">{selectedServer || 'None'}</strong></div>
                {selectedServer && (
                  <JarvisButton variant="ghost" size="sm" onClick={clearSelection}>Clear</JarvisButton>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <JarvisButton variant="ghost" onClick={() => setFilter((_) => "") }>
                Show All
              </JarvisButton>
              <JarvisButton
                variant="secondary"
                onClick={fetchList}
              >
                <RefreshCw size={16} />
              </JarvisButton>
            </div>
          </div>

          <div className="mb-4">
            <JarvisInput
              placeholder="Filter by name (e.g. J.A.R.V.I.S.)"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              icon={<Server size={16} />}
            />
          </div>

          <div className="space-y-3">
            {loading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="w-4 h-4 rounded-full border-2 border-jarvis-cyan/30 border-t-jarvis-cyan animate-spin" />
                Refreshing services...
              </div>
            )}

            {!loading && services.length === 0 && (
              <div className="text-sm text-muted-foreground">No services found.</div>
            )}

            <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {services.map((s) => (
                <motion.li
                  key={s.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                  className="p-4 border rounded bg-jarvis-dark/40"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="font-medium">{s.name || s.host}</div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {s.host}:{s.port}
                        {s.addresses && s.addresses.length > 0 && (
                          <span className="text-xs"> — {s.addresses.join(", ")}</span>
                        )}
                      </div>
                      {s.txt && Object.keys(s.txt).length > 0 && (
                        <div className="mt-2 text-xs text-slate-300">
                          {Object.entries(s.txt).map(([k, v]) => (
                            <div key={k} className="truncate">
                              <strong>{k}</strong>: {String(v)}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="flex flex-col items-end gap-2">
                      <div className="text-xs text-muted-foreground">Updated: {s.updatedAt ? new Date(s.updatedAt).toLocaleTimeString() : '-'}</div>
                      <div className="flex gap-2">
                        {selectedServer === (s.addresses && s.addresses[0] ? `http://${s.addresses[0]}:${s.port}` : `http://${s.host}:${s.port}`) ? (
                          <JarvisButton variant="outline" size="sm" disabled>
                            Selected
                          </JarvisButton>
                        ) : (
                          <JarvisButton variant="secondary" size="sm" onClick={() => selectServer(s)}>
                            Select
                          </JarvisButton>
                        )}

                        
                      </div>
                    </div>
                  </div>
                </motion.li>
              ))}
            </ul>
          </div>

          {/* System status */}
          <div className="mt-6 flex items-center justify-center gap-2">
            <div className="w-2 h-2 rounded-full bg-jarvis-cyan animate-pulse" />
            <span className="text-xs text-muted-foreground font-orbitron tracking-wider">DISCOVERY ONLINE</span>
          </div>
        </GlassPanel>
      </motion.div>

      {/* Corner decorations */}
      <div className="absolute top-8 left-8 w-16 h-16 border-l-2 border-t-2 border-jarvis-cyan/30" />
      <div className="absolute top-8 right-8 w-16 h-16 border-r-2 border-t-2 border-jarvis-cyan/30" />
      <div className="absolute bottom-8 left-8 w-16 h-16 border-l-2 border-b-2 border-jarvis-cyan/30" />
      <div className="absolute bottom-8 right-8 w-16 h-16 border-r-2 border-b-2 border-jarvis-cyan/30" />
    </div>
  );
}

