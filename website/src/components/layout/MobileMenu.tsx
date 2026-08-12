"use client";

import { useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLenis } from "lenis/react";
import { Button } from "@/components/shared/Button";
import { LINKS } from "@/lib/constants";

interface MobileMenuProps {
  open: boolean;
  onClose: () => void;
}

const navLinks = [
  { href: "/#features", label: "Features", anchor: true },
  { href: "/docs", label: "Docs" },
  { href: "/pricing", label: "Pricing" },
  { href: LINKS.github, label: "GitHub", external: true },
];

export function MobileMenu({ open, onClose }: MobileMenuProps) {
  const lenis = useLenis();
  const pathname = usePathname();
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (contentRef.current) {
      if (open) {
        contentRef.current.style.maxHeight = `${contentRef.current.scrollHeight}px`;
      } else {
        contentRef.current.style.maxHeight = "0px";
      }
    }
  }, [open]);

  const handleAnchorClick = useCallback(
    (e: React.MouseEvent, href: string) => {
      const hash = href.split("#")[1];
      if (!hash) return;

      if (pathname === "/") {
        e.preventDefault();
        onClose();
        setTimeout(() => lenis?.scrollTo(`#${hash}`, { offset: -80 }), 100);
      } else {
        onClose();
      }
    },
    [lenis, pathname, onClose]
  );

  return (
    <div
      ref={contentRef}
      className="md:hidden overflow-hidden transition-all duration-300 ease-in-out"
      style={{ maxHeight: 0 }}
    >
      <div className="border-t border-border bg-white px-4 sm:px-6 py-4 space-y-3">
        {navLinks.map((link) =>
          link.external ? (
            <a
              key={link.href}
              href={link.href}
              target="_blank"
              rel="noopener noreferrer"
              className="block text-sm text-muted hover:text-foreground py-2"
              onClick={onClose}
            >
              {link.label}
            </a>
          ) : link.anchor ? (
            <Link
              key={link.href}
              href={link.href}
              className="block text-sm text-muted hover:text-foreground py-2"
              onClick={(e) => handleAnchorClick(e, link.href)}
            >
              {link.label}
            </Link>
          ) : (
            <Link
              key={link.href}
              href={link.href}
              className="block text-sm text-muted hover:text-foreground py-2"
              onClick={onClose}
            >
              {link.label}
            </Link>
          )
        )}
        <div className="pt-2">
          <Button href="/docs" size="sm" className="w-full">
            Get Started
          </Button>
        </div>
      </div>
    </div>
  );
}
