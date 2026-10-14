/**
 * LINE webhook for ambify-bot.
 * Paste this file and roster.js into one Apps Script project.
 *
 * Script properties:
 *   LINE_CHANNEL_ACCESS_TOKEN
 *   LINE_CHANNEL_SECRET
 *   GEMINI_API_KEY
 *   GEMINI_MODEL         (optional, default gemini-3.8-flash)
 *   ADMIN_LINE_USER_ID   (only this LINE user can upload a roster PDF)
 *   ROSTER_FOLDER_ID     (Drive folder for roster JSON and upload PDFs)
 */

var NOT_UPDATED = "班表尚未更新。";
var ASK_ID = "請輸入員工編號來查詢班表。";
var NEED_BIND = "請先輸入你的員工編號。";
var MAX_MEDIA_BYTES = 15 * 1024 * 1024;
var GEMINI_FALLBACKS = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash"];

function doGet() {
  return ContentService.createTextOutput("ambify-bot line bot");
}

function doPost(e) {
  const body = (e && e.postData && e.postData.contents) || "";
  const signature = header_(e, "x-line-signature");
  if (signature && !verifyLineSignature_(body, signature)) {
    console.error("LINE signature mismatch; handling the event anyway.");
  }

  let payload;
  try {
    payload = JSON.parse(body || "{}");
  } catch (error) {
    console.error(error);
    return json_({ ok: true });
  }

  const events = payload.events || [];
  for (let i = 0; i < events.length; i += 1) {
    try {
      handleEvent_(events[i]);
    } catch (error) {
      console.error(error);
      sendText_(events[i], `處理失敗：${shortError_(error)}`);
    }
  }
  return json_({ ok: true });
}

/** Run once in the editor and approve the permission prompt. */
function authorize() {
  const config = config_();
  const missing = ["LINE_CHANNEL_ACCESS_TOKEN", "LINE_CHANNEL_SECRET", "GEMINI_API_KEY", "ROSTER_FOLDER_ID"].filter(
    (name) => !PropertiesService.getScriptProperties().getProperty(name),
  );
  if (missing.length) throw new Error(`缺少腳本屬性：${missing.join(", ")}`);
  UrlFetchApp.fetch("https://www.google.com", { muteHttpExceptions: true });
  const file = rosterFolder_().createFile("ambify-bot-auth-check.txt", "ok", MimeType.PLAIN_TEXT);
  file.setTrashed(true);
  ScriptApp.newTrigger("processRosterQueue").timeBased().after(60000).create();
  deleteMatchingTriggers_("processRosterQueue");
  console.log(`ok model=${config.model}`);
}

function handleEvent_(event) {
  if (!event) return;
  if (seenEvent_(event.webhookEventId)) return;
  const userId = event.source && event.source.userId;

  if (!config_().adminId) {
    if (event.type === "message" || event.type === "follow" || event.type === "postback") {
      sendText_(event, adminSetupText_(userId));
    }
    return;
  }
  if (event.type === "follow") {
    sendText_(event, rosterStatusText_());
    return;
  }
  if (event.type === "postback") {
    handlePostback_(event, userId);
    return;
  }
  if (event.type !== "message") return;

  const message = event.message || {};
  if (message.type === "text") {
    const trimmed = String(message.text || "").trim();
    const menu = menuAction_(trimmed);
    if (menu) {
      handleMenu_(event, userId, menu);
      return;
    }
    sendText_(event, handleText_(userId, trimmed));
    return;
  }
  if (!isAdmin_(userId)) {
    if (message.type === "image" || message.type === "file") sendText_(event, ASK_ID);
    return;
  }
  if (message.type === "image") {
    sendText_(event, "請傳班表 PDF。");
    return;
  }
  if (message.type !== "file") return;
  queueRoster_(event, userId, message);
}

function handleText_(userId, text) {
  const trimmed = String(text || "").trim();
  const roster = loadLookupRoster_();
  const now = queryNow_();
  if (!roster) return NOT_UPDATED;
  if (trimmed === "班表" || !looksLikeEmployeeId(trimmed)) {
    return formatRosterSummary(roster.days, now);
  }

  const today = taipeiToday_();
  const selected = collectSchedule(roster.days, trimmed, now);
  const upcoming = scheduleFromToday(selected, today);
  const reply = formatReply({
    nickname: selected.nickname,
    employeeId: selected.employeeId,
    days: upcoming.days,
    matched: selected.matched,
    hadShifts: selected.days.length > 0,
    nextWeekNote: selected.matched && !nextWeekPublished(roster.days, today, now),
    rosterDays: roster.days,
    now,
  });
  if (selected.matched) {
    userProps_(userId).setProperty("employeeId", selected.employeeId);
  }
  return reply;
}

function menuAction_(text) {
  if (text === "排行榜" || text === "工作時數排行榜") return "hours";
  if (text === "丟換班" || text === "丟換班查詢") return "drop";
  if (text === "今日班表") return "today";
  return "";
}

function handlePostback_(event, userId) {
  handleMenu_(event, userId, String((event.postback && event.postback.data) || ""));
}

function handleMenu_(event, userId, data) {
  const roster = loadLookupRoster_();
  if (!roster) {
    sendText_(event, NOT_UPDATED);
    return;
  }
  const now = queryNow_();
  const today = taipeiToday_();
  if (data === "today") {
    sendText_(event, formatTodayBoard(roster.days, today, now));
    return;
  }
  const employeeId = userProps_(userId).getProperty("employeeId");
  if (!employeeId) {
    sendText_(event, NEED_BIND);
    return;
  }

  if (data === "hours") {
    const monthRoster = loadMergedRoster_();
    if (!monthRoster) {
      sendText_(event, NOT_UPDATED);
      return;
    }
    sendText_(event, formatLeaderboard(monthRoster.days, employeeId, today, now));
    return;
  }
  if (data === "drop") {
    sendDropChoices_(event, roster, employeeId, today, now);
    return;
  }
  if (data.indexOf("drop|") === 0) {
    const parts = data.split("|");
    const drop = {
      date: parts[1],
      startTime: parts[2],
      endTime: parts[3],
      crossDay: parts[4] === "1",
    };
    const people = dropCandidates(roster.days, employeeId, drop, weekRange(drop.date), now);
    sendText_(event, formatDropCandidates(people, drop));
    return;
  }
  sendText_(event, "請再點一次底部選單。");
}

function sendDropChoices_(event, roster, employeeId, today, now) {
  const shifts = shiftsAfter(roster.days, employeeId, today, now);
  if (!shifts.length) {
    sendText_(event, "今天之後沒有可丟的班。");
    return;
  }
  if (shifts.length === 1) {
    const people = dropCandidates(roster.days, employeeId, shifts[0], weekRange(shifts[0].date), now);
    sendText_(event, formatDropCandidates(people, shifts[0]));
    return;
  }
  const items = shifts.slice(0, 13).map((shift) => {
    const label = `${shortDate(shift.date)} ${shift.startTime}–${shift.endTime}`;
    return {
      type: "action",
      action: {
        type: "postback",
        label: label.slice(0, 20),
        data: `drop|${shiftKey(shift)}`,
        displayText: label,
      },
    };
  });
  sendMessage_(event, "要丟哪一班？", items);
}

function rosterStatusText_() {
  const roster = loadLookupRoster_();
  if (!roster) return NOT_UPDATED;
  return formatRosterSummary(roster.days, queryNow_());
}

function isAdmin_(userId) {
  return userId === config_().adminId;
}

function adminSetupText_(userId) {
  return `你的 LINE userId 是 ${userId || "未知"}，請把它填進指令碼屬性 ADMIN_LINE_USER_ID。`;
}

function queueRoster_(event, userId, message) {
  const config = config_();
  if (!config.geminiKey || !config.lineToken) {
    sendText_(event, "機器人還沒設定 Gemini 或 LINE token。");
    return;
  }

  const media = downloadLineContent_(config.lineToken, message);
  if (media.error) {
    sendText_(event, media.error);
    return;
  }

  const hash = sha256Hex_(media.bytes);
  const existing = loadRosterByHash_(hash);
  if (existing) {
    setCurrentRosterHash_(hash);
    rememberRosterHash_(hash);
    sendText_(event, formatRosterSummary(existing.days, queryNow_()));
    return;
  }

  const upload = rosterFolder_().createFile(
    Utilities.newBlob(media.bytes, "application/pdf", `ambify-bot-upload-${userId}.pdf`),
  );
  enqueueRosterJob_(userId, upload.getId());
  replyOrPush_(event, "收到班表，正在讀整份 PDF。讀完會再傳名單，通常不用一分鐘。");
}

function enqueueRosterJob_(userId, pdfFileId) {
  const jobId = Utilities.getUuid();
  const props = PropertiesService.getScriptProperties();
  props.setProperty(`job:${jobId}`, JSON.stringify({
    userId,
    pdfFileId,
    created: Date.now(),
  }));
  const queue = JSON.parse(props.getProperty("jobQueue") || "[]");
  queue.push(jobId);
  props.setProperty("jobQueue", JSON.stringify(queue));
  ScriptApp.newTrigger("processRosterQueue").timeBased().after(1000).create();
}

/** Time-driven trigger entry. Do not rename. */
function processRosterQueue() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return;
  try {
    deleteMatchingTriggers_("processRosterQueue");
    const props = PropertiesService.getScriptProperties();
    const queue = JSON.parse(props.getProperty("jobQueue") || "[]");
    props.setProperty("jobQueue", "[]");
    for (let i = 0; i < queue.length; i += 1) {
      processRosterJob_(queue[i]);
    }
  } finally {
    lock.releaseLock();
  }
}

function processRosterJob_(jobId) {
  const props = PropertiesService.getScriptProperties();
  const raw = props.getProperty(`job:${jobId}`);
  props.deleteProperty(`job:${jobId}`);
  if (!raw) return;

  const job = JSON.parse(raw);
  let file = null;
  try {
    file = DriveApp.getFileById(job.pdfFileId);
    const bytes = file.getBlob().getBytes();
    pushText_(job.userId, ingestBytes_(job.userId, bytes));
  } catch (error) {
    console.error(error);
    pushText_(job.userId, `處理失敗：${shortError_(error)}`);
  }
  if (file) file.setTrashed(true);
}

function ingestBytes_(userId, bytes) {
  const hash = sha256Hex_(bytes);
  let document = loadRosterByHash_(hash);
  if (!document) {
    const extracted = askGemini_(config_(), { bytes, mime: "application/pdf" });
    if (extracted.error) return extracted.error;
    document = { days: extracted.days || [], sourceHash: hash };
    saveRosterByHash_(hash, document);
  }
  setCurrentRosterHash_(hash);
  rememberRosterHash_(hash);
  return formatRosterSummary(document.days, queryNow_());
}

function deleteMatchingTriggers_(handlerName) {
  const triggers = ScriptApp.getProjectTriggers();
  for (let i = 0; i < triggers.length; i += 1) {
    if (triggers[i].getHandlerFunction() === handlerName) {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
}

function downloadLineContent_(token, message) {
  const name = String((message && message.fileName) || "").toLowerCase();
  if (!name.endsWith(".pdf")) return { error: "請傳班表 PDF。" };
  if (message && message.fileSize && Number(message.fileSize) > MAX_MEDIA_BYTES) {
    return { error: "檔案超過 15MB。請壓縮後再傳整份 PDF。" };
  }

  const response = UrlFetchApp.fetch(`https://api-data.line.me/v2/bot/message/${message.id}/content`, {
    headers: { Authorization: `Bearer ${token}` },
    muteHttpExceptions: true,
  });
  if (response.getResponseCode() !== 200) {
    console.error(response.getContentText().slice(0, 300));
    return { error: "抓不到這個檔案，請再傳一次。" };
  }

  const blob = response.getBlob();
  const bytes = blob.getBytes();
  if (bytes.length > MAX_MEDIA_BYTES) {
    return { error: "檔案超過 15MB。請壓縮後再傳整份 PDF。" };
  }
  return { bytes, mime: "application/pdf" };
}

function askGemini_(config, media) {
  const prompt = [
    "你在讀國賓影城的掃描班表 PDF，可能有很多頁。",
    "每一頁抽出頁首日期，以及每一列的員工代號、暱稱、開始時間、結束時間、時數、部門。",
    "青色橫條是部門。橫條下面的列都算這個部門，直到下一條橫條。去掉「平日」和「假日」，售票部寫 TC，樓層寫 FL。",
    "表格外面的手寫不要讀。",
    "同一天的多頁合併到同一個 date。",
    "時間用 24 小時制 HH:MM。看不清的格子留空，不要猜。",
    "抽出所有列，不要只留一個人。",
    "只回 JSON，格式：{\"days\":[{\"date\":\"YYYY-MM-DD\",\"rows\":[{\"employee_id\":\"\",\"nickname\":\"\",\"department\":\"TC\",\"start_time\":\"HH:MM\",\"end_time\":\"HH:MM\",\"hours\":\"HH:MM\"}]}]}",
  ].join("\n");

  const models = [config.model].concat(GEMINI_FALLBACKS).filter((name, index, all) => name && all.indexOf(name) === index);
  let lastError = "Gemini 沒有回應。";

  for (let i = 0; i < models.length; i += 1) {
    const result = askGeminiModel_(config.geminiKey, models[i], prompt, media);
    if (result.days) {
      console.info(`Gemini model ${models[i]} returned ${result.days.length} day(s).`);
      return result;
    }
    lastError = result.error || lastError;
    console.error(`Gemini model ${models[i]}: ${lastError}`);
    if (!/不開放|找不到模型|not found|not supported|no longer available|new users/i.test(lastError)) {
      return { error: lastError };
    }
  }
  return { error: lastError };
}

function askGeminiModel_(apiKey, model, prompt, media) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`;
  const payload = JSON.stringify({
    contents: [{
      role: "user",
      parts: [
        { text: prompt },
        { inlineData: { mimeType: media.mime, data: Utilities.base64Encode(media.bytes) } },
      ],
    }],
    generationConfig: {
      temperature: 0,
      responseMimeType: "application/json",
    },
  });

  let response;
  try {
    response = UrlFetchApp.fetch(url, {
      method: "post",
      contentType: "application/json",
      muteHttpExceptions: true,
      payload,
    });
  } catch (error) {
    console.error(error);
    return { error: "讀班表逾時。請把 PDF 壓小一點再傳。" };
  }

  const raw = response.getContentText();
  if (response.getResponseCode() !== 200) {
    return { error: geminiError_(raw, model) };
  }

  try {
    const body = JSON.parse(raw);
    const parts = ((((body.candidates || [])[0] || {}).content || {}).parts) || [];
    let text = "";
    for (let i = 0; i < parts.length; i += 1) text += parts[i].text || "";
    const parsed = JSON.parse(text.replace(/```json/g, "").replace(/```/g, "").trim() || "{}");
    return { days: normalizeDays_(parsed) };
  } catch (error) {
    console.error(error);
    return { error: "Gemini 回傳的班表讀不下來，請再傳一次。" };
  }
}

function normalizeDays_(parsed) {
  if (Array.isArray(parsed.days)) return parsed.days;
  if (Array.isArray(parsed.pages)) return parsed.pages;
  if (parsed.date || parsed.rows) return [{ date: parsed.date || "", rows: parsed.rows || [] }];
  return [];
}

function geminiError_(raw, model) {
  try {
    const body = JSON.parse(raw);
    const message = (body.error && body.error.message) || raw;
    if (/not found|not supported|no longer available|new users/i.test(message)) {
      return `模型 ${model} 不開放給新帳號。可把 GEMINI_MODEL 設成 gemini-3.8-flash。`;
    }
    if (/quota|rate|resource exhausted/i.test(message)) return "Gemini 免費額度用完了，明天再試。";
    if (/inline|too large|payload|size/i.test(message)) return "檔案對 Gemini 太大。請壓縮 PDF 後再傳。";
    return `Gemini：${String(message).slice(0, 180)}`;
  } catch (error) {
    return `Gemini 連線失敗（${model}）。`;
  }
}

function sha256Hex_(bytes) {
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, bytes);
  let hex = "";
  for (let i = 0; i < digest.length; i += 1) {
    const value = digest[i] < 0 ? digest[i] + 256 : digest[i];
    hex += (`0${value.toString(16)}`).slice(-2);
  }
  return hex;
}

function rosterFolderId_() {
  return (PropertiesService.getScriptProperties().getProperty("ROSTER_FOLDER_ID") || "").trim();
}

function rosterFolder_() {
  const id = rosterFolderId_();
  if (!id) throw new Error("缺少腳本屬性：ROSTER_FOLDER_ID");
  return DriveApp.getFolderById(id);
}

function placeInRosterFolder_(file) {
  const id = rosterFolderId_();
  if (!id || !file) return file;
  const parents = file.getParents();
  while (parents.hasNext()) {
    if (parents.next().getId() === id) return file;
  }
  file.moveTo(DriveApp.getFolderById(id));
  return file;
}

function rosterFileName_(hash) {
  return `ambify-bot-roster-${hash}.json`;
}

function rosterIndexKey_(hash) {
  return `roster:${hash}`;
}

function findRosterFile_(hash) {
  const id = PropertiesService.getScriptProperties().getProperty(rosterIndexKey_(hash));
  if (!id) return null;
  try {
    const file = DriveApp.getFileById(id);
    try {
      placeInRosterFolder_(file);
    } catch (error) {
      console.error(error);
    }
    return file;
  } catch (error) {
    console.error(error);
    return null;
  }
}

function loadRosterByHash_(hash) {
  if (!hash) return null;
  const file = findRosterFile_(hash);
  if (!file) return null;
  try {
    const parsed = JSON.parse(file.getBlob().getDataAsString());
    if (!parsed || !Array.isArray(parsed.days)) return null;
    return parsed;
  } catch (error) {
    console.error(error);
    return null;
  }
}

function saveRosterByHash_(hash, document) {
  const name = rosterFileName_(hash);
  const content = JSON.stringify(document);
  const existing = findRosterFile_(hash);
  if (existing) {
    existing.setContent(content);
    return existing;
  }
  const file = rosterFolder_().createFile(name, content, MimeType.PLAIN_TEXT);
  PropertiesService.getScriptProperties().setProperty(rosterIndexKey_(hash), file.getId());
  return file;
}

function savedRosterDocuments_() {
  const documents = [];
  rosterHistory_().forEach((hash) => {
    const roster = loadRosterByHash_(hash);
    if (roster) documents.push(roster);
  });
  return documents;
}

function loadMergedRoster_() {
  const documents = savedRosterDocuments_();
  if (!documents.length) return null;
  return { days: mergeRosterDays(documents, queryNow_()) };
}

function loadLookupRoster_() {
  const documents = savedRosterDocuments_();
  if (!documents.length) return null;
  const days = lookupRosterDays(documents, taipeiToday_(), queryNow_());
  if (!days.length) return null;
  return { days };
}

function rosterHistory_() {
  const props = PropertiesService.getScriptProperties();
  let history = [];
  try {
    const parsed = JSON.parse(props.getProperty("rosterHistory") || "[]");
    if (Array.isArray(parsed)) history = parsed.filter(Boolean);
  } catch (error) {
    console.error(error);
  }
  const known = {};
  history.forEach((hash) => {
    known[hash] = true;
  });
  const extras = [];
  const all = props.getProperties();
  Object.keys(all).forEach((key) => {
    if (key.indexOf("roster:") !== 0) return;
    const hash = key.slice("roster:".length);
    if (!hash || known[hash]) return;
    const file = findRosterFile_(hash);
    extras.push({ hash, time: file ? file.getLastUpdated().getTime() : 0 });
  });
  extras.sort((left, right) => left.time - right.time);
  if (!extras.length) return history;
  extras.forEach((item) => history.push(item.hash));
  props.setProperty("rosterHistory", JSON.stringify(history));
  return history;
}

function rememberRosterHash_(hash) {
  if (!hash) return;
  const history = rosterHistory_().filter((item) => item !== hash);
  history.push(hash);
  PropertiesService.getScriptProperties().setProperty("rosterHistory", JSON.stringify(history));
}

function setCurrentRosterHash_(hash) {
  PropertiesService.getScriptProperties().setProperty("currentRosterHash", hash);
}

function sendText_(event, text) {
  sendMessage_(event, text);
}

function replyOrPush_(event, text) {
  sendMessage_(event, text);
}

function sendMessage_(event, text, items) {
  if (!text) return;
  const userId = event && event.source && event.source.userId;
  if (event && event.replyToken && replyMessage_(event.replyToken, text, items)) return;
  if (userId) pushMessage_(userId, text, items);
}

function replyMessage_(replyToken, text, items) {
  return postLineMessage_("https://api.line.me/v2/bot/message/reply", {
    replyToken,
    messages: [lineTextMessage_(text, items)],
  });
}

function pushText_(userId, text) {
  return pushMessage_(userId, text);
}

function pushMessage_(userId, text, items) {
  return postLineMessage_("https://api.line.me/v2/bot/message/push", {
    to: userId,
    messages: [lineTextMessage_(text, items)],
  });
}

function lineTextMessage_(text, items) {
  const message = { type: "text", text: String(text).slice(0, 4900) };
  if (items && items.length) message.quickReply = { items };
  return message;
}

function postLineMessage_(url, payload) {
  const token = config_().lineToken;
  if (!token) {
    console.error("LINE_CHANNEL_ACCESS_TOKEN is empty.");
    return false;
  }
  const response = UrlFetchApp.fetch(url, {
    method: "post",
    contentType: "application/json",
    headers: { Authorization: `Bearer ${token}` },
    muteHttpExceptions: true,
    payload: JSON.stringify(payload),
  });
  if (response.getResponseCode() === 200) return true;
  console.error(`${url} ${response.getResponseCode()} ${response.getContentText().slice(0, 300)}`);
  return false;
}

function verifyLineSignature_(body, signature) {
  const secret = config_().lineSecret;
  if (!secret || !signature) return false;
  const digest = Utilities.base64Encode(Utilities.computeHmacSha256Signature(body, secret));
  return digest === signature;
}

function seenEvent_(eventId) {
  if (!eventId) return false;
  const cache = CacheService.getScriptCache();
  if (cache.get(eventId)) return true;
  cache.put(eventId, "1", 600);
  return false;
}

function config_() {
  const props = PropertiesService.getScriptProperties();
  return {
    lineToken: (props.getProperty("LINE_CHANNEL_ACCESS_TOKEN") || "").trim(),
    lineSecret: (props.getProperty("LINE_CHANNEL_SECRET") || "").trim(),
    geminiKey: (props.getProperty("GEMINI_API_KEY") || "").trim(),
    model: (props.getProperty("GEMINI_MODEL") || "gemini-3.8-flash").trim(),
    adminId: (props.getProperty("ADMIN_LINE_USER_ID") || "").trim(),
  };
}

function userProps_(userId) {
  const key = `u:${userId || "unknown"}`;
  const props = PropertiesService.getScriptProperties();
  return {
    getProperty(name) {
      const all = JSON.parse(props.getProperty(key) || "{}");
      return all[name] || "";
    },
    setProperty(name, value) {
      const all = JSON.parse(props.getProperty(key) || "{}");
      all[name] = value;
      props.setProperty(key, JSON.stringify(all));
    },
    deleteProperty(name) {
      const all = JSON.parse(props.getProperty(key) || "{}");
      delete all[name];
      props.setProperty(key, JSON.stringify(all));
    },
  };
}

function queryNow_() {
  return new Date(Date.UTC(taipeiYear_(), 0, 1));
}

function taipeiYear_() {
  return Number(Utilities.formatDate(new Date(), "Asia/Taipei", "yyyy"));
}

function taipeiToday_() {
  return Utilities.formatDate(new Date(), "Asia/Taipei", "yyyy-MM-dd");
}

function shortError_(error) {
  return String((error && error.message) || error).slice(0, 180);
}

function header_(event, name) {
  const headers = (event && event.headers) || {};
  const wanted = name.toLowerCase();
  const found = Object.keys(headers).find((key) => key.toLowerCase() === wanted);
  return found ? headers[found] : "";
}

function json_(value) {
  return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(ContentService.MimeType.JSON);
}

