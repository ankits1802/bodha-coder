import { initialsOf } from "@/lib/format";

interface AvatarProps {
  name: string;
  size?: "sm" | "md";
  muted?: boolean;
}

const SIZES = { sm: "size-7 text-micro", md: "size-8 text-caption" } as const;

export function Avatar({ name, size = "sm", muted = false }: AvatarProps) {
  return (
    <span
      aria-hidden="true"
      data-initials={initialsOf(name)}
      className={`flex flex-none items-center justify-center rounded-full bg-avatar font-semibold text-label-soft after:content-[attr(data-initials)] ${SIZES[size]} ${muted ? "opacity-50" : ""}`}
    />
  );
}
