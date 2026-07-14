<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { onDestroy, tick } from 'svelte';
	import { LineChart } from '@evidence-dev/core-components';
	import { Query } from '@evidence-dev/sdk/usql';

	export let data = undefined;

	const SERIES_NAME = 'Selected';
	const EXCLUDED_DATES = new Set(['2026-07-03']);
	const EXCLUDED_DATE_LABELS = new Set(['Jul 03']);
	const GROUP_ORDER = ['Northeast', 'National', 'Ski'];
	const VARIANT_ORDER = ['funnel', 'website'];
	const CREATIVE_ORDER = ['Dynamic', 'Static'];
	const VARIANT_LABELS = {
		funnel: 'Funnel',
		website: 'Website'
	};
	const METRICS = {
		cpl: { key: 'cpl', label: 'Cost per lead', field: 'cpl' },
		cost_per_showing: { key: 'cost_per_showing', label: 'Cost per showing', field: 'cost_per_showing' }
	};
	const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

	let loaded = undefined;
	let unsub = () => {};
	let selectedGroups = new Set();
	let selectedVariants = new Set();
	let selectedCreatives = new Set();
	let selectedMetric = 'cpl';
	let groupFilterInitialized = false;
	let variantFilterInitialized = false;
	let creativeFilterInitialized = false;
	let root;

	async function preserveScroll(update) {
		const top = root ? root.getBoundingClientRect().top + window.scrollY - 16 : window.scrollY;
		update();
		await tick();
		requestAnimationFrame(() => {
			window.scrollTo({ top: Math.max(0, top), left: window.scrollX });
		});
	}

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
		return '$' + Number(value).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
	}

	function rowsFrom(rows) {
		if (!rows) return [];
		return Query.isQuery(rows) ? Array.from(rows) : rows;
	}

	function isoDate(value) {
		if (value instanceof Date && !Number.isNaN(value.getTime())) {
			const y = value.getFullYear();
			const m = String(value.getMonth() + 1).padStart(2, '0');
			const d = String(value.getDate()).padStart(2, '0');
			return `${y}-${m}-${d}`;
		}
		const str = String(value);
		if (/^\d{4}-\d{2}-\d{2}/.test(str)) {
			return str.slice(0, 10);
		}
		return str.slice(0, 10);
	}

	function labelForDate(value) {
		const iso = isoDate(value);
		const [, month, day] = iso.split('-');
		return `${monthNames[Number(month) - 1]} ${day}`;
	}

	function isExcludedRow(row) {
		if (EXCLUDED_DATE_LABELS.has(row.report_date_label)) return true;
		return EXCLUDED_DATES.has(isoDate(row.report_date));
	}

	function sortByDate(rows) {
		return [...rows].sort((a, b) => isoDate(a.report_date).localeCompare(isoDate(b.report_date)));
	}

	function normalizeRow(row) {
		const report_date = isoDate(row.report_date);
		return {
			report_date,
			report_date_label: row.report_date_label ?? labelForDate(report_date),
			campaign_group: row.campaign_group,
			website_variant: row.website_variant,
			creative_type: row.creative_type,
			daily_spend: Number(row.daily_spend) || 0,
			daily_leads: Number(row.daily_leads) || 0,
			daily_showings: Number(row.daily_showings) || 0
		};
	}

	function groupTotals(rows, field) {
		const totals = new Map();
		for (const row of rows) {
			const current = totals.get(row.campaign_group) ?? 0;
			totals.set(row.campaign_group, current + row[field]);
		}
		return totals;
	}

	function dimensionTotals(rows, field, key) {
		const totals = new Map();
		for (const row of rows) {
			const current = totals.get(row[key]) ?? 0;
			totals.set(row[key], current + row[field]);
		}
		return totals;
	}

	function aggregateByDate(rows) {
		const byDate = new Map();
		for (const row of rows) {
			const current = byDate.get(row.report_date) ?? {
				report_date: row.report_date,
				report_date_label: row.report_date_label,
				daily_spend: 0,
				daily_leads: 0,
				daily_showings: 0
			};
			current.daily_spend += row.daily_spend;
			current.daily_leads += row.daily_leads;
			current.daily_showings += row.daily_showings;
			byDate.set(row.report_date, current);
		}
		return sortByDate([...byDate.values()]);
	}

	function withCumulativeMetrics(rows) {
		let cumSpend = 0;
		let cumLeads = 0;
		let cumShowings = 0;
		return sortByDate(rows).map((row) => {
			cumSpend += row.daily_spend;
			cumLeads += row.daily_leads;
			cumShowings += row.daily_showings;
			return {
				...row,
				series: SERIES_NAME,
				cpl: cumLeads > 0 ? Math.round((cumSpend / cumLeads) * 100) / 100 : null,
				cost_per_showing: cumShowings > 0 ? Math.round((cumSpend / cumShowings) * 100) / 100 : null
			};
		});
	}

	$: rawRows = rowsFrom(loaded).filter((row) => !isExcludedRow(row));
	$: normalizedRows = rawRows.map((row) => normalizeRow(row));
	$: totalsByGroup = groupTotals(normalizedRows, 'daily_spend');
	$: totalsByVariant = dimensionTotals(normalizedRows, 'daily_spend', 'website_variant');
	$: totalsByCreative = dimensionTotals(normalizedRows, 'daily_spend', 'creative_type');
	$: availableGroups = GROUP_ORDER.filter((group) => normalizedRows.some((row) => row.campaign_group === group));
	$: availableVariants = VARIANT_ORDER.filter((variant) =>
		normalizedRows.some((row) => row.website_variant === variant)
	);
	$: availableCreatives = CREATIVE_ORDER.filter((creative) =>
		normalizedRows.some((row) => row.creative_type === creative)
	);

	$: if (availableGroups.length && !groupFilterInitialized) {
		selectedGroups = new Set(availableGroups);
		groupFilterInitialized = true;
	}

	$: if (availableVariants.length && !variantFilterInitialized) {
		selectedVariants = new Set(availableVariants);
		variantFilterInitialized = true;
	}

	$: if (availableCreatives.length && !creativeFilterInitialized) {
		selectedCreatives = new Set(availableCreatives);
		creativeFilterInitialized = true;
	}

	$: if (availableGroups.length && groupFilterInitialized) {
		const pruned = [...selectedGroups].filter((group) => availableGroups.includes(group));
		if (pruned.length !== selectedGroups.size) {
			selectedGroups = new Set(pruned);
		}
	}

	$: if (availableVariants.length && variantFilterInitialized) {
		const pruned = [...selectedVariants].filter((variant) => availableVariants.includes(variant));
		if (pruned.length !== selectedVariants.size) {
			selectedVariants = new Set(pruned);
		}
	}

	$: if (availableCreatives.length && creativeFilterInitialized) {
		const pruned = [...selectedCreatives].filter((creative) => availableCreatives.includes(creative));
		if (pruned.length !== selectedCreatives.size) {
			selectedCreatives = new Set(pruned);
		}
	}

	$: matchingRows = normalizedRows.filter(
		(row) =>
			selectedGroups.has(row.campaign_group) &&
			selectedVariants.has(row.website_variant) &&
			selectedCreatives.has(row.creative_type)
	);
	$: chartRows = withCumulativeMetrics(aggregateByDate(matchingRows));
	$: metricField = METRICS[selectedMetric].field;
	$: filteredRows = chartRows
		.map((row) => ({
			...row,
			metric_value: row[metricField]
		}))
		.filter((row) => row.metric_value != null);

	function toggleGroup(group) {
		preserveScroll(() => {
			const next = new Set(selectedGroups);
			if (next.has(group)) next.delete(group);
			else next.add(group);
			selectedGroups = next;
		});
	}

	function toggleVariant(variant) {
		preserveScroll(() => {
			const next = new Set(selectedVariants);
			if (next.has(variant)) next.delete(variant);
			else next.add(variant);
			selectedVariants = next;
		});
	}

	function toggleCreative(creative) {
		preserveScroll(() => {
			const next = new Set(selectedCreatives);
			if (next.has(creative)) next.delete(creative);
			else next.add(creative);
			selectedCreatives = next;
		});
	}

	function selectAllGroups() {
		preserveScroll(() => {
			selectedGroups = new Set(availableGroups);
		});
	}

	function clearAllGroups() {
		preserveScroll(() => {
			selectedGroups = new Set();
		});
	}

	function selectAllVariants() {
		preserveScroll(() => {
			selectedVariants = new Set(availableVariants);
		});
	}

	function clearAllVariants() {
		preserveScroll(() => {
			selectedVariants = new Set();
		});
	}

	function selectAllCreatives() {
		preserveScroll(() => {
			selectedCreatives = new Set(availableCreatives);
		});
	}

	function clearAllCreatives() {
		preserveScroll(() => {
			selectedCreatives = new Set();
		});
	}

	const echartsOptions = {
		tooltip: {
			trigger: 'axis',
			show: true,
			confine: true,
			formatter(params) {
				const items = Array.isArray(params) ? params : [params];
				const header = items[0]?.axisValueLabel ?? items[0]?.name ?? '';
				const points = [];

				for (const point of items) {
					if (point.seriesName === 'stackTotal') continue;
					const yVal = point.value?.[1] ?? point.value;
					const num = Number(yVal);
					if (Number.isNaN(num)) continue;
					points.push({
						name: point.seriesName,
						marker: point.marker,
						value: num
					});
				}

				points.sort((a, b) => b.value - a.value);
				const body = points
					.map(
						(point) =>
							`<br> <span style='font-size: 11px;'>${point.marker} ${point.name}<span/><span style='float:right; margin-left: 10px; font-size: 12px;'>${fmt(point.value)}</span>`
					)
					.join('');
				return `<span style='font-weight: 600;'>${header}</span>${body}`;
			}
		}
	};
</script>

{#if loaded?.error}
	<p class="text-sm text-negative">{loaded.error.message}</p>
{:else if Query.isQuery(loaded) && !loaded.dataLoaded}
	<div class="mb-8 h-44 animate-pulse rounded-lg bg-base-200"></div>
{:else if normalizedRows.length}
<div bind:this={root} class="mb-10 rounded-lg border border-base-content/20 bg-base-100 p-4">
	<div class="mb-4 space-y-4">
		<div class="rounded-lg border border-base-content/20 bg-base-100 p-4">
			<div class="flex flex-wrap gap-1">
				{#each Object.values(METRICS) as metric}
					<button
						type="button"
						class="rounded-md px-3 py-1.5 text-xs {selectedMetric === metric.key
							? 'bg-base-content text-base-100'
							: 'border border-base-content/20 hover:bg-base-200'}"
						on:click={() => {
							preserveScroll(() => {
								selectedMetric = metric.key;
							});
						}}
					>
						{metric.label}
					</button>
				{/each}
			</div>
		</div>

		<div class="rounded-lg border border-base-content/20 bg-base-100 p-4">
			<div class="mb-3 flex flex-wrap items-center justify-between gap-2">
				<p class="text-xs font-medium uppercase tracking-wide text-base-content/60">Campaign groups</p>
				<div class="flex flex-wrap gap-2">
					<button
						type="button"
						class="rounded-md border border-base-content/20 px-2.5 py-1 text-xs hover:bg-base-200"
						on:click={selectAllGroups}
					>
						All
					</button>
					<button
						type="button"
						class="rounded-md border border-base-content/20 px-2.5 py-1 text-xs hover:bg-base-200"
						on:click={clearAllGroups}
					>
						Remove all
					</button>
				</div>
			</div>
			<div class="flex flex-wrap gap-2">
				{#each availableGroups as group}
					<label
						class="flex cursor-pointer items-center gap-2 rounded-md border border-base-content/20 px-2.5 py-1.5 text-xs hover:bg-base-200"
					>
						<input
							type="checkbox"
							checked={selectedGroups.has(group)}
							on:change={() => toggleGroup(group)}
						/>
						<span>{group}</span>
						<span class="tabular-nums text-base-content-muted">{fmt(totalsByGroup.get(group))}</span>
					</label>
				{/each}
			</div>
		</div>

		<div class="rounded-lg border border-base-content/20 bg-base-100 p-4">
			<div class="mb-3 flex flex-wrap items-center justify-between gap-2">
				<p class="text-xs font-medium uppercase tracking-wide text-base-content/60">Creative</p>
				<div class="flex flex-wrap gap-2">
					<button
						type="button"
						class="rounded-md border border-base-content/20 px-2.5 py-1 text-xs hover:bg-base-200"
						on:click={selectAllCreatives}
					>
						All
					</button>
					<button
						type="button"
						class="rounded-md border border-base-content/20 px-2.5 py-1 text-xs hover:bg-base-200"
						on:click={clearAllCreatives}
					>
						Remove all
					</button>
				</div>
			</div>
			<div class="flex flex-wrap gap-2">
				{#each availableCreatives as creative}
					<label
						class="flex cursor-pointer items-center gap-2 rounded-md border border-base-content/20 px-2.5 py-1.5 text-xs hover:bg-base-200"
					>
						<input
							type="checkbox"
							checked={selectedCreatives.has(creative)}
							on:change={() => toggleCreative(creative)}
						/>
						<span>{creative}</span>
						<span class="tabular-nums text-base-content-muted">{fmt(totalsByCreative.get(creative))}</span>
					</label>
				{/each}
			</div>
		</div>

		<div class="rounded-lg border border-base-content/20 bg-base-100 p-4">
			<div class="mb-3 flex flex-wrap items-center justify-between gap-2">
				<p class="text-xs font-medium uppercase tracking-wide text-base-content/60">Web Page</p>
				<div class="flex flex-wrap gap-2">
					<button
						type="button"
						class="rounded-md border border-base-content/20 px-2.5 py-1 text-xs hover:bg-base-200"
						on:click={selectAllVariants}
					>
						All
					</button>
					<button
						type="button"
						class="rounded-md border border-base-content/20 px-2.5 py-1 text-xs hover:bg-base-200"
						on:click={clearAllVariants}
					>
						Remove all
					</button>
				</div>
			</div>
			<div class="flex flex-wrap gap-2">
				{#each availableVariants as variant}
					<label
						class="flex cursor-pointer items-center gap-2 rounded-md border border-base-content/20 px-2.5 py-1.5 text-xs hover:bg-base-200"
					>
						<input
							type="checkbox"
							checked={selectedVariants.has(variant)}
							on:change={() => toggleVariant(variant)}
						/>
						<span>{VARIANT_LABELS[variant] ?? variant}</span>
						<span class="tabular-nums text-base-content-muted">{fmt(totalsByVariant.get(variant))}</span>
					</label>
				{/each}
			</div>
		</div>
	</div>

	{#if filteredRows.length}
		<LineChart
			data={filteredRows}
			x=report_date_label
			y=metric_value
			series=series
			sort=false
			yFmt='$#,##0'
			legend=false
			{echartsOptions}
		/>
	{:else}
		<p class="text-sm text-base-content-muted">No {METRICS[selectedMetric].label.toLowerCase()} data for the selected filters yet.</p>
	{/if}
</div>
{/if}
