<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { onDestroy } from 'svelte';
	import { BigValue } from '@evidence-dev/core-components';
	import { Query } from '@evidence-dev/sdk/usql';

	export let overview = undefined;

	let overviewLoaded = undefined;
	let overviewUnsub = () => {};

	$: if (Query.isQuery(overview)) {
		overview.fetch();
		overviewUnsub();
		overviewUnsub = overview.subscribe((value) => {
			overviewLoaded = value;
		});
	} else {
		overviewLoaded = overview;
	}

	onDestroy(() => overviewUnsub());
</script>

{#if overviewLoaded?.error}
	<p class="text-sm text-negative">{overviewLoaded.error.message}</p>
{:else if Query.isQuery(overviewLoaded) && !overviewLoaded.dataLoaded}
	<section class="mb-10 rounded-lg border border-base-content/20 bg-base-200/20 p-5">
		<div class="grid grid-cols-1 gap-4 md:grid-cols-4">
			{#each Array(4) as _}
				<div class="h-24 animate-pulse rounded-lg bg-base-200"></div>
			{/each}
		</div>
	</section>
{:else if overviewLoaded?.length}
	<section class="mb-10 rounded-lg border border-base-content/20 bg-base-200/20 p-5">
		<div class="grid grid-cols-1 gap-4 md:grid-cols-4">
			<BigValue data={overviewLoaded} value="total_spend" fmt="$#,##0" title="Facebook spend" />
			<BigValue data={overviewLoaded} value="landing_page_visits" fmt="#,##0" title="Landing page visits" />
			<BigValue data={overviewLoaded} value="facebook_leads" fmt="#,##0" title="Facebook leads" />
			<BigValue data={overviewLoaded} value="showings_requested" fmt="#,##0" title="Showings requested" />
		</div>
	</section>
{/if}
