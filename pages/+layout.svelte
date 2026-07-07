<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	import { showQueries } from '@evidence-dev/component-utilities/stores';
	import { browser } from '$app/environment';
	import { afterNavigate } from '$app/navigation';
	import { addBasePath } from '@evidence-dev/sdk/utils/svelte';
	import { onMount, tick } from 'svelte';

	export let data;

	const logoHref = addBasePath('/client-report/');

	function fixLogoLinks() {
		document.querySelectorAll('a').forEach((link) => {
			if (link.querySelector('img[alt="Home"]')) {
				link.href = logoHref;
			}
		});
	}

	if (browser) {
		showQueries.set(false);
	}

	onMount(() => {
		fixLogoLinks();
	});

	afterNavigate(async () => {
		await tick();
		fixLogoLinks();
	});
</script>

<EvidenceDefaultLayout {data} neverShowQueries={true} logo="/integrity-logo.jpg" builtWithEvidence={false}>
	<slot slot="content" />
</EvidenceDefaultLayout>
