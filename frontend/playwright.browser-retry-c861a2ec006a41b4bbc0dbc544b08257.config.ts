import {defineConfig} from '@playwright/test';
import base from './playwright.config';

export default defineConfig({
  ...base,
  testMatch: 'journeys.spec.ts',
  grep: /a failed catalogue request/,
  outputDir: '../artifacts/browser-retry-c861a2ec006a41b4bbc0dbc544b08257/results',
  reporter: [
    ['line'],
    ['json', {outputFile: '../artifacts/browser-retry-c861a2ec006a41b4bbc0dbc544b08257/report.json'}]
  ],
  projects: (base.projects ?? []).map(project => ({
    ...project,
    use: {...project.use, channel: 'msedge'}
  }))
});