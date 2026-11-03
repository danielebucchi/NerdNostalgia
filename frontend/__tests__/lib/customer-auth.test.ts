import { describe, it, expect, vi, afterEach } from "vitest";

import { clearCustomerSession, loginCustomer } from "@/lib/customer-auth";
import { getStoredUser, getToken } from "@/lib/auth-store";

function mockLogin(role: string) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) =>
      new Response(
        JSON.stringify(
          url.endsWith("/api/auth/login")
            ? { access_token: "tok", token_type: "bearer" }
            : { id: 1, username: "u", email: "u@x", full_name: null, role },
        ),
        { status: 200 },
      ),
    ),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("loginCustomer", () => {
  it("l'admin che entra da /accedi apre anche la sessione admin", async () => {
    mockLogin("ADMIN");
    await loginCustomer("admin", "pw");
    expect(getToken()).toBe("tok");
    expect(getStoredUser()?.role).toBe("ADMIN");
  });

  it("un cliente normale no", async () => {
    mockLogin("USER");
    await loginCustomer("c@x.it", "pw");
    expect(getToken()).toBeNull();
  });

  it("uscire come admin chiude anche la sessione admin", async () => {
    mockLogin("ADMIN");
    await loginCustomer("admin", "pw");
    clearCustomerSession();
    expect(getToken()).toBeNull();
  });
});
