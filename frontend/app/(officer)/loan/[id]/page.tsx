import { Suspense } from "react";

import { DetailSkeleton, LoanDetail } from "@/components/LoanDetail";

// useParams suspends for request-time params under Cache Components, so it needs a boundary
export default function LoanPage() {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <LoanDetail />
    </Suspense>
  );
}
