import { check } from "k6";
import exec from "k6/execution";
import http from "k6/http";

const REQUIRED = ["BASE_URL", "LOAD_EMAIL", "LOAD_PASSWORD", "LOAD_PROVIDER_ID"];
const ALLOWED_HOST = /^(localhost|127\.0\.0\.1)$|(^|[.-])(staging|stg)([.-]|$)/;
const MS_PER_HOUR = 3600000;
const MS_PER_DAY = 86400000;
const SESSION_REFRESH_MS = 600000;
const JSON_HEADERS = { "Content-Type": "application/json", Accept: "application/json" };

const BASE_URL = withoutTrailingSlash(setting("BASE_URL", ""));
const EMAIL = setting("LOAD_EMAIL", "");
const PASSWORD = setting("LOAD_PASSWORD", "");
const PROVIDER_ID = setting("LOAD_PROVIDER_ID", "");
const PLACE_CODE = setting("LOAD_PLACE_CODE", "11");
const VISIT_TYPE = setting("LOAD_VISIT_TYPE", "Established patient");
const BILLED_CODE = setting("LOAD_BILLED_CODE", "99213");
const NOTES_PER_DAY = positive("NOTES_PER_DAY", 3000);
const WORKDAY_HOURS = positive("WORKDAY_HOURS", 8);
const NOTES_PER_UPLOAD = Math.max(1, Math.round(positive("NOTES_PER_UPLOAD", 10)));
const READS_PER_NOTE = positive("READS_PER_NOTE", 4);
const PEAK_FACTOR = positive("PEAK_FACTOR", 1);
const DURATION = setting("DURATION", "15m");

const uploadsPerHour = (NOTES_PER_DAY / NOTES_PER_UPLOAD / WORKDAY_HOURS) * PEAK_FACTOR;
const readsPerHour = ((NOTES_PER_DAY * READS_PER_NOTE) / WORKDAY_HOURS) * PEAK_FACTOR;

export const options = {
  scenarios: {
    uploads: arrivals("upload", uploadsPerHour, 3),
    reviews: arrivals("review", readsPerHour, 6),
  },
  thresholds: {
    checks: ["rate>0.99"],
    http_req_failed: ["rate<0.01"],
    "http_req_duration{name:sign_in}": ["p(95)<1500"],
    "http_req_duration{name:queue}": ["p(95)<800"],
    "http_req_duration{name:note}": ["p(95)<800"],
    "http_req_duration{name:upload}": ["p(95)<8000"],
  },
};

let session = null;

export function setup() {
  const missing = REQUIRED.filter((name) => !setting(name, ""));
  if (missing.length > 0) throw new Error(`set ${missing.join(", ")}`);
  const host = hostOf(BASE_URL);
  if (!ALLOWED_HOST.test(host)) throw new Error(`refusing to load ${host}: use localhost or a staging host`);
}

export function review() {
  const headers = authorised();
  const queue = http.get(`${BASE_URL}/api/notes`, { headers, tags: { name: "queue" } });
  check(queue, { "queue listed": (response) => response.status === 200 });
  const items = queue.status === 200 ? queue.json("items") || [] : [];
  if (items.length === 0) return;
  const note = items[Math.floor(Math.random() * items.length)];
  const detail = http.get(`${BASE_URL}/api/notes/${note.id}`, { headers, tags: { name: "note" } });
  check(detail, { "note opened": (response) => response.status === 200 });
}

export function upload() {
  const headers = authorised();
  const serviceDate = new Date(Date.now() - MS_PER_DAY).toISOString().slice(0, 10);
  const files = Array.from({ length: NOTES_PER_UPLOAD }, (_, index) => syntheticNote(serviceDate, index));
  const details = files.map(() => ({ billed: BILLED_CODE, visit_type: null }));
  const fields = {
    provider_id: PROVIDER_ID,
    service_date: serviceDate,
    place_code: PLACE_CODE,
    visit_type: VISIT_TYPE,
    details: JSON.stringify(details),
  };
  const form = multipart(fields, files);
  const response = http.post(`${BASE_URL}/api/uploads`, form.body, {
    headers: { ...headers, "Content-Type": form.contentType },
    tags: { name: "upload" },
    timeout: "120s",
  });
  check(response, {
    "notes uploaded": (reply) => reply.status === 200 && (reply.json("accepted") || []).length === files.length,
  });
}

function arrivals(scenario, perHour, maxVUs) {
  return {
    executor: "constant-arrival-rate",
    exec: scenario,
    rate: 1,
    timeUnit: `${Math.max(1, Math.round(MS_PER_HOUR / perHour))}ms`,
    duration: DURATION,
    preAllocatedVUs: 1,
    maxVUs,
  };
}

function authorised() {
  if (session === null) {
    session = signIn();
  } else if (Date.now() - session.at > SESSION_REFRESH_MS) {
    session = refreshed();
  }
  return { Authorization: `Bearer ${session.token}`, Accept: "application/json" };
}

function signIn() {
  const response = http.post(`${BASE_URL}/api/auth/login`, JSON.stringify({ email: EMAIL, password: PASSWORD }), {
    headers: JSON_HEADERS,
    tags: { name: "sign_in" },
  });
  const token = response.status === 200 ? response.json("access_token") : null;
  if (!check(response, { "signed in without two-step": () => Boolean(token) })) {
    exec.test.abort(`sign-in answered ${response.status}; use a test account without two-step verification`);
  }
  return { token, at: Date.now() };
}

function refreshed() {
  const response = http.post(`${BASE_URL}/api/auth/refresh`, null, {
    headers: { Accept: "application/json" },
    tags: { name: "refresh" },
    responseCallback: http.expectedStatuses(200, 401),
  });
  return response.status === 200 ? { token: response.json("access_token"), at: Date.now() } : signIn();
}

function syntheticNote(serviceDate, index) {
  const marker = `${exec.vu.idInTest}x${exec.scenario.iterationInTest}x${index}x${Date.now()}`;
  return {
    name: `${serviceDate} - LOADTEST SYNTHETIC - ${BILLED_CODE} - Progress ${marker}.pdf`,
    content: textPdf(`Synthetic load test note ${marker}. Follow-up visit, blood pressure stable. No patient data.`),
  };
}

function multipart(fields, files) {
  const boundary = `bodha-load-${exec.vu.idInTest}-${exec.scenario.iterationInTest}-${Date.now()}`;
  const values = Object.entries(fields).map(
    ([name, value]) => `--${boundary}\r\nContent-Disposition: form-data; name="${name}"\r\n\r\n${value}\r\n`,
  );
  const documents = files.map(
    (file) =>
      `--${boundary}\r\nContent-Disposition: form-data; name="files"; filename="${file.name}"\r\n` +
      `Content-Type: application/pdf\r\n\r\n${file.content}\r\n`,
  );
  return {
    body: `${[...values, ...documents].join("")}--${boundary}--\r\n`,
    contentType: `multipart/form-data; boundary=${boundary}`,
  };
}

function textPdf(text) {
  const stream = `BT /F1 10 Tf 40 760 Td (${text}) Tj ET`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let body = "%PDF-1.4\n";
  const offsets = [];
  objects.forEach((content, index) => {
    offsets.push(body.length);
    body += `${index + 1} 0 obj\n${content}\nendobj\n`;
  });
  const xref = body.length;
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  body += offsets.map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`).join("");
  return `${body}trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
}

function setting(name, fallback) {
  const value = __ENV[name];
  return value === undefined || value === "" ? fallback : value;
}

function positive(name, fallback) {
  const value = Number(setting(name, String(fallback)));
  if (!Number.isFinite(value) || value <= 0) throw new Error(`${name} must be a positive number`);
  return value;
}

function withoutTrailingSlash(url) {
  return url.endsWith("/") ? withoutTrailingSlash(url.slice(0, -1)) : url;
}

function hostOf(url) {
  const [, rest = ""] = url.split("://");
  return rest.split("/")[0].split(":")[0];
}
