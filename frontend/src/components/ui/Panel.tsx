import type { HTMLAttributes, ReactNode } from "react";

interface PanelProps extends HTMLAttributes<HTMLElement> {
  as?: "section" | "div" | "article" | "nav" | "aside";
  children: ReactNode;
}

export function Panel({ as: Tag = "section", className = "", children, ...rest }: PanelProps) {
  return (
    <Tag className={`overflow-hidden rounded-panel bg-surface shadow-panel ${className}`} {...rest}>
      {children}
    </Tag>
  );
}

interface PanelHeaderProps {
  title: ReactNode;
  actions?: ReactNode;
  level?: "h2" | "h3";
}

export function PanelHeader({ title, actions, level: Heading = "h2" }: PanelHeaderProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-4 pt-4 pb-3">
      <Heading className="m-0 font-sans text-headline font-semibold tracking-headline">{title}</Heading>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}
