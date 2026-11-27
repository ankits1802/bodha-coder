import type { HTMLAttributes, ReactNode, TdHTMLAttributes, ThHTMLAttributes } from "react";

interface TableProps {
  label: string;
  minWidth?: "sm" | "md" | "lg" | "xl";
  children: ReactNode;
}

const MIN_WIDTHS = { sm: "min-w-105", md: "min-w-160", lg: "min-w-205", xl: "min-w-300" } as const;

export function Table({ label, minWidth = "md", children }: TableProps) {
  return (
    <div className="overflow-x-auto">
      <table aria-label={label} className={`w-full border-collapse ${MIN_WIDTHS[minWidth]}`}>
        {children}
      </table>
    </div>
  );
}

export function Th({ className = "", ...rest }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={`border-b border-separator px-4 py-2.75 text-left text-caption font-medium whitespace-nowrap text-secondary ${className}`}
      {...rest}
    />
  );
}

export function Td({ className = "", ...rest }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={`border-b border-hairline px-4 py-3 align-middle ${className}`} {...rest} />;
}

interface RowProps extends HTMLAttributes<HTMLTableRowElement> {
  selected?: boolean;
}

export function Tr({ selected = false, className = "", ...rest }: RowProps) {
  const tone = selected ? "bg-row-selected" : "hover:bg-row-hover";
  return <tr className={`${tone} last:[&>td]:border-b-0 ${className}`} {...rest} />;
}

export function GroupRow({ colSpan, children }: { colSpan: number; children: ReactNode }) {
  return (
    <tr>
      <th
        scope="colgroup"
        colSpan={colSpan}
        className="border-b border-hairline bg-group-row px-4 py-2 text-left text-caption font-semibold text-secondary"
      >
        {children}
      </th>
    </tr>
  );
}
