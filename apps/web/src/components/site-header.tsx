"use client";

import { usePathname } from "next/navigation";

import { ThemeToggle } from "@/components/theme-toggle";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";

const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/chat": "Chat",
  "/manage": "Manage restaurants",
};

export function SiteHeader() {
  const pathname = usePathname();
  const title = TITLES[pathname] ?? "Connoisseur";

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
      <SidebarTrigger />
      <Separator orientation="vertical" className="h-5" />
      <h1 className="font-medium">{title}</h1>
      <div className="ml-auto">
        <ThemeToggle />
      </div>
    </header>
  );
}
