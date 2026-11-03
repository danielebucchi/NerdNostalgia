import { describe, it, expect, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

import { AdminArticleEditor } from "@/components/AdminArticleEditor";
import { clearToken, setStoredUser, setToken, type AdminUser } from "@/lib/auth-store";

const admin = { id: 1, username: "admin", email: "a@x", full_name: null, role: "ADMIN" } as AdminUser;

describe("AdminArticleEditor", () => {
  it("non si vede senza sessione admin", () => {
    render(<AdminArticleEditor articleId={7} />);
    expect(screen.queryByText(/Modifica articolo/)).not.toBeInTheDocument();
  });

  it("non si vede a un cliente normale", () => {
    window.localStorage.setItem("nn_admin_token", "t");
    window.localStorage.setItem("nn_admin_user", JSON.stringify({ ...admin, role: "USER" }));
    render(<AdminArticleEditor articleId={7} />);
    expect(screen.queryByText(/Modifica articolo/)).not.toBeInTheDocument();
  });

  it("compare all'admin e sparisce quando esce", async () => {
    setToken("t");
    setStoredUser(admin);
    render(<AdminArticleEditor articleId={7} />);
    expect(await screen.findByText(/Modifica articolo/)).toBeInTheDocument();
    act(() => clearToken());
    expect(screen.queryByText(/Modifica articolo/)).not.toBeInTheDocument();
  });
});
