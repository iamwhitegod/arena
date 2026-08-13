import { Button } from "@/components/shared/Button";
import { CodeBlock } from "@/components/shared/CodeBlock";
import { ScrollReveal } from "@/components/shared/ScrollReveal";
import { INSTALL_COMMAND, LINKS } from "@/lib/constants";

export function InstallCTA() {
  return (
    <section className="py-14 sm:py-28 bg-code-bg text-white">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
        <ScrollReveal>
          <h2 className="text-2xl sm:text-4xl font-bold tracking-tight">
            Ready to clip smarter?
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Install Arena, create its private local runtime, and process on your
            own machine. No Arena subscription required.
          </p>

          <div className="mt-10 max-w-xl mx-auto">
            <CodeBlock code={INSTALL_COMMAND} className="dark:bg-surface-alt" />
          </div>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              href="/docs"
              variant="secondary"
              size="lg"
            >
              Read the Docs
            </Button>
            <Button href={LINKS.github} external variant="ghost" size="lg" className="text-muted hover:text-white hover:bg-white/10">
              View Source on GitHub
            </Button>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
