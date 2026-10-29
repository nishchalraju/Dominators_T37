import type { User } from '@/types/api'

/**
 * The investigator's own name, suggested from the account when a case is opened (they can change it):
 * the display name, or the user name if it contains letters. A user name such as "12345" is not a name,
 * so nothing is suggested for it.
 */
export function suggestedInvestigatorName(user: Pick<User, 'display_name' | 'username'> | null): string {
  const display = user?.display_name?.trim()
  if (display) return display
  const username = user?.username ?? ''
  return /\p{L}/u.test(username) ? username : ''
}
