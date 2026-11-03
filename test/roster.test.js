const test = require("node:test");
const assert = require("node:assert/strict");
const roster = require("../gas/roster.js");

const SAMPLE_DAYS = [
  {
    date: "2026-10-06",
    rows: [
      { employee_id: "12345", nickname: "小明", start_time: "18:00", end_time: "01:00", hours: "07:00" },
      { employee_id: "12346", nickname: "阿花", start_time: "09:00", end_time: "18:00", hours: "09:00" },
    ],
  },
  {
    date: "2026/10/07",
    rows: [
      { employee_id: "12345", nickname: "小明", start_time: "09:00", end_time: "18:00", hours: "09:00" },
    ],
  },
];

test("overnight shift is seven hours", () => {
  const shift = roster.prepareShift({
    nickname: "小明",
    start_time: "18:00",
    end_time: "01:00",
    hours: "07:00",
  });
  assert.equal(shift.crossDay, true);
  assert.equal(shift.computed, "07:00");
  assert.equal(shift.warning, "");
});

test("hours mismatch is reported and the shift is kept", () => {
  const shift = roster.prepareShift({
    nickname: "小明",
    start_time: "09:00",
    end_time: "18:00",
    hours: "08:00",
  });
  assert.equal(shift.computed, "09:00");
  assert.match(shift.warning, /08:00/);
});

test("ocr 00:60 becomes 09:00", () => {
  assert.equal(roster.normalizeTime("00:60"), "09:00");
});

test("selects only the matching employee id", () => {
  const selected = roster.selectShifts(SAMPLE_DAYS[0].rows, "12345");
  assert.equal(selected.shifts.length, 1);
  assert.equal(selected.matched, true);
  assert.equal(selected.shifts[0].nickname, "小明");
});

test("nickname does not match an employee id", () => {
  const selected = roster.selectShifts(SAMPLE_DAYS[0].rows, "小明");
  assert.equal(selected.shifts.length, 0);
  assert.equal(selected.matched, false);
  assert.equal(roster.looksLikeEmployeeId("小明"), false);
  assert.equal(roster.looksLikeEmployeeId("12345"), true);
});

test("lists unique employee ids in first-seen order", () => {
  const people = roster.listEmployees(SAMPLE_DAYS);
  assert.deepEqual(people, [
    { employeeId: "12345", nickname: "小明" },
    { employeeId: "12346", nickname: "阿花" },
  ]);
});

test("roster summary asks for an employee id", () => {
  const text = roster.formatRosterSummary(SAMPLE_DAYS, new Date("2026-01-01T00:00:00Z"));
  assert.match(text, /已讀 10\/6–10\/7 的班表，共 2 人。/);
  assert.match(text, /12345 小明/);
  assert.match(text, /12346 阿花/);
  assert.match(text, /請輸入員工編號。/);
});

test("collects matching shifts across days by employee id", () => {
  const selected = roster.collectSchedule(
    SAMPLE_DAYS,
    "12345",
    new Date("2026-01-01T00:00:00Z"),
  );
  assert.equal(selected.days.length, 2);
  assert.equal(selected.days[0].date, "2026-10-06");
  assert.equal(selected.days[1].date, "2026-10-07");
  assert.equal(selected.matched, true);
  assert.equal(selected.nickname, "小明");
});

test("query reply lists each date and has no calendar link", () => {
  const selected = roster.collectSchedule(
    SAMPLE_DAYS,
    "12345",
    new Date("2026-01-01T00:00:00Z"),
  );
  const text = roster.formatReply(selected);
  assert.match(text, /12345 小明\n\n10\/6（二）\n18:00–01:00\n\n10\/7（三）/);
  assert.doesNotMatch(text, /的班表/);
  assert.match(text, /18:00–01:00/);
  assert.doesNotMatch(text, /跨日/);
  assert.doesNotMatch(text, /07:00/);
  assert.match(text, /10\/7（三）/);
  assert.doesNotMatch(text, /行事曆/);
});

test("unknown id asks again with the name list", () => {
  const text = roster.formatReply({
    employeeId: "99999",
    days: [],
    matched: false,
    rosterDays: SAMPLE_DAYS,
    now: new Date("2026-01-01T00:00:00Z"),
  });
  assert.match(text, /找不到這個員工編號。/);
  assert.match(text, /12345 小明/);
  assert.match(text, /請輸入員工編號。/);
});

test("four-hour shifts keep their hours and early or late endings use the usual finish", () => {
  assert.equal(roster.shiftPaidMinutes("2026-10-01", "14:00", "18:00", false), 4 * 60);
  assert.equal(roster.shiftPaidMinutes("2026-10-01", "09:00", "13:00", false), 4 * 60);
  assert.equal(roster.shiftPaidMinutes("2026-10-01", "09:00", "18:00", false), 7.5 * 60);
  assert.equal(roster.shiftPaidMinutes("2026-10-01", "10:00", "18:00", false), 7 * 60);
  assert.equal(roster.shiftPaidMinutes("2026-10-01", "12:00", "18:00", false), 5.5 * 60);
  assert.equal(roster.shiftPaidMinutes("2026-10-01", "18:00", "02:00", true), 6.5 * 60);
  assert.equal(roster.shiftPaidMinutes("2026-10-01", "17:00", "23:00", false), 5.5 * 60);
});

test("overnight shift stays in the month it starts", () => {
  assert.equal(roster.shiftPaidMinutes("2026-09-30", "18:00", "01:00", true), 330);
  assert.equal(roster.shiftPaidMinutes("2026-09-30", "18:00", "01:00", true, 2026, 9), 330);
  assert.equal(roster.shiftPaidMinutes("2026-09-30", "18:00", "01:00", true, 2026, 10), 0);
  assert.equal(roster.shiftPaidMinutes("2026-10-01", "09:00", "09:20", false), 0);
  assert.equal(roster.shiftPaidMinutes("2026-10-01", "09:00", "19:00", false), 9 * 60);
  const now = new Date("2026-01-01T00:00:00Z");
  const days = [
    { date: "2026-09-30", rows: [{ employee_id: "10001", nickname: "甲", start_time: "18:00", end_time: "01:00" }] },
    { date: "2026-10-01", rows: [{ employee_id: "10002", nickname: "乙", start_time: "09:00", end_time: "18:00" }] },
  ];
  const october = roster.formatLeaderboard(days, "10002", "2026-10-13", now).text;
  assert.match(october, /本月 7.5 小時/);
  assert.doesNotMatch(october, /10001/);
  const september = roster.monthHours(days, 2026, 9, now);
  assert.equal(september.people.find((person) => person.employeeId === "10001").minutes, 330);
});

test("leaderboard totals published days in the month without the 1st", () => {
  const now = new Date("2026-01-01T00:00:00Z");
  const board = roster.monthHours(SAMPLE_DAYS, 2026, 10, now);
  assert.equal(board.ready, true);
  assert.equal(board.through, "2026-10-07");
  const text = roster.formatLeaderboard(SAMPLE_DAYS, "12345", "2026-10-06", now).text;
  assert.match(text, /本月 13 小時/);
  assert.match(text, /統計區間 10\/6–10\/7/);
  assert.equal(
    roster.formatLeaderboard(
      [{ date: "2026-09-30", rows: [{ employee_id: "12345", nickname: "小明", start_time: "09:00", end_time: "18:00" }] }],
      "12345",
      "2026-10-06",
      now,
    ).text,
    "班表尚未更新。",
  );
});

test("leaderboard lists ten people per page", () => {
  const days = [
    {
      date: "2026-10-01",
      rows: Array.from({ length: 12 }, (_, index) => {
        const n = index + 1;
        return {
          employee_id: String(10000 + n),
          nickname: `人${n}`,
          start_time: "09:00",
          end_time: `${String(9 + n).padStart(2, "0")}:00`,
        };
      }),
    },
  ];
  const now = new Date("2026-01-01T00:00:00Z");
  const first = roster.formatLeaderboard(days, "10001", "2026-10-13", now, 1);
  assert.equal(first.page, 1);
  assert.equal(first.pages, 2);
  assert.match(first.text, /你是第 12 名，本月 0.5 小時。/);
  assert.match(first.text, /統計區間 10\/1–10\/1。/);
  assert.match(first.text, /第 1\/2 頁/);
  assert.match(first.text, /1\. 人12 11 小時/);
  assert.match(first.text, /10\. 人3 2.5 小時/);
  assert.doesNotMatch(first.text, /11\. 人2/);
  assert.doesNotMatch(first.text, /10012/);
  const second = roster.formatLeaderboard(days, "10001", "2026-10-13", now, 5);
  assert.equal(second.page, 2);
  assert.match(second.text, /第 2\/2 頁/);
  assert.match(second.text, /11\. 人2 1.5 小時/);
  assert.match(second.text, /12\. 人1 0.5 小時/);
  assert.doesNotMatch(second.text, /1\. 人12/);
});

test("week range is Friday through Thursday", () => {
  assert.deepEqual(roster.weekRange("2026-10-13"), { start: "2026-10-09", end: "2026-10-15" });
  assert.deepEqual(roster.weekRange("2026-10-16"), { start: "2026-10-16", end: "2026-10-22" });
});

test("drop candidates reject same-day work, an 11-hour gap, and a sixth day", () => {
  const week = roster.weekRange("2026-10-16");
  const days = [
    { date: "2026-10-15", rows: [
      { employee_id: "20002", nickname: "間隔不足", start_time: "22:00", end_time: "23:30" },
      { employee_id: "20004", nickname: "可接", start_time: "09:00", end_time: "12:00" },
      { employee_id: "20006", nickname: "跨日佔到當天", start_time: "22:00", end_time: "06:00" },
    ] },
    { date: "2026-10-16", rows: [
      { employee_id: "10001", nickname: "丟班人", start_time: "09:00", end_time: "18:00" },
      { employee_id: "20001", nickname: "當天有班", start_time: "18:00", end_time: "22:00" },
    ] },
    { date: "2026-10-17", rows: [
      { employee_id: "20004", nickname: "可接", start_time: "18:00", end_time: "22:00" },
    ] },
    ...["2026-10-17", "2026-10-18", "2026-10-19", "2026-10-20", "2026-10-21"].map((date) => ({
      date,
      rows: [{ employee_id: "20003", nickname: "已滿五天", start_time: "09:00", end_time: "18:00" }],
    })),
    { date: "2026-10-01", rows: [
      { employee_id: "20005", nickname: "沒排這週", start_time: "09:00", end_time: "18:00" },
    ] },
  ];
  const drop = { date: "2026-10-16", startTime: "09:00", endTime: "18:00", crossDay: false };
  const people = roster.dropCandidates(days, "10001", drop, week, new Date("2026-01-01T00:00:00Z"));
  assert.deepEqual(people.map((person) => person.employeeId), ["20004", "20005"]);
});

test("nobody eligible says so", () => {
  const days = [
    { date: "2026-10-16", rows: [
      { employee_id: "10001", nickname: "丟班人", start_time: "09:00", end_time: "18:00" },
      { employee_id: "20001", nickname: "當天有班", start_time: "12:00", end_time: "20:00" },
    ] },
  ];
  const drop = { date: "2026-10-16", startTime: "09:00", endTime: "18:00", crossDay: false };
  const text = roster.formatDropCandidates(
    roster.dropCandidates(days, "10001", drop, roster.weekRange("2026-10-16"), new Date("2026-01-01T00:00:00Z")),
    drop,
  );
  assert.match(text, /目前無合規人員可接班。/);
});

test("merged weeks total October once the 1st is present and a later day wins", () => {
  const now = new Date("2026-01-01T00:00:00Z");
  const days = roster.mergeRosterDays([
    { days: [
      { date: "2026-09-25", rows: [{ employee_id: "10001", nickname: "甲", start_time: "09:00", end_time: "18:00" }] },
      { date: "2026-10-01", rows: [{ employee_id: "10001", nickname: "甲", start_time: "09:00", end_time: "18:00" }] },
    ] },
    { days: [
      { date: "2026-10-01", rows: [{ employee_id: "10001", nickname: "甲", start_time: "10:00", end_time: "18:00" }] },
      { date: "2026-10-16", rows: [{ employee_id: "10001", nickname: "甲", start_time: "09:00", end_time: "18:00" }] },
    ] },
  ], now);
  assert.equal(days.find((day) => day.date === "2026-10-01").rows[0].start_time, "10:00");
  const text = roster.formatLeaderboard(days, "10001", "2026-10-13", now).text;
  assert.match(text, /本月 14.5 小時/);
  assert.match(text, /統計區間 10\/1–10\/16/);
  const onlyLater = roster.mergeRosterDays([
    { days: [{ date: "2026-10-16", rows: [{ employee_id: "10001", nickname: "甲", start_time: "09:00", end_time: "18:00" }] }] },
  ], now);
  assert.match(roster.formatLeaderboard(onlyLater, "10001", "2026-10-13", now).text, /本月 7.5 小時/);
});

test("three-digit staff ids stay out of lookup, the name list, hours, and drop shift", () => {
  const now = new Date("2026-01-01T00:00:00Z");
  const days = [
    {
      date: "2026-10-01",
      rows: [
        { employee_id: "211", nickname: "正職", start_time: "09:00", end_time: "18:00" },
        { employee_id: "12345", nickname: "小明", start_time: "09:00", end_time: "18:00" },
      ],
    },
    {
      date: "2026-10-16",
      rows: [
        { employee_id: "12345", nickname: "小明", start_time: "09:00", end_time: "18:00" },
      ],
    },
  ];
  assert.deepEqual(roster.listEmployees(days).map((person) => person.employeeId), ["12345"]);
  const selected = roster.collectSchedule(days, "211", now);
  assert.equal(selected.matched, false);
  const text = roster.formatReply({ ...selected, rosterDays: days, now });
  assert.match(text, /找不到這個員工編號。/);
  assert.doesNotMatch(text, /211/);
  assert.doesNotMatch(roster.formatLeaderboard(days, "12345", "2026-10-13", now).text, /211/);
  const people = roster.dropCandidates(
    days,
    "12345",
    { date: "2026-10-16", startTime: "09:00", endTime: "18:00", crossDay: false },
    roster.weekRange("2026-10-16"),
    now,
  );
  assert.deepEqual(people.map((person) => person.employeeId), []);
});

test("evening drop keeps late, mid, and floating shifts", () => {
  const now = new Date("2026-01-01T00:00:00Z");
  const days = [
    {
      date: "2026-10-09",
      rows: [
        { employee_id: "30001", nickname: "早班", start_time: "09:30", end_time: "18:00" },
        { employee_id: "30002", nickname: "晚班", start_time: "18:00", end_time: "22:00" },
        { employee_id: "30003", nickname: "中班", start_time: "12:00", end_time: "20:00" },
        { employee_id: "30004", nickname: "平手", start_time: "09:00", end_time: "13:00" },
        { employee_id: "30005", nickname: "外時段", start_time: "15:00", end_time: "20:00" },
        { employee_id: "30006", nickname: "多數早", start_time: "10:00", end_time: "18:00" },
        { employee_id: "30007", nickname: "早加外", start_time: "09:00", end_time: "18:00" },
        { employee_id: "224", nickname: "正職", start_time: "18:00", end_time: "22:00" },
      ],
    },
    {
      date: "2026-10-10",
      rows: [
        { employee_id: "30001", nickname: "早班", start_time: "10:59", end_time: "18:00" },
        { employee_id: "30004", nickname: "平手", start_time: "19:00", end_time: "23:00" },
        { employee_id: "30006", nickname: "多數早", start_time: "09:00", end_time: "18:00" },
        { employee_id: "30007", nickname: "早加外", start_time: "10:00", end_time: "18:00" },
      ],
    },
    {
      date: "2026-10-11",
      rows: [
        { employee_id: "30006", nickname: "多數早", start_time: "09:00", end_time: "18:00" },
        { employee_id: "30007", nickname: "早加外", start_time: "15:30", end_time: "20:00" },
      ],
    },
    {
      date: "2026-10-12",
      rows: [
        { employee_id: "30006", nickname: "多數早", start_time: "17:00", end_time: "22:00" },
      ],
    },
    {
      date: "2026-10-16",
      rows: [
        { employee_id: "10001", nickname: "丟班人", start_time: "18:00", end_time: "22:00" },
      ],
    },
  ];
  const week = roster.weekRange("2026-10-16");
  const evening = { date: "2026-10-16", startTime: "18:00", endTime: "22:00", crossDay: false };
  const people = roster.dropCandidates(days, "10001", evening, week, now);
  assert.deepEqual(people.map((person) => person.employeeId), ["30002", "30003", "30004", "30005", "30007"]);
  assert.deepEqual(
    people.filter((person) => person.floating).map((person) => person.employeeId),
    ["30004", "30005", "30007"],
  );
  const text = roster.formatDropCandidates(people, evening);
  assert.match(text, /30002 晚班/);
  assert.match(text, /30003 中班/);
  assert.doesNotMatch(text, /30003 中班（流動班別）/);
  assert.match(text, /30004 平手（流動班別）/);
  assert.doesNotMatch(text, /30001/);
  assert.doesNotMatch(text, /30006/);
  assert.doesNotMatch(text, /224/);

  const mid = roster.dropCandidates(
    days,
    "10001",
    { date: "2026-10-16", startTime: "11:00", endTime: "18:00", crossDay: false },
    week,
    now,
  );
  assert.deepEqual(mid.map((person) => person.employeeId), ["30003", "30004", "30005", "30007"]);

  const outside = roster.dropCandidates(
    days,
    "10001",
    { date: "2026-10-16", startTime: "15:00", endTime: "20:00", crossDay: false },
    week,
    now,
  );
  assert.deepEqual(outside.map((person) => person.employeeId), ["30003", "30004", "30005", "30007"]);
});

test("lookup keeps the week nearest today and the following week", () => {
  const now = new Date("2026-01-01T00:00:00Z");
  const documents = [
    {
      days: [
        { date: "2026-10-09", rows: [{ employee_id: "10001", nickname: "甲", start_time: "09:00", end_time: "18:00" }] },
        { date: "2026-10-15", rows: [{ employee_id: "10002", nickname: "乙", start_time: "18:00", end_time: "22:00" }] },
      ],
    },
    {
      days: [
        { date: "2026-10-09", rows: [{ employee_id: "10001", nickname: "甲", start_time: "10:00", end_time: "18:00" }] },
        { date: "2026-10-02", rows: [{ employee_id: "10003", nickname: "舊", start_time: "09:00", end_time: "18:00" }] },
      ],
    },
    {
      days: [
        { date: "2026-10-16", rows: [{ employee_id: "10001", nickname: "甲", start_time: "12:00", end_time: "20:00" }] },
      ],
    },
  ];
  const days = roster.lookupRosterDays(documents, "2026-10-13", now);
  assert.deepEqual(days.map((day) => day.date), ["2026-10-09", "2026-10-15", "2026-10-16"]);
  assert.equal(days[0].rows[0].start_time, "10:00");
  const selected = roster.collectSchedule(days, "10001", now);
  assert.deepEqual(selected.days.map((day) => day.date), ["2026-10-09", "2026-10-16"]);
});

test("a distance tie keeps the later week and the week after it", () => {
  const now = new Date("2026-01-01T00:00:00Z");
  const documents = [
    { days: [{ date: "2026-10-08", rows: [{ employee_id: "10001", nickname: "舊", start_time: "09:00", end_time: "18:00" }] }] },
    { days: [{ date: "2026-10-16", rows: [{ employee_id: "10002", nickname: "近", start_time: "09:00", end_time: "18:00" }] }] },
    { days: [{ date: "2026-10-23", rows: [{ employee_id: "10002", nickname: "近", start_time: "18:00", end_time: "22:00" }] }] },
  ];
  const days = roster.lookupRosterDays(documents, "2026-10-12", now);
  assert.deepEqual(days.map((day) => day.date), ["2026-10-16", "2026-10-23"]);
});

test("leaderboard keeps the current month and leaves other months out", () => {
  const now = new Date("2026-01-01T00:00:00Z");
  const days = [
    { date: "2026-09-25", rows: [{ employee_id: "10003", nickname: "丙", start_time: "09:00", end_time: "18:00" }] },
    { date: "2026-10-02", rows: [{ employee_id: "10001", nickname: "甲", start_time: "09:00", end_time: "18:00" }] },
    { date: "2026-10-16", rows: [{ employee_id: "10001", nickname: "甲", start_time: "09:00", end_time: "18:00" }] },
    {
      date: "2026-11-06",
      rows: [
        { employee_id: "10001", nickname: "甲", start_time: "09:00", end_time: "18:00" },
        { employee_id: "10002", nickname: "乙", start_time: "09:00", end_time: "18:00" },
      ],
    },
  ];
  const text = roster.formatLeaderboard(days, "10001", "2026-10-13", now).text;
  assert.match(text, /本月 15 小時/);
  assert.match(text, /統計區間 10\/2–10\/16/);
  assert.doesNotMatch(text, /10002/);
  assert.doesNotMatch(text, /10003/);
});

test("lookup lists today onward and notes a missing next week", () => {
  const now = new Date("2026-01-01T00:00:00Z");
  const days = [
    { date: "2026-10-09", rows: [{ employee_id: "10001", nickname: "甲", start_time: "09:00", end_time: "18:00" }] },
    { date: "2026-10-13", rows: [{ employee_id: "10001", nickname: "甲", start_time: "18:00", end_time: "22:00" }] },
    { date: "2026-10-15", rows: [{ employee_id: "10001", nickname: "甲", start_time: "09:00", end_time: "18:00" }] },
  ];
  const selected = roster.collectSchedule(days, "10001", now);
  const upcoming = roster.scheduleFromToday(selected, "2026-10-13");
  assert.deepEqual(upcoming.days.map((day) => day.date), ["2026-10-13", "2026-10-15"]);
  assert.equal(roster.nextWeekPublished(days, "2026-10-13", now), false);
  const text = roster.formatReply({
    ...upcoming,
    hadShifts: selected.days.length > 0,
    nextWeekNote: true,
    today: "2026-10-13",
  });
  assert.match(text, /10\/13（二）\n18:00–22:00\n\n10\/15（四）/);
  assert.doesNotMatch(text, /10\/9/);
  assert.match(text, /下週（10\/16–10\/22）的班表還沒讀到，所以上面沒有那幾天/);
  assert.match(text, /本週二/);

  const laterOnly = roster.scheduleFromToday(
    roster.collectSchedule(
      [{ date: "2026-10-09", rows: [{ employee_id: "10001", nickname: "甲", start_time: "09:00", end_time: "18:00" }] }],
      "10001",
      now,
    ),
    "2026-10-13",
  );
  const empty = roster.formatReply({
    ...laterOnly,
    hadShifts: true,
    nextWeekNote: true,
    today: "2026-10-13",
  });
  assert.match(empty, /從今天起沒有班/);
  assert.doesNotMatch(empty, /沒讀到上下班時間/);
});

test("lookup shows TC or FL on each shift", () => {
  const now = new Date("2026-01-01T00:00:00Z");
  const days = [
    {
      date: "2026-10-16",
      rows: [{ employee_id: "1326902", nickname: "Lydia", department: "平日售票部", start_time: "09:00", end_time: "18:00" }],
    },
    {
      date: "2026-10-17",
      rows: [{ employee_id: "1326902", nickname: "Lydia", department: "假日樓層", start_time: "18:00", end_time: "01:00" }],
    },
  ];
  const text = roster.formatReply(roster.collectSchedule(days, "1326902", now));
  assert.match(text, /1326902 Lydia\n\n10\/16（五）\nTC  09:00–18:00\n\n10\/17（六）\nFL  18:00–01:00/);
  assert.doesNotMatch(text, /跨日/);
  assert.doesNotMatch(text, /07:00/);
});

test("department labels are TC and FL", () => {
  assert.equal(roster.normalizeDepartment("平日售票部"), "TC");
  assert.equal(roster.normalizeDepartment("假日樓層"), "FL");
  assert.equal(roster.normalizeDepartment("TC"), "TC");
  assert.equal(roster.normalizeDepartment("櫃台"), "");
  assert.equal(roster.normalizeDepartment("F"), "FL");
  assert.equal(roster.normalizeDepartment("T"), "");
  const shift = roster.prepareShift({
    employee_id: "1326902",
    nickname: "Lydia",
    department: "平日售票部",
    start_time: "09:00",
    end_time: "18:00",
    hours: "09:00",
  });
  assert.equal(shift.department, "TC");
});

test("today board lists TC then FL without employee ids", () => {
  const now = new Date("2026-01-01T00:00:00Z");
  const days = [
    {
      date: "2026-10-16",
      rows: [
        { employee_id: "211", nickname: "正職", department: "售票部", start_time: "09:00", end_time: "18:00" },
        { employee_id: "1326902", nickname: "Lydia", department: "平日售票部", start_time: "09:00", end_time: "18:00" },
        { employee_id: "1321901", nickname: "Peggy", department: "平日樓層", start_time: "09:30", end_time: "18:00" },
        { employee_id: "1326502", nickname: "Ben", department: "樓層", start_time: "09:00", end_time: "18:00" },
        { employee_id: "10001", nickname: "", department: "", start_time: "17:00", end_time: "23:00" },
      ],
    },
    {
      date: "2026-10-17",
      rows: [
        { employee_id: "1326902", nickname: "Lydia", department: "TC", start_time: "09:00", end_time: "18:00" },
      ],
    },
  ];
  const text = roster.formatTodayBoard(days, "2026-10-16", now);
  assert.match(text, /10\/16（五）\n\nTC\n/);
  const tc = text.split("\nFL\n")[0];
  assert.match(tc, /09:00–18:00  (?:正職、Lydia|Lydia、正職)/);
  assert.match(text, /FL\n09:00–18:00  Ben\n09:30–18:00  Peggy/);
  assert.match(text, /未分部門\n17:00–23:00  未具名/);
  assert.doesNotMatch(text, /211/);
  assert.doesNotMatch(text, /1326902/);
  assert.equal(roster.formatTodayBoard(days, "2026-10-18", now), "今天沒有班表。");
});

test("today board lists trainers, floor closing, remarks, and handwritten shifts", () => {
  const now = new Date("2026-01-01T00:00:00Z");
  const days = [
    {
      date: "2026-11-09",
      notes: [
        { department: "FL", kind: "closing", text: "今日樓層打烊要細清（原因略）" },
        { department: "TC", kind: "closing", text: "打烊細清" },
        { department: "TC", kind: "remark", text: "簡短事項" },
      ],
      rows: [
        {
          employee_id: "1321901",
          nickname: "Peggy",
          department: "TC",
          start_time: "09:30",
          end_time: "18:00",
          training: { role: "trainer", partner: "Lydia", department: "F", day: 1 },
        },
        {
          employee_id: "1326902",
          nickname: "Lydia",
          department: "FL",
          start_time: "09:30",
          end_time: "18:00",
          training: { role: "trainee", department: "F", day: 1 },
        },
      ],
    },
    {
      date: "2026-10-22",
      rows: [
        { employee_id: "1326902", nickname: "Lydia", department: "TC", start_time: "10:00", end_time: "18:00" },
        { employee_id: "1324005", nickname: "Jack", department: "TC", start_time: "17:00", end_time: "23:00" },
      ],
    },
  ];
  const board = roster.formatTodayBoard(days, "2026-11-09", now);
  assert.match(board, /T\n09:30–18:00  Peggy T Lydia FL Day 1/);
  assert.match(board, /FL（打烊細清）\n09:30–18:00  Lydia/);
  assert.doesNotMatch(board, /TC\n09:30–18:00  Peggy/);
  assert.match(board, /備註\n簡短事項/);
  assert.doesNotMatch(board, /備註\nTC/);
  assert.doesNotMatch(board, /原因略/);
  const extra = roster.formatTodayBoard(days, "2026-10-22", now);
  assert.match(extra, /TC\n10:00–18:00  Lydia\n17:00–23:00  Jack/);
  const lydia = roster.formatReply(roster.collectSchedule(days, "1326902", now));
  assert.match(lydia, /FL  09:30–18:00\nPeggy T Lydia FL Day 1/);
  assert.match(lydia, /TC  10:00–18:00/);
  const peggy = roster.formatReply(roster.collectSchedule(days, "1321901", now));
  assert.match(peggy, /TC  09:30–18:00\nPeggy T Lydia FL Day 1/);
});

test("drop choices skip today and keep a later week", () => {
  const days = [
    { date: "2026-10-13", rows: [{ employee_id: "10001", nickname: "甲", start_time: "09:00", end_time: "18:00" }] },
    { date: "2026-10-09", rows: [{ employee_id: "10001", nickname: "甲", start_time: "09:00", end_time: "18:00" }] },
    { date: "2026-10-16", rows: [{ employee_id: "10001", nickname: "甲", start_time: "18:00", end_time: "22:00" }] },
  ];
  const shifts = roster.shiftsAfter(days, "10001", "2026-10-13", new Date("2026-01-01T00:00:00Z"));
  assert.deepEqual(shifts.map((shift) => shift.date), ["2026-10-16"]);
});
