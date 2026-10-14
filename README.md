# ambify-bot

[中文](README.zh-TW.md) • [Install](#install) • [Usage](#usage) • [Settings](#settings) • [LLM policy](#llm-policy)

![LINE Messaging API](https://img.shields.io/badge/LINE-Messaging_API-06C755?style=flat-square&logo=line&logoColor=white)

Send a full Ambassador cinema roster PDF in LINE. The bot lists employee numbers and nicknames. Send a number and it replies with that person's shifts.

The webhook runs on Apps Script. Replies stay in the chat. The roster passes through LINE, Gemini, and your Google Drive.

---

### Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Install](#install)
- [Usage](#usage)
- [Settings](#settings)
- [LLM policy](#llm-policy)

# Introduction

One official account holds one current roster. An admin uploads the PDF. Everyone else looks up a shift by employee number.

+ **Lookups list shifts from today onward.** When next week's roster has not been read, the reply says it may not have been released yet and comes out on Tuesday at the earliest. Drop-shift uses the week closest to today, plus the next week when it has already been read, and lists shifts after today. On a shared day, the last upload wins. The hours board lists the current month and names its first and last published day.
+ **Lookup uses the employee number.** The nickname is shown beside it.
+ **Apps Script is the webhook.** Parsed rosters sit in your Google Drive.

# Features

- The admin sends a PDF. The bot says it received the file, reads it in the background, and then sends the employee list. That usually takes under a minute.
- Anyone can send an employee number, such as `12345`, and get that person's shifts from today onward. Each shift is marked `TC` or `FL` and shows only the clock times. When next week's roster has not been read, the reply says it may not have been released yet, and that it comes out on Tuesday at the earliest.
- The same PDF bytes are skipped. A later upload of an earlier week stays out of lookups and drop-shift. Lookups list shifts from today onward. Drop-shift uses the week closest to today, plus the next week when that week is already read, and lists shifts after today. The hours board includes every read week in the current month, names the first and last published day, and leaves other months out.
- Keep each file under 15MB. When the free Gemini quota runs out, the reply states the reason.
- A rich menu in the LINE console sends `排行榜`, `丟換班`, and `今日班表`. The bot treats those three strings as the menu.

### Hours

Hours use the Taipei calendar month. Each shift is its start-to-end length, then minus 0.5 hours. A result below zero counts as zero. A shift that crosses midnight stays in the month it starts, including the minutes after midnight.

The hours board lists the current Taipei month. Every read week in that month counts. The reply names the first and last published day of that month. Other months stay out. Days that were never read stay out.

Your hours and rank come first. Under that, only the top five names for the month.

### Drop shift

The bot names who can take one of your shifts after today on that roster, including the next week when it has already been read. Today and earlier shifts stay out. One later shift is used as it is. Several shifts ask which one to drop. None replies "今天之後沒有可丟的班。"

A person qualifies when all three hold:

- The drop day is empty for them. A cross-day shift that lands on that day counts as work.
- At least 11 hours after the previous day's end, and at least 11 hours before the next day's start. A side with no shift counts as clear. The gap uses the real clock times, before the 0.5 hour cut.
- After taking the shift, they are on the schedule for at most 5 days that week.

Three-digit employee numbers are full-time staff. They stay out of the name list, lookups, the hours board, and this reply. Today's board still lists their nicknames and shift times.

The dropped shift's start time sets its type: 09:00–10:59 morning, 11:00–14:59 mid, 17:00–19:59 evening. A person uses the type that appears most often on the rosters already read. A tie, or any start outside those windows, is a floating shift. The reply keeps people of the dropped shift's type, mid-shift people, and floating-shift people. A dropped shift outside the three windows keeps mid-shift and floating-shift people. A floating shift is marked "（流動班別）". Mid-shift people appear once. An empty list replies "目前無合規人員可接班。" The menu asks for an employee number until this LINE account has looked one up.

# Prerequisites

- A [LINE Developers](https://developers.line.biz/) Messaging API channel, with a long-lived channel access token and a channel secret
- A [Gemini API key](https://aistudio.google.com/apikey)
- A Google account for a new [Apps Script](https://script.google.com/) project. That account owns the Drive files

# Install

1. In the Apps Script project, add `roster.gs` and `Code.gs`. Paste `gas/roster.js` and `gas/Code.js`. Replace the default `Code.gs` with that paste.
2. Project settings → show the manifest, then replace it with `gas/appsscript.json`.
3. Project settings → script properties:

| Property | Value |
| --- | --- |
| `LINE_CHANNEL_ACCESS_TOKEN` | The long-lived LINE token |
| `LINE_CHANNEL_SECRET` | The LINE channel secret |
| `GEMINI_API_KEY` | The AI Studio key |
| `GEMINI_MODEL` | Optional. Default `gemini-3.8-flash` |
| `ADMIN_LINE_USER_ID` | The admin's LINE userId. Until this is set, any message replies with your userId |
| `ROSTER_FOLDER_ID` | Drive folder ID from the folder URL, the part after `folders/` |

4. Select `authorize` and run it. Approve external connections, **Google Drive** (full Drive, including files the app did not create), and triggers. Run it again after a code or permission change.
5. Deploy → new deployment → web app. Execute as yourself. Who has access: anyone. Copy the URL. It ends in `/exec`.

On the channel's Messaging API tab:

1. Paste the `/exec` URL as the webhook and press Verify.
2. Turn on Use webhook.
3. Turn off auto-reply and the greeting, so they leave the bot's replies alone.
4. Add the official account from a phone.

After a code change, deploy again: manage deployments → edit → new version. The webhook URL stays. Paste the new `Code.gs` and `roster.gs`, then run `authorize` again.

# Usage

One current roster is shared. Only `ADMIN_LINE_USER_ID` can upload a PDF.

| Action | Effect |
| --- | --- |
| Admin sends a roster PDF | The bot says it received the file, then sends the employee list when reading finishes |
| Someone else sends a PDF or a photo | The bot asks for an employee number |
| Add the account, roster already read | The name list, then a prompt for an employee number |
| Add the account, roster still empty | "班表尚未更新。" |
| An employee number, such as `12345` | That person's shifts from today onward. Each shift is marked `TC` or `FL` and shows only the clock times. This LINE account is stored against that number. If next week is not read yet, the reply says so |
| `班表`, or any text that is not a number | The name list again |
| `排行榜` | Your rank and hours for the current month, then the top five |
| `丟換班` | Who can take one of your shifts after today |
| `今日班表` | Today's TC and FL. People on the same hours share a line. Full-time staff are included |
| The same PDF again | The stored roster is reused |

Set the bottom menu in the LINE console. The buttons send the text `排行榜`, `丟換班`, and `今日班表`.

# Settings

Script properties are the configuration.

- **LINE token and secret** come from the Messaging API channel. Use the long-lived token.
- **Gemini key** comes from AI Studio. Leave **model** empty to use `gemini-3.8-flash`.
- **Admin** is one LINE userId. Leave it empty, send the bot any message, and paste the userId from the reply.
- **Roster folder** is a Drive folder ID. Roster JSON and upload PDFs are created there. A roster already saved elsewhere moves into this folder the next time it is opened.
- **Webhook** is the web app `/exec` URL. Use webhook stays on. Auto-reply and the add-friend greeting stay off.
- **Menu** is a rich menu in the LINE console. The three buttons send `排行榜`, `丟換班`, and `今日班表`.

# LLM policy

This repository was developed with AI. The bot and this README were written with an AI coding assistant, then reviewed and kept by the maintainer.

AI-assisted contributions are fine. Say so in the pull request, keep the change small enough to review, and answer questions about it yourself.
