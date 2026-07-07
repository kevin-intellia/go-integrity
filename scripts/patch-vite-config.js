import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const pkgTemplate = path.join(
	root,
	'node_modules/@evidence-dev/evidence/template/vite.config.js'
);

const refreshPath = path.join(root, 'scripts/vite-refresh-plugin.js').replace(/\\/g, '/');
const duckdbPath = path.join(root, 'scripts/vite-duckdb-cdn-plugin.js').replace(/\\/g, '/');

let content = fs.readFileSync(pkgTemplate, 'utf8');

if (!content.includes('duckdbCdnPlugin')) {
	if (!content.includes('refreshDataPlugin')) {
		content = `import { refreshDataPlugin } from '${refreshPath}';\nimport { duckdbCdnPlugin } from '${duckdbPath}';\n${content}`;
		content = content.replace(
			'plugins: [sveltekit()',
			'plugins: [refreshDataPlugin(), duckdbCdnPlugin(), sveltekit()'
		);
	} else if (!content.includes(`from '${duckdbPath}'`)) {
		content = content.replace(
			`import { refreshDataPlugin } from '${refreshPath}';`,
			`import { refreshDataPlugin } from '${refreshPath}';\nimport { duckdbCdnPlugin } from '${duckdbPath}';`
		);
		content = content.replace(
			'plugins: [refreshDataPlugin(), sveltekit()',
			'plugins: [refreshDataPlugin(), duckdbCdnPlugin(), sveltekit()'
		);
	}
	fs.writeFileSync(pkgTemplate, content);
}
