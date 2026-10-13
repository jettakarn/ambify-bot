/**
 * Pure roster helpers shared by the LINE bot.
 * Apps Script loads this file as globals. Node tests use module.exports.
 */

function compactEmployeeId(value) {
  return String(value || "").replace(/\s+/g, "");
}

function looksLikeEmployeeId(value) {
  return /^\d{3,8}$/.test(compactEmployeeId(value));
}

function isFullTimeId(value) {
  return /^\d{3}$/.test(compactEmployeeId(value));
}

function shiftKind(startTime) {
  const minutes = parseMinutes(startTime);
  if (minutes >= 9 * 60 && minutes <= 10 * 60 + 59) return "early";
  if (minutes >= 11 * 60 && minutes <= 14 * 60 + 59) return "mid";
  if (minutes >= 17 * 60 && minutes <= 19 * 60 + 59) return "late";
  return "other";
}

function personShiftKind(shifts) {
  const counts = { early: 0, mid: 0, late: 0 };
  for (const shift of shifts || []) {
    const kind = shiftKind(shift.startTime);
    if (kind === "other") return "float";
    counts[kind] += 1;
  }
  const ranked = ["early", "mid", "late"].filter((kind) => counts[kind] > 0);
  if (!ranked.length) return "float";
  ranked.sort((left, right) => counts[right] - counts[left]);
  if (ranked.length > 1 && counts[ranked[0]] === counts[ranked[1]]) return "float";
  return ranked[0];
}

function normalizeTime(value) {
  if (!value) return null;
  let cleaned = String(value).trim().replace(/：/g, ":").replace(/[Oo]/g, "0");
  cleaned = cleaned.replace(/[^\d:]/g, "");
  if (!/^\d{1,2}:\d{2}$/.test(cleaned)) return null;
  let [hour, minute] = cleaned.split(":").map((part) => Number(part));
  if (hour === 0 && minute === 60) return "09:00";
  if (minute >= 60 || hour >= 24) return null;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function normalizeDate(value, now) {
  if (!value) return null;
  const text = String(value).trim();
  let match = text.match(/(\d{4})\s*[/\-.年]\s*(\d{1,2})\s*[/\-.月]\s*(\d{1,2})/);
  if (match) return isoDate(match[1], match[2], match[3]);
  match = text.match(/(\d{1,2})\s*月\s*(\d{1,2})/);
  if (!match) return null;
  const year = (now || new Date()).getFullYear();
  return isoDate(year, match[1], match[2]);
}

function isoDate(yearValue, monthValue, dayValue) {
  const year = Number(yearValue);
  const month = Number(monthValue);
  const day = Number(dayValue);
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null;
  }
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function parseMinutes(hhmm) {
  const [hour, minute] = hhmm.split(":").map((part) => Number(part));
  return hour * 60 + minute;
}

function formatMinutes(total) {
  const hours = Math.floor(total / 60);
  const minutes = total % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function inferCrossDay(startTime, endTime) {
  if (!startTime || !endTime) return false;
  return parseMinutes(endTime) <= parseMinutes(startTime);
}

function durationMinutes(startTime, endTime, crossDay) {
  let start = parseMinutes(startTime);
  let end = parseMinutes(endTime);
  if (crossDay || end <= start) end += 24 * 60;
  return end - start;
}

function prepareShift(row) {
  const startTime = normalizeTime(row.start_time || row.start);
  const endTime = normalizeTime(row.end_time || row.end);
  const hours = normalizeTime(row.hours);
  if (!startTime || !endTime) return null;
  const crossDay = inferCrossDay(startTime, endTime);
  const computed = formatMinutes(durationMinutes(startTime, endTime, crossDay));
  let warning = "";
  if (hours && hours !== computed) {
    warning = `${startTime}–${endTime} 算出 ${computed}，班表寫 ${hours}`;
  }
  return {
    employeeId: compactEmployeeId(row.employee_id || row.employeeId),
    nickname: String(row.nickname || "").trim(),
    startTime,
    endTime,
    hours,
    computed,
    crossDay,
    warning,
  };
}

function selectShifts(rows, employeeId) {
  const wanted = compactEmployeeId(employeeId);
  const shifts = [];
  let matched = false;
  if (isFullTimeId(wanted)) return { shifts, matched };
  for (const row of rows || []) {
    const id = compactEmployeeId(row.employee_id || row.employeeId);
    if (isFullTimeId(id) || id !== wanted) continue;
    matched = true;
    const shift = prepareShift(row);
    if (shift) shifts.push(shift);
  }
  return { shifts, matched };
}

function collectSchedule(days, employeeId, now) {
  const resultDays = [];
  let matched = false;
  let nickname = "";
  for (const day of days || []) {
    const selected = selectShifts(day.rows, employeeId);
    if (selected.matched) matched = true;
    if (!selected.shifts.length) continue;
    if (!nickname) nickname = selected.shifts[0].nickname || "";
    resultDays.push({
      date: normalizeDate(day.date, now),
      shifts: selected.shifts,
      employeeId: selected.shifts[0].employeeId,
    });
  }
  return { days: resultDays, matched, nickname, employeeId: compactEmployeeId(employeeId) };
}

function listEmployees(days) {
  const people = [];
  const seen = {};
  for (const day of days || []) {
    const rows = day.rows || [];
    for (let i = 0; i < rows.length; i += 1) {
      const id = compactEmployeeId(rows[i].employee_id || rows[i].employeeId);
      if (!id || isFullTimeId(id) || seen[id]) continue;
      seen[id] = true;
      people.push({
        employeeId: id,
        nickname: String(rows[i].nickname || "").trim(),
      });
    }
  }
  return people;
}

function rosterDateRange(days, now) {
  const dates = [];
  for (const day of days || []) {
    const date = normalizeDate(day.date, now);
    if (date) dates.push(date);
  }
  dates.sort();
  if (!dates.length) return null;
  return { start: dates[0], end: dates[dates.length - 1] };
}

function shortDate(iso) {
  const parts = String(iso).split("-");
  return `${Number(parts[1])}/${Number(parts[2])}`;
}

function formatPeopleLines(people) {
  return people.map((person) => (
    person.nickname ? `${person.employeeId} ${person.nickname}` : person.employeeId
  ));
}

function formatRosterSummary(days, now) {
  const people = listEmployees(days);
  const range = rosterDateRange(days, now);
  const lines = [];
  if (range) {
    lines.push(`已讀 ${shortDate(range.start)}–${shortDate(range.end)} 的班表，共 ${people.length} 人。`);
  } else {
    lines.push(`已讀班表，共 ${people.length} 人。`);
  }
  lines.push(...formatPeopleLines(people));
  if (!people.length) lines.push("沒讀到員工編號。");
  lines.push("請輸入員工編號。");
  return lines.join("\n");
}

function formatWhen(date) {
  if (!date) return "日期未辨識";
  const parsed = new Date(`${date}T00:00:00Z`);
  const weekdays = ["日", "一", "二", "三", "四", "五", "六"];
  const month = parsed.getUTCMonth() + 1;
  const day = parsed.getUTCDate();
  return `${month}/${day}（${weekdays[parsed.getUTCDay()]}）`;
}

function addIsoDays(iso, days) {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function weekRange(todayIso) {
  const date = new Date(`${todayIso}T00:00:00Z`);
  const sinceFriday = (date.getUTCDay() + 2) % 7;
  const start = addIsoDays(todayIso, -sinceFriday);
  return { start, end: addIsoDays(start, 6) };
}

function intervalOf(date, startTime, endTime, crossDay) {
  const start = Date.parse(`${date}T${startTime}:00Z`);
  let end = Date.parse(`${date}T${endTime}:00Z`);
  if (crossDay || end <= start) end += 24 * 60 * 60 * 1000;
  return { start, end };
}

function overlaps(left, right) {
  return left.start < right.end && right.start < left.end;
}

function paidInterval(date, startTime, endTime, crossDay) {
  const span = intervalOf(date, startTime, endTime, crossDay);
  const start = span.start + 30 * 60 * 1000;
  if (start >= span.end) return null;
  return { start, end: span.end };
}

function shiftPaidMinutes(date, startTime, endTime, crossDay, year, month) {
  const paid = paidInterval(date, startTime, endTime, crossDay);
  if (!paid) return 0;
  const total = overlapMinutes(paid, paid);
  if (!year || !month) return total;
  const monthKey = `${year}-${String(month).padStart(2, "0")}`;
  if (String(date || "").slice(0, 7) !== monthKey) return 0;
  return total;
}

function overlapMinutes(left, right) {
  const start = Math.max(left.start, right.start);
  const end = Math.min(left.end, right.end);
  if (end <= start) return 0;
  return Math.round((end - start) / 60000);
}

function eachRosterShift(days, now, visit) {
  for (const day of days || []) {
    const date = normalizeDate(day.date, now);
    if (!date) continue;
    for (const row of day.rows || []) {
      const shift = prepareShift(row);
      if (shift && !isFullTimeId(shift.employeeId)) visit(date, shift);
    }
  }
}

function publishedDates(days, now) {
  const dates = [];
  for (const day of days || []) {
    const date = normalizeDate(day.date, now);
    if (date && dates.indexOf(date) === -1) dates.push(date);
  }
  dates.sort();
  return dates;
}

function monthHours(days, year, month, now) {
  const dates = publishedDates(days, now);
  const monthStart = isoDate(year, month, 1);
  const inMonth = dates.filter((date) => monthStart && date.slice(0, 7) === monthStart.slice(0, 7));
  if (!monthStart || !inMonth.length) return { ready: false, people: [] };
  const through = inMonth[inMonth.length - 1];
  const totals = {};
  eachRosterShift(days, now, (date, shift) => {
    if (date.slice(0, 7) !== monthStart.slice(0, 7)) return;
    const paid = paidInterval(date, shift.startTime, shift.endTime, shift.crossDay);
    if (!paid || !shift.employeeId) return;
    const minutes = overlapMinutes(paid, paid);
    if (!totals[shift.employeeId]) {
      totals[shift.employeeId] = { employeeId: shift.employeeId, nickname: shift.nickname, minutes: 0 };
    }
    if (shift.nickname) totals[shift.employeeId].nickname = shift.nickname;
    totals[shift.employeeId].minutes += minutes;
  });
  const monthDays = [];
  for (const day of days || []) {
    const date = normalizeDate(day.date, now);
    if (date && date.slice(0, 7) === monthStart.slice(0, 7)) monthDays.push(day);
  }
  listEmployees(monthDays).forEach((person) => {
    if (!totals[person.employeeId]) {
      totals[person.employeeId] = { employeeId: person.employeeId, nickname: person.nickname, minutes: 0 };
    }
  });
  const people = Object.keys(totals).map((id) => totals[id]);
  people.sort((left, right) => right.minutes - left.minutes || left.employeeId.localeCompare(right.employeeId));
  return { ready: true, through, people };
}

function formatHourValue(minutes) {
  const rounded = Math.round((minutes / 60) * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

function formatLeaderboard(days, employeeId, todayIso, now) {
  const today = new Date(`${todayIso}T00:00:00Z`);
  const board = monthHours(days, today.getUTCFullYear(), today.getUTCMonth() + 1, now);
  if (!board.ready) return "班表尚未更新。";
  const wanted = compactEmployeeId(employeeId);
  const rank = board.people.findIndex((person) => person.employeeId === wanted);
  const mine = rank === -1 ? { minutes: 0 } : board.people[rank];
  const lines = [
    `你是第 ${rank === -1 ? board.people.length + 1 : rank + 1} 名，本月 ${formatHourValue(mine.minutes)} 小時。`,
    `統計至 ${shortDate(board.through)}。`,
  ];
  board.people.slice(0, 5).forEach((person, index) => {
    const name = person.nickname ? `${person.employeeId} ${person.nickname}` : person.employeeId;
    lines.push(`${index + 1}. ${name} ${formatHourValue(person.minutes)} 小時`);
  });
  return lines.join("\n");
}

function shiftsInWeek(days, employeeId, week, now) {
  const shifts = [];
  eachRosterShift(days, now, (date, shift) => {
    if (shift.employeeId !== compactEmployeeId(employeeId)) return;
    if (date < week.start || date > week.end) return;
    shifts.push({
      date,
      startTime: shift.startTime,
      endTime: shift.endTime,
      crossDay: shift.crossDay,
      nickname: shift.nickname,
      employeeId: shift.employeeId,
    });
  });
  return shifts;
}

function shiftsAfter(days, employeeId, todayIso, now) {
  const shifts = [];
  eachRosterShift(days, now, (date, shift) => {
    if (shift.employeeId !== compactEmployeeId(employeeId)) return;
    if (date <= todayIso) return;
    shifts.push({
      date,
      startTime: shift.startTime,
      endTime: shift.endTime,
      crossDay: shift.crossDay,
      nickname: shift.nickname,
      employeeId: shift.employeeId,
    });
  });
  shifts.sort((left, right) => left.date < right.date ? -1 : left.date > right.date ? 1 : left.startTime < right.startTime ? -1 : 1);
  return shifts;
}

function mergeRosterDays(documents, now) {
  const byDate = {};
  (documents || []).forEach((document) => {
    (document.days || []).forEach((day) => {
      const date = normalizeDate(day.date, now);
      if (!date) return;
      byDate[date] = { date, rows: day.rows || [] };
    });
  });
  return Object.keys(byDate).sort().map((date) => byDate[date]);
}

function daysUntil(fromIso, toIso) {
  const from = Date.parse(`${fromIso}T00:00:00Z`);
  const to = Date.parse(`${toIso}T00:00:00Z`);
  return Math.round((to - from) / 86400000);
}

function weekDistance(todayIso, week) {
  if (todayIso < week.start) return daysUntil(todayIso, week.start);
  if (todayIso > week.end) return daysUntil(week.end, todayIso);
  return 0;
}

function lookupRosterDays(documents, todayIso, now) {
  const merged = mergeRosterDays(documents, now);
  const weeks = {};
  merged.forEach((day) => {
    if (!day.date) return;
    const week = weekRange(day.date);
    weeks[week.start] = week;
  });
  const starts = Object.keys(weeks);
  if (!starts.length) return [];
  let best = starts[0];
  let bestDistance = weekDistance(todayIso, weeks[best]);
  starts.forEach((start) => {
    const distance = weekDistance(todayIso, weeks[start]);
    if (distance < bestDistance || (distance === bestDistance && start > best)) {
      best = start;
      bestDistance = distance;
    }
  });
  const keep = {};
  keep[best] = true;
  const next = addIsoDays(best, 7);
  if (weeks[next]) keep[next] = true;
  return merged.filter((day) => keep[weekRange(day.date).start]);
}

function shiftKey(shift) {
  return `${shift.date}|${shift.startTime}|${shift.endTime}|${shift.crossDay ? 1 : 0}`;
}

function occupiedDates(date, startTime, endTime, crossDay, week) {
  const span = intervalOf(date, startTime, endTime, crossDay);
  const dates = [];
  let cursor = week ? week.start : date;
  const last = week ? week.end : addIsoDays(date, crossDay ? 1 : 0);
  while (cursor <= last) {
    const bounds = {
      start: Date.parse(`${cursor}T00:00:00Z`),
      end: Date.parse(`${addIsoDays(cursor, 1)}T00:00:00Z`),
    };
    if (overlaps(span, bounds)) dates.push(cursor);
    cursor = addIsoDays(cursor, 1);
  }
  return dates;
}

function coversDate(date, startTime, endTime, crossDay, target) {
  return occupiedDates(date, startTime, endTime, crossDay).indexOf(target) !== -1;
}

function dropCandidates(days, employeeId, drop, week, now) {
  const owner = compactEmployeeId(employeeId);
  const dropSpan = intervalOf(drop.date, drop.startTime, drop.endTime, drop.crossDay);
  const blockedDates = occupiedDates(drop.date, drop.startTime, drop.endTime, drop.crossDay);
  const previousDay = addIsoDays(drop.date, -1);
  const nextDay = addIsoDays(blockedDates[blockedDates.length - 1], 1);
  const byPerson = {};
  eachRosterShift(days, now, (date, shift) => {
    if (!shift.employeeId || shift.employeeId === owner) return;
    if (!byPerson[shift.employeeId]) {
      byPerson[shift.employeeId] = { employeeId: shift.employeeId, nickname: shift.nickname, shifts: [] };
    }
    if (shift.nickname) byPerson[shift.employeeId].nickname = shift.nickname;
    byPerson[shift.employeeId].shifts.push({ date, ...shift });
  });
  listEmployees(days).forEach((person) => {
    if (!person.employeeId || person.employeeId === owner || byPerson[person.employeeId]) return;
    byPerson[person.employeeId] = { employeeId: person.employeeId, nickname: person.nickname, shifts: [] };
  });

  const people = [];
  Object.keys(byPerson).sort().forEach((id) => {
    const person = byPerson[id];
    const blocksDay = person.shifts.some((shift) => blockedDates.some((target) => coversDate(
      shift.date, shift.startTime, shift.endTime, shift.crossDay, target,
    )));
    if (blocksDay) return;

    const previous = person.shifts.filter((shift) => shift.date === previousDay);
    if (previous.length) {
      const latestEnd = Math.max(...previous.map((shift) => intervalOf(
        shift.date, shift.startTime, shift.endTime, shift.crossDay,
      ).end));
      if (dropSpan.start - latestEnd < 11 * 60 * 60 * 1000) return;
    }

    const following = person.shifts.filter((shift) => shift.date === nextDay);
    if (following.length) {
      const earliestStart = Math.min(...following.map((shift) => intervalOf(
        shift.date, shift.startTime, shift.endTime, shift.crossDay,
      ).start));
      if (earliestStart - dropSpan.end < 11 * 60 * 60 * 1000) return;
    }

    const worked = {};
    person.shifts.forEach((shift) => {
      occupiedDates(shift.date, shift.startTime, shift.endTime, shift.crossDay, week).forEach((date) => {
        worked[date] = true;
      });
    });
    occupiedDates(drop.date, drop.startTime, drop.endTime, drop.crossDay, week).forEach((date) => {
      worked[date] = true;
    });
    if (Object.keys(worked).length > 5) return;
    const kind = personShiftKind(person.shifts);
    const dropKind = shiftKind(drop.startTime);
    const sameKind = dropKind !== "other" && kind === dropKind;
    if (!sameKind && kind !== "mid" && kind !== "float") return;
    people.push({
      employeeId: person.employeeId,
      nickname: person.nickname,
      floating: kind === "float",
    });
  });
  return people;
}

function formatDropCandidates(people, drop) {
  const when = `${shortDate(drop.date)} ${drop.startTime}–${drop.endTime}`;
  if (!people.length) return `${when}\n目前無合規人員可接班。`;
  const lines = [`${when} 可接班：`];
  people.forEach((person) => {
    const label = person.nickname ? `${person.employeeId} ${person.nickname}` : person.employeeId;
    lines.push(person.floating ? `${label}（流動班別）` : label);
  });
  return lines.join("\n");
}

function formatReply(result) {
  const days = result.days || (result.shifts && result.shifts.length
    ? [{ date: result.date, shifts: result.shifts }]
    : []);
  const label = result.nickname
    ? `${result.employeeId || ""} ${result.nickname}`.trim()
    : (result.employeeId || "");
  const lines = days.length > 1
    ? [`${label} 的班表`]
    : [`${formatWhen(result.date || (days[0] && days[0].date))} ${label}`.trim()];

  if (!days.length) {
    lines.length = 0;
    lines.push(result.matched ? "有看到這個編號，但沒讀到上下班時間。" : "找不到這個員工編號。");
    if (result.rosterDays) return `${lines.join("\n")}\n${formatRosterSummary(result.rosterDays, result.now)}`;
    return lines.join("\n");
  }

  days.forEach((day) => {
    if (days.length > 1) lines.push(formatWhen(day.date));
    (day.shifts || []).forEach((shift) => {
      const span = shift.crossDay ? "，跨日" : "";
      lines.push(`${shift.startTime}–${shift.endTime}（${shift.computed}${span}）`);
      if (shift.warning) lines.push(`時數對不上：${shift.warning}`);
    });
  });
  return lines.join("\n");
}

if (typeof module !== "undefined") {
  module.exports = {
    compactEmployeeId,
    looksLikeEmployeeId,
    normalizeTime,
    normalizeDate,
    prepareShift,
    selectShifts,
    collectSchedule,
    listEmployees,
    formatRosterSummary,
    formatReply,
    inferCrossDay,
    weekRange,
    shiftPaidMinutes,
    monthHours,
    formatLeaderboard,
    shiftsInWeek,
    shiftsAfter,
    mergeRosterDays,
    lookupRosterDays,
    shiftKey,
    dropCandidates,
    formatDropCandidates,
  };
}
