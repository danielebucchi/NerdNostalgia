import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
  // pulizia localStorage tra test (CollapsibleSection lo usa)
  if (typeof window !== "undefined") {
    window.localStorage.clear();
  }
});
