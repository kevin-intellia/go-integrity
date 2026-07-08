<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	import { showQueries } from '@evidence-dev/component-utilities/stores';
	import { browser } from '$app/environment';
	import { afterNavigate, goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { addBasePath } from '@evidence-dev/sdk/utils/svelte';
	import { dev } from '$app/environment';
	import { onMount, tick } from 'svelte';

	export let data;

	const productionHome =
		import.meta.env.PUBLIC_DEPLOY_TARGET === 'internal' ? '/meta-ads/' : '/client-report/';
	const homeHref = addBasePath(dev ? '/meta-ads/' : productionHome);
	const logoHref = homeHref;

	function isRootPath(pathname) {
		const normalized = pathname.replace(/\/$/, '') || '/';
		const root = addBasePath('/').replace(/\/$/, '') || '/';
		return normalized === root;
	}

	function redirectHomeToDefaultReport() {
		if (!browser || !isRootPath($page.url.pathname)) return;
		goto(homeHref, { replaceState: true });
	}

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
		redirectHomeToDefaultReport();
		fixLogoLinks();
	});

	afterNavigate(async () => {
		await tick();
		redirectHomeToDefaultReport();
		fixLogoLinks();
	});
</script>

<EvidenceDefaultLayout {data} neverShowQueries={true} logo="/integrity-logo.jpg" builtWithEvidence={false}>
	<slot slot="content" />
</EvidenceDefaultLayout>
