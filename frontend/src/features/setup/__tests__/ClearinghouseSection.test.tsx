import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getClearinghouse, readHostKey, saveClearinghouse } from "@/lib/api/clearinghouse";
import type { ClearinghouseConnection, ClearinghouseView } from "@/lib/api/types";
import { ClearinghouseSection } from "../ClearinghouseSection";

vi.mock("@/lib/api/clearinghouse", () => ({
  getClearinghouse: vi.fn(),
  saveClearinghouse: vi.fn(),
  removeClearinghouse: vi.fn(),
  readHostKey: vi.fn(),
  testClearinghouse: vi.fn(),
}));

const FINGERPRINT = "SHA256:ungWv48Bz+pBQUDeXa4iI7ADYaOWF3qctBD/YfIAFa0";
const SAVED: ClearinghouseConnection = {
  id: "connection-1",
  name: "Office Ally",
  transport: "sftp",
  usage: "test",
  sender_qualifier: "ZZ",
  sender_id: "SUB123",
  receiver_qualifier: "ZZ",
  receiver_id: "330897513",
  receiver_name: "Office Ally",
  host: "ftp10.officeally.com",
  port: 22,
  username: "lakeside",
  auth_kind: "password",
  secret_saved: true,
  host_key_sha256: FINGERPRINT,
  outbound_folder: "/inbound",
  inbound_folder: "/outbound",
  saved_at: "2026-11-27T10:00:00Z",
};

function view(connection: ClearinghouseConnection | null): ClearinghouseView {
  return { connection, encryption_ready: true };
}

function type(name: string, value: string): void {
  fireEvent.change(screen.getByRole("textbox", { name }), { target: { value } });
}

describe("clearinghouse connection", () => {
  afterEach(() => {
    vi.mocked(saveClearinghouse).mockReset();
    vi.mocked(readHostKey).mockReset();
  });

  it("never shows the saved password and keeps it when the field is left empty", async () => {
    vi.mocked(getClearinghouse).mockResolvedValue(view(SAVED));
    vi.mocked(saveClearinghouse).mockResolvedValue(view({ ...SAVED, id: "connection-2" }));
    render(<ClearinghouseSection />);
    const password = await screen.findByLabelText("Password");
    expect(password).toHaveValue("");
    expect(password).toHaveAttribute("placeholder", "Saved");
    expect(screen.getByText(FINGERPRINT)).toBeInTheDocument();
    type("Folder for responses", "/acks");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(saveClearinghouse).toHaveBeenCalledTimes(1));
    expect(vi.mocked(saveClearinghouse).mock.calls[0]?.[0]).toMatchObject({
      password: null,
      private_key: null,
      host_key_sha256: FINGERPRINT,
      inbound_folder: "/acks",
    });
  });

  it("reads the host key and sends the fingerprint the admin accepted with the new password", async () => {
    vi.mocked(getClearinghouse).mockResolvedValue(view(null));
    vi.mocked(readHostKey).mockResolvedValue({ host_key_sha256: FINGERPRINT });
    vi.mocked(saveClearinghouse).mockResolvedValue(view(SAVED));
    render(<ClearinghouseSection />);
    await screen.findByRole("textbox", { name: "Clearinghouse" });
    type("Clearinghouse", "Office Ally");
    type("Sender ID", "sub123");
    type("Receiver ID", "330897513");
    type("Receiver name", "Office Ally");
    type("Host", "ftp10.officeally.com");
    type("User name", "lakeside");
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct horse" } });
    type("Folder for claims", "/inbound");
    type("Folder for responses", "/outbound");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Read the host key")).toBeInTheDocument();
    expect(saveClearinghouse).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Read host key" }));
    await waitFor(() => expect(readHostKey).toHaveBeenCalledWith("ftp10.officeally.com", 22));
    expect(await screen.findByText(FINGERPRINT)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(saveClearinghouse).toHaveBeenCalledTimes(1));
    expect(vi.mocked(saveClearinghouse).mock.calls[0]?.[0]).toMatchObject({
      sender_id: "SUB123",
      port: 22,
      auth_kind: "password",
      password: "correct horse",
      host_key_sha256: FINGERPRINT,
    });
  });

  it("asks only for the envelope identifiers when claims are uploaded to a portal", async () => {
    vi.mocked(getClearinghouse).mockResolvedValue(view(null));
    render(<ClearinghouseSection />);
    await screen.findByRole("textbox", { name: "Clearinghouse" });
    fireEvent.click(screen.getByRole("radio", { name: "Portal upload" }));
    expect(screen.queryByRole("textbox", { name: "Host" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Read host key" })).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Sender ID" })).toBeInTheDocument();
  });
});
