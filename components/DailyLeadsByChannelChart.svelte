<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { onDestroy } from 'svelte';
	import { LineChart } from '@evidence-dev/core-components';
	import { Query } from '@evidence-dev/sdk/usql';

	export let data = undefined;

	const ALL_LEADS = 'All leads';

	let loaded = undefined;
	let unsub = () => {};
	let selectedChannel = '';

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

	function channelTotals(rows) {
		const totals = new Map();
		for (const row of rows) {
			const current = totals.get(row.channel) ?? 0;
			totals.set(row.channel, current + (Number(row.daily_leads) || 0));
		}
		return totals;
	}

	$: allRows = rowsFrom(loaded);
	$: totalsByChannel = channelTotals(allRows);
	$: totalLeadsInRange = [...totalsByChannel.values()].reduce((sum, value) => sum + value, 0);
	$: allLeadsRows = (() => {
		const byDate = new Map();
		for (const row of allRows) {
			const current = byDate.get(row.lead_date) ?? {
				lead_date: row.lead_date,
				lead_date_label: row.lead_date_label,
				channel: ALL_LEADS,
				daily_leads: 0
			};
			current.daily_leads += Number(row.daily_leads) || 0;
			byDate.set(row.lead_date, current);
		}
		return [...byDate.values()].sort((a, b) => String(a.lead_date).localeCompare(String(b.lead_date)));
	})();
	$: availableChannels = [ALL_LEADS, ...[...totalsByChannel.entries()]
		.sort((a, b) => b[1] - a[1])
		.map(([channel]) => channel)];

	$: if (availableChannels.length && !availableChannels.includes(selectedChannel)) {
		selectedChannel = ALL_LEADS;
	}

	$: filteredRows =
		selectedChannel === ALL_LEADS
			? allLeadsRows
			: allRows.filter((row) => row.channel === selectedChannel);

	$: leadsInRange =
		selectedChannel === ALL_LEADS
			? totalLeadsInRange
			: totalsByChannel.get(selectedChannel) ?? 0;
</script>

{#if loaded?.error}
	<p class="text-sm text-negative">{loaded.error.message}</p>
{:else if Query.isQuery(loaded) && !loaded.dataLoaded}
	<div class="mb-8 h-44 animate-pulse rounded-lg bg-base-200"></div>
{:else if allRows.length}
	<div class="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-base-content/20 bg-base-100 p-4">
		<label class="flex flex-wrap items-center gap-2 text-sm">
			<span class="font-medium">Channel</span>
			<select
				class="rounded-md border border-base-content/20 bg-base-100 px-3 py-1.5 text-sm"
				bind:value={selectedChannel}
			>
				{#each availableChannels as channel}
					<option value={channel}>{channel}</option>
				{/each}
			</select>
		</label>
		<p class="text-sm text-base-content-muted">
			{leadsInRange.toLocaleString('en-US')} leads in range
		</p>
	</div>

	<LineChart
		data={filteredRows}
		title="Daily leads by channel"
		x=lead_date_label
		y=daily_leads
		sort=false
		yFmt='#,##0'
		legend=false
	/>
{/if}
