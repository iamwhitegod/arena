interface SectionHeaderProps {
  title: string;
  subtitle?: string;
}

export function SectionHeader({ title, subtitle }: SectionHeaderProps) {
  return (
    <div className="text-center mb-10 sm:mb-16">
      <h2 className="text-2xl font-bold tracking-tight sm:text-4xl">{title}</h2>
      {subtitle && (
        <p className="mt-3 sm:mt-4 text-base sm:text-lg text-muted max-w-2xl mx-auto">{subtitle}</p>
      )}
    </div>
  );
}
