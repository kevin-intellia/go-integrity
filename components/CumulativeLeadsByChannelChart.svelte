<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { onDestroy } from 'svelte';
	import { LineChart } from '@evidence-dev/core-components';
	import { Query } from '@evidence-dev/sdk/usql';

	export let data = undefined;

	let loaded = undefined;
	let unsub = () => {};
	let selectedChannels = new Set();
	let showAllLine = true;
	let filterInitialized = false;

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

	function fmt(value) {
		return Number(value).toLocaleString('en-US');
	}

	function rowsFrom(rows) {
		if (!rows) return [];
		return Query.isQuery(rows) ? Array.from(rows) : rows;
	}

	function channelTotals(rows) {
		const totals = new Map();
		for (const row of rows) {
			if (row.channel === 'All') continue;
			const current = totals.get(row.channel) ?? 0;
			totals.set(row.channel, Math.max(current, Number(row.cumulative_leads) || 0));
		}
		return totals;
	}

	$: allRows = rowsFrom(loaded);
	$: totalsByChannel = channelTotals(allRows);
	$: availableChannels = [...totalsByChannel.entries()]
		.sort((a, b) => b[1] - a[1])
		.map(([channel]) => channel);

	$: if (availableChannels.length && !filterInitialized) {
		selectedChannels = new Set(availableChannels);
		filterInitialized = true;
	}

	$: if (availableChannels.length && filterInitialized) {
		const next = new Set([...selectedChannels].filter((channel) => availableChannels.includes(channel)));
		if (next.size === 0) {
			selectedChannels = new Set(availableChannels);
		} else if (next.size !== selectedChannels.size) {
			selectedChannels = next;
		}
	}

	$: filteredRows = allRows.filter((row) => {
		if (row.channel === 'All') return showAllLine;
		return selectedChannels.has(row.channel);
	});

	function toggleChannel(channel) {
		const next = new Set(selectedChannels);
		if (next.has(channel)) {
			if (next.size > 1) next.delete(channel);
		} else {
			next.add(channel);
		}
		selectedChannels = next;
	}

	function selectAllChannels() {
		selectedChannels = new Set(availableChannels);
	}

	function selectTopChannels(count) {
		selectedChannels = new Set(availableChannels.slice(0, count));
	}

	const echartsOptions = {
		tooltip: {
			trigger: 'axis',
			show: true,
			confine: true,
			formatter(params) {
				const items = Array.isArray(params) ? params : [params];
				const header = items[0]?.axisValueLabel ?? items[0]?.name ?? '';
				const channels = [];
				let allPoint = null;

				for (const point of items) {
					if (point.seriesName === 'stackTotal') continue;

					const yVal = point.value?.[1] ?? 0;
					const num = Number(yVal) || 0;

					if (point.seriesName === 'All') {
						allPoint = { marker: point.marker, value: num };
						continue;
					}

					channels.push({
						name: point.seriesName,
						marker: point.marker,
						value: num
					});
				}

				channels.sort((a, b) => b.value - a.value);

				let body = channels
					.map(
						(point) =>
							`<br> <span style='font-size: 11px;'>${point.marker} ${point.name}<span/><span style='float:right; margin-left: 10px; font-size: 12px;'>${fmt(point.value)}</span>`
					)
					.join('');

				if (allPoint) {
					body += `<br><span style='font-weight: 600;'>${allPoint.marker} All</span><span style='float:right; margin-left: 10px; font-weight: 600;'>${fmt(allPoint.value)}</span>`;
				}

				return `<span style='font-weight: 600;'>${header}</span>${body}`;
			}
		}
	};
</script>

{#if loaded?.error}
	<p class="text-sm text-negative">{loaded.error.message}</p>
{:else if Query.isQuery(loaded) && !loaded.dataLoaded}
	<div class="mb-8 h-44 animate-pulse rounded-lg bg-base-200"></div>
{:else if allRows.length}
	<div class="mb-4 rounded-lg border border-base-content/20 bg-base-100 p-4">
		<div class="mb-3 flex flex-wrap items-center justify-between gap-2">
			<p class="text-sm font-medium">Channels</p>
			<div class="flex flex-wrap gap-2">
				<button
					type="button"
					class="rounded-md border border-base-content/20 px-2.5 py-1 text-xs hover:bg-base-200"
					on:click={selectAllChannels}
				>
					All
				</button>
				<button
					type="button"
					class="rounded-md border border-base-content/20 px-2.5 py-1 text-xs hover:bg-base-200"
					on:click={() => selectTopChannels(5)}
				>
					Top 5
				</button>
				<label class="flex items-center gap-2 rounded-md border border-base-content/20 px-2.5 py-1 text-xs">
					<input type="checkbox" bind:checked={showAllLine} />
					Total line
				</label>
			</div>
		</div>
		<div class="flex flex-wrap gap-2">
			{#each availableChannels as channel}
				<label
					class="flex cursor-pointer items-center gap-2 rounded-md border border-base-content/20 px-2.5 py-1.5 text-xs hover:bg-base-200"
				>
					<input
						type="checkbox"
						checked={selectedChannels.has(channel)}
						on:change={() => toggleChannel(channel)}
					/>
					<span>{channel}</span>
					<span class="tabular-nums text-base-content-muted">{fmt(totalsByChannel.get(channel))}</span>
				</label>
			{/each}
		</div>
	</div>

	<LineChart
		data={filteredRows}
		title="Cumulative leads by channel"
		x=lead_date_label
		y=cumulative_leads
		series=channel
		seriesOrder={['All']}
		sort=false
		yFmt='#,##0'
		legend=true
		seriesColors={{ All: '#e4e4e7' }}
		{echartsOptions}
	/>
{/if}
