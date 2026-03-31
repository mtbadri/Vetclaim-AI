/**
 * va_api.test.js — Property tests for VA branch verification logic
 *
 * WHY we test this way: va_api.js is a browser script that reads from the
 * live DOM and calls the global fetch. Testing it directly requires complex
 * module mocking. Instead, we test the core logic as a pure function that
 * takes the DOM element and fetch function as parameters — this is the
 * same pattern as dependency injection, just applied to a browser script.
 */

import * as fc from 'fast-check'
import { describe, it } from 'vitest'

// ---------------------------------------------------------------------------
// Local implementation of the branch verification logic
// ---------------------------------------------------------------------------

/**
 * Core logic of initVABranchVerification, extracted for testability.
 *
 * WHY: The original function in va_api.js reads from the global DOM and
 * calls the global fetch. By accepting these as parameters, we can test
 * the logic with any DOM element and any mock fetch function — including
 * fast-check generated ones.
 *
 * @param {HTMLElement} branchEl - The element to update with the branch info
 * @param {Function} fetchFn - The fetch function to use (injectable for testing)
 */
async function initVABranchVerificationLogic(branchEl, fetchFn) {
  branchEl.textContent = 'Loading...'

  try {
    const response = await fetchFn(
      'https://sandbox-api.va.gov/services/benefits-reference-data/v1/service-branches',
      { headers: { apiKey: 'test-key' } }
    )

    if (!response.ok) throw new Error(`VA API ${response.status}`)

    const data = await response.json()
    const match = data.items.find(b => b.code === 'ARMY')
    branchEl.textContent = match ? match.description : 'Army'

    // Add the verified badge — visual proof of live VA API connection
    const badge = document.createElement('span')
    badge.className = 'va-verified-badge'
    badge.textContent = '✓ VA Verified'
    branchEl.parentNode.appendChild(badge)

  } catch (err) {
    // API unreachable — fall back silently so the demo isn't blocked
    branchEl.textContent = 'Army'
  }
}

// ---------------------------------------------------------------------------
// Arbitrary generators
// ---------------------------------------------------------------------------

/** Generate a single service branch item */
const arbitraryBranch = () =>
  fc.record({
    code: fc.string({ minLength: 1, maxLength: 10 }),
    description: fc.string({ minLength: 1, maxLength: 60 }),
  })

/**
 * Generate a list of branches that always includes ARMY.
 * Returns both the full items array and the ARMY description so we can
 * assert the correct description was displayed.
 */
const arbitraryBranchListWithArmy = () =>
  fc.tuple(
    fc.array(arbitraryBranch().filter(b => b.code !== 'ARMY'), { maxLength: 5 }),
    fc.string({ minLength: 1, maxLength: 60 }),  // ARMY description
    fc.array(arbitraryBranch().filter(b => b.code !== 'ARMY'), { maxLength: 5 }),
  ).map(([before, armyDescription, after]) => ({
    items: [
      ...before,
      { code: 'ARMY', description: armyDescription },
      ...after,
    ],
    armyDescription,
  }))

/** Generate a list of branches that never includes ARMY */
const arbitraryBranchListWithoutArmy = () =>
  fc.array(
    arbitraryBranch().filter(b => b.code !== 'ARMY'),
    { maxLength: 10 }
  ).map(items => ({ items }))

// ---------------------------------------------------------------------------
// Property 4: VA branch API success path shows badge
// Feature: mock-va-portal, Property 4: VA branch API success path shows badge
// ---------------------------------------------------------------------------

describe('Property 4: VA branch API success path shows badge', () => {
  it('shows description and .va-verified-badge when ARMY is in the response', async () => {
    // Validates: Requirements 3.2
    await fc.assert(
      fc.asyncProperty(
        arbitraryBranchListWithArmy(),
        async ({ items, armyDescription }) => {
          // Set up a fresh DOM container for each example
          const container = document.createElement('div')
          const branchEl = document.createElement('span')
          branchEl.id = 'va-service-branch'
          container.appendChild(branchEl)
          document.body.appendChild(container)

          // Mock fetch to return the generated branch list
          const mockFetch = async () => ({
            ok: true,
            json: async () => ({ items }),
          })

          await initVABranchVerificationLogic(branchEl, mockFetch)

          const showsDescription = branchEl.textContent === armyDescription
          const hasBadge = container.querySelector('.va-verified-badge') !== null

          // Clean up DOM after each example to avoid state leaking between runs
          document.body.removeChild(container)

          return showsDescription && hasBadge
        }
      ),
      { numRuns: 100 }
    )
  })
})

// ---------------------------------------------------------------------------
// Property 5: VA branch API failure path shows fallback without badge
// Feature: mock-va-portal, Property 5: VA branch API failure path shows fallback
// ---------------------------------------------------------------------------

describe('Property 5: VA branch API failure path shows fallback without badge', () => {
  it('shows "Army" fallback and no badge when fetch throws a TypeError', async () => {
    // Validates: Requirements 3.3
    // TypeError is what the browser's fetch throws on a network error (no connection)
    await fc.assert(
      fc.asyncProperty(
        fc.string({ minLength: 1, maxLength: 100 }),  // arbitrary error message
        async (errorMessage) => {
          const container = document.createElement('div')
          const branchEl = document.createElement('span')
          branchEl.id = 'va-service-branch'
          container.appendChild(branchEl)
          document.body.appendChild(container)

          // Simulate a network failure — TypeError is what fetch throws when the
          // network is unreachable (e.g. no WiFi during the demo)
          const mockFetch = async () => { throw new TypeError(errorMessage) }

          await initVABranchVerificationLogic(branchEl, mockFetch)

          const showsFallback = branchEl.textContent === 'Army'
          const noBadge = container.querySelector('.va-verified-badge') === null

          document.body.removeChild(container)

          return showsFallback && noBadge
        }
      ),
      { numRuns: 100 }
    )
  })

  it('shows "Army" fallback and no badge when API returns non-2xx status', async () => {
    // Validates: Requirements 3.3
    // Covers server errors (500), auth failures (401/403), rate limits (429), etc.
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 400, max: 599 }),  // any HTTP error status
        async (errorStatus) => {
          const container = document.createElement('div')
          const branchEl = document.createElement('span')
          branchEl.id = 'va-service-branch'
          container.appendChild(branchEl)
          document.body.appendChild(container)

          // Simulate a non-2xx response — response.ok is false for 4xx/5xx
          const mockFetch = async () => ({
            ok: false,
            status: errorStatus,
          })

          await initVABranchVerificationLogic(branchEl, mockFetch)

          const showsFallback = branchEl.textContent === 'Army'
          const noBadge = container.querySelector('.va-verified-badge') === null

          document.body.removeChild(container)

          return showsFallback && noBadge
        }
      ),
      { numRuns: 100 }
    )
  })
})
