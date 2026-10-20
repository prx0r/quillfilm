// Minimal Cloudflare binding type (keeps workers-types out of the app).
interface Fetcher {
  fetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response>;
}

export interface Env {
  ASSETS: Fetcher;
  OC_API_KEY: string;
  BRIDGE_URL?: string;
  BRIDGE_KEY?: string;
}

const GO_UPSTREAM = 'https://opencode.ai/zen/go/v1/chat/completions';

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);

    // Same-origin web search: DuckDuckGo via worker egress (the app box's
    // IP is datacenter-blocked for YouTube but DDG answers fine from here).
    // Returns [{title, url, snippet}] JSON for the chat web_search tool.
    if (url.pathname === '/api/search' && req.method === 'GET') {
      const q = (url.searchParams.get('q') || '').slice(0, 300);
      if (!q) return new Response('missing q', { status: 400 });
      try {
        const ddg = await fetch(
          'https://html.duckduckgo.com/html/?q=' + encodeURIComponent(q),
          { headers: { 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36' } },
        );
        const html = await ddg.text();
        const results: Array<{ title: string; url: string; snippet: string }> = [];
        for (const block of html.split('results_links')) {
          if (results.length >= 8) break;
          const link = block.match(/<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]*)<\/a>/);
          if (!link) continue;
          let href = link[1];
          const uddg = href.match(/[?&]uddg=([^&]+)/);
          try {
            href = uddg ? decodeURIComponent(uddg[1]) : new URL(href, 'https://duckduckgo.com').href;
          } catch { continue; }
          if (!/^https?:\/\//.test(href)) continue;
          const snip = block.match(/class="result__snippet"[^>]*>([\s\S]*?)<\/a>/);
          const snipText = snip ? snip[1].replace(/<[^>]*>/g, '') : '';
          results.push({
            title: link[2].replace(/&#x27;|&#39;/g, "'").replace(/&amp;/g, '&').trim(),
            url: href,
            snippet: snipText.replace(/&#x27;|&#39;/g, "'").replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim().slice(0, 300),
          });
        }
        return Response.json({ results });
      } catch (e) {
        return new Response('search upstream failed', { status: 502 });
      }
    }

    // Box bridge: /api/yt/* and /api/render/* proxy to the quill-bridge
    // service (yt-dlp + transcripts + clips; async render jobs). The bridge
    // lives wherever YouTube/GPU is reachable; BRIDGE_URL points at it
    // (tunnel hostname). Until YouTube cookies land on a bridge box, its yt
    // endpoints answer 502 youtube-blocked.
    // No bridge configured (or tunnel down): answer 501, never a bare 404.
    const isBridgePath = url.pathname.startsWith('/api/yt/') || url.pathname.startsWith('/api/render/') || url.pathname.startsWith('/api/tts/');
    if (isBridgePath && !env.BRIDGE_URL) {
      return Response.json({ error: 'bridge-offline',
        hint: 'quill-bridge not connected — video pulls + render jobs need it (see BRIDGE.md)' },
        { status: 501 });
    }
    if (isBridgePath && env.BRIDGE_URL) {
      const target = env.BRIDGE_URL.replace(/\/$/, '') + url.pathname.slice('/api'.length) + url.search;
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (env.BRIDGE_KEY) headers['X-Bridge-Key'] = env.BRIDGE_KEY;
      const init: RequestInit = { method: req.method, headers };
      if (req.method !== 'GET' && req.method !== 'HEAD') init.body = await req.arrayBuffer();
      const upstream = await fetch(target, init);
      const body = await upstream.arrayBuffer();
      return new Response(body, {
        status: upstream.status,
        headers: { 'Content-Type': upstream.headers.get('Content-Type') || 'application/json' },
      });
    }

    // Same-origin AI proxy: browser posts OpenAI-shape here, worker injects
    // the Go key + session header server-side. Key never reaches the client.
    if (url.pathname === '/v1/chat/completions' && req.method === 'POST') {
      let body: unknown;
      try {
        body = await req.json();
      } catch {
        return new Response('bad json', { status: 400 });
      }
      const upstream = await fetch(GO_UPSTREAM, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${env.OC_API_KEY}`,
          'x-opencode-session': crypto.randomUUID(),
        },
        body: JSON.stringify(body),
      });
      const text = await upstream.text();
      return new Response(text, {
        status: upstream.status,
        headers: {
          'Content-Type':
            upstream.headers.get('Content-Type') || 'application/json',
        },
      });
    }
    return env.ASSETS.fetch(req);
  },
};
