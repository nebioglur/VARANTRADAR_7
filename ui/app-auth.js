/**
 * VarantRadar Pro - Verdent-Managed Supabase Auth entegrasyonu.
 * @verdent/auth-js builtin auth UI (Google + e-posta/parola + sifre kurtarma)
 * ve supabase-js session yonetimini kullanir; token'lar uygulama tarafinda
 * saklanmaz, supabase-js kendi persistent session'ini yonetir.
 *
 * Kullanim: window.VerdentAuthKit (Promise) -> { supabase, auth, session }
 */
import { createVerdentAuth } from './vendor/verdent-auth/index.js';

async function loadAuthConfig() {
    const res = await fetch('/api/auth_config');
    if (!res.ok) throw new Error('auth_config yüklenemedi: ' + res.status);
    return await res.json();
}

const kitPromise = (async () => {
    const cfg = await loadAuthConfig();
    const supabase = window.supabase.createClient(cfg.supabase_url, cfg.publishable_key, {
        auth: {
            persistSession: true,
            autoRefreshToken: true,
            detectSessionInUrl: true,
        },
    });
    const auth = createVerdentAuth({ supabase });
    return { supabase, auth, config: cfg };
})();

window.VerdentAuthKit = kitPromise;

/** Cookie oturumunu Supabase access token ile senkronize eder. */
async function syncServerSession(supabase) {
    try {
        const { data } = await supabase.auth.getSession();
        const token = data?.session?.access_token;
        if (!token) return false;
        const res = await fetch('/api/auth/session', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token },
        });
        return res.ok;
    } catch (e) {
        console.warn('[Auth] Session sync hatasi', e);
        return false;
    }
}

/** Modal acar; basarili giriste Flask cookie oturumunu kurup ana sayfaya doner. */
async function openAuthModal(extraOptions) {
    const { supabase, auth } = await kitPromise;
    auth.openSignInModal(Object.assign({
        redirectTo: window.location.origin + '/',
        locale: 'tr',
        onSuccess: async () => {
            await syncServerSession(supabase);
            window.location.replace('/');
        },
    }, extraOptions || {}));
}

function wireLoginPage(supabase, auth, session) {
    if (session) {
        // Zaten oturum var -> cookie oturumunu tazele, sonra ana uygulamaya gec.
        // (Tarayici kapaninca Flask cookie'si silinir ama Supabase session
        // localStorage'da yasar; once sync etmezsek / <-> /login dongusune girer.)
        syncServerSession(supabase).then(() => window.location.replace('/'));
        return;
    }
    const bind = (id, opts) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('click', () => openAuthModal(opts));
    };
    bind('btn-open-signin', {});
    bind('btn-open-signup', { initialView: 'signUp' });
    bind('btn-open-forgot', { initialView: 'forgotPassword' });
}

function wireMainApp(supabase, auth, session) {
    if (session?.user) {
        const emailEl = document.getElementById('user-chip-email');
        if (emailEl) emailEl.textContent = session.user.email || 'Hesap';
        const chip = document.getElementById('user-chip');
        if (chip) chip.style.display = 'flex';
    }
    const btn = document.getElementById('btn-signout');
    if (btn) {
        btn.addEventListener('click', async () => {
            try { await supabase.auth.signOut(); } catch (e) { /* yoksay */ }
            window.location.href = '/logout';
        });
    }
}

kitPromise.then(async ({ supabase, auth }) => {
    const isLoginPage = !!document.getElementById('auth-login-card');
    const { data } = await supabase.auth.getSession();
    const session = data?.session || null;

    if (isLoginPage) {
        wireLoginPage(supabase, auth, session);
    } else {
        wireMainApp(supabase, auth, session);
    }

    supabase.auth.onAuthStateChange((event) => {
        if (event === 'SIGNED_OUT' && !isLoginPage) {
            window.location.href = '/logout';
        }
    });
}).catch((e) => {
    console.error('[Auth] Baslatma hatasi', e);
});
