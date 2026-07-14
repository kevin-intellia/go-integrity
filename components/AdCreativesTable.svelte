<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { onDestroy } from 'svelte';
	import { Query } from '@evidence-dev/sdk/usql';

	export let data = undefined;

	const moneyCols = new Set(['spend', 'cpc', 'cpl', 'cost_per_showing']);
	const pctCols = new Set(['link_ctr']);
	const countCols = new Set(['landing_page_visits', 'facebook_leads', 'showings']);

	const columns = [
		{ id: 'ad_name', title: 'Ad' },
		{ id: 'creative_type', title: 'Creative' },
		{ id: 'spend', title: 'Spend' },
		{ id: 'facebook_leads', title: 'CRM leads' },
		{ id: 'cpl', title: 'CPL' },
		{ id: 'link_ctr', title: 'Link CTR', description: 'Link clicks divided by impressions' },
		{ id: 'cpc', title: 'CPC' },
		{ id: 'landing_page_visits', title: 'Visits' },
		{ id: 'showings', title: 'Showings' },
		{ id: 'cost_per_showing', title: 'Cost/showing' }
	];

	let loaded = undefined;
	let unsub = () => {};

	$: if (Query.isQuery(data)) {
		data.fetch();
		unsub();
		unsub = data.subscribe((value) => {
			loaded = value;
		});
	} else {
		loaded = data;
	}

	onDestroy(() => unsub());

	function rowsFrom(rows) {
		if (!rows) return [];
		return Query.isQuery(rows) ? Array.from(rows) : rows;
	}

	function formatValue(columnId, value) {
		if (value == null || value === '') return '—';
		const num = Number(value);
		if (Number.isNaN(num)) return String(value);
		if (moneyCols.has(columnId)) {
			return num.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
		}
		if (pctCols.has(columnId)) {
			return `${num.toLocaleString('en-US', { maximumFractionDigits: 1 })}%`;
		}
		if (countCols.has(columnId)) {
			return num.toLocaleString('en-US');
		}
		return String(value);
	}

	function compareRows(a, b) {
		const aLeads = Number(a.facebook_leads) || 0;
		const bLeads = Number(b.facebook_leads) || 0;
		if (aLeads !== bLeads) return bLeads - aLeads;
		const aCpl = Number(a.cpl);
		const bCpl = Number(b.cpl);
		if (aLeads > 0 && bLeads > 0 && aCpl !== bCpl) return aCpl - bCpl;
		const aCtr = Number(a.link_ctr) || 0;
		const bCtr = Number(b.link_ctr) || 0;
		if (aCtr !== bCtr) return bCtr - aCtr;
		return Number(b.spend) - Number(a.spend);
	}

	$: rows = rowsFrom(loaded).sort(compareRows);
	$: hasMetaSpend = rows.some((row) => Number(row.spend) > 0);
</script>

{#if loaded?.error}
	<p class="text-sm text-negative">{loaded.error.message}</p>
{:else if Query.isQuery(loaded) && !loaded.dataLoaded}
	<div class="mb-8 h-44 animate-pulse rounded-lg bg-base-200"></div>
{:else if rows.length}
<div class="mb-10 rounded-lg border border-base-content/20 bg-base-100 p-4">
	<p class="mb-4 text-sm text-base-content-muted">
		Individual ads. CRM matches <code class="text-xs">utm_content</code> to ad name; spend joins ad set via <code class="text-xs">utm_term</code> and splits by lead share within each ad set.
		{#if !hasMetaSpend}
			Exact per-ad spend replaces estimates after you refresh your Meta token and run <code class="text-xs">npm run sync:meta</code>.
		{/if}
	</p>

	<div class="overflow-x-auto">
		<table class="ad-grid w-full text-sm">
			<thead>
				<tr class="border-b border-base-content/20 text-left text-xs uppercase tracking-wide text-base-content/60">
					{#each columns as column}
						<th class="px-3 py-2 font-medium" title={column.description}>{column.title}</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each rows as row}
					<tr class="border-b border-base-content/10 hover:bg-base-200/40">
						{#each columns as column}
							<td
								class="px-3 py-2 {column.id === 'ad_name' || column.id === 'creative_type' ? 'text-cell' : 'tabular-nums'}"
								title={column.id === 'ad_name' ? row.ad_name : undefined}
							>
								{#if column.id === 'ad_name'}
									<span class="ad-name-text">{row.ad_name}</span>
								{:else if column.id === 'creative_type'}
									{row.creative_type}
								{:else}
									{formatValue(column.id, row[column.id])}
								{/if}
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
{:else}
<div class="mb-10 rounded-lg border border-base-content/20 bg-base-100 p-4">
	<p class="text-sm text-base-content-muted">
		No ad-level data yet. Refresh your Meta token and run <code class="text-xs">npm run sync:meta</code> to pull individual ad performance.
	</p>
</div>
{/if}

<style>
	.ad-grid {
		table-layout: fixed;
		min-width: 64rem;
	}

	.ad-grid th:first-child,
	.ad-grid td:first-child {
		width: 24%;
		text-align: left;
	}

	.ad-grid th:nth-child(2),
	.ad-grid td:nth-child(2) {
		width: 8%;
		text-align: left;
	}

	.text-cell {
		white-space: normal;
		vertical-align: top;
	}

	.ad-name-text {
		overflow-wrap: anywhere;
		word-break: break-word;
		line-height: 1.4;
	}

	.ad-grid th:nth-child(n + 3),
	.ad-grid td:nth-child(n + 3) {
		width: 7%;
		text-align: right;
	}
</style>
