import type { JevAnswer, JevQuestions, JevResponse, JevState } from './types.js';

/** Vercel AI Gateway's evaluation route; TypeSafe's own endpoint is paused for new signups. */
export const SYSTEM_ONE_URL = 'https://ai-gateway.vercel.sh/v1/evaluate';
export const DEFAULT_MODEL = 'typesafe-ai/jev';

/** The gateway names TypeSafe's `noul` question type `boolean`. */
function toGatewayQuestions(questions: JevQuestions): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(questions).map(([name, q]) => [
      name,
      q.type === 'noul' ? { ...q, type: 'boolean' } : q,
    ]),
  );
}

export interface JevRequest {
  url: string;
  method: 'POST';
  headers: Record<string, string>;
  body: string;
}

/** The HTTP request for one Jev call, for any fetch-like transport. */
export function buildJevRequest(
  params: {
    apiKey: string;
    model?: string;
    baseUrl?: string;
  },
  state: JevState,
  questions: JevQuestions,
): JevRequest {
  return {
    url: params.baseUrl ?? SYSTEM_ONE_URL,
    method: 'POST',
    headers: {
      authorization: `Bearer ${params.apiKey}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model: params.model ?? DEFAULT_MODEL,
      state,
      questions: toGatewayQuestions(questions),
    }),
  };
}

/** Validates a Jev response body; throws on anything but an `answers` object. */
export function parseJevResponse(
  status: number,
  ok: boolean,
  text: string,
): JevResponse {
  if (!ok) {
    throw new Error(`Jev request failed (${status}): ${text.slice(0, 200)}`);
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error('Jev returned malformed JSON');
  }
  if (
    parsed === null ||
    typeof parsed !== 'object' ||
    !('answers' in parsed) ||
    parsed.answers === null ||
    typeof parsed.answers !== 'object'
  ) {
    throw new Error('Jev response is missing answers');
  }
  return parsed as JevResponse;
}

/** The `noul` probability of one answer; throws when it is not there. */
export function noulAnswer(
  answers: Record<string, JevAnswer>,
  name: string,
): number {
  const answer = answers[name] as unknown as Record<string, unknown> | undefined;
  // `noul` on TypeSafe's API; the gateway's boolean field name is not yet documented.
  const value = ['noul', 'boolean', 'probability', 'p', 'value']
    .map((key) => answer?.[key])
    .find((v): v is number => typeof v === 'number' && Number.isFinite(v));
  if (value === undefined) {
    throw new Error(`Invalid Jev answer for ${name}`);
  }
  return value;
}
