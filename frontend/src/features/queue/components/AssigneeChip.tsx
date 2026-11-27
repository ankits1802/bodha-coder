import { Avatar } from "@/components/ui/Avatar";

export function AssigneeChip({ name }: { name: string | null }) {
  if (!name) return null;
  return (
    <span title={name} className="inline-flex">
      <Avatar name={name} />
      <span className="sr-only">{name}</span>
    </span>
  );
}
