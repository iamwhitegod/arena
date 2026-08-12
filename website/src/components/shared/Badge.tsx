interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "outline";
}

export function Badge({ children, variant = "default" }: BadgeProps) {
  const base = "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium";
  const styles =
    variant === "outline"
      ? "border border-border text-muted"
      : "bg-arena-600/10 text-arena-600";

  return <span className={`${base} ${styles}`}>{children}</span>;
}
