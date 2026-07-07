import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';
import path from 'path';

const execAsync = promisify(exec);

function findProjectRoot(startDir) {
	let dir = startDir;
	while (dir !== path.dirname(dir)) {
		const pkgPath = path.join(dir, 'package.json');
		if (fs.existsSync(pkgPath)) {
			const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
			if (pkg.scripts?.refresh) return dir;
		}
		dir = path.dirname(dir);
	}
	throw new Error('Could not find project root');
}

export function refreshDataPlugin() {
	return {
		name: 'evidence-refresh-data',
		configureServer(server) {
			server.middlewares.use('/api/refresh-data', async (req, res) => {
				if (req.method !== 'POST') {
					res.statusCode = 405;
					res.end('Method not allowed');
					return;
				}

				let projectRoot;
				try {
					projectRoot = findProjectRoot(server.config.root);
				} catch (error) {
					res.statusCode = 500;
					res.setHeader('Content-Type', 'application/json');
					res.end(JSON.stringify({ ok: false, error: error.message }));
					return;
				}

				const steps = [
					['npm run sync:meta', 'Meta ads'],
					['npm run sync:ghl', 'GHL'],
					['npm run sources', 'Evidence sources']
				];
				const warnings = [];

				for (const [command, label] of steps) {
					try {
						const { stdout, stderr } = await execAsync(command, {
							cwd: projectRoot,
							timeout: 180000,
							env: { ...process.env }
						});
						if (stdout) warnings.push(`${label}: ${stdout}`.trim());
						if (stderr) warnings.push(`${label}: ${stderr}`.trim());
					} catch (error) {
						warnings.push(`${label} failed: ${error.message}`);
					}
				}

				res.setHeader('Content-Type', 'application/json');
				res.end(JSON.stringify({ ok: true, warnings }));
			});
		}
	};
}
