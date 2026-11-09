import { LangArea } from "@/lib/i18n";

export default function ManagerLayout({ children }: { children: React.ReactNode }) {
  return <LangArea area="manager">{children}</LangArea>;
}
