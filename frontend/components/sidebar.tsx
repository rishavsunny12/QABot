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
  LayoutGrid,
  CalendarClock,
  ScanEye,
  LogOut,
  CreditCard,
} from "lucide-react";
import { ProjectSwitcher } from "@/components/project-switcher";
import { TeamSwitcher } from "@/components/team-switcher";
import { useAuth } from "@/lib/auth-context";

const links = [
  { href: "/", label: "Workspace", icon: LayoutGrid },
  { href: "/setup", label: "Project Setup", icon: Settings },
  { href: "/discovery", label: "Discovery", icon: Search },
  { href: "/flows", label: "Flow Map", icon: Map },
  { href: "/tests", label: "Test Catalog", icon: FlaskConical },
  { href: "/schedules", label: "Schedules", icon: CalendarClock },
  { href: "/visual-regression", label: "Visual Regression", icon: ScanEye },
  { href: "/runs", label: "Run History", icon: History },
  { href: "/billing", label: "Billing", icon: CreditCard },
  { href: "/settings", label: "Settings", icon: LayoutDashboard },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="flex w-64 flex-col border-r border-[hsl(var(--border))] bg-[hsl(var(--card))] p-4">
      <div className="mb-8 flex items-center gap-2 px-2">
        <Bot className="h-8 w-8 text-blue-400" />
        <div>
          <div className="font-semibold">AutoQA Agent</div>
          <div className="text-xs text-gray-400">Autonomous Testing</div>
        </div>
      </div>
      <TeamSwitcher />
      <ProjectSwitcher />
      <nav className="flex flex-1 flex-col gap-1">
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              (href === "/"
                ? pathname === "/"
                : pathname === href || pathname.startsWith(href + "/"))
                ? "bg-blue-600/20 text-blue-300"
                : "text-gray-300 hover:bg-white/5"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
      </nav>
      {user && (
        <div className="mt-4 border-t border-[hsl(var(--border))] pt-4 text-sm">
          <div className="px-2 text-gray-300">{user.name}</div>
          <div className="px-2 text-xs text-gray-500">{user.email}</div>
          <button
            className="mt-2 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-gray-400 hover:bg-white/5"
            onClick={() => logout().then(() => window.location.assign("/login"))}
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      )}
    </aside>
  );
}
