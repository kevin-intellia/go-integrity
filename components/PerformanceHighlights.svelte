<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { onDestroy } from 'svelte';
	import { Info } from '@evidence-dev/core-components';
	import {
		formatValue,
		getFormatObjectFromString
	} from '@evidence-dev/component-utilities/formatting';
	import checkInputs from '@evidence-dev/component-utilities/checkInputs';
	import { Query } from '@evidence-dev/sdk/usql';

	export let data = undefined;

	const pctFormat = getFormatObjectFromString('0.0"%"', 'number');

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
		checkInputs(list, ['overall_ctr', 'top_audience_ctr', 'industry_ctr_avg']);
		return list[0];
	}
</script>

{#if loaded?.error}
	<p class="text-sm text-negative">{loaded.error.message}</p>
{:else if Query.isQuery(loaded) && !loaded.dataLoaded}
	<div class="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
		{#each Array(3) as _}
			<div class="h-32 animate-pulse rounded-lg bg-base-200"></div>
		{/each}
	</div>
{:else if loaded?.length}
	{@const row = rowFrom(loaded)}
	<div class="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
		<div
			class="flex flex-col gap-2 rounded-lg border border-positive/30 bg-positive/5 p-5"
		>
			<p class="text-3xl font-semibold tabular-nums leading-none text-positive">
				{formatValue(row.top_audience_ctr, pctFormat)}
			</p>
			<p class="flex items-center gap-1 text-base font-medium">
				Top Audience CTR
				<Info
					description="Highest click-through rate among individual ad audiences. Website visits divided by impressions for that audience only."
				/>
			</p>
			<p class="text-sm leading-snug text-base-content-muted">
				{row.top_audience} leads all audiences at {row.top_audience_vs_benchmark}× the industry
				benchmark. The average across all audiences is
				{formatValue(row.overall_ctr, pctFormat)}.
			</p>
		</div>

		<div
			class="flex flex-col gap-2 rounded-lg border border-primary/30 bg-primary/5 p-5"
		>
			<p class="text-3xl font-semibold tabular-nums leading-none text-primary">
				{formatValue(row.overall_ctr, pctFormat)}
			</p>
			<p class="flex items-center gap-1 text-base font-medium">
				Average Across Audiences
				<Info
					description="Weighted average click-through rate across every ad audience: total website visits divided by total impressions."
				/>
			</p>
			<p class="text-sm leading-snug text-base-content-muted">
				All audiences combined average {formatValue(row.overall_ctr, pctFormat)}, above the
				~{formatValue(row.industry_ctr_avg, pctFormat)} typical for real estate Facebook
				campaigns.
			</p>
		</div>

		<div
			class="flex flex-col gap-2 rounded-lg border border-base-content/20 bg-base-100 p-5"
		>
			<p class="text-3xl font-semibold tabular-nums leading-none">
				{formatValue(row.industry_ctr_avg, pctFormat)}
			</p>
			<p class="flex items-center gap-1 text-base font-medium">
				Industry Benchmark
				<Info
					description="Approximate click-through rate benchmark for real estate ads on Meta platforms, based on published industry averages."
				/>
			</p>
			<p class="text-sm leading-snug text-base-content-muted">
				Real estate ads typically land around 3% CTR. This campaign is performing above that
				baseline.
			</p>
		</div>
	</div>
{/if}
