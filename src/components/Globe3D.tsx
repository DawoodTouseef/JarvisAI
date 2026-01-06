import { useRef, Suspense } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Sphere } from "@react-three/drei";
import * as THREE from "three";

const Globe = () => {
  const meshRef = useRef<THREE.Mesh>(null);
  const wireframeRef = useRef<THREE.Mesh>(null);
  const pointsRef = useRef<THREE.Points>(null);

  useFrame((state) => {
    const time = state.clock.getElapsedTime();
    
    if (meshRef.current) {
      meshRef.current.rotation.y = time * 0.1;
    }
    if (wireframeRef.current) {
      wireframeRef.current.rotation.y = time * 0.1;
      wireframeRef.current.rotation.x = Math.sin(time * 0.05) * 0.1;
    }
    if (pointsRef.current) {
      pointsRef.current.rotation.y = time * 0.05;
    }
  });

  // Create globe points
  const pointsGeometry = new THREE.BufferGeometry();
  const pointCount = 2000;
  const positions = new Float32Array(pointCount * 3);
  
  for (let i = 0; i < pointCount; i++) {
    const phi = Math.acos(-1 + (2 * i) / pointCount);
    const theta = Math.sqrt(pointCount * Math.PI) * phi;
    const radius = 1.02;
    
    positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = radius * Math.cos(phi);
  }
  
  pointsGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));

  return (
    <group>
      {/* Inner solid sphere */}
      <Sphere ref={meshRef} args={[0.98, 64, 64]}>
        <meshBasicMaterial
          color="#0a1628"
          transparent
          opacity={0.9}
        />
      </Sphere>

      {/* Wireframe sphere */}
      <Sphere ref={wireframeRef} args={[1, 32, 32]}>
        <meshBasicMaterial
          color="#00d4ff"
          wireframe
          transparent
          opacity={0.3}
        />
      </Sphere>

      {/* Outer glow sphere */}
      <Sphere args={[1.1, 32, 32]}>
        <meshBasicMaterial
          color="#00d4ff"
          transparent
          opacity={0.05}
          side={THREE.BackSide}
        />
      </Sphere>

      {/* Points on surface */}
      <points ref={pointsRef} geometry={pointsGeometry}>
        <pointsMaterial
          color="#00d4ff"
          size={0.01}
          transparent
          opacity={0.8}
          sizeAttenuation
        />
      </points>

      {/* Latitude lines */}
      {[...Array(6)].map((_, i) => {
        const phi = (Math.PI / 7) * (i + 1);
        const radius = Math.sin(phi);
        return (
          <mesh key={i} rotation={[Math.PI / 2, 0, 0]} position={[0, Math.cos(phi), 0]}>
            <ringGeometry args={[radius - 0.005, radius + 0.005, 64]} />
            <meshBasicMaterial color="#00d4ff" transparent opacity={0.2} side={THREE.DoubleSide} />
          </mesh>
        );
      })}
    </group>
  );
};

export const Globe3D = () => {
  return (
    <div className="w-full h-full min-h-[200px]">
      <Suspense fallback={
        <div className="w-full h-full flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-jarvis-cyan/30 border-t-jarvis-cyan rounded-full animate-spin" />
        </div>
      }>
        <Canvas camera={{ position: [0, 0, 2.5], fov: 45 }}>
          <ambientLight intensity={0.5} />
          <pointLight position={[10, 10, 10]} intensity={1} />
          <Globe />
          <OrbitControls
            enableZoom={false}
            enablePan={false}
            autoRotate
            autoRotateSpeed={0.5}
            minPolarAngle={Math.PI / 4}
            maxPolarAngle={Math.PI / 1.5}
          />
        </Canvas>
      </Suspense>
    </div>
  );
};
