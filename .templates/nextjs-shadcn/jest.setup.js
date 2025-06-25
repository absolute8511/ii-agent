// Optional: configure or set up a testing framework before each test.
// If you delete this file, remove `setupFilesAfterEnv` from `jest.config.js`

// Used for __tests__/testing-library.js
// Learn more: https://github.com/testing-library/jest-dom
// import '@testing-library/jest-dom'

// Add global polyfills for Node.js environment
global.TextEncoder = require('util').TextEncoder;
global.TextDecoder = require('util').TextDecoder;

// Add polyfill for Request API
if (typeof global.Request === 'undefined') {
    const { Request } = require('undici');
    global.Request = Request;
  }
  
  // Add polyfill for Response API (often needed alongside Request)
  if (typeof global.Response === 'undefined') {
    const { Response } = require('undici');
    global.Response = Response;
  }
  
  // Add polyfill for fetch API (if not already available)
  if (typeof global.fetch === 'undefined') {
    const { fetch } = require('undici');
    global.fetch = fetch;
  }