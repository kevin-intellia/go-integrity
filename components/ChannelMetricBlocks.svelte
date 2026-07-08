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
			key: 'leads',
			title: 'Leads',
			summary: 'Leads attributed to this channel in the CRM.',
			format: '#,##0'
		},
		{
			key: 'appointments',
			title: 'Showings requested',
			summary: 'Leads who requested a showing.',
			format: '#,##0'
		},
		{
			key: 'appointment_rate_pct',
			title: 'Showing rate',
			summary: 'Showings requested as a percent of leads from this channel.',
			format: '0.0"%"'
		},
		{
			key: 'share_pct',
			title: 'Share of all leads',
			summary: 'This channel as a percent of total leads.',
			format: '0.0"%"'
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
		checkInputs(list, ['leads']);
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
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4 mb-8">
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
