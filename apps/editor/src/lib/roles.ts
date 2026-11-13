// Role names are the ones of the server (Mutalaa.Infrastructure.Identity.Roles). The server decides;
// the panel only hides buttons the user cannot use.

export const ROLE_EDITOR = 'editor';
export const ROLE_ADMIN = 'admin';

type Roles = readonly string[] | null | undefined;

function has(roles: Roles, role: string): boolean {
  return roles?.includes(role) ?? false;
}

/** Editor policy: editor or admin (review decisions, corrections). */
export function canDecide(roles: Roles): boolean {
  return has(roles, ROLE_EDITOR) || has(roles, ROLE_ADMIN);
}

/** Admin policy: release requests, preview, promote, rollback. */
export function canPublish(roles: Roles): boolean {
  return has(roles, ROLE_ADMIN);
}

export function canManageUsers(roles: Roles): boolean {
  return has(roles, ROLE_ADMIN);
}

/** Admin policy: approving all the draft units of a Risale book at once (K-51 madde 11). */
export function canApproveBooks(roles: Roles): boolean {
  return has(roles, ROLE_ADMIN);
}
