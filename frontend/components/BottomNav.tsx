"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, ClipboardList } from "lucide-react";
import { cn } from "@/lib/cn";

const TABS = [
  { href: "/",          label: "Home",     Icon: Home },
  { href: "/dashboard", label: "My Plans", Icon: ClipboardList },
];

export default function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-(--border) bg-white md:hidden">
      <div
        className="flex"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 4px)" }}
      >
        {TABS.map(({ href, label, Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className="flex flex-1 flex-col items-center gap-1 pt-2 pb-3 transition-colors"
            >
              {/* Active pill above icon */}
              <span
                className={cn(
                  "mb-0.5 h-1 w-8 rounded-full transition-all duration-200",
                  active ? "bg-(--primary)" : "bg-transparent",
                )}
              />
              <Icon
                size={24}
                strokeWidth={active ? 2.5 : 1.8}
                className={active ? "text-(--primary)" : "text-(--muted-fg)"}
              />
              <span
                className={cn(
                  "text-[11px] font-semibold",
                  active ? "text-(--primary)" : "text-(--muted-fg)",
                )}
              >
                {label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
