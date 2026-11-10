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
    await expect(page.getByText(movie.scores.overall.message??'Not enough audience reviews yet.', {exact: true}).first()).toBeVisible();
  }
  // Check actual rendered ordering: the summary component precedes the review list.
  const summary = page.locator('section.summary');
  await expect(summary.getByRole('heading', {name:'What the reviews are saying',exact:true})).toBeVisible();
  const summaryBeforeReviews=await page.evaluate(()=>{const summary=document.querySelector('section.summary');const reviews=Array.from(document.querySelectorAll('h2')).find(node=>node.textContent==='From the audience');return !!summary&&!!reviews&&Boolean(summary.compareDocumentPosition(reviews)&Node.DOCUMENT_POSITION_FOLLOWING);});
  expect(summaryBeforeReviews,'Evidence summary must precede individual audience reviews').toBeTruthy();
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
  const login=page.waitForResponse(response=>response.url().endsWith('/auth/login')&&response.request().method()==='POST');
  await page.getByRole('button', {name: 'Sign in', exact: true}).click();
  const loginResponse=await login;expect(loginResponse.status()).toBe(200);
  const token=(await loginResponse.json()).access_token as string;
  await expect(page).toHaveURL(/\/profile$/);
  let created:string|undefined;
  try{
    // Client navigation keeps the deliberately in-memory authenticated session.
    await page.getByRole('link', {name: 'Discover', exact: true}).click();
    await page.getByRole('textbox',{name:'Search movie titles',exact:true}).fill(movie.title);
    await page.getByRole('button',{name:'Find a film',exact:true}).click();
    await page.locator(`a[href="/movies/${movieId}"]`).first().click();
    await page.getByLabel('Your review', {exact: true}).fill(process.env.E2E_REVIEW_TEXT!);
    await page.getByLabel(/Allow this published review to contribute/).uncheck();
    await page.getByLabel(/Separately allow this review/).uncheck();
    await page.getByLabel(/Allow similarity checks/).uncheck();
    const saved = page.waitForResponse(response => response.request().method() === 'POST'
      && response.url().endsWith(`/movies/${movieId}/reviews`));
    await page.getByRole('button', {name: 'Publish review', exact: true}).click();
    const response = await saved;expect(response.status()).toBe(201);
    const receipt=await response.json();created=receipt.review_id;
    expect(created).toMatch(/^[0-9a-f-]{36}$/i);
    await expect(page.getByRole('status').filter({hasText:/Review saved|review is saved|analysis/i}).first()).toBeVisible();
    if(process.env.E2E_REQUIRE_MODELS==='1'){
      // This must fail when any required actual approved component is unavailable.
      await expect(page.getByRole('status').filter({hasText:/analysis complete/i}).first()).toBeVisible({timeout:65_000});
    }
  }finally{
    if(created){const removed=await request.delete(`${backend}/reviews/${created}`,{headers:{Authorization:`Bearer ${token}`}});expect(removed.status()).toBe(204);}
  }
});
