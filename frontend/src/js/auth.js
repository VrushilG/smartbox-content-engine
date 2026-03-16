/**
 * auth.js — Supabase authentication module
 *
 * Supports Google OAuth SSO and email/password auth via Supabase Auth.
 * Lazily initialised once the backend /config endpoint returns
 * valid Supabase credentials.  If no credentials are returned
 * the module is a no-op and the app runs unauthenticated.
 */

// Supabase JS v2 loaded as an ES module from the CDN.
// createClient will be undefined when Supabase is not configured — handled gracefully.
let createClient;

async function _loadSdk() {
  if (createClient) return;
  try {
    const mod = await import(
      "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm"
    );
    createClient = mod.createClient;
  } catch (err) {
    console.warn("auth: failed to load Supabase SDK", err);
  }
}

let _supabase = null;
let _user = null;
let _authChangeCallback = null;

/**
 * Initialise the auth module with the public Supabase config.
 * Returns the currently signed-in user, or null.
 *
 * @param {{ supabase_url: string, supabase_anon_key: string }} config
 * @returns {Promise<object|null>}
 */
export async function initAuth(config) {
  if (!config?.supabase_url || !config?.supabase_anon_key) return null;

  await _loadSdk();
  if (!createClient) return null;

  _supabase = createClient(config.supabase_url, config.supabase_anon_key);

  // Restore session from URL hash (after Google OAuth redirect)
  const { data: { session } } = await _supabase.auth.getSession();
  _user = session?.user ?? null;

  // Subscribe to future auth changes (sign in, sign out, token refresh)
  _supabase.auth.onAuthStateChange((_event, newSession) => {
    _user = newSession?.user ?? null;
    if (_authChangeCallback) _authChangeCallback(_user);
  });

  return _user;
}

/**
 * Register a callback invoked whenever the auth state changes.
 * @param {(user: object|null) => void} callback
 */
export function onAuthStateChange(callback) {
  _authChangeCallback = callback;
}

/**
 * Trigger the Google OAuth redirect flow.
 */
export async function signInWithGoogle() {
  if (!_supabase) return;
  await _supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: window.location.origin + "/",
    },
  });
}

/**
 * Sign the current user out and clear the local session.
 */
export async function signOut() {
  if (!_supabase) return;
  await _supabase.auth.signOut();
}

/** Return the currently signed-in user object (or null). */
export function getUser() {
  return _user;
}

/**
 * Sign in with email and password.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{ error: string|null }>}
 */
export async function signInWithEmail(email, password) {
  if (!_supabase) return { error: "Auth not configured." };
  const { error } = await _supabase.auth.signInWithPassword({ email, password });
  return { error: error?.message ?? null };
}

/**
 * Create a new account with email and password.
 * @param {string} email
 * @param {string} password
 * @returns {Promise<{ error: string|null }>}
 */
export async function signUpWithEmail(email, password) {
  if (!_supabase) return { error: "Auth not configured." };
  const { error } = await _supabase.auth.signUp({ email, password });
  return { error: error?.message ?? null };
}

/**
 * Send a password reset email.
 * @param {string} email
 * @returns {Promise<{ error: string|null }>}
 */
export async function resetPasswordForEmail(email) {
  if (!_supabase) return { error: "Auth not configured." };
  const { error } = await _supabase.auth.resetPasswordForEmail(email, {
    redirectTo: window.location.origin + "/",
  });
  return { error: error?.message ?? null };
}
