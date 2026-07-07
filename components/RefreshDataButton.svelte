<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { dev } from '$app/environment';
	import { Info } from '@evidence-dev/core-components';

	let loading = false;
	let error = '';
	let message = '';

	const refreshHelpDev =
		'Pulls the latest Meta ads and GHL CRM data, then rebuilds the dashboard. The page reloads when finished. Usually takes 30–90 seconds; allow up to 2 minutes on a slow connection. If the Meta token has expired, CRM data will still refresh.';

	const refreshHelpProd =
		'Starts a full rebuild with fresh CRM and Meta data. Takes about 2–3 minutes — reload the page when finished.';

	async function refreshData() {
		if (loading) return;

		loading = true;
		error = '';
		message = '';

		try {
			if (dev) {
				const response = await fetch('/api/refresh-data', { method: 'POST' });
				const result = await response.json();

				if (!response.ok || !result.ok) {
					throw new Error(result.error || 'Refresh failed');
				}

				window.location.reload();
				return;
			}

			const password = prompt('Refresh password (leave blank if none):') ?? '';
			const response = await fetch('/api/trigger-refresh', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ password })
			});
			const result = await response.json();

			if (!response.ok || !result.ok) {
				throw new Error(result.error || 'Refresh failed');
			}

			message = result.message || 'Rebuild started. Reload in a few minutes.';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Refresh failed';
		} finally {
			loading = false;
		}
	}
</script>

<div class="mb-6 flex items-center justify-end gap-2">
	{#if error}
		<span class="text-xs text-negative">{error}</span>
	{/if}
	{#if message}
		<span class="text-xs text-base-content-muted">{message}</span>
	{/if}
	<button
		type="button"
		class="rounded border border-base-content/15 px-2.5 py-1 text-xs text-base-content-muted transition-colors hover:border-base-content/30 hover:text-base-content disabled:opacity-50"
		on:click={refreshData}
		disabled={loading}
	>
		{loading ? 'Refreshing…' : 'Refresh data'}
	</button>
	<Info description={dev ? refreshHelpDev : refreshHelpProd} size={4} />
</div>
