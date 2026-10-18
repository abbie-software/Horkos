export default function PageHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-6 sm:mb-8">
      <h1 className="font-serif text-2xl font-semibold tracking-tight sm:text-3xl">
        {title}
      </h1>
      {subtitle && (
        <p className="mt-1 max-w-2xl text-sm text-muted sm:text-base">
          {subtitle}
        </p>
      )}
    </div>
  );
}