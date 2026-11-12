import {test,expect,type Page,type APIRequestContext} from '@playwright/test';

const backend='http://localhost:8000/api/v1';
test.beforeEach(()=>test.skip(process.env.RUN_LOCAL_E2E!=='1','Explicit real localhost services opt-in required.'));

async function signIn(page:Page){
  await page.goto('/auth');
  await page.getByLabel('Email',{exact:true}).fill(process.env.E2E_EMAIL!);
  await page.getByLabel('Password',{exact:true}).fill(process.env.E2E_PASSWORD!);
  const login=page.waitForResponse(response=>response.url().endsWith('/auth/login')&&response.request().method()==='POST');
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  const response=await login;expect(response.status()).toBe(200);
  const value=await response.json();await expect(page).toHaveURL(/\/profile$/);
  return value.access_token as string;
}

async function sendChat(page:Page,request:APIRequestContext,token:string,query:string){
  const queued=page.waitForResponse(response=>response.url().endsWith('/chat/query')&&response.request().method()==='POST');
  await page.getByRole('textbox',{name:'Movie discovery query',exact:true}).fill(query);
  await page.getByRole('button',{name:/^Discover/}).click();
  const receipt=await queued;expect(receipt.status()).toBe(202);
  const turn=await receipt.json();let result:any;
  await expect.poll(async()=>{const response=await request.get(`${backend}/chat/turns/${turn.turn_id}`,{headers:{Authorization:`Bearer ${token}`}});
    expect(response.status()).toBe(200);result=await response.json();return result.status;},
    {timeout:65_000,intervals:[1000,2000]}).toMatch(/^(complete|failed)$/);
  expect(result.status,'The real discovery worker must complete the requested turn').toBe('complete');
  expect(result.reply.text).toBeTruthy();
  await expect(page.locator('.chat-message').filter({hasText:result.reply.text}).last()).toBeVisible();
  return result.reply;
}

test('real empty search and keyboard navigation remain usable',async({page,request})=>{
  const term=`no-catalogue-title-${crypto.randomUUID()}`;
  const lookup=await request.get(`${backend}/movies?q=${encodeURIComponent(term)}`);
  expect(lookup.status()).toBe(200);expect((await lookup.json()).total).toBe(0);
  await page.goto(`/discover?q=${encodeURIComponent(term)}`);
  await expect(page.getByRole('heading',{name:'No films in this frame.',exact:true})).toBeVisible();
  await expect(page.getByRole('textbox',{name:'Search movie titles',exact:true})).toBeEnabled();
  await page.keyboard.press('Control+Home');await page.keyboard.press('Tab');
  await expect(page.getByRole('link',{name:'Skip to content',exact:true})).toBeFocused();
});

test('a failed catalogue request shows retry and recovers from the actual backend',async({page})=>{
  // Deliberate transport failure only: no API JSON or model predictions are mocked.
  await page.route('**/api/v1/movies?*',route=>route.abort('failed'));
  await page.goto('/discover');
  await expect(page.getByRole('alert')).toBeVisible();
  await page.unroute('**/api/v1/movies?*');
  await page.getByRole('button',{name:'Try again',exact:true}).click();
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.getByRole('heading',{name:/From the catalogue|No films in this frame/})).toBeVisible();
});

test('owned preferences/watchlist, real grounded context, microphone denial and text fallback',async({page,request,context})=>{
  test.skip(process.env.RUN_PROFILE_E2E!=='1','Dedicated-account preference/watchlist/chat writes require explicit opt-in.');
  test.skip(!process.env.E2E_EMAIL||!process.env.E2E_PASSWORD||!process.env.E2E_MOVIE_ID,'Supply an existing dedicated account and canonical movie ID privately.');
  const movieId=process.env.E2E_MOVIE_ID!;
  expect(movieId).toMatch(/^[1-9]\d*$/);
  const movieResponse=await request.get(`${backend}/movies/${movieId}`);expect(movieResponse.status()).toBe(200);
  const movie=await movieResponse.json();
  await context.addInitScript(()=>{
    if(navigator.mediaDevices)Object.defineProperty(navigator.mediaDevices,'getUserMedia',{
      configurable:true,value:()=>Promise.reject(new DOMException('Denied by isolated browser test','NotAllowedError'))});
  });
  const token=await signIn(page);const auth={Authorization:`Bearer ${token}`};
  const originalProfile=await request.get(`${backend}/me`,{headers:auth});expect(originalProfile.status()).toBe(200);
  const original=(await originalProfile.json()).preferences;
  const originalWatchlist=await request.get(`${backend}/me/watchlist`,{headers:auth});expect(originalWatchlist.status()).toBe(200);
  const hadMovie=(await originalWatchlist.json()).movies.some((row:{id:string})=>row.id===movieId);
  let conversationId:string|undefined;
  page.on('response',async response=>{
    if(response.url().endsWith('/chat/query')&&response.status()===202)conversationId=(await response.json()).conversation_id;
  });
  try{
    await page.getByLabel('Favourite genres, separated by commas').fill('Drama');
    await page.getByLabel('Favourite theme identifiers, separated by commas').fill('');
    await page.getByLabel(/Allow ratings and selected preferences/).check();
    await page.getByRole('button',{name:'Save preferences',exact:true}).click();
    await expect(page.getByRole('status').filter({hasText:'Preferences saved.'})).toBeVisible();
    await page.getByRole('link',{name:'Discover',exact:true}).click();
    await page.getByRole('textbox',{name:'Search movie titles',exact:true}).fill(movie.title);
    await page.getByRole('button',{name:'Find a film',exact:true}).click();
    await page.locator(`a[href="/movies/${movieId}"]`).first().click();
    await page.getByRole('button',{name:/Add to watchlist/}).click();
    await expect(page.getByRole('status').filter({hasText:'Added to your watchlist.'})).toBeVisible();
    await page.getByRole('link',{name:'Watchlist',exact:true}).click();
    await expect(page.locator(`a[href="/movies/${movieId}"]`).first()).toBeVisible();
    await page.getByRole('link',{name:'For you',exact:true}).click();
    if(process.env.E2E_REQUIRE_MODELS==='1'){
      await expect(page.locator('.recommendation-grid')).toBeVisible();
      await expect(page.getByText(/Personalized match/).first()).toBeVisible();
    }else await expect(page.locator('.recommendation-grid, .state.error, .state.empty').first()).toBeVisible();
    await page.getByRole('link',{name:'Film companion',exact:true}).click();
    await page.getByRole('button',{name:/Voice$/}).click();
    await expect(page.getByRole('alert')).toBeVisible();
    await expect(page.getByRole('textbox',{name:'Movie discovery query',exact:true})).toBeEnabled();
    const matches=await sendChat(page,request,token,'Recommend drama movies under 180 minutes');
    for(const candidate of matches.movies??[]){expect(candidate.genres).toContain('Drama');expect(candidate.runtime_minutes).toBeLessThanOrEqual(180);}
    const profile=await sendChat(page,request,token,`How is ${movie.title}?`);
    expect(profile.status).toBe('grounded');expect(profile.movies.some((row:{id:string})=>row.id===movieId)).toBeTruthy();
    const shorter=await sendChat(page,request,token,'Show me something shorter');
    if(movie.runtime_minutes)for(const candidate of shorter.movies??[])expect(candidate.runtime_minutes).toBeLessThan(movie.runtime_minutes);
    else expect(shorter.status).toBe('clarification');
    await page.getByRole('button',{name:'Clear conversation',exact:true}).click();conversationId=undefined;
    await expect(page.locator('.chat-message')).toHaveCount(0);
  }finally{
    // Restore only this account's explicit changes; never reset the database.
    const restore=await request.put(`${backend}/me/preferences`,{headers:auth,data:original});expect(restore.status()).toBe(200);
    if(!hadMovie){const removed=await request.delete(`${backend}/me/watchlist/${movieId}`,{headers:auth});expect(removed.status()).toBe(204);}
    if(conversationId)await request.delete(`${backend}/chat/conversations/${conversationId}`,{headers:auth});
  }
});

test('browser core catalogue requests stay on localhost during an offline rehearsal',async({page,context,request})=>{
  test.skip(process.env.RUN_OFFLINE_E2E!=='1','Explicit offline-rehearsal opt-in required.');
  const movieId=process.env.E2E_MOVIE_ID;test.skip(!movieId,'Supply a genuine cached catalogue movie.');
  const externalAttempts:string[]=[];
  await context.route('**/*',route=>{
    const parsed=new URL(route.request().url());
    if(['localhost','127.0.0.1','[::1]'].includes(parsed.hostname))return route.continue();
    if(!['http:','https:'].includes(parsed.protocol))return route.continue();
    externalAttempts.push(parsed.hostname);return route.abort('blockedbyclient');
  });
  const response=await request.get(`${backend}/movies/${movieId}`);expect(response.status()).toBe(200);
  const movie=await response.json();await page.goto(`/movies/${movieId}`);
  await expect(page.getByRole('heading',{name:movie.title,exact:true})).toBeVisible();
  expect(externalAttempts.length,'Core browser catalogue must not require remote resources').toBe(0);
  // This audits browser requests only; backend/worker OS-network isolation is a separate rehearsal.
});
