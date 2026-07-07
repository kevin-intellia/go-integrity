import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

import './patch-vite-config.js';

const child = spawn('npx evidence dev --open /', {
	cwd: root,
	stdio: 'inherit',
	shell: true
});

child.on('exit', (code) => {
	process.exit(code ?? 0);
});
