import { describe, it, expect } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CollapsibleSection } from "@/components/admin/CollapsibleSection";

describe("CollapsibleSection", () => {
  it("renderizza titolo e icona", () => {
    render(
      <CollapsibleSection storageKey="t1" title="Vendite esterne" icon="💰">
        <p>contenuto</p>
      </CollapsibleSection>,
    );
    expect(screen.getByText("Vendite esterne")).toBeInTheDocument();
    expect(screen.getByText("💰")).toBeInTheDocument();
  });

  it("default open mostra i children dopo l'idratazione", async () => {
    render(
      <CollapsibleSection storageKey="t2" title="X" defaultOpen>
        <p>contenuto X</p>
      </CollapsibleSection>,
    );
    // I children sono renderizzati solo dopo l'effect di hydration
    expect(await screen.findByText("contenuto X")).toBeInTheDocument();
  });

  it("click toggle chiude e riapre", async () => {
    const user = userEvent.setup();
    render(
      <CollapsibleSection storageKey="t3" title="Y" defaultOpen>
        <p>contenuto Y</p>
      </CollapsibleSection>,
    );
    expect(await screen.findByText("contenuto Y")).toBeInTheDocument();
    const btn = screen.getByRole("button");
    await user.click(btn);
    expect(screen.queryByText("contenuto Y")).not.toBeInTheDocument();
    await user.click(btn);
    expect(screen.getByText("contenuto Y")).toBeInTheDocument();
  });

  it("persiste stato in localStorage con chiave prefissata", async () => {
    const user = userEvent.setup();
    render(
      <CollapsibleSection storageKey="dashboard.spese" title="Spese" defaultOpen>
        <p>x</p>
      </CollapsibleSection>,
    );
    // Apertura iniziale → click chiude → storage="0"
    await screen.findByText("x");
    await user.click(screen.getByRole("button"));
    expect(window.localStorage.getItem("nn:dash:collapse:dashboard.spese")).toBe("0");
    await user.click(screen.getByRole("button"));
    expect(window.localStorage.getItem("nn:dash:collapse:dashboard.spese")).toBe("1");
  });

  it("rispetta stato persistito al mount (preferisce 0 anche se defaultOpen=true)", async () => {
    window.localStorage.setItem("nn:dash:collapse:dashboard.spese", "0");
    render(
      <CollapsibleSection storageKey="dashboard.spese" title="Spese" defaultOpen>
        <p>nascosto</p>
      </CollapsibleSection>,
    );
    // Dopo hydration deve risultare chiuso
    await act(async () => {});
    expect(screen.queryByText("nascosto")).not.toBeInTheDocument();
  });

  it("badge appare quando passato", () => {
    render(
      <CollapsibleSection storageKey="t6" title="Lotti" badge="3">
        <p>x</p>
      </CollapsibleSection>,
    );
    expect(screen.getByText("3")).toBeInTheDocument();
  });
});
