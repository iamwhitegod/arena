#!/usr/bin/env node

console.error(
  'Direct packing/publishing from cli/ is disabled. Run `npm run package:stage`, then publish `.package/`.'
);
process.exitCode = 1;
