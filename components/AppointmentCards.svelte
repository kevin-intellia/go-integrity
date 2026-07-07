<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { onDestroy } from 'svelte';
	import { Query } from '@evidence-dev/sdk/usql';

	export let data = undefined;

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

	function rowsFrom(value) {
		return Query.isQuery(value) ? Array.from(value) : value ?? [];
	}

	function statusClass(status) {
		return status === 'Showing Booked'
			? 'bg-positive/15 text-positive'
			: 'bg-info/15 text-info';
	}

	function statusLabel(status) {
		return status === 'Showing Booked' ? 'Booked' : 'Requested';
	}
</script>

{#if loaded?.error}
	<p class="text-sm text-negative">{loaded.error.message}</p>
{:else if Query.isQuery(loaded) && !loaded.dataLoaded}
	<div class="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
		{#each Array(6) as _}
			<div class="h-20 animate-pulse rounded-md bg-base-200"></div>
		{/each}
	</div>
{:else if loaded?.length}
	{@const rows = rowsFrom(loaded)}
	<div class="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
		{#each rows as row}
			<div class="rounded-md border border-base-content/15 bg-base-100 px-3.5 py-3">
				<div class="mb-1.5 flex items-start justify-between gap-2">
					<p class="text-sm font-semibold leading-snug">{row.name}</p>
					<span
						class="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium leading-none {statusClass(
							row.status
						)}"
					>
						{statusLabel(row.status)}
					</span>
				</div>
				<p class="text-xs leading-snug text-base-content-muted">
					<span class="font-medium">{row.channel}</span>
					<span aria-hidden="true"> · </span>
					{row.audience}
				</p>
			</div>
		{/each}
	</div>
	{#if rows.some((row) => row.audience === 'Unattributed')}
		<p class="text-xs leading-relaxed text-base-content-muted">
			<span class="font-medium text-base-content">Unattributed</span>
			— we couldn't match these leads to a specific ad audience, usually because they came from
			email or another source without audience tracking.
		</p>
	{/if}
{/if}
