import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';

function Scene() {
  const geometry = new THREE.BoxGeometry(1, 1, 1);
  return <mesh geometry={geometry}><meshStandardMaterial color="#f59e0b" /></mesh>;
}

export default function ThreeCapabilityFixture() {
  return <main aria-label="Interactive scene"><Canvas fallback={<div data-webgl-fallback>Interactive scene unavailable; content remains available.</div>}><ambientLight /><Scene /><OrbitControls /></Canvas></main>;
}
