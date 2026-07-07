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
			key: 'impressions',
			title: 'Impressions',
			summary: 'Times the ads appeared on screen.'
		},
		{
			key: 'landing_page_clicks',
			title: 'Page Visits',
			summary: 'Link clicks to the landing page from the ads.'
		},
		{
			key: 'learn_more_forms',
			title: 'Lead Forms',
			summary: 'Facebook ad leads in the CRM.'
		},
		{
			key: 'appointments_booked',
			title: 'Appointments',
			summary: 'Requested via Facebook ads.'
		}
	];

	const valueFormat = getFormatObjectFromString('#,##0', 'number');
	const dateFormat = getFormatObjectFromString('mmm d, yyyy', 'date');

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
		checkInputs(list, ['impressions']);
		return list[0];
	}
</script>

{#if loaded?.error}
	<p class="text-sm text-negative">{loaded.error.message}</p>
{:else if Query.isQuery(loaded) && !loaded.dataLoaded}
	<div class="mb-8 h-44 animate-pulse rounded-lg bg-base-200"></div>
{:else if loaded?.length}
	{@const row = rowFrom(loaded)}
	<p class="mb-4 text-sm text-base-content-muted">
		Paid ad funnel{#if row.ads_started_on}
			· Ads started {formatValue(row.ads_started_on, dateFormat)}{/if}.
	</p>
	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4 mb-8">
		{#each metrics as metric}
			<div
				class="flex min-h-[9rem] flex-col gap-2 rounded-lg border border-base-content/20 bg-base-100 p-5"
			>
				<p class="text-3xl font-semibold tabular-nums leading-none">
					{formatValue(row[metric.key], valueFormat)}
				</p>
				<p class="text-base font-medium leading-snug">{metric.title}</p>
				<p class="text-sm leading-snug text-base-content-muted">{metric.summary}</p>
			</div>
		{/each}
	</div>
{/if}
