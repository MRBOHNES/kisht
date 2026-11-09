import { Suspense } from "react";

import { OutcomeSheet, SheetSkeleton } from "@/components/OutcomeSheet";

export default function LogOutcomePage() {
  return (
    <Suspense fallback={<SheetSkeleton />}>
      <OutcomeSheet />
    </Suspense>
  );
}
