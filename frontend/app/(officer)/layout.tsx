import { LangArea } from "@/lib/i18n";

export default function OfficerLayout({ children }: LayoutProps<"/">) {
  return (
    <LangArea area="officer">
      <div className="mx-auto min-h-screen w-full max-w-[420px] px-4 pb-8">{children}</div>
    </LangArea>
  );
}
