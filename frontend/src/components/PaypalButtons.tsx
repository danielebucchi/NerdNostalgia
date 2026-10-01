"use client";

import { useEffect, useRef, useState } from "react";
import {
  capturePaypalOrder,
  createPaypalOrder,
  getPaypalConfig,
  type PaypalConfig,
} from "@/lib/api";

interface Props {
  /** Crea il NOSTRO ordine (validando il form) e ne ritorna l'id.
   *  Deve lanciare se i dati non sono validi: il popup non si apre. */
  createOurOrder: () => Promise<number>;
  /** Pagamento incassato e ordine marcato PAGATO dal backend. */
  onPaid: (orderId: number) => void;
  onError: (message: string) => void;
  currency?: string;
  disabled?: boolean;
  /** Comunica al dialog se PayPal e' utilizzabile, per sapere se resta
   *  almeno un metodo di pagamento. */
  onAvailability?: (available: boolean) => void;
}

// Una sola <script> per pagina, anche con piu' istanze del componente.
let sdkPromise: Promise<void> | null = null;

function loadSdk(clientId: string, currency: string): Promise<void> {
  if (sdkPromise) return sdkPromise;
  sdkPromise = new Promise((resolve, reject) => {
    const src =
      `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(clientId)}` +
      `&currency=${encodeURIComponent(currency)}&locale=it_IT&components=buttons` +
      `&intent=capture&disable-funding=credit`;
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      sdkPromise = null; // permetti un nuovo tentativo
      reject(new Error("SDK PayPal non caricato"));
    };
    document.head.appendChild(script);
  });
  return sdkPromise;
}

/**
 * Bottoni PayPal ufficiali: il pagamento si apre nella finestra PayPal e
 * torna indietro confermato, invece del vecchio link paypal.me che ci
 * lasciava all'oscuro di tutto.
 *
 * Importo e articoli li costruisce il backend a partire dall'ordine: qui non
 * passa nessuna cifra, altrimenti basterebbe la console del browser per
 * decidere quanto pagare.
 */
export function PaypalButtons({
  createOurOrder,
  onPaid,
  onError,
  currency = "EUR",
  disabled,
  onAvailability,
}: Props) {
  const [config, setConfig] = useState<PaypalConfig | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const holder = useRef<HTMLDivElement>(null);
  // L'id del nostro ordine nasce in createOrder e serve in onApprove.
  const ourOrderId = useRef<number | null>(null);
  // I callback cambiano a ogni render; i bottoni PayPal si montano una volta
  // sola, quindi legge sempre l'ultima versione da qui.
  const handlers = useRef({ createOurOrder, onPaid, onError, disabled });
  handlers.current = { createOurOrder, onPaid, onError, disabled };
  const availabilityRef = useRef(onAvailability);
  availabilityRef.current = onAvailability;

  useEffect(() => {
    let cancelled = false;
    getPaypalConfig().then((c) => {
      if (cancelled) return;
      setConfig(c);
      if (!c?.configured) availabilityRef.current?.(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!config?.configured || !holder.current) return;
    let cancelled = false;

    loadSdk(config.client_id, currency)
      .then(() => {
        if (cancelled || !holder.current) return;
        const paypal = (window as unknown as { paypal?: Record<string, never> })
          .paypal as unknown as {
          Buttons: (opts: Record<string, unknown>) => {
            render: (el: HTMLElement) => Promise<void>;
          };
        };
        if (!paypal?.Buttons) {
          setFailed(true);
          availabilityRef.current?.(false);
          return;
        }

        paypal
          .Buttons({
            style: { layout: "vertical", shape: "pill", label: "paypal", height: 48 },
            onClick: (_data: unknown, actions: { resolve: () => void; reject: () => void }) =>
              handlers.current.disabled ? actions.reject() : actions.resolve(),
            createOrder: async () => {
              const id = await handlers.current.createOurOrder();
              ourOrderId.current = id;
              return createPaypalOrder(id);
            },
            onApprove: async () => {
              const id = ourOrderId.current;
              if (id == null) throw new Error("Ordine mancante");
              await capturePaypalOrder(id);
              handlers.current.onPaid(id);
            },
            onError: (err: unknown) => {
              handlers.current.onError(
                err instanceof Error ? err.message : "Pagamento PayPal non riuscito",
              );
            },
            onCancel: () => {
              // Annullare non e' un errore: l'ordine resta PENDING e il
              // carrello resta pieno, cosi' puo' riprovare.
              handlers.current.onError(
                "Pagamento annullato. Il carrello è ancora pieno, puoi riprovare.",
              );
            },
          })
          .render(holder.current)
          .then(() => {
            if (cancelled) return;
            setReady(true);
            availabilityRef.current?.(true);
          })
          .catch(() => {
            if (cancelled) return;
            setFailed(true);
            availabilityRef.current?.(false);
          });
      })
      .catch(() => {
        if (cancelled) return;
        setFailed(true);
        availabilityRef.current?.(false);
      });

    return () => {
      cancelled = true;
    };
  }, [config, currency]);

  if (config && !config.configured) return null;
  if (failed) {
    return (
      <p className="text-sm text-pink-deep text-center">
        ⚠ Non riesco a caricare PayPal. Riprova fra poco o scrivimi.
      </p>
    );
  }

  return (
    <div>
      <div ref={holder} />
      {!ready && (
        <p className="text-xs text-ink-soft text-center py-2">
          Carico PayPal…
        </p>
      )}
      {config?.sandbox && ready && (
        <p className="text-[11px] text-ink-soft text-center">
          PayPal in modalità test (sandbox)
        </p>
      )}
    </div>
  );
}
