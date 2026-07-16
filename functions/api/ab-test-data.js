const BASE_URL = 'https://services.leadconnectorhq.com';
const API_VERSION = '2021-07-28';
const PAGE_SIZE = 100;
const TEST_START_UTC = '2026-07-15T15:19:56';
const CONTROL_SOURCE_PATTERN = /vt-optin/i;
const VARIATION_SOURCE = 'Website Lead';
const STOWE_SITE = 'stowelegacyestate.com';
const KV_VIEWS_KEY = 'home_ab_page_views';
const RETRYABLE_STATUS_CODES = new Set([400, 429, 500, 502, 503, 504]);
const RETRY_DELAYS_MS = [1000, 2000, 4000];

function apiHeaders(token) {
	return {
		Authorization: `Bearer ${token}`,
		Version: API_VERSION,
		Accept: 'application/json',
		'Content-Type': 'application/json'
	};
}

function firstAttribution(record) {
	const attributions = record.attributions || [];
	return attributions[0] || {};
}

function pageUrlFromContact(contact) {
	const attr = firstAttribution(contact);
	return attr.pageUrl || attr.url || '';
}

function sleep(ms) {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

async function requestWithRetries(url, options) {
	let lastError = null;

	for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt++) {
		try {
			const response = await fetch(url, options);
			if (RETRYABLE_STATUS_CODES.has(response.status) && attempt < RETRY_DELAYS_MS.length) {
				await sleep(RETRY_DELAYS_MS[attempt]);
				continue;
			}
			if (!response.ok) {
				const body = await response.text().catch(() => '');
				throw new Error(`GHL request failed (${response.status}): ${body.slice(0, 200)}`);
			}
			return response;
		} catch (error) {
			lastError = error;
			if (attempt >= RETRY_DELAYS_MS.length) {
				throw error;
			}
			await sleep(RETRY_DELAYS_MS[attempt]);
		}
	}

	throw lastError || new Error(`GHL request failed for ${url}`);
}

async function fetchAllContacts(token, locationId) {
	const headers = apiHeaders(token);
	let params = new URLSearchParams({
		locationId,
		limit: String(PAGE_SIZE)
	});
	const rows = [];
	let expectedTotal = null;

	while (true) {
		const response = await requestWithRetries(`${BASE_URL}/contacts/?${params}`, { headers });
		const payload = await response.json();
		const contacts = payload.contacts || [];
		const meta = payload.meta || {};

		if (expectedTotal === null) {
			expectedTotal = Number(meta.total) || null;
		}

		for (const contact of contacts) {
			rows.push(contact);
		}

		if (expectedTotal !== null && rows.length >= expectedTotal) {
			break;
		}
		if (!contacts.length || !meta.nextPageUrl) {
			break;
		}

		params = new URLSearchParams({
			locationId,
			limit: String(PAGE_SIZE),
			startAfter: String(meta.startAfter),
			startAfterId: meta.startAfterId
		});
	}

	if (expectedTotal !== null && rows.length < expectedTotal) {
		throw new Error(`GHL contacts fetch incomplete: got ${rows.length} of ${expectedTotal}`);
	}

	return rows;
}

function contactName(contact) {
	const parts = [contact.firstName, contact.lastName].filter(
		(part) => part && String(part) !== 'None'
	);
	return parts.join(' ').trim() || '—';
}

function isSinceTestStart(dateAdded) {
	if (!dateAdded) {
		return false;
	}
	return new Date(dateAdded).getTime() >= new Date(`${TEST_START_UTC}Z`).getTime();
}

function buildSubmissionRow(contact, index) {
	const pageUrl = pageUrlFromContact(contact);
	return {
		n: index,
		time: contact.dateAdded || '',
		name: contactName(contact),
		email: contact.email || '—',
		url: pageUrl ? pageUrl.slice(0, 120) : '—',
		source: contact.source || '—',
		duplicate: false
	};
}

function isControlContact(contact) {
	const email = (contact.email || '').trim();
	const source = contact.source || '';
	if (!email || !isSinceTestStart(contact.dateAdded)) {
		return false;
	}
	return CONTROL_SOURCE_PATTERN.test(source);
}

function isVariationContact(contact) {
	const email = (contact.email || '').trim();
	const source = (contact.source || '').trim();
	if (!email || !isSinceTestStart(contact.dateAdded)) {
		return false;
	}
	if (source !== VARIATION_SOURCE) {
		return false;
	}
	return pageUrlFromContact(contact).toLowerCase().includes(STOWE_SITE);
}

function filterArmContacts(contacts, arm) {
	return contacts
		.filter((contact) => (arm === 'control' ? isControlContact(contact) : isVariationContact(contact)))
		.sort((a, b) => new Date(a.dateAdded).getTime() - new Date(b.dateAdded).getTime());
}

function markDuplicates(rows) {
	const seen = new Set();
	return rows.map((row) => {
		const email = String(row.email || '')
			.trim()
			.toLowerCase();
		if (!email || email === '—') {
			return { ...row, duplicate: false };
		}
		const duplicate = seen.has(email);
		seen.add(email);
		return { ...row, duplicate };
	});
}

function padToGhlCount(rows, target) {
	const out = rows.map((row) => ({ ...row }));
	while (out.length < target) {
		out.push({
			n: out.length + 1,
			time: '',
			name: 'Repeat submit',
			email: '—',
			url: '—',
			source: '—',
			duplicate: true,
			unknown: true
		});
	}
	return out.map((row, index) => ({ ...row, n: index + 1 }));
}

async function loadStaticJson(request, filename) {
	const statsUrl = new URL(`/${filename}`, request.url);
	try {
		const response = await fetch(statsUrl, { cache: 'no-store' });
		if (!response.ok) {
			return null;
		}
		return response.json();
	} catch {
		return null;
	}
}

async function loadSharedStats(env) {
	if (!env.AB_TEST_KV) {
		return null;
	}
	const raw = await env.AB_TEST_KV.get(KV_VIEWS_KEY);
	if (!raw) {
		return null;
	}
	try {
		return JSON.parse(raw);
	} catch {
		return null;
	}
}

async function saveSharedStats(env, stats) {
	if (!env.AB_TEST_KV) {
		throw new Error(
			'Shared stats storage is not configured. Add AB_TEST_KV KV binding on the internal Cloudflare project.'
		);
	}
	const payload = {
		views: {
			control: Number(stats.views?.control) || 0,
			variation: Number(stats.views?.variation) || 0
		},
		optins: {
			control: Number(stats.optins?.control) || 0,
			variation: Number(stats.optins?.variation) || 0
		},
		updated_at: new Date().toISOString(),
		source: 'GHL split test UI'
	};
	await env.AB_TEST_KV.put(KV_VIEWS_KEY, JSON.stringify(payload));
	return payload;
}

function rowFromManual(entry, formName) {
	return {
		n: 0,
		time: entry.time_edt || '',
		name: entry.name || '—',
		email: entry.email || '—',
		url: entry.url || '—',
		source: entry.source || formName,
		duplicate: Boolean(entry.duplicate)
	};
}

function mergeManualRows(apiRows, manualEntries, formName) {
	const out = [...apiRows];

	for (const entry of manualEntries || []) {
		const email = String(entry.email || '')
			.trim()
			.toLowerCase();
		if (!email) {
			continue;
		}

		const manualCount = manualEntries.filter(
			(row) =>
				String(row.email || '')
					.trim()
					.toLowerCase() === email
		).length;
		const currentCount = out.filter(
			(row) =>
				String(row.email || '')
					.trim()
					.toLowerCase() === email
		).length;

		if (currentCount < manualCount) {
			out.push(rowFromManual(entry, formName));
		}
	}

	return out.sort((a, b) => new Date(a.time || 0).getTime() - new Date(b.time || 0).getTime());
}

async function buildGhlStats(env, request, controlRows, variationRows) {
	const sharedStats = await loadSharedStats(env);
	const staticStats = (await loadStaticJson(request, 'ghl_split_stats_home_ab.json')) || {};
	const viewsSource = sharedStats?.views ? sharedStats : staticStats;
	const optinsSource = sharedStats?.optins ? sharedStats : staticStats;

	return {
		views: {
			control: Number(viewsSource?.views?.control) || 0,
			variation: Number(viewsSource?.views?.variation) || 0
		},
		optins: {
			control: Number(optinsSource?.optins?.control) || controlRows.length,
			variation: Number(optinsSource?.optins?.variation) || variationRows.length
		},
		updated_at: sharedStats?.updated_at || staticStats.updated_at || '',
		stats_source: sharedStats?.views || sharedStats?.optins ? 'shared' : 'static',
		notes: staticStats.notes || ''
	};
}

async function buildAbTestPayload(env, request) {
	const token = env.GHL_PRIVATE_INTEGRATION_TOKEN;
	const locationId = (env.GHL_LOCATION_ID || '').trim();

	if (!token || !locationId) {
		throw new Error('GHL credentials are not configured on this deployment');
	}

	const contacts = await fetchAllContacts(token, locationId);
	const formConfig = (await loadStaticJson(request, 'form_submissions_home_ab.json')) || {};

	const controlRaw = filterArmContacts(contacts, 'control').map((contact, index) =>
		buildSubmissionRow(contact, index + 1)
	);
	const variationRaw = filterArmContacts(contacts, 'variation').map((contact, index) =>
		buildSubmissionRow(contact, index + 1)
	);

	const controlMerged = mergeManualRows(
		controlRaw,
		formConfig.control_submissions,
		formConfig.control_form_name || 'Control form'
	);
	const variationMerged = mergeManualRows(
		variationRaw,
		formConfig.variation_submissions,
		formConfig.variation_form_name || 'Funnel Leads'
	);

	const controlMarked = markDuplicates(controlMerged);
	const variationMarked = markDuplicates(variationMerged);
	const ghl = await buildGhlStats(env, request, controlMarked, variationMarked);

	return {
		ok: true,
		updated_at: new Date().toISOString(),
		control_submissions: padToGhlCount(controlMarked, ghl.optins.control),
		variation_submissions: padToGhlCount(variationMarked, ghl.optins.variation),
		ghl
	};
}

export async function onRequestGet({ env, request }) {
	try {
		const payload = await buildAbTestPayload(env, request);
		return Response.json(payload);
	} catch (error) {
		return Response.json(
			{
				ok: false,
				error: error instanceof Error ? error.message : 'Failed to load A/B test data'
			},
			{ status: 502 }
		);
	}
}

export async function onRequestPost({ env, request }) {
	let body = {};
	try {
		body = await request.json();
	} catch {
		return Response.json({ ok: false, error: 'Invalid JSON body' }, { status: 400 });
	}

	const controlViews = Number(body?.views?.control);
	const variationViews = Number(body?.views?.variation);
	const controlOptins = Number(body?.optins?.control);
	const variationOptins = Number(body?.optins?.variation);
	if (
		!Number.isFinite(controlViews) ||
		!Number.isFinite(variationViews) ||
		!Number.isFinite(controlOptins) ||
		!Number.isFinite(variationOptins) ||
		controlViews < 0 ||
		variationViews < 0 ||
		controlOptins < 0 ||
		variationOptins < 0
	) {
		return Response.json({ ok: false, error: 'Invalid GHL stats — enter views and opt-ins' }, { status: 400 });
	}

	try {
		await saveSharedStats(env, {
			views: { control: controlViews, variation: variationViews },
			optins: { control: controlOptins, variation: variationOptins }
		});
		const payload = await buildAbTestPayload(env, request);
		return Response.json(payload);
	} catch (error) {
		return Response.json(
			{
				ok: false,
				error: error instanceof Error ? error.message : 'Failed to save GHL stats'
			},
			{ status: 500 }
		);
	}
}
