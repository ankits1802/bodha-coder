import { fireEvent, render, screen } from "@testing-library/react";
import type { AnchorHTMLAttributes, ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { BatchPage, UploadedBatch } from "@/lib/api/types";
import { getPlaces, getUploadHistory } from "@/lib/api/uploads";
import { RecentUploads } from "../components/RecentUploads";
import { uploadStatus } from "../uploadHistory";

const navigation = vi.hoisted(() => ({ replace: vi.fn(), search: "" }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(navigation.search),
  usePathname: () => "/upload",
  useRouter: () => ({ replace: navigation.replace, push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/api/uploads", () => ({ getUploadHistory: vi.fn(), getPlaces: vi.fn() }));

const BATCH: UploadedBatch = {
  id: "batch-1",
  provider_name: "Elena Varga",
  service_date: "2026-11-25",
  place_code: "11",
  visit_type: "Established patient",
  uploaded_by: "Priya Raman",
  created_at: "2026-11-25T22:15:54Z",
  counts: { ready: 10, failed: 2 },
};

function page(items: UploadedBatch[], total: number, offset = 0): BatchPage {
  return { items, total, offset, page_size: 50 };
}

describe("RecentUploads", () => {
  beforeEach(() => {
    navigation.search = "";
    navigation.replace.mockReset();
    vi.mocked(getPlaces).mockResolvedValue([{ code: "11", name: "Office" }]);
  });

  it("lists each upload with its counts and a link to its notes in the queue", async () => {
    vi.mocked(getUploadHistory).mockResolvedValue(page([BATCH], 1));
    render(<RecentUploads refresh={0} />);

    const link = await screen.findByRole("link", { name: "Open Elena Varga, 25 Nov in the review queue" });
    expect(link).toHaveAttribute("href", "/queue?batch=batch-1");
    expect(screen.getByText("Priya Raman")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("2 could not be read")).toBeInTheDocument();
    expect(getUploadHistory).toHaveBeenCalledWith(0);
    expect(screen.queryByRole("navigation", { name: "Pages" })).not.toBeInTheDocument();
  });

  it("pages through older uploads with the offset kept in the address", async () => {
    vi.mocked(getUploadHistory).mockResolvedValue(page([BATCH], 51));
    render(<RecentUploads refresh={0} />);

    expect(await screen.findByText("1–1 of 51")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(navigation.replace).toHaveBeenCalledWith("/upload?offset=50", { scroll: false });
  });

  it("asks for the page named in the address", async () => {
    navigation.search = "offset=50";
    vi.mocked(getUploadHistory).mockResolvedValue(page([BATCH], 51, 50));
    render(<RecentUploads refresh={0} />);

    expect(await screen.findByText("51–51 of 51")).toBeInTheDocument();
    expect(getUploadHistory).toHaveBeenCalledWith(50);
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  it("shows an empty state before the first upload", async () => {
    vi.mocked(getUploadHistory).mockResolvedValue(page([], 0));
    render(<RecentUploads refresh={0} />);
    expect(await screen.findByText("No uploads yet")).toBeInTheDocument();
  });
});

describe("uploadStatus", () => {
  it("names failures first, then notes still being read, then done", () => {
    expect(uploadStatus({ counts: { failed: 1, queued: 1, ready: 3 } })).toEqual({ tone: "bad", label: "1 could not be read" });
    expect(uploadStatus({ counts: { queued: 2, reading: 1, ready: 3 } })).toEqual({ tone: "neutral", label: "3 being read" });
    expect(uploadStatus({ counts: { ready: 2, approved: 1, exported: 4 } })).toEqual({ tone: "ok", label: "Read" });
  });
});
