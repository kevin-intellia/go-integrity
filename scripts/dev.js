import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

import './patch-vite-config.js';

function ensureSvelteKitTypeDirs() {
	const typesRoot = path.join(root, '.evidence/template/.svelte-kit/types/src/pages');
	fs.mkdirSync(typesRoot, { recursive: true });
}

const MAX_RESTARTS = 10;
const RESTART_DELAY_MS = 2000;

let restartCount = 0;
let openBrowser = true;
let shuttingDown = false;
let child = null;

function startDev() {
	ensureSvelteKitTypeDirs();
	child = spawn(
		openBrowser ? 'npx evidence dev --open /' : 'npx evidence dev',
		{
			cwd: root,
			stdio: 'inherit',
			shell: true
		}
	);
	openBrowser = false;

	child.on('exit', (code, signal) => {
		if (shuttingDown || signal === 'SIGINT' || signal === 'SIGTERM') {
			process.exit(0);
		}

		if (code === 0 && shuttingDown) {
			process.exit(0);
		}

		restartCount += 1;
		if (restartCount > MAX_RESTARTS) {
			console.error(
				'Dev server crashed too many times. Fix the error above, then run npm run dev again.'
			);
			process.exit(code ?? 1);
		}

		console.error(
			`Dev server stopped (code ${code ?? 'unknown'}). Restarting in ${RESTART_DELAY_MS / 1000}s... (${restartCount}/${MAX_RESTARTS})`
		);
		setTimeout(startDev, RESTART_DELAY_MS);
	});
}

function shutdown() {
	shuttingDown = true;
	if (child) {
		child.kill('SIGTERM');
	}
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

startDev();
