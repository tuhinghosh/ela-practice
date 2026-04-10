import { activities } from "@/lib/mock-data";

import ActivityClient from "./activity-client";

export function generateStaticParams() {
  return activities.map((activity) => ({ activityId: activity.id }));
}

type ActivityPageProps = {
  params: Promise<{ activityId: string }>;
};

export default async function ActivityPage({ params }: ActivityPageProps) {
  const { activityId } = await params;
  return <ActivityClient activityId={activityId} />;
}
