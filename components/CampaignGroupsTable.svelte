<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { onDestroy, tick } from 'svelte';
	import { Query } from '@evidence-dev/sdk/usql';

	export let data = undefined;
	export let audiences = undefined;

	const GROUP_ORDER = ['Northeast', 'National', 'Ski'];
	const VARIANT_ORDER = ['funnel', 'website'];
	const VARIANT_LABELS = {
		funnel: 'Funnel',
		website: 'Website'
	};

	const moneyCols = new Set(['spend', 'cost_per_visit', 'cpl', 'cost_per_showing']);
	const pctCols = new Set(['visit_to_lead_pct']);
	const countCols = new Set(['landing_page_visits', 'facebook_leads', 'showings']);

	const columns = [
		{ id: 'campaign_group', title: 'Campaign group' },
		{ id: 'spend', title: 'Spend' },
		{
			id: 'landing_page_visits',
			title: 'Total landing page visits',
			shortTitle: 'Visits',
			description: 'Meta link clicks to the landing page'
		},
		{
			id: 'visit_to_lead_pct',
			title: 'Visit → lead',
			shortTitle: 'Lead %',
			description: 'CRM leads as a percent of landing page visits'
		},
		{
			id: 'cost_per_visit',
			title: 'Cost per visit',
			shortTitle: 'Cost/visit',
			description: 'Spend divided by landing page visits'
		},
		{ id: 'facebook_leads', title: 'CRM leads' },
		{ id: 'cpl', title: 'CPL' },
		{ id: 'showings', title: 'Showings' },
		{
			id: 'cost_per_showing',
			title: 'Cost per showing',
			shortTitle: 'Cost/showing',
			description: 'Spend divided by CRM showings'
		}
	];

	let loaded = undefined;
	let loadedAudiences = undefined;
	let unsub = () => {};
	let unsubAudiences = () => {};
	let expandedGroups = new Set();
	let selectedVariants = new Set(VARIANT_ORDER);
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

	$: if (Query.isQuery(audiences)) {
		audiences.fetch();
		unsubAudiences();
		unsubAudiences = audiences.subscribe((value) => {
			loadedAudiences = value;
		});
	} else {
		loadedAudiences = audiences;
	}

	onDestroy(() => {
		unsub();
		unsubAudiences();
	});

	function rowsFrom(rows) {
		if (!rows) return [];
		return Query.isQuery(rows) ? Array.from(rows) : rows;
	}

	function fmtMoney(value) {
		return Math.round(Number(value) * 100) / 100;
	}

	function sumMetrics(rows) {
		return rows.reduce(
			(acc, row) => ({
				spend: acc.spend + Number(row.spend || 0),
				landing_page_visits: acc.landing_page_visits + Number(row.landing_page_visits || 0),
				facebook_leads: acc.facebook_leads + Number(row.facebook_leads || 0),
				showings: acc.showings + Number(row.showings || 0)
			}),
			{ spend: 0, landing_page_visits: 0, facebook_leads: 0, showings: 0 }
		);
	}

	function toDisplayRow(campaign_group, metrics) {
		const spend = fmtMoney(metrics.spend);
		const landing_page_visits = metrics.landing_page_visits;
		const facebook_leads = metrics.facebook_leads;
		const showings = metrics.showings;
		return {
			campaign_group,
			spend,
			landing_page_visits,
			visit_to_lead_pct:
				landing_page_visits > 0
					? Math.round((1000 * facebook_leads) / landing_page_visits) / 10
					: null,
			cost_per_visit:
				landing_page_visits > 0 ? fmtMoney(metrics.spend / landing_page_visits) : null,
			facebook_leads,
			cpl: facebook_leads > 0 ? fmtMoney(metrics.spend / facebook_leads) : null,
			showings,
			cost_per_showing: showings > 0 ? fmtMoney(metrics.spend / showings) : null
		};
	}

	function formatValue(columnId, value) {
		if (value == null || value === '') return '—';
		const num = Number(value);
		if (Number.isNaN(num)) return String(value);
		if (moneyCols.has(columnId)) {
			return num.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
		}
		if (pctCols.has(columnId)) {
			return `${num.toLocaleString('en-US', { maximumFractionDigits: 1 })}%`;
		}
		if (countCols.has(columnId)) {
			return num.toLocaleString('en-US');
		}
		return String(value);
	}

	function fmtFilterTotal(value) {
		return (
			'$' +
			Number(value).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
		);
	}

	function audienceValue(audience, columnId) {
		if (columnId === 'campaign_group') return audience.audience;
		if (columnId === 'cost_per_visit') {
			return audience.landing_page_visits > 0
				? fmtMoney(audience.spend / audience.landing_page_visits)
				: null;
		}
		if (columnId === 'visit_to_lead_pct') {
			return audience.landing_page_visits > 0
				? Math.round((1000 * audience.facebook_leads) / audience.landing_page_visits) / 10
				: null;
		}
		if (columnId === 'cpl') {
			return audience.facebook_leads > 0 ? fmtMoney(audience.spend / audience.facebook_leads) : null;
		}
		if (columnId === 'cost_per_showing') {
			return audience.showings > 0 ? fmtMoney(audience.spend / audience.showings) : null;
		}
		return audience[columnId];
	}

	function toggleGroup(group) {
		const next = new Set(expandedGroups);
		if (next.has(group)) {
			next.delete(group);
		} else {
			next.add(group);
		}
		expandedGroups = next;
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

	$: rawRows = rowsFrom(loaded);
	$: rawAudienceRows = rowsFrom(loadedAudiences);
	$: availableVariants = VARIANT_ORDER.filter((variant) =>
		rawRows.some((row) => row.website_variant === variant)
	);

	$: if (availableVariants.length && !variantFilterInitialized) {
		selectedVariants = new Set(availableVariants);
		variantFilterInitialized = true;
	}

	$: if (availableVariants.length && variantFilterInitialized) {
		const pruned = [...selectedVariants].filter((variant) => availableVariants.includes(variant));
		if (pruned.length !== selectedVariants.size) {
			selectedVariants = new Set(pruned);
		}
	}

	$: filteredRows = rawRows.filter((row) => selectedVariants.has(row.website_variant));
	$: filteredAudienceRows = rawAudienceRows.filter((row) => selectedVariants.has(row.website_variant));
	$: totalsByVariant = VARIANT_ORDER.reduce((acc, variant) => {
		acc[variant] = sumMetrics(rawRows.filter((row) => row.website_variant === variant)).spend;
		return acc;
	}, {});
	$: detailRows = GROUP_ORDER.map((group) =>
		toDisplayRow(group, sumMetrics(filteredRows.filter((row) => row.campaign_group === group)))
	).filter((row) => row.spend > 0 || row.landing_page_visits > 0 || row.facebook_leads > 0);
	$: totalRow = toDisplayRow('Total', sumMetrics(filteredRows));
	$: audiencesByGroup = filteredAudienceRows.reduce((acc, row) => {
		const group = row.campaign_group;
		if (!acc[group]) acc[group] = [];
		const existing = acc[group].find((item) => item.audience === row.audience);
		if (existing) {
			existing.spend += Number(row.spend || 0);
			existing.landing_page_visits += Number(row.landing_page_visits || 0);
			existing.facebook_leads += Number(row.facebook_leads || 0);
			existing.showings += Number(row.showings || 0);
		} else {
			acc[group].push({
				audience: row.audience,
				spend: Number(row.spend || 0),
				landing_page_visits: Number(row.landing_page_visits || 0),
				facebook_leads: Number(row.facebook_leads || 0),
				showings: Number(row.showings || 0)
			});
		}
		return acc;
	}, {});
	$: Object.values(audiencesByGroup).forEach((rows) => {
		rows.sort((a, b) => b.spend - a.spend);
	});
</script>

{#if loaded?.error}
	<p class="text-sm text-negative">{loaded.error.message}</p>
{:else if Query.isQuery(loaded) && !loaded.dataLoaded}
	<div class="mb-8 h-40 animate-pulse rounded-lg bg-base-200"></div>
{:else if rawRows.length}
<div bind:this={root} class="mb-10 rounded-lg border border-base-content/20 bg-base-100 p-4">
	<div class="mb-4 rounded-lg border border-base-content/20 bg-base-100 p-4">
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
					<span class="tabular-nums text-base-content-muted">{fmtFilterTotal(totalsByVariant[variant])}</span>
				</label>
			{/each}
		</div>
	</div>

	<p class="mb-2 text-xs text-base-content/60">Click a campaign group to expand audience breakdown.</p>
	<div class="campaign-groups-table overflow-x-auto rounded-lg border border-base-content/20">
		<table class="campaign-groups-grid min-w-full text-sm">
			<colgroup>
				<col class="col-name" />
				<col span="8" class="col-metric" />
			</colgroup>
			<thead class="bg-base-200/60 text-left">
				<tr>
					{#each columns as column}
						<th
							class="px-3 py-3 font-medium {column.id === 'campaign_group' ? 'name-header' : 'metric-header'}"
							title={column.description ?? column.title}
						>
							{column.shortTitle ?? column.title}
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each detailRows as row}
					{@const groupAudiences = audiencesByGroup[row.campaign_group] ?? []}
					{@const isExpanded = expandedGroups.has(row.campaign_group)}
					<tr
						class="group-row border-t border-base-content/10 cursor-pointer hover:bg-base-200/30"
						on:click={() => toggleGroup(row.campaign_group)}
						on:keydown={(event) => {
							if (event.key === 'Enter' || event.key === ' ') {
								event.preventDefault();
								toggleGroup(row.campaign_group);
							}
						}}
						tabindex="0"
						aria-expanded={isExpanded}
					>
						{#each columns as column, columnIndex}
							{#if columnIndex === 0}
								<td class="px-4 py-3 name-cell">
									<div class="name-cell-inner">
										<span class="chevron" aria-hidden="true">
											{isExpanded ? '▾' : '▸'}
										</span>
										<span class="name-text" title={row[column.id]}>
											{formatValue(column.id, row[column.id])}
										</span>
									</div>
								</td>
							{:else}
								<td class="px-4 py-3 metric-cell">
									{formatValue(column.id, row[column.id])}
								</td>
							{/if}
						{/each}
					</tr>
					{#if isExpanded}
						{#each groupAudiences as audience}
							{@const audienceName = audienceValue(audience, 'campaign_group')}
							<tr class="audience-row border-t border-base-content/5 bg-base-200/20 text-base-content/80">
								{#each columns as column}
									{#if column.id === 'campaign_group'}
										<td class="px-4 py-3 name-cell audience-name-cell">
											<span class="name-text" title={audienceName}>{audienceName}</span>
										</td>
									{:else}
										<td class="px-4 py-3 metric-cell">
											{formatValue(column.id, audienceValue(audience, column.id))}
										</td>
									{/if}
								{/each}
							</tr>
						{:else}
							<tr class="audience-row border-t border-base-content/5 bg-base-200/20 text-base-content/60">
								<td class="px-4 py-3 audience-name-cell" colspan={columns.length}>
									No audiences with spend in range.
								</td>
							</tr>
						{/each}
					{/if}
				{/each}
				{#if selectedVariants.size}
					<tr class="total-row border-t-2 border-base-content/30 bg-base-200/40 font-semibold">
						{#each columns as column, columnIndex}
							{#if columnIndex === 0}
								<td class="px-4 py-3 name-cell">
									<span class="name-text">{formatValue(column.id, totalRow[column.id])}</span>
								</td>
							{:else}
								<td class="px-4 py-3 metric-cell">
									{formatValue(column.id, totalRow[column.id])}
								</td>
							{/if}
						{/each}
					</tr>
				{/if}
			</tbody>
		</table>
	</div>
</div>
{/if}

<style>
	.campaign-groups-grid {
		table-layout: fixed;
		width: 100%;
		min-width: 68rem;
	}

	.col-name {
		width: 24%;
	}

	.col-metric {
		width: 8.4%;
	}

	.name-header,
	.metric-header {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.metric-header,
	.metric-cell {
		text-align: right;
		white-space: nowrap;
	}

	.name-cell {
		max-width: 0;
		overflow: hidden;
	}

	.name-cell-inner {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		min-width: 0;
	}

	.chevron {
		flex: 0 0 0.75rem;
		color: color-mix(in srgb, currentColor 50%, transparent);
	}

	.name-text {
		display: block;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		min-width: 0;
	}

	.audience-name-cell {
		padding-left: 2.5rem;
	}
</style>
