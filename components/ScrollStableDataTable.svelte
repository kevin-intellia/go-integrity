<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { tick } from 'svelte';
	import { DataTable } from '@evidence-dev/core-components';

	export let data;

	let container;

	function isPaginationInteraction(target) {
		return target?.closest?.('.page-changer, .page-input');
	}

	async function stabilizeScroll(event) {
		if (!container || !isPaginationInteraction(event.target)) return;

		const top = container.getBoundingClientRect().top + window.scrollY - 16;
		await tick();
		requestAnimationFrame(() => {
			window.scrollTo({ top: Math.max(0, top), left: window.scrollX });
		});
	}
</script>

<div bind:this={container} on:click={stabilizeScroll} on:change={stabilizeScroll} on:keyup={stabilizeScroll}>
	<DataTable {...$$restProps} {data}>
		<slot />
	</DataTable>
</div>
