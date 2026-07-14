<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { onDestroy, tick } from 'svelte';
	import { LineChart } from '@evidence-dev/core-components';
	import { Query } from '@evidence-dev/sdk/usql';

	export let data = undefined;

	const TOTAL = 'Total';
	const GROUP_ORDER = ['Northeast', 'National', 'Ski'];
	const VARIANT_ORDER = ['funnel', 'website'];
	const VARIANT_LABELS = {
		funnel: 'Funnel',
		website: 'Website'
	};
	const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

	let loaded = undefined;
	let unsub = () => {};
	let selectedGroups = new Set();
	let selectedVariants = new Set();
	let showTotalLine = true;
	let groupFilterInitialized = false;
	let variantFilterInitialized = false;
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
			daily_spend: Number(row.daily_spend) || 0
		};
	}

	function groupTotals(rows) {
		const totals = new Map();
		for (const row of rows) {
			if (row.campaign_group === TOTAL) continue;
			const current = totals.get(row.campaign_group) ?? 0;
			totals.set(row.campaign_group, current + row.daily_spend);
		}
		return totals;
	}

	function variantTotals(rows) {
		const totals = new Map();
		for (const row of rows) {
			const current = totals.get(row.website_variant) ?? 0;
			totals.set(row.website_variant, current + row.daily_spend);
		}
		return totals;
	}

	function aggregateByGroup(rows) {
		const byDateGroup = new Map();
		for (const row of rows) {
			const key = `${row.report_date}|${row.campaign_group}`;
			const current = byDateGroup.get(key) ?? {
				report_date: row.report_date,
				report_date_label: row.report_date_label,
				campaign_group: row.campaign_group,
				daily_spend: 0
			};
			current.daily_spend += row.daily_spend;
			byDateGroup.set(key, current);
		}
		return [...byDateGroup.values()];
	}

	$: rawRows = rowsFrom(loaded).filter((row) => row.campaign_group !== TOTAL);
	$: normalizedRows = rawRows.map((row) => normalizeRow(row));
	$: totalsByGroup = groupTotals(normalizedRows);
	$: totalsByVariant = variantTotals(normalizedRows);
	$: availableGroups = GROUP_ORDER.filter((group) => normalizedRows.some((row) => row.campaign_group === group));
	$: availableVariants = VARIANT_ORDER.filter((variant) =>
		normalizedRows.some((row) => row.website_variant === variant)
	);

	$: if (availableGroups.length && !groupFilterInitialized) {
		selectedGroups = new Set(availableGroups);
		groupFilterInitialized = true;
	}

	$: if (availableVariants.length && !variantFilterInitialized) {
		selectedVariants = new Set(availableVariants);
		variantFilterInitialized = true;
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

	$: matchingRows = normalizedRows.filter(
		(row) => selectedGroups.has(row.campaign_group) && selectedVariants.has(row.website_variant)
	);
	$: chartRows = aggregateByGroup(matchingRows);
	$: totalRows = (() => {
		const byDate = new Map();
		for (const row of matchingRows) {
			const current = byDate.get(row.report_date) ?? {
				report_date: row.report_date,
				report_date_label: row.report_date_label,
				campaign_group: TOTAL,
				daily_spend: 0
			};
			current.daily_spend += row.daily_spend;
			byDate.set(row.report_date, current);
		}
		return sortByDate([...byDate.values()]);
	})();
	$: filteredRows = [...chartRows, ...(showTotalLine ? totalRows : [])];

	function toggleGroup(group) {
		preserveScroll(() => {
			const next = new Set(selectedGroups);
			if (next.has(group)) {
				next.delete(group);
			} else {
				next.add(group);
			}
			selectedGroups = next;
		});
	}

	function toggleVariant(variant) {
		preserveScroll(() => {
			const next = new Set(selectedVariants);
			if (next.has(variant)) {
				next.delete(variant);
			} else {
				next.add(variant);
			}
			selectedVariants = next;
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

	const echartsOptions = {
		tooltip: {
			trigger: 'axis',
			show: true,
			confine: true,
			formatter(params) {
				const items = Array.isArray(params) ? params : [params];
				const header = items[0]?.axisValueLabel ?? items[0]?.name ?? '';
				const groups = [];
				let totalPoint = null;

				for (const point of items) {
					if (point.seriesName === 'stackTotal') continue;

					const yVal = point.value?.[1] ?? 0;
					const num = Number(yVal) || 0;

					if (point.seriesName === TOTAL) {
						totalPoint = { marker: point.marker, value: num };
						continue;
					}

					groups.push({
						name: point.seriesName,
						marker: point.marker,
						value: num
					});
				}

				groups.sort((a, b) => b.value - a.value);

				let body = groups
					.map(
						(point) =>
							`<br> <span style='font-size: 11px;'>${point.marker} ${point.name}<span/><span style='float:right; margin-left: 10px; font-size: 12px;'>${fmt(point.value)}</span>`
					)
					.join('');

				const totalValue =
					totalPoint?.value ??
					(groups.length > 0 ? groups.reduce((sum, point) => sum + point.value, 0) : null);

				if (totalValue != null) {
					const marker =
						totalPoint?.marker ??
						"<span style='display:inline-block;margin-right:4px;border-radius:50%;width:10px;height:10px;background:#e4e4e7;'></span>";
					body += `<br><span style='font-weight: 600;'>${marker} ${TOTAL}</span><span style='float:right; margin-left: 10px; font-weight: 600;'>${fmt(totalValue)}</span>`;
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
{:else if normalizedRows.length}
<div bind:this={root} class="mb-10 rounded-lg border border-base-content/20 bg-base-100 p-4">
	<div class="mb-4 space-y-4">
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

		<div class="flex justify-end">
			<label class="flex items-center gap-2 rounded-md border border-base-content/20 px-2.5 py-1 text-xs">
				<input
					type="checkbox"
					checked={showTotalLine}
					on:change={(event) => {
						preserveScroll(() => {
							showTotalLine = event.currentTarget.checked;
						});
					}}
				/>
				Total line
			</label>
		</div>
	</div>

	<LineChart
		data={filteredRows}
		x=report_date_label
		y=daily_spend
		series=campaign_group
		seriesOrder={[TOTAL]}
		sort=false
		yFmt='$#,##0'
		legend=false
		seriesColors={{ [TOTAL]: '#e4e4e7' }}
		{echartsOptions}
	/>
</div>
{/if}
