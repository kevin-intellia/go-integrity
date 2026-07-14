<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { onDestroy } from 'svelte';
	import { Query } from '@evidence-dev/sdk/usql';

	export let data = undefined;

	const CREATIVE_ORDER = ['Non-dynamic', 'Dynamic'];
	const moneyCols = new Set(['spend', 'cpc', 'cpl', 'cost_per_showing']);
	const pctCols = new Set(['link_ctr']);
	const countCols = new Set(['landing_page_visits', 'facebook_leads', 'showings']);

	const columns = [
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
		const order = CREATIVE_ORDER.indexOf(a.creative_type) - CREATIVE_ORDER.indexOf(b.creative_type);
		return order;
	}

	$: rows = rowsFrom(loaded).sort(compareRows);
	$: winner =
		rows.length === 2 && rows.every((row) => Number(row.facebook_leads) > 0)
			? [...rows].sort((a, b) => Number(a.cpl) - Number(b.cpl))[0]?.creative_type
			: null;
</script>

{#if loaded?.error}
	<p class="text-sm text-negative">{loaded.error.message}</p>
{:else if Query.isQuery(loaded) && !loaded.dataLoaded}
	<div class="mb-8 h-24 animate-pulse rounded-lg bg-base-200"></div>
{:else if rows.length}
<div class="mb-6 rounded-lg border border-base-content/20 bg-base-100 p-4">
	<p class="mb-4 text-sm text-base-content-muted">
		Account-wide Dynamic vs Non-dynamic.
		{#if winner}
			<span class="text-base-content"> Lowest CPL: <strong>{winner}</strong>.</span>
		{/if}
	</p>

	<div class="overflow-x-auto">
		<table class="creative-grid w-full text-sm">
			<thead>
				<tr class="border-b border-base-content/20 text-left text-xs uppercase tracking-wide text-base-content/60">
					{#each columns as column}
						<th class="px-3 py-2 font-medium" title={column.description}>{column.title}</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each rows as row}
					<tr
						class="border-b border-base-content/10 hover:bg-base-200/40 {row.creative_type === winner ? 'bg-success/10' : ''}"
					>
						{#each columns as column}
							<td class="px-3 py-2 tabular-nums">{formatValue(column.id, row[column.id])}</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
{/if}

<style>
	.creative-grid {
		table-layout: fixed;
		min-width: 48rem;
	}

	.creative-grid th:first-child,
	.creative-grid td:first-child {
		width: 14%;
		text-align: left;
	}

	.creative-grid th:nth-child(n + 2),
	.creative-grid td:nth-child(n + 2) {
		width: 10.75%;
		text-align: right;
	}
</style>
