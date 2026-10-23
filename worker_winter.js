// Paste this entire file into a new Cloudflare Worker and click Deploy.
const FEED_URL = "https://raw.githubusercontent.com/Loungechill/Autorus_Linglong/main/feed_winter.xml";

export default {
  async fetch(request) {
    const path = new URL(request.url).pathname;
    if (path !== "/" && path !== "/feed.xml") {
      return new Response("Not found", { status: 404 });
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", {
        status: 405, headers: { Allow: "GET, HEAD" },
      });
    }
    try {
      const upstream = await fetch(FEED_URL, {
        cf: { cacheTtl: 300, cacheEverything: true },
        signal: AbortSignal.timeout(30000),
      });
      if (!upstream.ok) throw new Error(`GitHub returned ${upstream.status}`);
      return new Response(request.method === "HEAD" ? null : upstream.body, {
        headers: {
          "Content-Type": "application/xml; charset=utf-8",
          "Cache-Control": "public, max-age=300",
          "X-Content-Type-Options": "nosniff",
        },
      });
    } catch (error) {
      console.error("Winter feed unavailable", error);
      return new Response("Feed temporarily unavailable", {
        status: 502, headers: { "Cache-Control": "no-store" },
      });
    }
  },
};
