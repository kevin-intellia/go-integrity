import { createRequire } from 'module';
import { readFileSync } from 'fs';
import { dirname, join } from 'path';

const require = createRequire(import.meta.url);
const duckdbPkgPath = require.resolve('@duckdb/duckdb-wasm');
const duckdbRoot = dirname(dirname(duckdbPkgPath));
const { version } = JSON.parse(readFileSync(join(duckdbRoot, 'package.json'), 'utf8'));

const CDN_BASE = `https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@${version}/dist`;

const WASM_CDN = {
	'duckdb-eh.wasm': `${CDN_BASE}/duckdb-eh.wasm`,
	'duckdb-mvp.wasm': `${CDN_BASE}/duckdb-mvp.wasm`
};

export function duckdbCdnPlugin() {
	return {
		name: 'duckdb-cdn',
		enforce: 'pre',
		resolveId(source) {
			if (source.includes('@duckdb/duckdb-wasm/dist/') && source.endsWith('.wasm?url')) {
				return `\0duckdb-cdn:${source}`;
			}
		},
		load(id) {
			if (!id.startsWith('\0duckdb-cdn:')) return null;

			const wasmName = Object.keys(WASM_CDN).find((name) => id.includes(name));
			if (!wasmName) return null;

			return `export default ${JSON.stringify(WASM_CDN[wasmName])};`;
		}
	};
}
