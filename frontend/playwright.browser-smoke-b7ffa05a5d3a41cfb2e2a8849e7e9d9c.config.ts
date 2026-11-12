import {defineConfig} from '@playwright/test';
import base from './playwright.config';

export default defineConfig({
  ...base,
  testMatch: 'catalogue.spec.ts',
  grep: /real catalogue, movie details|private pages preserve/,
  outputDir: '../artifacts/browser-smoke-b7ffa05a5d3a41cfb2e2a8849e7e9d9c/results',
  reporter: [
    ['line'],
    ['json', {outputFile: '../artifacts/browser-smoke-b7ffa05a5d3a41cfb2e2a8849e7e9d9c/report.json'}]
  ],
  projects: (base.projects ?? []).map(project => ({
    ...project,
    use: {...project.use, channel: 'msedge'}
  }))
});