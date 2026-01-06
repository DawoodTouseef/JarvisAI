import { useState } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { JarvisButton } from "@/components/ui/JarvisButton";
import { JarvisInput } from "@/components/ui/JarvisInput";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { ParticleField } from "@/components/ParticleField";
import { ScanLines } from "@/components/ScanLines";
import { User, Lock, Mic, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { Eye,EyeOff } from "lucide-react";


const Login = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedServer, setSelectedServer] = useState<string | null>(() => localStorage.getItem('jarvis:selectedServer'));

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    const server = localStorage.getItem('jarvis:selectedServer');
    if (!server) {
      toast.error('No server selected. Please choose a server on the Services page.');
      setIsLoading(false);
      return navigate('/services');
    }

    try {
      const res = await fetch(`${server}/api/v1/auths/signin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err || 'Authentication failed');
      }
      const data = await res.json();
      if (data.token) localStorage.setItem('jarvis:token', data.token);
      toast.success('Authentication successful. Welcome back.', {
        description: 'JARVIS systems online.',
        className: 'bg-jarvis-dark border-jarvis-cyan/30',
      });
      navigate('/');
    } catch (err) {
      console.error('Login failed', err);
      toast.error('Login failed: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setIsLoading(false);
    }
  };
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

      {/* Radial glow behind card */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <motion.div
          className="w-[600px] h-[600px] rounded-full"
          style={{
            background: "radial-gradient(circle, hsl(185 100% 50% / 0.1) 0%, transparent 70%)",
          }}
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.5, 0.8, 0.5],
          }}
          transition={{
            duration: 4,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      </div>

      {/* Login Card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="relative z-10 w-full max-w-md px-4"
      >
        <GlassPanel variant="glow" className="p-8">
          {/* Logo/Icon */}
          <motion.div
            className="flex justify-center mb-8"
            animate={{ rotate: 360 }}
            transition={{ duration: 60, repeat: Infinity, ease: "linear" }}
          >
            <div className="relative w-24 h-24">
              {/* Outer ring */}
              <motion.div
                className="absolute inset-0 rounded-full border-2 border-jarvis-cyan/40"
                animate={{ rotate: -360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              />
              {/* Middle ring */}
              <motion.div
                className="absolute inset-2 rounded-full border border-jarvis-cyan/30"
                animate={{ rotate: 360 }}
                transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
              />
              {/* Inner circle */}
              <div className="absolute inset-4 rounded-full bg-jarvis-cyan/10 flex items-center justify-center shadow-glow">
                <motion.div
                  className="w-8 h-8 rounded-full bg-jarvis-cyan/20 border border-jarvis-cyan/40"
                  animate={{
                    boxShadow: [
                      "0 0 20px hsl(185 100% 50% / 0.4)",
                      "0 0 40px hsl(185 100% 50% / 0.6)",
                      "0 0 20px hsl(185 100% 50% / 0.4)",
                    ],
                  }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              </div>
            </div>
          </motion.div>

          {/* Title */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-center mb-8"
          >
            <h1 className="text-3xl font-orbitron font-bold text-foreground glow-text tracking-wider">
              J.A.R.V.I.S
            </h1>
            <p className="text-muted-foreground mt-2 font-rajdhani text-sm tracking-widest uppercase">
              Client Authentication Required
            </p>
          </motion.div>

          {/* Selected server info */}
          <div className="mb-4 text-center text-sm text-muted-foreground">
            {selectedServer ? (
              <div className="flex items-center justify-center gap-2">
                <div>Selected server: <strong className="ml-1">{selectedServer}</strong></div>
                <JarvisButton variant="ghost" size="sm" onClick={() => { localStorage.removeItem('jarvis:selectedServer'); setSelectedServer(null); }}>Change</JarvisButton>
              </div>
            ) : (
              <div>
                <span>No server selected.</span>
                <div>
                  <JarvisButton variant="secondary" size="sm" onClick={() => navigate('/services')}>Select Server</JarvisButton>
                </div>
              </div>
            )}
          </div>

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-6">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
            >
              <JarvisInput
                type="email"
                placeholder="Enter your identifier"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                icon={<User size={18} />}
                required
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
            >
              <div className="flex-items">
                <JarvisInput
                type={showPassword ? "text" : "password"}
                placeholder="Enter access code"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                icon={<Lock size={18} />}
                required
              />
              <JarvisButton onClick={()=>{
                setShowPassword(!showPassword)
              }}>
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </JarvisButton>
              </div>
            </motion.div>

            {/* Voice Auth Option */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="flex items-center justify-center gap-2 text-muted-foreground text-sm"
            >
              <Mic size={14} />
              <span className="font-rajdhani tracking-wide">Voice authentication available</span>
            </motion.div>

            {/* Submit Button */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
            >
              <JarvisButton
                type="submit"
                variant="primary"
                size="lg"
                className="w-full group"
                disabled={isLoading}
              >
                {isLoading ? (
                  <motion.div
                    className="w-5 h-5 border-2 border-jarvis-cyan/30 border-t-jarvis-cyan rounded-full"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  />
                ) : (
                  <>
                    <span>Initialize Session</span>
                    <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                  </>
                )}
              </JarvisButton>
            </motion.div>
          </form>

          {/* Status indicator */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
            className="mt-8 flex items-center justify-center gap-2"
          >
            <motion.div
              className="w-2 h-2 rounded-full bg-jarvis-cyan"
              animate={{
                opacity: [0.5, 1, 0.5],
                scale: [1, 1.2, 1],
              }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <span className="text-xs text-muted-foreground font-orbitron tracking-wider">
              SYSTEM READY
            </span>
          </motion.div>
        </GlassPanel>
      </motion.div>

      {/* Corner decorations */}
      <div className="absolute top-8 left-8 w-16 h-16 border-l-2 border-t-2 border-jarvis-cyan/30" />
      <div className="absolute top-8 right-8 w-16 h-16 border-r-2 border-t-2 border-jarvis-cyan/30" />
      <div className="absolute bottom-8 left-8 w-16 h-16 border-l-2 border-b-2 border-jarvis-cyan/30" />
      <div className="absolute bottom-8 right-8 w-16 h-16 border-r-2 border-b-2 border-jarvis-cyan/30" />
    </div>
  );
};

export default Login;
