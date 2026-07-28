const config = window.CALENDAR_CONFIG || {};
const button = document.querySelector("#jz-subscribe");
const setupNote = document.querySelector("#jz-setup-note");
const calendarId = String(config.jzCalendarId || "").trim();
const isConfigured =
  calendarId && calendarId !== "REPLACE_WITH_PUBLIC_JZ_CALENDAR_ID";

if (isConfigured) {
  const query = new URLSearchParams({ cid: calendarId });
  button.href = `https://calendar.google.com/calendar/render?${query.toString()}`;
  button.target = "_blank";
  button.rel = "noopener noreferrer";
  button.removeAttribute("aria-disabled");
  setupNote.hidden = true;
} else {
  button.addEventListener("click", (event) => event.preventDefault());
}
