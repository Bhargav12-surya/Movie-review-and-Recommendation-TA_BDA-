/**
 * CineScope · Service Layer
 * 
 * Unified API layer that abstracts the backend communication.
 * Transparently falls back to the browser-side demo engine
 * when no Python API is available.
 * 
 * Features:
 * - Auto-detect API mode vs demo mode
 * - Request retry with exponential backoff
 * - Structured error messages
 * - Request deduplication via AbortController
 */

import * as demo from './engine.js';

/* ── Exported State ── */

export let apiMode = false;
export let health = {};
export let catalog = [];
export let taxonomy = {};


/* ── API Client ── */

const MAX_RETRIES = 2;
const RETRY_DELAY = 800;

function createRequestId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  const bytes = globalThis.crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = [...bytes].map((value) => value.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

async function api(path, body, method, options = {}) {
  let lastError;
  const requestMethod = method || (body ? 'POST' : 'GET');
  const retries = options.retries ?? (requestMethod === 'GET' ? MAX_RETRIES : 0);

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const r = await fetch('/api' + path, {
        method: requestMethod,
        headers: {
          ...(body ? { 'Content-Type': 'application/json' } : {}),
          ...(options.headers || {}),
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: options.signal,
      });

      if (!r.ok) {
        let detail;
        try {
          detail = (await r.json()).detail;
        } catch { /* ignore */ }

        // Don't retry client errors (4xx)
        if (r.status >= 400 && r.status < 500) {
          const error = new Error(
            typeof detail === 'string'
              ? detail
              : `Request failed (${r.status}). Please check your input.`
          );
          error.status = r.status;
          throw error;
        }

        const error = new Error(
          typeof detail === 'string'
            ? detail
            : `Server error (${r.status}). Please try again.`
        );
        error.status = r.status;
        throw error;
      }

      return r.json();
    } catch (e) {
      lastError = e;

      if (e.name === 'AbortError') throw e;

      // Do not retry client errors. Mutating calls opt in only when they carry
      // an idempotency key, as review submission does below.
      if ((e.status >= 400 && e.status < 500) || attempt === retries) {
        throw e;
      }

      // Wait before retrying
      await new Promise((resolve) =>
        setTimeout(resolve, RETRY_DELAY * Math.pow(2, attempt))
      );
    }
  }

  throw lastError;
}


/* ── Initialization ── */

export async function init() {
  // Try to connect to the Python backend
  try {
    const r = await fetch('/api/health', {
      signal: AbortSignal.timeout(2500),
    });

    if (r.ok && r.headers.get('content-type')?.includes('application/json')) {
      health = await r.json();
      apiMode = health.status === 'ok';
    }
  } catch {
    // Backend not available, will use demo mode
  }

  if (apiMode) {
    // API mode: fetch from backend
    catalog = (await api('/movies?limit=500')).movies;

    try {
      taxonomy = await (await fetch('/taxonomy.json')).json();
    } catch {
      // Taxonomy not critical
    }
  } else {
    // Demo mode: use browser engine
    await demo.initEngine();
    catalog = demo.catalog;
      health = {
        demo_data: true,
        sentiment_model: 'lexicon-context-rules',
      };
    taxonomy = demo.tax;
  }

  return catalog;
}


/* ── User History ── */

export const getHistory = async () =>
  apiMode
    ? (await api('/users/local/history')).ratings
    : demo.history();

export const rate = async (id, rating) =>
  apiMode
    ? (await api('/users/local/ratings', { movie_id: id, rating }, 'PUT')).ratings
    : demo.rate(id, rating);

export const unrate = async (id) =>
  apiMode
    ? (await api(`/users/local/ratings/${id}`, null, 'DELETE')).ratings
    : demo.unrate(id);


/* ── Recommendations ── */

export const recommend = async (q = '', genres = [], themes = [], limit = 12) =>
  apiMode
    ? (
        await api(
          `/users/local/recommendations?q=${encodeURIComponent(q)}&genres=${encodeURIComponent(
            genres.join(',')
          )}&themes=${encodeURIComponent(themes.join(','))}&limit=${limit}`
        )
      ).movies
    : demo.recommend(q, genres, themes, limit);


/* ── Movie Details ── */

export const details = async (id) =>
  apiMode
    ? api(`/movies/${id}`)
    : {
        ...catalog.find((m) => m.movie_id === id),
        review_summary: demo.summary(id),
      };


/* ── Review Analysis ── */

let analysisController;

export function cancelAnalysis() {
  analysisController?.abort();
  analysisController = undefined;
}

export const analyze = async (text, id) => {
  if (!apiMode) return demo.analyze(text, id);
  cancelAnalysis();
  const controller = new AbortController();
  analysisController = controller;
  try {
    return await api(
      '/analyze',
      { text, movie_id: id },
      'POST',
      { signal: controller.signal, retries: 1 }
    );
  } finally {
    if (analysisController === controller) analysisController = undefined;
  }
};

export const saveReview = async (id, text) =>
  apiMode
    ? api(
        '/reviews',
        { movie_id: id, text, request_id: createRequestId() },
        'POST',
        { retries: 1 }
      )
    : demo.saveReview(id, text);


/* ── Chat ── */

export const chat = async (message, context) =>
  apiMode
    ? api('/users/local/chat', { message, context })
    : demo.chat(message, context);
