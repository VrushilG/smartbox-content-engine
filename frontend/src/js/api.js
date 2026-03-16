/**
 * api.js — HTTP fetch wrapper and SSE EventSource client
 *
 * Responsibilities:
 * - postCSV(file): uploads a CSV file to POST /process and returns the SSE job stream URL
 * - connectSSE(onEvent, onError, onComplete): opens an EventSource on /process and
 *   routes parsed SSE events to callbacks
 *
 * Note: /process streams SSE directly from a single POST endpoint.
 * We use fetch with ReadableStream to consume the SSE response body.
 */

const API_BASE = "";

/**
 * Upload a CSV file and consume the SSE response stream.
 *
 * @param {File} file - The CSV file to upload
 * @param {{ userId?: string, onEvent: Function, onError: Function, onComplete: Function }} callbacks
 */
export async function postCSV(file, { userId, onEvent, onError, onComplete }) {
  const formData = new FormData();
  formData.append("file", file);

  const headers = {};
  if (userId) headers["X-User-Id"] = userId;

  let response;
  try {
    response = await fetch(`${API_BASE}/process`, {
      method: "POST",
      body: formData,
      headers,
    });
  } catch (err) {
    onError(`Network error: ${err.message}`);
    return;
  }

  if (!response.ok) {
    let detail = `Server error ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch (_) {
      // ignore parse error
    }
    onError(detail);
    return;
  }

  // Read the SSE stream line by line
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  let currentEvent = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop(); // keep incomplete last line

    for (const line of lines) {
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        const rawData = line.slice(5).trim();
        try {
          const data = JSON.parse(rawData);
          onEvent(currentEvent, data);
          if (currentEvent === "job_complete") {
            onComplete(data);
          }
        } catch (_) {
          // malformed data line — skip
        }
        currentEvent = null;
      }
    }
  }
}
