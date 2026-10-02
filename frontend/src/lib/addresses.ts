"use client";

import { customerFetch } from "@/lib/customer-auth";

/* Rubrica indirizzi del cliente.
 *
 * Esiste per una ragione sola: chi compra una seconda volta non deve
 * riscrivere via, CAP, città e telefono da capo. */

export interface Address {
  id: number;
  label: string | null;
  full_name: string;
  phone: string | null;
  street: string;
  city: string;
  postal_code: string;
  province: string | null;
  country: string;
  is_default: boolean;
}

export interface AddressInput {
  label?: string | null;
  full_name: string;
  phone?: string | null;
  street: string;
  city: string;
  postal_code: string;
  province?: string | null;
  country: string;
  is_default?: boolean;
}

export function listAddresses(): Promise<Address[]> {
  return customerFetch<Address[]>("/api/addresses");
}

export function createAddress(input: AddressInput): Promise<Address> {
  return customerFetch<Address>("/api/addresses", {
    method: "POST",
    body: input,
  });
}

export function updateAddress(
  id: number,
  input: AddressInput,
): Promise<Address> {
  return customerFetch<Address>(`/api/addresses/${id}`, {
    method: "PUT",
    body: input,
  });
}

export function makeDefault(id: number): Promise<Address> {
  return customerFetch<Address>(`/api/addresses/${id}/default`, {
    method: "POST",
  });
}

export function deleteAddress(id: number): Promise<void> {
  return customerFetch<void>(`/api/addresses/${id}`, { method: "DELETE" });
}

/** Riga leggibile per gli elenchi: "Via Roma 12 — 56021 Cascina (PI)". */
export function formatAddress(a: Address): string {
  const dopo = [a.postal_code, a.city].filter(Boolean).join(" ");
  const prov = a.province ? ` (${a.province})` : "";
  return `${a.street} — ${dopo}${prov}`;
}

/** Due indirizzi sono "lo stesso" se coincidono via, CAP e città. Serve a
 *  non riproporre di salvare qualcosa che in rubrica c'è già. */
export function sameAddress(a: Address, b: AddressInput): boolean {
  const n = (v: string | null | undefined) =>
    (v ?? "").trim().toLowerCase().replace(/\s+/g, " ");
  return (
    n(a.street) === n(b.street) &&
    n(a.postal_code) === n(b.postal_code) &&
    n(a.city) === n(b.city)
  );
}
