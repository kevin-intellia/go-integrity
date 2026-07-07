import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const pkgTemplate = path.join(
	root,
	'node_modules/@evidence-dev/evidence/template/vite.config.js'
);

function patchPackageTemplate() {
	let content = fs.readFileSync(pkgTemplate, 'utf8');
	if (content.includes('refreshDataPlugin')) return;

	const pluginPath = path.join(root, 'scripts/vite-refresh-plugin.js').replace(/\\/g, '/');
	content = `import { refreshDataPlugin } from '${pluginPath}';\n${content}`;
	content = content.replace(
		'plugins: [sveltekit()',
		'plugins: [refreshDataPlugin(), sveltekit()'
	);
	fs.writeFileSync(pkgTemplate, content);
}

patchPackageTemplate();

const child = spawn('npx evidence dev --open /', {
	cwd: root,
	stdio: 'inherit',
	shell: true
});

child.on('exit', (code) => {
	process.exit(code ?? 0);
});
