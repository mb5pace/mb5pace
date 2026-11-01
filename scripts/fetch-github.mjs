import { mkdir, writeFile } from "node:fs/promises";

const username = process.env.GITHUB_USERNAME || "mb5pace";
const token = process.env.GITHUB_TOKEN;

if (!token) {
  throw new Error("GITHUB_TOKEN is missing. Set it to a GitHub Actions token.");
}

const to = new Date();
const from = new Date(to);
from.setUTCFullYear(from.getUTCFullYear() - 1);

const query = `
  query ContributionCalendar($login: String!, $from: DateTime!, $to: DateTime!) {
    user(login: $login) {
      contributionsCollection(from: $from, to: $to) {
        contributionCalendar {
          totalContributions
          weeks {
            contributionDays {
              date
              contributionCount
              contributionLevel
            }
          }
        }
      }
    }
  }
`;

const response = await fetch("https://api.github.com/graphql", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    "User-Agent": "mb5pace-contribution-rings",
  },
  body: JSON.stringify({
    query,
    variables: {
      login: username,
      from: from.toISOString(),
      to: to.toISOString(),
    },
  }),
});

if (!response.ok) {
  throw new Error(`GitHub GraphQL request failed: ${response.status} ${await response.text()}`);
}

const payload = await response.json();

if (payload.errors?.length) {
  throw new Error(payload.errors.map((error) => error.message).join("\\n"));
}

const calendar = payload.data?.user?.contributionsCollection?.contributionCalendar;
if (!calendar) {
  throw new Error(`Could not find a contribution calendar for @${username}. Check the username and token.`);
}

const levelMap = {
  NONE: 0,
  FIRST_QUARTILE: 1,
  SECOND_QUARTILE: 2,
  THIRD_QUARTILE: 3,
  FOURTH_QUARTILE: 4,
};

const days = calendar.weeks.flatMap((week) =>
  week.contributionDays.map((day) => ({
    date: day.date,
    count: day.contributionCount,
    level: levelMap[day.contributionLevel] ?? 0,
  }))
);

await mkdir("data", { recursive: true });
await writeFile(
  "data/github.json",
  JSON.stringify(
    {
      username,
      generatedAt: new Date().toISOString(),
      totalContributions: calendar.totalContributions,
      days,
    },
    null,
    2
  ) + "\\n"
);

console.log(`Saved ${days.length} days and ${calendar.totalContributions} contributions for @${username}.`);
