import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { forgetRemote } from "@/hooks/remoteCache";
import {
  createEhrKey,
  getEhrConnection,
  getEhrDocuments,
  getEhrPullRuns,
  pauseEhrPulls,
  resumeEhrPulls,
  saveEhrConnection,
  testEhrConnection,
} from "@/lib/api/ehrConnection";
import { EHR_CONNECTION_KEY, EhrConnectionPanel } from "../EhrConnectionPanel";
import { EHR_DOCUMENTS_KEY, EHR_RUNS_KEY } from "../EhrPullResults";
import { DEFAULT_SCOPES, DOCUMENTS, JWKS_URL, NO_DOCUMENTS, NO_RUNS, OFF, PULLING, RUNS, WITH_KEY } from "./ehrFixtures";

vi.mock("@/lib/api/ehrConnection", () => ({
  getEhrConnection: vi.fn(),
  saveEhrConnection: vi.fn(),
  createEhrKey: vi.fn(),
  pauseEhrPulls: vi.fn(),
  resumeEhrPulls: vi.fn(),
  testEhrConnection: vi.fn(),
  getEhrPullRuns: vi.fn(),
  getEhrDocuments: vi.fn(),
}));

function forget(): void {
  forgetRemote(EHR_CONNECTION_KEY);
  for (const version of [0, 1, 2]) {
    forgetRemote(`${EHR_RUNS_KEY}:${version}`);
    forgetRemote(`${EHR_DOCUMENTS_KEY}:${version}:0`);
  }
}

describe("EhrConnectionPanel", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    forget();
    vi.mocked(getEhrConnection).mockResolvedValue(PULLING);
    vi.mocked(getEhrPullRuns).mockResolvedValue(NO_RUNS);
    vi.mocked(getEhrDocuments).mockResolvedValue(NO_DOCUMENTS);
  });

  it("shows nothing to set up while Bodha cannot hold EHR keys", async () => {
    vi.mocked(getEhrConnection).mockResolvedValue({ ...OFF, available: false, status: "unavailable" });
    render(<EhrConnectionPanel />);
    expect(await screen.findByText("Not available")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create key" })).not.toBeInTheDocument();
  });

  it("creates a key and offers its JWKS URL to copy", async () => {
    vi.mocked(getEhrConnection).mockResolvedValue(OFF);
    vi.mocked(createEhrKey).mockResolvedValue(WITH_KEY);
    const events = userEvent.setup();
    render(<EhrConnectionPanel />);
    await events.click(await screen.findByRole("button", { name: "Create key" }));
    expect(createEhrKey).toHaveBeenCalledWith("RS384");
    expect(await screen.findByRole("status", { name: "JWKS URL" })).toHaveTextContent(JWKS_URL);
    await events.click(screen.getByRole("button", { name: "Copy JWKS URL" }));
    expect(await navigator.clipboard.readText()).toBe(JWKS_URL);
    expect(screen.getByText("private_key_jwt")).toBeInTheDocument();
  });

  it("replaces the key only after confirming", async () => {
    vi.mocked(createEhrKey).mockResolvedValue(PULLING);
    const events = userEvent.setup();
    render(<EhrConnectionPanel />);
    await events.click(await screen.findByRole("button", { name: "New key" }));
    expect(createEhrKey).not.toHaveBeenCalled();
    await events.click(within(screen.getByRole("dialog", { name: "Replace this key?" })).getByRole("button", { name: "Replace" }));
    expect(createEhrKey).toHaveBeenCalledTimes(1);
  });

  it("saves the base URL, client ID, scopes, note types and start date", async () => {
    vi.mocked(getEhrConnection).mockResolvedValue(WITH_KEY);
    vi.mocked(saveEhrConnection).mockResolvedValue(PULLING);
    const events = userEvent.setup();
    render(<EhrConnectionPanel />);
    await events.type(await screen.findByLabelText("FHIR base URL"), "https://ehr.example.com/fhir/r4");
    await events.type(screen.getByLabelText("Client ID"), "bodha-lakeside");
    await events.click(screen.getByRole("switch", { name: "Nursing facility notes" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Start date" }), { target: { value: "1 Nov 2026" } });
    await events.click(screen.getByRole("button", { name: "Save" }));
    expect(saveEhrConnection).toHaveBeenCalledWith({
      base_url: "https://ehr.example.com/fhir/r4",
      client_id: "bodha-lakeside",
      scopes: DEFAULT_SCOPES,
      note_types: ["progress", "nursing_facility"],
      start_date: "2026-11-01",
    });
    expect(await screen.findByText("Saved")).toBeInTheDocument();
    expect(screen.getByText("https://auth.example.com/oauth2/token")).toBeInTheDocument();
  });

  it("does not send settings with a missing field", async () => {
    vi.mocked(getEhrConnection).mockResolvedValue(WITH_KEY);
    const events = userEvent.setup();
    render(<EhrConnectionPanel />);
    await events.type(await screen.findByLabelText("FHIR base URL"), "http://ehr.example.com");
    await events.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByText("Enter an https address")).toBeInTheDocument();
    expect(screen.getByText("Enter the client ID")).toBeInTheDocument();
    expect(saveEhrConnection).not.toHaveBeenCalled();
  });

  it("tests the connection and shows each step", async () => {
    vi.mocked(testEhrConnection).mockResolvedValue({
      passed: false,
      tested_at: "2026-11-27T16:00:00Z",
      steps: [
        { step: "configuration", passed: true, detail: "token endpoint https://auth.example.com/oauth2/token" },
        { step: "token", passed: false, detail: "the token endpoint answered 401 invalid_client" },
      ],
    });
    const events = userEvent.setup();
    render(<EhrConnectionPanel />);
    await events.click(await screen.findByRole("button", { name: "Test connection" }));
    const steps = await screen.findByRole("list", { name: "Test connection" });
    expect(within(steps).getByText("SMART configuration")).toBeInTheDocument();
    expect(within(steps).getByText("the token endpoint answered 401 invalid_client")).toBeInTheDocument();
  });

  it("pauses and resumes pulling", async () => {
    vi.mocked(pauseEhrPulls).mockResolvedValue({ ...PULLING, status: "paused", connection: { ...PULLING.connection!, paused: true } });
    vi.mocked(resumeEhrPulls).mockResolvedValue(PULLING);
    const events = userEvent.setup();
    render(<EhrConnectionPanel />);
    await events.click(await screen.findByRole("button", { name: "Pause" }));
    expect(await screen.findByText("Paused")).toBeInTheDocument();
    await events.click(screen.getByRole("button", { name: "Resume" }));
    expect(await screen.findByText("Pulling notes")).toBeInTheDocument();
  });

  it("lists recent pulls and every document with its outcome", async () => {
    vi.mocked(getEhrPullRuns).mockResolvedValue(RUNS);
    vi.mocked(getEhrDocuments).mockResolvedValue(DOCUMENTS);
    render(<EhrConnectionPanel />);
    const pulls = await screen.findByRole("list", { name: "Recent pulls" });
    expect(within(pulls).getByText("Failed: Token refused")).toBeInTheDocument();
    expect(within(pulls).getByText("3 accepted, 1 already uploaded, 1 refused, 0 skipped")).toBeInTheDocument();
    const documents = await screen.findByRole("list", { name: "Documents" });
    expect(within(documents).getByText("Refused: No provider with this NPI")).toBeInTheDocument();
    expect(within(documents).getByRole("link", { name: "Open note" })).toHaveAttribute("href", "/notes/note-1");
  });
});
