import { spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

import './patch-vite-config.js';

const typesRoot = path.join(root, '.evidence/template/.svelte-kit/types/src/pages');
fs.mkdirSync(typesRoot, { recursive: true });
const typesFile = path.join(typesRoot, '$types.d.ts');
if (!fs.existsSync(typesFile)) {
	fs.writeFileSync(typesFile, 'export {};\n');
}

const buildDir = path.join(root, 'build');
if (fs.existsSync(buildDir)) {
	fs.rmSync(buildDir, { recursive: true, force: true });
}

spawnSync('.venv/bin/python', ['scripts/build_ab_test_viz.py'], { cwd: root, stdio: 'inherit' });

spawnSync('npx evidence dev --open /', {
	cwd: root,
	stdio: 'inherit',
	shell: true
});
