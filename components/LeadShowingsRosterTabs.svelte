<script context="module">
	export const evidenceInclude = true;
</script>

<script>
	import { Column } from '@evidence-dev/core-components';
	import ScrollStableDataTable from './ScrollStableDataTable.svelte';

	export let leadsData = undefined;
	export let showingsData = undefined;

	let activeTab = 'leads';

	const tabClass = (tab) =>
		`rounded-md border px-3 py-1.5 text-sm transition-colors ${
			activeTab === tab
				? 'border-base-content/30 bg-base-200 font-medium'
				: 'border-base-content/20 hover:bg-base-200'
		}`;
</script>

<div class="mb-4 flex flex-wrap gap-2">
	<button type="button" class={tabClass('leads')} on:click={() => (activeTab = 'leads')}>
		All leads
	</button>
	<button type="button" class={tabClass('showings')} on:click={() => (activeTab = 'showings')}>
		All showings
	</button>
</div>

{#if activeTab === 'leads'}
	<ScrollStableDataTable
		data={leadsData}
		search=true
		rows=500
		sort="lead_date desc"
		title="All leads"
		subtitle="Every CRM lead in the date range."
	>
		<Column id="contact_name" title="Name" description="Contact name from GoHighLevel." />
		<Column id="lead_date" title="Lead date" description="Date the lead entered the CRM." />
		<Column id="pipeline_stage" title="Stage" description="Pipeline stage or opportunity status." />
		<Column id="channel" title="Channel" description="Marketing channel attributed to this lead." />
		<Column id="audience" title="Audience" description="Ad audience mapped from UTM term (Facebook leads)." />
		<Column id="showing_status" title="Showing status" description="Showing requested or booked (appointments only)." />
		<Column id="entry_point" title="Entry point" description="Form or source that created the lead." />
		<Column id="email" title="Email" description="Contact email from GoHighLevel." />
		<Column id="phone" title="Phone" description="Contact phone from GoHighLevel." />
		<Column id="first_name" title="First name" description="Contact first name." />
		<Column id="last_name" title="Last name" description="Contact last name." />
		<Column id="contact_source" title="Contact source" description="Form or source recorded on the contact." />
		<Column id="contact_type" title="Contact type" description="Contact type in GoHighLevel." />
		<Column id="contact_date_added" title="Contact added" description="When the contact was created in GoHighLevel." />
		<Column id="contact_date_updated" title="Contact updated" description="When the contact was last updated." />
		<Column id="tags" title="Tags" description="Tags applied to the contact." />
		<Column id="utm_source" title="UTM source" description="UTM source from first-touch attribution." />
		<Column id="utm_medium" title="UTM medium" description="UTM medium from first-touch attribution." />
		<Column id="utm_campaign" title="UTM campaign" description="UTM campaign from first-touch attribution." />
		<Column id="utm_content" title="UTM content" description="UTM content from first-touch attribution." />
		<Column id="utm_term" title="UTM term" description="UTM term used to map ad audience." />
		<Column id="utm_keyword" title="UTM keyword" description="UTM keyword from first-touch attribution." />
		<Column id="device_type" title="Device" description="Device type from first-touch attribution." />
		<Column id="session_source" title="Session source" description="Session source when no UTM tags are present." />
		<Column id="referrer" title="Referrer" description="Referring URL from first-touch attribution." />
		<Column id="page_url" title="Page URL" description="Landing page URL from first-touch attribution." />
		<Column id="user_agent" title="User agent" description="Browser user agent from first-touch attribution." />
		<Column id="opportunity_name" title="Opportunity" description="Opportunity name in GoHighLevel." />
		<Column id="opportunity_status" title="Opp. status" description="Opportunity status in GoHighLevel." />
		<Column id="opportunity_source" title="Opp. source" description="Source recorded on the opportunity." />
		<Column id="monetary_value" title="Value" fmt='$#,##0.00' description="Monetary value on the opportunity." />
		<Column id="opportunity_created" title="Opp. created" description="When the opportunity was created." />
		<Column id="opportunity_updated" title="Opp. updated" description="When the opportunity was last updated." />
		<Column id="last_status_change" title="Last status change" description="When the opportunity status last changed." />
		<Column id="pipeline_id" title="Pipeline ID" description="GoHighLevel pipeline identifier." />
		<Column id="pipeline_stage_id" title="Stage ID" description="GoHighLevel pipeline stage identifier." />
		<Column id="opp_utm_source" title="Opp. UTM source" description="UTM source stored on the opportunity." />
		<Column id="opp_utm_medium" title="Opp. UTM medium" description="UTM medium stored on the opportunity." />
		<Column id="opp_utm_campaign" title="Opp. UTM campaign" description="UTM campaign stored on the opportunity." />
		<Column id="opp_utm_content" title="Opp. UTM content" description="UTM content stored on the opportunity." />
		<Column id="opp_utm_term" title="Opp. UTM term" description="UTM term stored on the opportunity." />
		<Column id="opp_utm_keyword" title="Opp. UTM keyword" description="UTM keyword stored on the opportunity." />
		<Column id="opportunity_id" title="Opportunity ID" description="GoHighLevel opportunity identifier." />
		<Column id="contact_id" title="Contact ID" description="GoHighLevel contact identifier." />
	</ScrollStableDataTable>
{:else}
	<ScrollStableDataTable
		data={showingsData}
		search=true
		rows=500
		sort="lead_date desc"
		title="All showings"
		subtitle="Full contact and opportunity fields for each showing request."
	>
		<Column id="contact_name" title="Name" description="Contact name from GoHighLevel." />
		<Column id="showing_status" title="Status" description="Showing requested or booked via private showing form." />
		<Column id="lead_date" title="Lead date" description="Date the lead entered the CRM." />
		<Column id="channel" title="Channel" description="Marketing channel attributed to this lead." />
		<Column id="audience" title="Audience" description="Ad audience mapped from UTM term." />
		<Column id="email" title="Email" description="Contact email from GoHighLevel." />
		<Column id="phone" title="Phone" description="Contact phone from GoHighLevel." />
		<Column id="first_name" title="First name" description="Contact first name." />
		<Column id="last_name" title="Last name" description="Contact last name." />
		<Column id="contact_source" title="Contact source" description="Form or source recorded on the contact." />
		<Column id="contact_type" title="Contact type" description="Contact type in GoHighLevel." />
		<Column id="contact_date_added" title="Contact added" description="When the contact was created in GoHighLevel." />
		<Column id="contact_date_updated" title="Contact updated" description="When the contact was last updated." />
		<Column id="tags" title="Tags" description="Tags applied to the contact." />
		<Column id="utm_source" title="UTM source" description="UTM source from first-touch attribution." />
		<Column id="utm_medium" title="UTM medium" description="UTM medium from first-touch attribution." />
		<Column id="utm_campaign" title="UTM campaign" description="UTM campaign from first-touch attribution." />
		<Column id="utm_content" title="UTM content" description="UTM content from first-touch attribution." />
		<Column id="utm_term" title="UTM term" description="UTM term used to map ad audience." />
		<Column id="utm_keyword" title="UTM keyword" description="UTM keyword from first-touch attribution." />
		<Column id="device_type" title="Device" description="Device type from first-touch attribution." />
		<Column id="session_source" title="Session source" description="Session source when no UTM tags are present." />
		<Column id="referrer" title="Referrer" description="Referring URL from first-touch attribution." />
		<Column id="page_url" title="Page URL" description="Landing page URL from first-touch attribution." />
		<Column id="user_agent" title="User agent" description="Browser user agent from first-touch attribution." />
		<Column id="opportunity_name" title="Opportunity" description="Opportunity name in GoHighLevel." />
		<Column id="opportunity_status" title="Opp. status" description="Opportunity status in GoHighLevel." />
		<Column id="opportunity_source" title="Opp. source" description="Source recorded on the opportunity." />
		<Column id="monetary_value" title="Value" fmt='$#,##0.00' description="Monetary value on the opportunity." />
		<Column id="opportunity_created" title="Opp. created" description="When the opportunity was created." />
		<Column id="opportunity_updated" title="Opp. updated" description="When the opportunity was last updated." />
		<Column id="last_status_change" title="Last status change" description="When the opportunity status last changed." />
		<Column id="pipeline_id" title="Pipeline ID" description="GoHighLevel pipeline identifier." />
		<Column id="pipeline_stage_id" title="Stage ID" description="GoHighLevel pipeline stage identifier." />
		<Column id="opp_utm_source" title="Opp. UTM source" description="UTM source stored on the opportunity." />
		<Column id="opp_utm_medium" title="Opp. UTM medium" description="UTM medium stored on the opportunity." />
		<Column id="opp_utm_campaign" title="Opp. UTM campaign" description="UTM campaign stored on the opportunity." />
		<Column id="opp_utm_content" title="Opp. UTM content" description="UTM content stored on the opportunity." />
		<Column id="opp_utm_term" title="Opp. UTM term" description="UTM term stored on the opportunity." />
		<Column id="opp_utm_keyword" title="Opp. UTM keyword" description="UTM keyword stored on the opportunity." />
		<Column id="opportunity_id" title="Opportunity ID" description="GoHighLevel opportunity identifier." />
		<Column id="contact_id" title="Contact ID" description="GoHighLevel contact identifier." />
	</ScrollStableDataTable>
{/if}
