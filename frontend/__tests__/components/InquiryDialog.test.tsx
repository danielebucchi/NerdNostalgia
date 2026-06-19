import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Mock del modulo api: lo dichiariamo PRIMA di importare il componente
vi.mock("@/lib/api", () => ({
  submitInquiry: vi.fn(async (payload: unknown) => ({ id: 1, ...(payload as object) })),
}));

import { InquiryDialog } from "@/components/InquiryDialog";
import { submitInquiry } from "@/lib/api";

describe("InquiryDialog", () => {
  beforeEach(() => {
    vi.mocked(submitInquiry).mockClear();
  });

  it("non renderizza se open=false", () => {
    const onClose = vi.fn();
    render(<InquiryDialog open={false} onClose={onClose} />);
    expect(screen.queryByText(/Contattami|Chiedi info/)).not.toBeInTheDocument();
  });

  it("renderizza titolo Contattami se senza articleTitle", () => {
    render(<InquiryDialog open={true} onClose={() => {}} />);
    expect(screen.getByText("Contattami")).toBeInTheDocument();
  });

  it("usa titolo 'Chiedi info' con articleTitle", () => {
    render(
      <InquiryDialog open={true} onClose={() => {}} articleId={5} articleTitle="N64" />,
    );
    expect(screen.getByText("Chiedi info")).toBeInTheDocument();
  });

  it("invia form con i campi compilati", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<InquiryDialog open={true} onClose={onClose} articleId={42} articleTitle="GBC" />);

    await user.type(screen.getByLabelText(/Nome/i), "Mario Rossi");
    await user.type(screen.getByLabelText(/^Email/i), "mario@example.com");
    await user.type(
      screen.getByLabelText(/Messaggio/i),
      "Vorrei sapere se l'articolo è disponibile",
    );
    await user.click(screen.getByRole("button", { name: /Invia richiesta/i }));

    await waitFor(() => {
      expect(submitInquiry).toHaveBeenCalledTimes(1);
    });

    const payload = vi.mocked(submitInquiry).mock.calls[0][0];
    expect(payload.name).toBe("Mario Rossi");
    expect(payload.email).toBe("mario@example.com");
    expect(payload.article_id).toBe(42);
    // Subject autogenerato dal titolo articolo
    expect(payload.subject).toContain("GBC");
    // Honeypot vuoto da utente vero
    expect(payload.website).toBeUndefined();
  });

  it("mostra schermata di successo dopo l'invio", async () => {
    const user = userEvent.setup();
    render(<InquiryDialog open={true} onClose={() => {}} />);

    await user.type(screen.getByLabelText(/Nome/i), "Anna");
    await user.type(screen.getByLabelText(/^Email/i), "anna@test.it");
    await user.type(screen.getByLabelText(/Messaggio/i), "ciao ciao test");
    await user.click(screen.getByRole("button", { name: /Invia richiesta/i }));

    await waitFor(() => {
      expect(screen.getByText(/Richiesta inviata!/i)).toBeInTheDocument();
    });
  });

  it("se submitInquiry rigetta, mostra l'errore", async () => {
    vi.mocked(submitInquiry).mockRejectedValueOnce(new Error("Rate limit exceeded"));
    const user = userEvent.setup();
    render(<InquiryDialog open={true} onClose={() => {}} />);

    await user.type(screen.getByLabelText(/Nome/i), "X");
    await user.type(screen.getByLabelText(/^Email/i), "x@x.it");
    await user.type(screen.getByLabelText(/Messaggio/i), "test errore display");
    await user.click(screen.getByRole("button", { name: /Invia richiesta/i }));

    await waitFor(() => {
      expect(screen.getByText(/Rate limit exceeded/)).toBeInTheDocument();
    });
  });

  it("invia il valore del honeypot se compilato (bot)", async () => {
    const user = userEvent.setup();
    render(<InquiryDialog open={true} onClose={() => {}} />);

    // Honeypot e' un input nascosto offscreen, raggiungibile via name e' meno facile,
    // ma `getByLabelText` con testo del label invisibile funziona perche' RTL legge
    // i label associati (anche se hidden via CSS).
    const honeypot = screen.getByLabelText(/Sito web/i);
    await user.type(honeypot, "https://spam.example");

    await user.type(screen.getByLabelText(/Nome/i), "Bot");
    await user.type(screen.getByLabelText(/^Email/i), "bot@b.it");
    await user.type(screen.getByLabelText(/Messaggio/i), "spam message bot test");
    await user.click(screen.getByRole("button", { name: /Invia richiesta/i }));

    await waitFor(() => {
      expect(submitInquiry).toHaveBeenCalledTimes(1);
    });
    const payload = vi.mocked(submitInquiry).mock.calls[0][0];
    expect(payload.website).toBe("https://spam.example");
  });
});
