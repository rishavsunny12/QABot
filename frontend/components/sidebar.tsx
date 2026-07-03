"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import {
  LayoutDashboard,
  Map,
  FlaskConical,
  History,
  Settings,
  Search,
  Bot,
} from "lucide-react";

const links = [
  { href: "/setup", label: "Project Setup", icon: Settings },
  { href: "/discovery", label: "Discovery", icon: Search },
  { href: "/flows", label: "Flow Map", icon: Map },
  { href: "/tests", label: "Test Catalog", icon: FlaskConical },
  { href: "/runs", label: "Run History", icon: History },
  { href: "/settings", label: "Settings", icon: LayoutDashboard },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-64 flex-col border-r border-[hsl(var(--border))] bg-[hsl(var(--card))] p-4">
      <div className="mb-8 flex items-center gap-2 px-2">
        <Bot className="h-8 w-8 text-blue-400" />
        <div>
          <div className="font-semibold">AutoQA Agent</div>
          <div className="text-xs text-gray-400">Autonomous Testing</div>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-1">
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              pathname === href || pathname.startsWith(href + "/")
                ? "bg-blue-600/20 text-blue-300"
                : "text-gray-300 hover:bg-white/5"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
