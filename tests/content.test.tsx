// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

const backend = vi.hoisted(() => ({
  get_clips: vi.fn(),
  get_endpoints: vi.fn(),
  pair: vi.fn(),
  remove_endpoint: vi.fn(),
  start_export: vi.fn(),
  get_job: vi.fn(),
}));

vi.mock("@decky/api", () => ({
  callable: (route: keyof typeof backend) => backend[route],
  definePlugin: (factory: unknown) => factory,
}));

vi.mock("@decky/ui", () => ({
  ButtonItem: ({ children, onClick, disabled, description }: any) =>
    <button onClick={onClick} disabled={disabled}>{children}{description && <small>{description}</small>}</button>,
  PanelSection: ({ title, children }: any) => <section><h2>{title}</h2>{children}</section>,
  PanelSectionRow: ({ children }: any) => <div>{children}</div>,
  TextField: ({ label, value, onChange }: any) =>
    <label>{label}<input value={value} onChange={onChange} /></label>,
  staticClasses: { Title: "title" },
}));

import { Content } from "../src/Content";

const clip = {
  id: "clip-1", app_id: 250900, game: "Example Game", name: "",
  date: "2026-10-06 15:11", duration_seconds: 192,
};
const endpoint = { id: "pc-1", name: "My PC", url: "http://192.168.1.20:57321" };

beforeEach(() => {
  vi.resetAllMocks();
  backend.get_clips.mockResolvedValue([clip]);
  backend.get_endpoints.mockResolvedValue([]);
  backend.start_export.mockResolvedValue("job-1");
  backend.get_job.mockResolvedValue({ state: "done", message: "Saved" });
});
afterEach(cleanup);

describe("Clip Export menu", () => {
  it("shows game and date, then saves the selected clip locally", async () => {
    render(<Content />);
    await screen.findByText(/Example Game/);
    expect(screen.getByText(/2026-10-06 15:11/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Save MP4 on Deck/ }));
    await waitFor(() => expect(backend.start_export).toHaveBeenCalledWith("clip-1", "local"));
  });

  it("pairs a computer and sends the selected clip there", async () => {
    backend.get_endpoints.mockResolvedValueOnce([]).mockResolvedValueOnce([endpoint]);
    backend.pair.mockResolvedValue(endpoint);
    render(<Content />);
    await screen.findByText(/Example Game/);
    fireEvent.change(screen.getByLabelText("Receiver URL"), { target: { value: endpoint.url } });
    fireEvent.change(screen.getByLabelText("Six-digit code"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Pair computer" }));
    await waitFor(() => expect(backend.pair).toHaveBeenCalledWith(endpoint.url, "123456"));
    fireEvent.click(await screen.findByRole("button", { name: "Send to My PC" }));
    await waitFor(() => expect(backend.start_export).toHaveBeenCalledWith("clip-1", "pc-1"));
  });
});
