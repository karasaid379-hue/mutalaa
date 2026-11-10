import type { components } from '@/api/schema';

// Types of the review area, all derived from the generated schema (no hand-written API types).
export type ReviewItem = components['schemas']['ReviewItemDto'];
export type ReviewDetail = components['schemas']['ReviewDetailDto'];
export type ReviewListPage = components['schemas']['ReviewListResponse'];
export type ReviewStats = components['schemas']['ReviewStatsResponse'];
export type DecisionResult = components['schemas']['ReviewDecisionResult'];
export type BulkOutcome = components['schemas']['BulkDecisionOutcome'];
export type Session = components['schemas']['SessionResponse'];
export type UnitDetail = components['schemas']['UnitDetail'];

export type DecisionKind = 'onaylandi' | 'reddedildi';
