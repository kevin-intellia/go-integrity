import { spawn, spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DEV_OPEN_PATH = process.env.DEV_OPEN_PATH || process.argv[2] || '/';

import './patch-vite-config.js';

function ensureSvelteKitTypeDirs() {
	const typesRoot = path.join(root, '.evidence/template/.svelte-kit/types/src/pages');
	fs.mkdirSync(typesRoot, { recursive: true });

	const typesFile = path.join(typesRoot, '$types.d.ts');
	if (!fs.existsSync(typesFile)) {
		fs.writeFileSync(typesFile, 'export {};\n');
	}

	for (const route of ['home-ab-test', 'meta-ads', 'client-report', 'facebook', 'api', 'explore', 'settings']) {
		fs.mkdirSync(path.join(typesRoot, route), { recursive: true });
	}
}

function cleanDevArtifacts() {
	const buildDir = path.join(root, 'build');
	if (fs.existsSync(buildDir)) {
		fs.rmSync(buildDir, { recursive: true, force: true });
		console.log('Removed stale build/ output (confuses Vite dev watcher).');
	}
}

function ensureEvidenceData() {
	const parquet = path.join(
		root,
		'.evidence/template/static/data/ghl/_lead_records/_lead_records.parquet'
	);
	if (!fs.existsSync(parquet)) {
		console.log('Evidence data missing — running npm run sources...');
		spawnSync('npm', ['run', 'sources'], { cwd: root, stdio: 'inherit' });
	}
}

function prepareDevAssets() {
	ensureEvidenceData();
	spawnSync('.venv/bin/python', ['scripts/build_ab_test_viz.py'], {
		cwd: root,
		stdio: 'inherit'
	});
}

const MAX_RESTARTS = 10;
const RESTART_DELAY_MS = 2000;

let restartCount = 0;
let openBrowser = true;
let shuttingDown = false;
let child = null;
let prepared = false;

function startDev() {
	if (!prepared) {
		cleanDevArtifacts();
		ensureSvelteKitTypeDirs();
		prepareDevAssets();
		prepared = true;
	} else {
		ensureSvelteKitTypeDirs();
	}

	const openArg = openBrowser ? ` --open ${DEV_OPEN_PATH}` : '';
	child = spawn(`npx evidence dev${openArg}`, {
		cwd: root,
		stdio: 'inherit',
		shell: true
	});
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
