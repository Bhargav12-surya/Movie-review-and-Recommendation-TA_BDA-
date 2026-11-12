import {defineConfig} from '@playwright/test';
import base from './playwright.config';

export default defineConfig({
  ...base,
  testMatch: 'journeys.spec.ts',
  outputDir: '../artifacts/browser-journeys-781b58771ba24592a7032421e4f31a98/results',
  projects: (base.projects ?? []).map(project => ({
    ...project,
    use: {...project.use, channel: 'msedge'}
  }))
});