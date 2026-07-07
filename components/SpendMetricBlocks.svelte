<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { onDestroy } from 'svelte';
	import {
		formatValue,
		getFormatObjectFromString
	} from '@evidence-dev/component-utilities/formatting';
	import checkInputs from '@evidence-dev/component-utilities/checkInputs';
	import { Query } from '@evidence-dev/sdk/usql';

	export let data = undefined;

	const metrics = [
		{
			key: 'spend',
			title: 'Total Spend',
			summary: 'Ad spend across all campaigns in the last 30 days.',
			format: '$#,##0'
		},
		{
			key: 'meta_leads',
			title: 'Meta Leads',
			summary: 'Lead form submissions tracked by Meta pixel.',
			format: '#,##0'
		},
		{
			key: 'cpl_meta',
			title: 'CPL — Meta',
			summary: 'Cost per lead based on Meta-reported conversions.',
			format: '$#,##0'
		},
		{
			key: 'cpc',
			title: 'CPC',
			summary: 'Average cost per link click to the landing page.',
			format: '$#,##0.00'
		},
		{
			key: 'ctr',
			title: 'CTR',
			summary: 'Click-through rate: link clicks divided by impressions.',
			format: '0.0"%"'
		},
		{
			key: 'cost_per_showing',
			title: 'Cost per Showing',
			summary: 'Spend divided by Meta-reported showing requests.',
			format: '$#,##0'
		}
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

	function rowFrom(rows) {
		const list = Query.isQuery(rows) ? Array.from(rows) : rows;
		checkInputs(list, ['spend']);
		return list[0];
	}

	function formatFor(format) {
		return getFormatObjectFromString(format, 'number');
	}
</script>

{#if loaded?.error}
	<p class="text-sm text-negative">{loaded.error.message}</p>
{:else if Query.isQuery(loaded) && !loaded.dataLoaded}
	<div class="mb-8 h-44 animate-pulse rounded-lg bg-base-200"></div>
{:else if loaded?.length}
	{@const row = rowFrom(loaded)}
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 mb-8">
		{#each metrics as metric}
			<div
				class="flex min-h-[9rem] flex-col gap-2 rounded-lg border border-base-content/20 bg-base-100 p-5"
			>
				<p class="text-3xl font-semibold tabular-nums leading-none">
					{formatValue(row[metric.key], formatFor(metric.format))}
				</p>
				<p class="text-base font-medium leading-snug">{metric.title}</p>
				<p class="text-sm leading-snug text-base-content-muted">{metric.summary}</p>
			</div>
		{/each}
	</div>
{/if}
