import {defineConfig} from '@playwright/test';
import base from './playwright.config';

export default defineConfig({
  ...base,
  testMatch: 'journeys.spec.ts',
  grep: /owned preferences\/watchlist/,
  outputDir: '../artifacts/browser-private-5567a0843ff447918e83e980e9e3e947/results',
  projects: (base.projects ?? []).map(project => ({
    ...project,
    use: {...project.use, channel: 'msedge'}
  }))
});