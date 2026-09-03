import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { compileTsx } from '../dist/compile.js';

const fixture = async (name, dependencies, extra = {}) => {
  const sourceCode = await readFile(new URL(`../fixtures/${name}`, import.meta.url), 'utf8');
  const result = await compileTsx({
    sourceCode,
    componentName: name.replace(/[^a-z0-9]/gi, '_'),
    siteId: 'contract-fixture',
    capabilityManifest: { dependencies, ...extra },
  });
  assert.equal(result.success, true, `${name} failed: ${result.error || result.validationErrors?.join(', ')}`);
  return result;
};

await fixture('approved-surface.tsx', [
  'react', 'react-dom', 'framer-motion', 'gsap', 'lenis',
  'embla-carousel-react', 'lucide-react', '@radix-ui/react-dialog', '@radix-ui/react-tabs',
]);
await fixture('shadcn-surface.tsx', ['react', 'react-dom']);
const three = await fixture('three-capability.tsx', ['three', '@react-three/fiber', '@react-three/drei'], { webglFallback: true });
assert.deepEqual(three.dependencyInventory, ['three', '@react-three/fiber', '@react-three/drei']);

const unused = await compileTsx({
  sourceCode: '',
  jsEntry: "console.log('no capability');",
  componentName: 'Unused',
  siteId: 'contract-negative',
  capabilityManifest: { dependencies: ['gsap'] },
});
assert.equal(unused.success, false);
assert.ok(unused.validationErrors?.some((error) => error.includes('Declared capability is unused')));

const webglWithoutFallback = await compileTsx({
  sourceCode: '',
  jsEntry: "import * as THREE from 'three'; console.log(THREE);",
  componentName: 'WebglWithoutFallback',
  siteId: 'contract-negative',
  capabilityManifest: { dependencies: ['three'] },
});
assert.equal(webglWithoutFallback.success, false);
assert.ok(webglWithoutFallback.validationErrors?.some((error) => error.includes('2D fallback')));

console.log('compiler contract verified');
