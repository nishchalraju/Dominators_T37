import { describe, expect, it } from 'vitest'
import { suggestedInvestigatorName } from './names'

describe('suggestedInvestigatorName', () => {
  it('prefers the display name', () => {
    expect(suggestedInvestigatorName({ display_name: '  Anita Rao ', username: 'anita_rao' })).toBe('Anita Rao')
  })

  it('falls back to a user name that contains letters, underscores included', () => {
    expect(suggestedInvestigatorName({ display_name: null, username: 'bob_second' })).toBe('bob_second')
    expect(suggestedInvestigatorName({ display_name: '   ', username: 'e2e.user-1' })).toBe('e2e.user-1')
  })

  it('suggests nothing when the user name is not a name, or when nobody is signed in', () => {
    expect(suggestedInvestigatorName({ display_name: null, username: '12345' })).toBe('')
    expect(suggestedInvestigatorName({ display_name: null, username: '___' })).toBe('')
    expect(suggestedInvestigatorName(null)).toBe('')
  })

  it('recognises letters of any script', () => {
    expect(suggestedInvestigatorName({ display_name: null, username: 'ರವಿ' })).toBe('ರವಿ')
  })
})
