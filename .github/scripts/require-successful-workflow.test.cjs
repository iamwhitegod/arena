const assert = require("node:assert/strict");
const test = require("node:test");

const { findSuccessfulRun } = require("./require-successful-workflow.cjs");

const EXPECTED_SHA = "a".repeat(40);

test("accepts a completed successful push for the exact commit", () => {
  const run = {
    head_sha: EXPECTED_SHA,
    head_branch: "main",
    status: "completed",
    conclusion: "success",
    event: "push",
    html_url: "https://github.com/example/arena/actions/runs/1",
  };

  assert.equal(
    findSuccessfulRun({ workflow_runs: [run] }, EXPECTED_SHA, "main"),
    run,
  );
});

test("accepts a manual verification but rejects pull requests and other SHAs", () => {
  const wrongSha = {
    head_sha: "b".repeat(40),
    head_branch: "main",
    status: "completed",
    conclusion: "success",
    event: "push",
  };
  const pullRequest = {
    head_sha: EXPECTED_SHA,
    head_branch: "main",
    status: "completed",
    conclusion: "success",
    event: "pull_request",
  };
  const manual = {
    head_sha: EXPECTED_SHA,
    head_branch: "main",
    status: "completed",
    conclusion: "success",
    event: "workflow_dispatch",
  };

  assert.equal(
    findSuccessfulRun(
      { workflow_runs: [wrongSha, pullRequest, manual] },
      EXPECTED_SHA,
      "main",
    ),
    manual,
  );
});

test("fails closed for malformed, pending, or failed workflow evidence", () => {
  assert.equal(findSuccessfulRun({}, EXPECTED_SHA, "main"), undefined);
  assert.equal(
    findSuccessfulRun(
      {
        workflow_runs: [
          {
            head_sha: EXPECTED_SHA,
            head_branch: "main",
            status: "in_progress",
            conclusion: null,
            event: "push",
          },
          {
            head_sha: EXPECTED_SHA,
            head_branch: "main",
            status: "completed",
            conclusion: "failure",
            event: "push",
          },
        ],
      },
      EXPECTED_SHA,
      "main",
    ),
    undefined,
  );
});

test("rejects successful evidence from a non-default branch", () => {
  const run = {
    head_sha: EXPECTED_SHA,
    head_branch: "release-branch",
    status: "completed",
    conclusion: "success",
    event: "workflow_dispatch",
  };

  assert.equal(
    findSuccessfulRun({ workflow_runs: [run] }, EXPECTED_SHA, "main"),
    undefined,
  );
});
