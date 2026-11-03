
const ACTIVATION_URL =
  "https://cloudkrafts-qr-manager-x3zh.onrender.com/activate";

const SUPABASE_TABLE = "qr";

function redirect(url, status = 302) {
  return new Response(null, {
    status,
    headers: {
      Location: url,
      "Cache-Control": "no-store",
    },
  });
}

function validDestination(value) {
  try {
    const url = new URL(value);

    return (
      (url.protocol === "https:" || url.protocol === "http:") &&
      Boolean(url.hostname) &&
      !url.username &&
      !url.password
    );
  } catch {
    return false;
  }
}

export default {
  async fetch(request, env) {
    const requestUrl = new URL(request.url);

    // Health check
    if (requestUrl.pathname === "/healthz") {
      return new Response("CloudKrafts QR Redirect is running", {
        headers: {
          "Content-Type": "text/plain",
          "Cache-Control": "no-store",
        },
      });
    }

    // QR redirect endpoint
    const match = requestUrl.pathname.match(/^\/r\/(ck[0-9]{6})$/);

    if (!match) {
      return new Response("Unknown QR code", {
        status: 404,
        headers: {
          "Cache-Control": "no-store",
        },
      });
    }

    const qrId = match[1];

    // Supabase configuration must be stored as Cloudflare secrets.
    if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
      return new Response("Redirect service configuration missing", {
        status: 503,
      });
    }

    const supabaseUrl = env.SUPABASE_URL.replace(/\/+$/, "");

    const query = new URLSearchParams({
      select: "id,status,url",
      id: `eq.${qrId}`,
      limit: "1",
    });

    const databaseResponse = await fetch(
      `${supabaseUrl}/rest/v1/${SUPABASE_TABLE}?${query}`,
      {
        method: "GET",
        headers: {
          apikey: env.SUPABASE_SERVICE_ROLE_KEY,
          Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
          Accept: "application/json",
        },
      }
    );

    if (!databaseResponse.ok) {
      return new Response("QR database temporarily unavailable", {
        status: 503,
        headers: {
          "Cache-Control": "no-store",
        },
      });
    }

    const records = await databaseResponse.json();

    if (!Array.isArray(records) || records.length === 0) {
      return new Response("Unknown QR code", {
        status: 404,
        headers: {
          "Cache-Control": "no-store",
        },
      });
    }

    const qr = records[0];

    // Activated QR: direct customer redirect.
    if (qr.status === "active" && validDestination(qr.url)) {
      return redirect(qr.url);
    }

    // Unused QR: existing Render activation page.
    const activationUrl = new URL(ACTIVATION_URL);
    activationUrl.searchParams.set("id", qrId);

    return redirect(activationUrl.toString());
  },
};
