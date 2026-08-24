#!/usr/bin/env node

const fs = require("node:fs");

const ALLOWED_EVENTS = new Set(["push", "workflow_dispatch"]);

function findSuccessfulRun(payload, expectedSha, expectedBranch) {
  const runs = Array.isArray(payload?.workflow_runs)
    ? payload.workflow_runs
    : [];
  return runs.find(
    (run) =>
      run?.head_sha === expectedSha &&
      run?.head_branch === expectedBranch &&
      run?.status === "completed" &&
      run?.conclusion === "success" &&
      ALLOWED_EVENTS.has(run?.event),
  );
}

function main(argv) {
  const [evidenceFile, expectedSha, expectedBranch, workflowLabel] = argv;
  if (!evidenceFile || !expectedSha || !expectedBranch || !workflowLabel) {
    throw new Error(
      "Usage: require-successful-workflow.cjs <runs-json> <expected-sha> <expected-branch> <workflow-label>",
    );
  }
  if (!/^[0-9a-f]{40}$/i.test(expectedSha)) {
    throw new Error(
      `Expected a full 40-character Git SHA; received ${JSON.stringify(expectedSha)}`,
    );
  }

  const payload = JSON.parse(fs.readFileSync(evidenceFile, "utf8"));
  const verified = findSuccessfulRun(payload, expectedSha, expectedBranch);
  if (!verified) {
    throw new Error(
      `No successful ${workflowLabel} push/dispatch run exists for exact commit ${expectedSha} on ${expectedBranch}`,
    );
  }

  console.log(`Using ${workflowLabel} verification: ${verified.html_url}`);
}

module.exports = { findSuccessfulRun };

if (require.main === module) {
  try {
    main(process.argv.slice(2));
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}
