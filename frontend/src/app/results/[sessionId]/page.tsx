import { Suspense } from "react";

import { recentSessions } from "@/lib/mock-data";
import ResultsClient from "./results-client";

export function generateStaticParams() {
  return recentSessions.map((session) => ({ sessionId: session.id }));
}

type ResultsPageProps = {
  params: Promise<{ sessionId: string }>;
};

export default async function ResultsPage({ params }: ResultsPageProps) {
  const { sessionId } = await params;
  return (
    <Suspense fallback={<div>Loading results...</div>}>
      <ResultsClient initialSessionId={sessionId} />
    </Suspense>
  );
}
