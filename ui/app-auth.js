/**
 * VarantRadar Pro - Verdent-Managed Supabase Auth entegrasyonu.
 * @verdent/auth-js builtin auth UI (Google + e-posta/parola + sifre kurtarma)
 * ve supabase-js session yonetimini kullanir; token'lar uygulama tarafinda
 * saklanmaz, supabase-js kendi persistent session'ini yonetir.
 *
 * Kullanim: window.VerdentAuthKit (Promise) -> { supabase, auth, session }
 */
window.__vrAuthBooted = true;

import { createVerdentAuth } from './vendor/verdent-auth/index.js';

function showAuthError(msg) {
    const box = document.getElementById('auth-error-box');
    if (box) {
        box.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> ' + msg;
        box.style.display = 'block';
    }
}

/** Gizli/ozel pencerede localStorage engellenirse bellek-ici depoya duser. */
function safeLocalStorage() {
    try {
        const t = '__vr_storage_test__';
        window.localStorage.setItem(t, '1');
        window.localStorage.removeItem(t);
        return window.localStorage;
    } catch (e) {
        const mem = {};
        return {
            getItem: (k) => (k in mem ? mem[k] : null),
            setItem: (k, v) => { mem[k] = String(v); },
            removeItem: (k) => { delete mem[k]; },
        };
    }
}

/**
 * AKTIF PROJE DIŞI oturum verilerini temizler.
 * Auth projesi değişince tarayıcıda eski projenin token'ları kalır; widget
 * bunları yeni projenin GoTrue'suna gönderir -> "invalid JWT: signature is
 * invalid" hatası. Aktif proje referansı uyuşmayan her auth depo kaydı silinir.
 */
function purgeForeignAuthStorage(activeRef) {
    try {
        const ls = safeLocalStorage();
        if (typeof ls.length !== 'number') return; // bellek-içi depo: gerek yok
        const doomed = [];
        for (let i = 0; i < ls.length; i++) {
            const k = ls.key(i);
            if (!k) continue;
            const kl = k.toLowerCase();
            if (kl.includes('-auth-token') || kl.includes('auth.token') || kl.includes('verdent-auth')) {
                if (!k.includes(activeRef)) doomed.push(k);
            }
        }
        doomed.forEach((k) => {
            try { ls.removeItem(k); } catch (e) { /* yoksay */ }
        });
        if (doomed.length) console.info('[Auth] Eski proje oturum verisi temizlendi:', doomed.length, 'kayıt');
    } catch (e) { /* yoksay */ }
}

async function loadAuthConfig() {
    const res = await fetch('/api/auth_config');
    if (!res.ok) throw new Error('auth_config yüklenemedi: ' + res.status);
    return await res.json();
}

const kitPromise = (async () => {
    const cfg = await loadAuthConfig();
    // Aktif proje referansini URL'nin son parcasindan al (…/p/pf565…)
    let activeRef = '';
    try { activeRef = (cfg.supabase_url || '').split('/').filter(Boolean).pop() || ''; } catch (e) {}
    purgeForeignAuthStorage(activeRef);
    const supabase = window.supabase.createClient(cfg.supabase_url, cfg.publishable_key, {
        auth: {
            persistSession: true,
            autoRefreshToken: true,
            detectSessionInUrl: true,
            storage: safeLocalStorage(),
        },
    });
    const auth = createVerdentAuth({
        supabase,
        oauth: {
            // Google OAuth web-message akisini Verdent yonetir; dogrudan
            // GoTrue authorize ucu popup'a beklenen token mesajini gondermez.
            authorizeUrl: cfg.oauth_initiate_url || 'https://cloud-oauth.verdent.ai/app/initiate'
        }
    });
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
        if (!res.ok) {
            // Sunucu token'i dogrulayamadiysa istemcideki oturum bozuktur:
            // temizle ki widget her acilista ayni hatayi tekrarlamasin.
            try { await supabase.auth.signOut(); } catch (e) { /* yoksay */ }
            return false;
        }
        return true;
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

/**
 * Giris butonlarini KIT HAZIR OLMADAN hemen baglar:
 * mobilde yavas baglanti/ozel pencere durumunda butonlar oluk Olmaz;
 * tiklamada "Yukleniyor" gosterilir, hata olursa sayfada gorunur mesaj cikar.
 */
function bindAuthButtons() {
    const bind = (id, opts) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.addEventListener('click', async () => {
            const original = el.innerHTML;
            try {
                el.disabled = true;
                el.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Yükleniyor...';
                await openAuthModal(opts);
            } catch (e) {
                console.error('[Auth] Modal acilamadi', e);
                showAuthError('Giriş ekranı açılamadı. İnternet bağlantınızı kontrol edip sayfayı yenileyin. ' +
                    '(Hata: ' + (e && e.message ? e.message : 'bilinmiyor') + ')');
            } finally {
                el.disabled = false;
                el.innerHTML = original;
            }
        });
    };
    bind('btn-open-signin', {});
    bind('btn-open-signup', { initialView: 'signUp' });
    bind('btn-open-forgot', { initialView: 'forgotPassword' });
}

function wireLoginPage(supabase, auth, session) {
    if (session) {
        // Zaten oturum var -> cookie oturumunu tazele, sonra ana uygulamaya gec.
        // (Tarayici kapaninca Flask cookie'si silinir ama Supabase session
        // localStorage'da yasar; once sync etmezsek / <-> /login dongusune girer.)
        syncServerSession(supabase).then(() => window.location.replace('/'));
        return;
    }
}

function wireMainApp(supabase, auth, session) {
    // Chip adi: Supabase oturumunda e-posta, klasik giriste /api/me
    const emailEl = document.getElementById('user-chip-email');
    if (session?.user?.email && emailEl) {
        emailEl.textContent = session.user.email;
    } else if (emailEl) {
        fetch('/api/me').then(r => r.json()).then(d => {
            if (d.status === 'success' && d.name) emailEl.textContent = d.name;
        }).catch(() => {});
    }
    const chip = document.getElementById('user-chip');
    if (chip) chip.style.display = 'flex';
    const btn = document.getElementById('btn-signout');
    if (btn) {
        btn.addEventListener('click', async () => {
            try { await supabase.auth.signOut(); } catch (e) { /* yoksay */ }
            window.location.href = '/logout';
        });
    }
}

// Butonlari modul yuklenir yuklenmez bagla (login sayfasinda)
if (document.getElementById('auth-login-card')) {
    bindAuthButtons();
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
    if (document.getElementById('auth-login-card')) {
        showAuthError('Oturum sistemi başlatılamadı: ' + (e && e.message ? e.message : e) +
            '<br>Sayfayı yenileyip tekrar deneyin.');
    }
});
