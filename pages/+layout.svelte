<script>
	import '@evidence-dev/tailwind/fonts.css';
	import '../app.css';
	import { EvidenceDefaultLayout } from '@evidence-dev/core-components';
	import { showQueries } from '@evidence-dev/component-utilities/stores';
	import { browser } from '$app/environment';

	export let data;

	if (browser) {
		showQueries.set(false);
	}
</script>

<EvidenceDefaultLayout {data} neverShowQueries={true} logo="/integrity-logo.jpg" builtWithEvidence={false}>
	<slot slot="content" />
</EvidenceDefaultLayout>
