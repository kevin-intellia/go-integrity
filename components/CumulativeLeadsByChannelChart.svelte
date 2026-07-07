<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { LineChart } from '@evidence-dev/core-components';

	export let data = undefined;

	function fmt(value) {
		return Number(value).toLocaleString('en-US');
	}

	const echartsOptions = {
		tooltip: {
			trigger: 'axis',
			show: true,
			confine: true,
			formatter(params) {
				const items = Array.isArray(params) ? params : [params];
				const header = items[0]?.axisValueLabel ?? items[0]?.name ?? '';
				let body = '';
				let allValue = null;
				let allMarker = '';

				for (let i = items.length - 1; i >= 0; i--) {
					const point = items[i];
					if (point.seriesName === 'stackTotal') continue;

					const yVal = point.value?.[1] ?? 0;
					const num = Number(yVal) || 0;

					if (point.seriesName === 'All') {
						allValue = num;
						allMarker = point.marker;
						continue;
					}

					body += `<br> <span style='font-size: 11px;'>${point.marker} ${point.seriesName}<span/><span style='float:right; margin-left: 10px; font-size: 12px;'>${fmt(num)}</span>`;
				}

				if (allValue !== null) {
					body += `<br><span style='font-weight: 600;'>${allMarker} All</span><span style='float:right; margin-left: 10px; font-weight: 600;'>${fmt(allValue)}</span>`;
				}

				return `<span style='font-weight: 600;'>${header}</span>${body}`;
			}
		}
	};
</script>

<LineChart
	{data}
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
