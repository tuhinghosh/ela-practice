export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: string | Array<{ msg: string }>; error?: string };
      if (Array.isArray(payload.detail)) {
        message = payload.detail.map((d) => d.msg).join("; ");
      } else {
        message = payload.detail ?? payload.error ?? message;
      }
    } catch {
      // Keep fallback message.
    }
    throw new ApiError(response.status, message);
  }

  return (await response.json()) as T;
}

export type DashboardResponse = {
  child_profile: { display_name: string; grade_level: number };
  mission: { activity_id: string; title: string; mission_label: string; skill_tags: string[] };
  rewards: { stars: number; streak_days: number; badges: string[] };
  progress: {
    completion_count: number;
    average_score_percent: number;
    strengths: string[];
    growth_areas: string[];
  };
  recent_sessions: Array<{
    session_id: string;
    activity_id: string;
    activity_title: string;
    score_percent: number;
    submitted_at: string;
  }>;
};

export type ActivitiesResponse = {
  themes: string[];
  difficulties: Array<"easy" | "medium" | "difficult">;
  activities: Array<{
    id: string;
    title: string;
    theme: string;
    difficulty: "easy" | "medium" | "difficult";
    passage_type: "literary" | "informational" | "poetry";
    mission_label: string;
    skill_tags: string[];
  }>;
};

export type ActivityDetailResponse = {
  id: string;
  title: string;
  theme: string;
  difficulty: "easy" | "medium" | "difficult";
  passage_type: "literary" | "informational" | "poetry";
  mission_label: string;
  passage_title: string;
  passage_text: string;
  skill_tags: string[];
  questions: Array<{
    id: string;
    type: "multiple-choice" | "short-response";
    prompt: string;
    choices?: string[];
  }>;
};

export type SubmitResponse = {
  session_id: string;
  activity_id: string;
  total_score: number;
  max_score: number;
  score_percent: number;
  rubric: {
    completion: string;
    relevance: string;
    sentence_completeness: string;
    skill_specific_checks: string[];
  };
  skill_breakdown: Record<string, number>;
  reward_snapshot: {
    stars_before: number;
    stars_after: number;
    stars_earned: number;
    streak_before: number;
    streak_after: number;
    badges_before: string[];
    badges_after: string[];
    new_badges: string[];
    points_earned: number;
    total_points: number;
  };
};

export type ParentProgressResponse = {
  child_profile: { display_name: string; grade_level: number };
  summary: {
    session_count: number;
    average_score_percent: number;
    last_submitted_at: string | null;
    strengths: string[];
    growth_areas: string[];
    trend: "starting" | "improving" | "steady" | "needs-support";
    skill_summary: {
      strength: string;
      struggle: string;
    };
  };
  recent_sessions: Array<{
    session_id: string;
    activity_id: string;
    activity_title: string;
    score_percent: number;
    submitted_at: string;
  }>;
  writing_feedback_summaries: Array<{
    activity_title: string;
    summary: string;
  }>;
  skill_history?: Record<
    "7_day" | "30_day" | "all_time",
    Record<string, { attempts: number; avg_score: number }>
  >;
  practice_next?: Array<{ skill: string; avg_score: number; attempts: number }>;
  recent_questions?: Array<{
    session_id: string;
    activity_id: string;
    activity_title: string;
    question_id: string;
    question_type: "multiple-choice" | "short-response";
    prompt: string;
    skill_tags: string[];
    submitted_at: string | null;
    child_answer: string | null;
    correct_answer: string | null;
    is_correct: boolean | null;
  }>;
  rewards?: {
    stars: number;
    streak_days: number;
    badges: string[];
  };
  ai_usage?: {
    enabled: boolean;
    used: number;
    limit: number;
    remaining: number | null;
    reset_at: string;
  };
};

export type SessionResultResponse = {
  session_id: string;
  activity_id: string;
  activity_title: string;
  submitted_at: string | null;
  total_score: number;
  max_score: number;
  score_percent: number;
  rubric: {
    completion: string;
    relevance: string;
    sentence_completeness: string;
    skill_specific_checks: string[];
  };
  skill_breakdown: Record<string, number>;
  reward_snapshot?: {
    stars_before: number;
    stars_after: number;
    stars_earned: number;
    streak_before: number;
    streak_after: number;
    badges_before: string[];
    badges_after: string[];
    new_badges: string[];
    points_earned: number;
    total_points: number;
  };
};

export type AICoachResponse = {
  message_to_child: string;
  message_to_parent?: string | null;
  hint?: string | null;
  explanation: string;
  celebration: string;
  suggested_next_activity_id?: string | null;
  suggested_skill_tag?: string | null;
  writing_feedback?: string | null;
  confidence: number;
  used_fallback: boolean;
  model: string;
};

export async function getDashboard(): Promise<DashboardResponse> {
  return request<DashboardResponse>("/api/dashboard");
}

export async function listActivities(filters?: {
  theme?: string;
  difficulty?: "easy" | "medium" | "difficult";
}): Promise<ActivitiesResponse> {
  const params = new URLSearchParams();
  if (filters?.theme) params.set("theme", filters.theme);
  if (filters?.difficulty) params.set("difficulty", filters.difficulty);
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return request<ActivitiesResponse>(`/api/activities${suffix}`);
}

export async function getActivity(activityId: string): Promise<ActivityDetailResponse> {
  return request<ActivityDetailResponse>(`/api/activities/${activityId}`);
}

export async function submitActivity(
  activityId: string,
  payload: { responses: Array<{ question_id: string; answer_choice?: string; answer_text?: string }> },
): Promise<SubmitResponse> {
  return request<SubmitResponse>(`/api/activities/${activityId}/submit`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getParentProgress(): Promise<ParentProgressResponse> {
  return request<ParentProgressResponse>("/api/progress/parent");
}

export async function getSessionResult(sessionId: string): Promise<SessionResultResponse> {
  return request<SessionResultResponse>(`/api/sessions/${sessionId}`);
}

export async function getAICoachFeedback(
  sessionId: string,
  childQuestion?: string,
): Promise<AICoachResponse> {
  return request<AICoachResponse>("/api/ai/coach", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      child_question: childQuestion,
    }),
  });
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<{ status: string }> {
  return request<{ status: string }>("/api/auth/password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}
