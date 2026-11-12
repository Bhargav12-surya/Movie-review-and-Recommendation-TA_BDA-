import {defineConfig} from '@playwright/test';
import base from './playwright.config';

export default defineConfig({
  ...base,
  testMatch: 'journeys.spec.ts',
  grep: /owned preferences\/watchlist/,
  outputDir: '../artifacts/browser-private-fixed-ae941521d4664a2da67543567ecc1640/results',
  projects: (base.projects ?? []).map(project => ({
    ...project,
    use: {...project.use, channel: 'msedge'}
  }))
});