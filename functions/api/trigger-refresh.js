export async function onRequestPost({ env, request }) {
	const password = env.REFRESH_PASSWORD;

	if (password) {
		let body = {};
		try {
			body = await request.json();
		} catch {
			body = {};
		}

		if (body.password !== password) {
			return Response.json({ ok: false, error: 'Invalid refresh password' }, { status: 401 });
		}
	}

	const hook = env.DEPLOY_HOOK_URL;
	if (!hook) {
		return Response.json(
			{ ok: false, error: 'Deploy hook is not configured' },
			{ status: 500 }
		);
	}

	const response = await fetch(hook, { method: 'POST' });
	if (!response.ok) {
		return Response.json({ ok: false, error: 'Deploy hook request failed' }, { status: 502 });
	}

	return Response.json({
		ok: true,
		message: 'Rebuild started. Fresh data will be live in about 2–3 minutes. Reload this page then.'
	});
}
