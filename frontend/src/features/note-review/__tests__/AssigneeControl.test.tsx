import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { assignNotes } from "@/lib/api/notes";
import { getTeam } from "@/lib/api/team";
import type { NoteHeader, Role } from "@/lib/api/types";
import { clearSession, setSession } from "@/lib/session/store";
import { AssigneeControl } from "../components/AssigneeControl";

vi.mock("@/lib/api/notes", () => ({ assignNotes: vi.fn() }));
vi.mock("@/lib/api/team", () => ({ getTeam: vi.fn() }));

function signIn(role: Role): void {
  setSession({ access_token: "token", user: { id: "user-1", name: "Priya Nair", email: "priya@example.com", role, billing_only: false, practice: null } });
}

function note(assignedTo: string | null, assigneeName: string | null): NoteHeader {
  return { id: "note-1", status: "ready", assigned_to: assignedTo, assignee_name: assigneeName } as unknown as NoteHeader;
}

describe("AssigneeControl", () => {
  afterEach(() => {
    clearSession();
    vi.mocked(assignNotes).mockReset();
    vi.mocked(getTeam).mockReset();
  });

  it("lets a coder take an open note and give it back", async () => {
    signIn("coder");
    vi.mocked(assignNotes).mockResolvedValue({ assigned: ["note-1"] });
    render(<AssigneeControl note={note(null, null)} />);
    expect(screen.getByText("Unassigned")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Assign to me" }));
    expect(await screen.findByText("Assigned to Priya Nair")).toBeInTheDocument();
    expect(assignNotes).toHaveBeenLastCalledWith(["note-1"], "user-1");
    fireEvent.click(screen.getByRole("button", { name: "Unassign" }));
    expect(await screen.findByText("Unassigned")).toBeInTheDocument();
    expect(assignNotes).toHaveBeenLastCalledWith(["note-1"], null);
  });

  it("shows a coder who has someone else's note without offering to take it", () => {
    signIn("coder");
    render(<AssigneeControl note={note("user-2", "Omar Haddad")} />);
    expect(screen.getByText("Assigned to Omar Haddad")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("lets an admin pick any active note reader", async () => {
    signIn("admin");
    vi.mocked(getTeam).mockResolvedValue({
      seats: 10,
      members: [
        { id: "user-1", name: "Priya Nair", email: "p@example.com", role: "admin", status: "active", mfa_enabled: true, last_active_at: null },
        { id: "user-2", name: "Omar Haddad", email: "o@example.com", role: "coder", status: "active", mfa_enabled: false, last_active_at: null },
        { id: "user-3", name: "Sam Okafor", email: "s@example.com", role: "viewer", status: "active", mfa_enabled: false, last_active_at: null },
        { id: "user-4", name: "Ana Ruiz", email: "a@example.com", role: "coder", status: "invited", mfa_enabled: false, last_active_at: null },
      ],
    });
    vi.mocked(assignNotes).mockResolvedValue({ assigned: ["note-1"] });
    render(<AssigneeControl note={note(null, null)} />);

    fireEvent.click(screen.getByRole("combobox", { name: "Assigned to" }));
    const omar = await screen.findByRole("option", { name: "Omar Haddad" });
    expect(screen.queryByRole("option", { name: "Sam Okafor" })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Ana Ruiz" })).not.toBeInTheDocument();
    fireEvent.click(omar);
    await waitFor(() => expect(assignNotes).toHaveBeenCalledWith(["note-1"], "user-2"));
  });
});
