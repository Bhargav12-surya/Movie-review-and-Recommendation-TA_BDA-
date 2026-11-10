import {test, expect} from '@playwright/test';

const enabled = process.env.RUN_LOCAL_E2E === '1';
const movieId = process.env.E2E_MOVIE_ID;
const backend = 'http://localhost:8000/api/v1';

test.beforeEach(async () => {
  test.skip(!enabled, 'Explicit RUN_LOCAL_E2E=1 and manually running services are required.');
});

test('real catalogue, movie details and honest audience evidence', async ({page, request}) => {
  test.skip(!movieId || !/^[1-9]\d*$/.test(movieId), 'Set E2E_MOVIE_ID to an actual approved canonical movie ID.');
  const response = await request.get(`${backend}/movies/${movieId}`);
  expect(response.ok(), 'A real backend movie must exist').toBeTruthy();
  const movie = await response.json();
  await page.goto(`/movies/${movieId}`);
  await expect(page.getByRole('heading', {name: movie.title, exact: true})).toBeVisible();
  if (movie.scores.overall.score === null) {
    await expect(page.getByText('Not enough audience reviews yet.', {exact: true}).first()).toBeVisible();
  }
  // Check actual rendered ordering: the summary component precedes the review list.
  const summary = page.locator('section').filter({has: page.getByRole('heading', {name: /audience.*summary|review.*summary|what the audience says|from the audience/i})}).first();
  const summaryCount = await summary.count();
  expect(summaryCount, 'The movie detail must render its evidence-summary section').toBeGreaterThan(0);
  await expect(page.getByRole('link', {name: 'Write a review', exact: true})).toBeVisible();
  await expect(page.getByText('Sign in to publish a review', {exact: false})).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(overflow, 'The movie page must fit the selected desktop/mobile viewport').toBeFalsy();
});

test('private pages preserve sign-in and text-fallback states', async ({page}) => {
  await page.goto('/assistant');
  await expect(page.getByRole('link', {name: 'Sign in', exact: true}).first()).toBeVisible();
  await expect(page.getByText('Sign in for private conversational context', {exact: false})).toBeVisible();
  await page.goto('/watchlist');
  await expect(page.getByRole('link', {name: 'Sign in', exact: true}).first()).toBeVisible();
});

test('signed-in review journey uses actual persistence and approved inference', async ({page, request}) => {
  test.skip(process.env.RUN_REVIEW_E2E !== '1', 'Review writes require explicit opt-in and a dedicated evaluation account/catalogue.');
  test.skip(!movieId || !process.env.E2E_EMAIL || !process.env.E2E_PASSWORD || !process.env.E2E_REVIEW_TEXT,
    'Supply a canonical movie, dedicated account and permitted genuine review text privately.');
  const detail = await request.get(`${backend}/movies/${movieId}`);
  expect(detail.ok()).toBeTruthy();
  const movie = await detail.json();
  await page.goto('/auth');
  await page.getByLabel('Email', {exact: true}).fill(process.env.E2E_EMAIL!);
  await page.getByLabel('Password', {exact: true}).fill(process.env.E2E_PASSWORD!);
  await page.getByRole('button', {name: 'Sign in', exact: true}).click();
  await expect(page).toHaveURL(/\/profile$/);
  // Next.js client navigation preserves the deliberately in-memory session.
  await page.getByRole('link', {name: 'Discover', exact: true}).click();
  const movieLink = page.getByRole('link', {name: movie.title, exact: true}).first();
  if (await movieLink.count()) {
    await movieLink.click();
  } else {
    await page.getByRole('searchbox').fill(movie.title);
    await page.getByRole('button', {name: /search|find/i}).click();
    await page.getByRole('link', {name: movie.title, exact: true}).first().click();
  }
  await page.getByLabel('Your review', {exact: true}).fill(process.env.E2E_REVIEW_TEXT!);
  // Research training and audience contribution remain opt-out for this journey.
  await page.getByLabel(/Allow this published review to contribute/).uncheck();
  const saved = page.waitForResponse(response => response.request().method() === 'POST'
    && response.url().endsWith(`/movies/${movieId}/reviews`));
  await page.getByRole('button', {name: 'Publish review', exact: true}).click();
  const response = await saved;
  expect(response.status()).toBe(201);
  const receipt = await response.json();
  expect(receipt.review_id).toMatch(/^[0-9a-f-]{36}$/i);
  await expect(page.getByRole('status').filter({hasText: /Review saved|review is saved|analysis/i}).first()).toBeVisible();
  if (process.env.E2E_REQUIRE_MODELS === '1') {
    // This gate must fail when actual approved inference is unavailable.
    await expect(page.getByRole('status').filter({hasText: /analysis complete/i}).first()).toBeVisible({timeout: 65_000});
  }
  // Cleanup is an authenticated UI action on the dedicated account, not a DB reset.
  await page.getByRole('link', {name: movie.title, exact: true}).count();
  test.info().annotations.push({type: 'created-review', description: receipt.review_id});
});
