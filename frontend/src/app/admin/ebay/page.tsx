"use client";

import { useEffect, useRef, useState } from "react";
import { AdminShell } from "@/components/admin/AdminShell";
import { adminApi } from "@/lib/admin-api";

/* Collegamento eBay, dall'inizio alla fine.
 *
 * Le credenziali (App ID, Cert ID, RuName, refresh token) stanno nel vault
 * di garganacl e arrivano al backend come variabili d'ambiente: da qui non
 * si scrivono. La pagina fa le due cose scomode da fare a mano:
 *  - il consenso: eBay rimanda qui con ?code=..., che scade in 5 minuti e
 *    va scambiato subito per il refresh token da mettere nel vault;
 *  - le business policy: gli ID si leggono dall'account e si salvano nelle
 *    impostazioni con un clic, invece di copiarli da una risposta JSON. */

interface Status {
  env: "sandbox" | "production";
  marketplace_id: string;
  has_credentials: boolean;
  can_start_consent: boolean;
  configured: boolean;
}

interface SettingEntry {
  key: string;
  value: string;
}

interface Exchange {
  refresh_token: string | null;
  refresh_token_expires_in: number | null;
}

type Option = { id: string; name: string };

// Impostazione ← elenco dell'account eBay da cui sceglierla.
const POLICY_FIELDS: {
  key: string;
  label: string;
  pick: (p: Policies) => Option[];
}[] = [
  {
    key: "ebay_fulfillment_policy_id",
    label: "Spedizione",
    pick: (p) =>
      (p.fulfillment?.fulfillmentPolicies ?? []).map((x) => ({ id: x.fulfillmentPolicyId, name: x.name })),
  },
  {
    key: "ebay_payment_policy_id",
    label: "Pagamento",
    pick: (p) => (p.payment?.paymentPolicies ?? []).map((x) => ({ id: x.paymentPolicyId, name: x.name })),
  },
  {
    key: "ebay_return_policy_id",
    label: "Reso",
    pick: (p) => (p.return?.returnPolicies ?? []).map((x) => ({ id: x.returnPolicyId, name: x.name })),
  },
  {
    key: "ebay_merchant_location_key",
    label: "Magazzino (sede di spedizione)",
    pick: (p) =>
      (p.locations?.locations ?? []).map((x) => ({ id: x.merchantLocationKey, name: x.name || x.merchantLocationKey })),
  },
];

interface Policies {
  fulfillment?: { fulfillmentPolicies?: { fulfillmentPolicyId: string; name: string }[] };
  payment?: { paymentPolicies?: { paymentPolicyId: string; name: string }[] };
  return?: { returnPolicies?: { returnPolicyId: string; name: string }[] };
  locations?: { locations?: { merchantLocationKey: string; name?: string }[] };
}

function errorText(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export default function AdminEbayPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exchange, setExchange] = useState<Exchange | null>(null);
  const [exchanging, setExchanging] = useState(false);
  const [copied, setCopied] = useState(false);
  const [policies, setPolicies] = useState<Policies | null>(null);
  const [policiesError, setPoliciesError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  // React in sviluppo monta due volte: il code e' monouso, va scambiato una volta sola.
  const exchangeStarted = useRef(false);

  useEffect(() => {
    adminApi
      .get<Status>("/api/ebay/status")
      .then(setStatus)
      .catch((err) => setError(errorText(err)));

    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const denied = params.get("error");
    if (code || denied) {
      // Via dall'indirizzo: ricaricare la pagina riproverebbe un code gia' usato.
      window.history.replaceState(null, "", window.location.pathname);
    }
    if (denied) {
      setError(`eBay non ha dato il consenso (${params.get("error_description") || denied}).`);
    } else if (code && !exchangeStarted.current) {
      exchangeStarted.current = true;
      setExchanging(true);
      adminApi
        .post<Exchange>("/api/ebay/oauth-exchange", { code })
        .then(setExchange)
        .catch((err) => setError(`Scambio del codice fallito: ${errorText(err)}`))
        .finally(() => setExchanging(false));
    }
  }, []);

  useEffect(() => {
    if (!status?.configured) return;
    adminApi
      .get<Policies>("/api/ebay/policies")
      .then(setPolicies)
      .catch((err) => setPoliciesError(errorText(err)));
    adminApi.get<SettingEntry[]>("/api/settings/").then((entries) => {
      const current = Object.fromEntries(
        entries.filter((e) => POLICY_FIELDS.some((f) => f.key === e.key)).map((e) => [e.key, e.value]),
      );
      setSaved(current);
      setDraft(current);
    });
  }, [status?.configured]);

  async function connect() {
    setError(null);
    try {
      const { url } = await adminApi.get<{ url: string }>("/api/ebay/consent-url");
      window.location.href = url;
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function savePolicies() {
    setSaving(true);
    setError(null);
    try {
      const updated = await adminApi.put<SettingEntry[]>("/api/settings/", { values: draft });
      const current = Object.fromEntries(
        updated.filter((e) => e.key in draft).map((e) => [e.key, e.value]),
      );
      setSaved(current);
      setDraft(current);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setSaving(false);
    }
  }

  const dirty = POLICY_FIELDS.some((f) => (draft[f.key] ?? "") !== (saved[f.key] ?? ""));

  return (
    <AdminShell>
      <h1 className="display text-3xl text-ink mb-2">eBay</h1>
      <p className="text-ink-soft text-sm mb-6">
        Collegamento dell&apos;account per mettere in vendita le carte e leggere i prezzi di eBay.
      </p>

      {error && <p className="text-pink-deep font-semibold mb-4">⚠ {error}</p>}

      {exchanging && <div className="card p-5 mb-6">Collego l&apos;account eBay…</div>}

      {exchange?.refresh_token && (
        <div className="card p-5 mb-6 ring-2 ring-pink-deep">
          <h2 className="display text-lg text-ink mb-2">Account collegato: ultimo passo</h2>
          <p className="text-sm text-ink-soft mb-3">
            Questo è il refresh token: vale circa 18 mesi ed è una credenziale, trattalo come una
            password. Copialo nel vault di garganacl come <code>vault_ebay_refresh_token</code>, poi
            fai il deploy (<code>make apps</code>). Non viene salvato da nessuna parte: se chiudi la
            pagina prima di copiarlo, rifai il collegamento.
          </p>
          <textarea
            readOnly
            value={exchange.refresh_token}
            className="w-full font-mono text-xs p-3 rounded-xl ring-1 ring-ink/15 bg-white/80 h-28"
            onFocus={(e) => e.target.select()}
          />
          <button
            type="button"
            className="btn btn-primary text-sm mt-2"
            onClick={async () => {
              await navigator.clipboard.writeText(exchange.refresh_token ?? "");
              setCopied(true);
            }}
          >
            {copied ? "✓ Copiato" : "Copia"}
          </button>
        </div>
      )}

      {status && (
        <div className="card p-5 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <h2 className="display text-lg text-ink">Stato</h2>
            <span className={`chip ${status.env === "production" ? "chip-mint" : "chip-star"}`}>
              {status.env === "production" ? "Produzione" : "Sandbox (prove)"}
            </span>
            <span className="chip chip-sky">{status.marketplace_id}</span>
          </div>
          <ol className="space-y-3 text-sm">
            <Step done={status.has_credentials} title="Credenziali dell'app (App ID e Cert ID)">
              Nel vault: <code>vault_ebay_client_id</code> e <code>vault_ebay_client_secret</code>.
            </Step>
            <Step done={status.can_start_consent} title="RuName (indirizzo di ritorno del consenso)">
              Nel vault: <code>vault_ebay_redirect_runame</code>. Su eBay l&apos;&quot;auth accepted
              URL&quot; deve essere questa pagina.
            </Step>
            <Step done={status.configured} title="Account eBay collegato">
              {status.configured ? (
                "Refresh token presente."
              ) : (
                <button
                  type="button"
                  className="btn btn-primary text-sm mt-1"
                  onClick={connect}
                  disabled={!status.can_start_consent}
                >
                  Collega account eBay
                </button>
              )}
            </Step>
          </ol>
        </div>
      )}

      {status?.configured && (
        <div className="card p-5">
          <h2 className="display text-lg text-ink mb-1">Business policy</h2>
          <p className="text-sm text-ink-soft mb-4">
            Servono per pubblicare. Si creano su eBay (Account › Preferenze di vendita › Business
            policy); qui scegli quali usare.
          </p>
          {policiesError && <p className="text-pink-deep text-sm mb-3">⚠ {policiesError}</p>}
          {!policies && !policiesError && <p className="text-ink-soft text-sm">Leggo l&apos;account…</p>}
          {policies && (
            <div className="space-y-3">
              {POLICY_FIELDS.map((f) => {
                const options = f.pick(policies);
                return (
                  <label key={f.key} className="block">
                    <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">{f.label}</span>
                    {options.length === 0 ? (
                      <p className="text-sm text-pink-deep mt-1">Nessuna su eBay: va creata prima.</p>
                    ) : (
                      <select
                        className="input mt-1 block w-full rounded-xl ring-1 ring-ink/15 bg-white/80 px-3 py-2"
                        value={draft[f.key] ?? ""}
                        onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}
                      >
                        <option value="">— scegli —</option>
                        {options.map((o) => (
                          <option key={o.id} value={o.id}>
                            {o.name} ({o.id})
                          </option>
                        ))}
                      </select>
                    )}
                  </label>
                );
              })}
              <button
                type="button"
                className="btn btn-primary text-sm"
                onClick={savePolicies}
                disabled={!dirty || saving}
              >
                {saving ? "Salvo…" : "Salva"}
              </button>
            </div>
          )}
        </div>
      )}
    </AdminShell>
  );
}

function Step({ done, title, children }: { done: boolean; title: string; children: React.ReactNode }) {
  return (
    <li className="flex gap-3">
      <span className="text-lg leading-5" aria-hidden="true">
        {done ? "✅" : "⬜"}
      </span>
      <div>
        <p className="font-semibold text-ink">{title}</p>
        <div className="text-ink-soft">{children}</div>
      </div>
    </li>
  );
}
