import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { NoteComment } from "@/lib/api/types";
import { CommentThread } from "../components/CommentThread";
import { activeMention, insertMention, mentionedIds } from "../mentions";
import type { NoteCommentsApi } from "../useNoteComments";

const CORA = { id: "u-cora", name: "Cora Coder", role: "coder" };
const COLE = { id: "u-cole", name: "Cole Compliance", role: "compliance" };
const MINE: NoteComment = {
  id: "c-1",
  finding_key: "em",
  body: "Time supports the level.",
  author_name: "Ana Admin",
  author_role: "admin",
  at: "2026-11-26T15:04:00Z",
  mentions: [],
  removed: null,
  can_remove: true,
};
const REMOVED: NoteComment = {
  ...MINE,
  id: "c-2",
  body: "Wrong note",
  can_remove: false,
  removed: { by: "Ana Admin", role: "admin", at: "2026-11-26T15:10:00Z" },
};

function fakeApi(comments: NoteComment[]): NoteCommentsApi {
  return {
    comments,
    people: [CORA, COLE],
    error: null,
    canSeeRemoved: true,
    showRemoved: true,
    setShowRemoved: vi.fn(),
    post: vi.fn().mockResolvedValue(true),
    remove: vi.fn().mockResolvedValue(undefined),
    posting: false,
    actionError: null,
  };
}

describe("mentions", () => {
  it("finds the mention being typed and inserts the chosen person", () => {
    const text = "Please check @Co";
    const mention = activeMention(text, text.length);
    expect(mention).toEqual({ start: 13, query: "Co" });
    expect(activeMention("mail@example", 12)).toBeNull();
    const edit = insertMention(text, mention!, text.length, CORA);
    expect(edit).toEqual({ text: "Please check @Cora Coder ", caret: 25 });
    expect(mentionedIds("@Cora Coder thanks", [CORA, COLE, CORA])).toEqual(["u-cora"]);
  });
});

describe("comment thread", () => {
  it("lists the finding's comments and posts a new one with the people mentioned", async () => {
    const user = userEvent.setup();
    const api = fakeApi([MINE]);
    render(<CommentThread api={api} findingKey="em" label="Comment on Office visit" />);
    expect(screen.getByText("Time supports the level.")).toBeInTheDocument();

    await user.type(screen.getByRole("combobox", { name: "Comment on Office visit" }), "Please check @Co");
    expect(screen.getByRole("option", { name: "Cora Coder" })).toBeInTheDocument();
    await user.keyboard("{Enter}");
    await user.click(screen.getByRole("button", { name: "Post" }));

    expect(api.post).toHaveBeenCalledWith("em", "Please check @Cora Coder", ["u-cora"]);
  });

  it("removes a comment and shows who removed one that was removed", async () => {
    const user = userEvent.setup();
    const api = fakeApi([MINE, REMOVED]);
    render(<CommentThread api={api} findingKey="em" label="Comment on Office visit" />);

    await user.click(screen.getByRole("button", { name: "Remove" }));

    expect(api.remove).toHaveBeenCalledWith("c-1");
    expect(screen.getAllByRole("button", { name: "Remove" })).toHaveLength(1);
    expect(screen.getByText(/^Removed by Ana Admin/)).toBeInTheDocument();
  });

  it("does not post an empty comment", async () => {
    const api = fakeApi([]);
    render(<CommentThread api={api} findingKey={null} label="Comment on the note" />);

    expect(screen.getByRole("button", { name: "Post" })).toBeDisabled();
  });
});
