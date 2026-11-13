// Role names are the ones of the server (Mutalaa.Infrastructure.Identity.Roles). The server decides;
// the panel only hides buttons the user cannot use.

export const ROLE_EDITOR = 'editor';
export const ROLE_ADMIN = 'admin';
export const ROLE_UZMAN = 'uzman';

type Roles = readonly string[] | null | undefined;

function has(roles: Roles, role: string): boolean {
  return roles?.includes(role) ?? false;
}

/** Editor policy: editor or admin (review decisions, corrections). */
export function canDecide(roles: Roles): boolean {
  return has(roles, ROLE_EDITOR) || has(roles, ROLE_ADMIN);
}

/**
 * Whether the user may decide a review in its current status: an open record is decided by an editor or an
 * admin, a record sent to an expert (`uzmanda`) only by the `uzman` role (K-51 madde 2). Other statuses are
 * closed, so any decision role passes (the form is closed by the status itself).
 */
export function canDecideStatus(roles: Roles, status: string): boolean {
  return status === 'uzmanda' ? has(roles, ROLE_UZMAN) : canDecide(roles);
}

/** Whether the user may send an open record to an expert (editor policy, like the other link actions). */
export function canSendToExpert(roles: Roles): boolean {
  return canDecide(roles);
}

/** Admin policy: release requests, preview, promote, rollback. */
export function canPublish(roles: Roles): boolean {
  return has(roles, ROLE_ADMIN);
}

export function canManageUsers(roles: Roles): boolean {
  return has(roles, ROLE_ADMIN);
}
