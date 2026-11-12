import {defineConfig} from '@playwright/test';
import base from './playwright.config';

export default defineConfig({
  ...base,
  testMatch: 'journeys.spec.ts',
  grep: /owned preferences\/watchlist/,
  outputDir: '../artifacts/browser-private-fixed-5869aad5cb074c6dbe544a3a8ecdbcf7/results',
  projects: (base.projects ?? []).map(project => ({
    ...project,
    use: {...project.use, channel: 'msedge'}
  }))
});